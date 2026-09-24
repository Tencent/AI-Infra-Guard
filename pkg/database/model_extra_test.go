// Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Requirement: Any integration or derivative work must explicitly attribute
// Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
// documentation or user interface, as detailed in the NOTICE file.

package database

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestModelStoreKeepsAndClearsExtraFields(t *testing.T) {
	_, modelStore, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, modelStore.CreateModel(&Model{
		ModelID:      "extra-1",
		Username:     "u1",
		ModelName:    "gpt-test",
		Token:        "secret-token",
		BaseURL:      "https://api.example.com/v1",
		ExtraHeaders: map[string]string{"Authorization": "Bearer secret"},
		ExtraBody:    map[string]any{"provider.order": []string{"anthropic"}},
	}))

	stored, err := modelStore.GetModel("extra-1")
	require.NoError(t, err)
	assert.Equal(t, "Bearer secret", stored.ExtraHeaders["Authorization"])
	assert.NotNil(t, stored.ExtraBody["provider.order"])

	// 传空 map 表示清空：客户端要能删掉之前配置的头和请求体字段。
	require.NoError(t, modelStore.UpdateModel("extra-1", "u1", map[string]interface{}{
		"extra_headers": map[string]string{},
		"extra_body":    map[string]any{},
	}))

	cleared, err := modelStore.GetModel("extra-1")
	require.NoError(t, err)
	assert.Empty(t, cleared.ExtraHeaders)
	assert.Empty(t, cleared.ExtraBody)

	// 不传这两个字段则保持原值，只有显式的空 map 才是清空。
	require.NoError(t, modelStore.UpdateModel("extra-1", "u1", map[string]interface{}{
		"extra_headers": map[string]string{"X-Title": "kept"},
	}))
	require.NoError(t, modelStore.UpdateModel("extra-1", "u1", map[string]interface{}{
		"note": "only the note changed",
	}))

	kept, err := modelStore.GetModel("extra-1")
	require.NoError(t, err)
	assert.Equal(t, "only the note changed", kept.Note)
	assert.Equal(t, "kept", kept.ExtraHeaders["X-Title"])
}
