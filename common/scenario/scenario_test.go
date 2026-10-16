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

package scenario

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestLoadBuiltInScenarios(t *testing.T) {
	items, err := Load("../../data/scenarios")
	require.NoError(t, err)
	require.Len(t, items, 3)
	ids := make([]string, 0, len(items))
	for _, item := range items {
		ids = append(ids, item.ID)
		_, err := os.Stat(filepath.Join(item.Dir, "SKILL.md"))
		require.NoError(t, err)
	}
	require.Equal(t, []string{"gov-compliance", "model-prelaunch", "agent-security"}, ids)
	_, ok := ByID(items, "example-custom")
	require.False(t, ok)
}

func TestMissingAnyInput(t *testing.T) {
	item := Scenario{Needs: Needs{Model: true, Any: []string{"url", "code"}}}
	err := item.Missing(Input{HasModel: true}, "zh")
	require.Error(t, err)
	require.NoError(t, item.Missing(Input{HasModel: true, HasCode: true}, "zh"))
}
