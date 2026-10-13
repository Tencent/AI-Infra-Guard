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

package websocket

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"
)

// newModelAPITestStore 建一个临时库并返回 ModelStore，用完删除文件。
func newModelAPITestStore(t *testing.T) *database.ModelStore {
	t.Helper()

	dbPath := filepath.Join(t.TempDir(), "model-api-test.db")
	db, err := database.InitDB(database.NewConfig(dbPath))
	require.NoError(t, err)

	// GetModel 会 Preload("User")，所以 users 表也要建起来（由 TaskStore 负责迁移）
	taskStore := database.NewTaskStore(db)
	require.NoError(t, taskStore.Init())

	store := database.NewModelStore(db)
	require.NoError(t, store.Init())

	t.Cleanup(func() {
		sqlDB, err := db.DB()
		if err == nil && sqlDB != nil {
			_ = sqlDB.Close()
		}
		_ = os.Remove(dbPath)
	})

	return store
}

// TestHandleUpdateModelKeepsMaskedExtraFields 覆盖“前端把掩码值原样回传”的场景。
//
// GET 接口返回的 extra_headers / extra_body 是掩码后的值，编辑表单会把它填回
// 输入框。如果更新接口直接写库，******** 就会变成真实请求头，用户的密钥被覆盖。
func TestHandleUpdateModelKeepsMaskedExtraFields(t *testing.T) {
	store := newModelAPITestStore(t)

	require.NoError(t, store.CreateModel(&database.Model{
		ModelID:      "m1",
		Username:     "u1",
		ModelName:    "gpt-test",
		Token:        "sk-real-token",
		BaseURL:      "https://api.example.com/v1",
		Note:         "origin",
		Limit:        10,
		ExtraHeaders: map[string]string{"Authorization": "Bearer real-secret"},
		ExtraBody:    map[string]any{"provider.order": []any{"anthropic"}},
	}))

	body := map[string]any{
		"model": map[string]any{
			"model":    "gpt-test",
			"token":    maskedToken,
			"base_url": "https://api.example.com/v1",
			"note":     "edited",
			"limit":    10,
			"extra_headers": map[string]string{
				"Authorization": maskedToken, // 未改动：必须沿用原值
				"X-Title":       "AI-Infra-Guard",
			},
			"extra_body": map[string]any{
				"provider.order": maskedToken, // 未改动：必须沿用原值
			},
		},
	}
	raw, err := json.Marshal(body)
	require.NoError(t, err)

	gin.SetMode(gin.TestMode)
	recorder := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(recorder)
	c.Request = httptest.NewRequest(http.MethodPut, "/api/v1/models/m1", bytes.NewReader(raw))
	c.Request.Header.Set("Content-Type", "application/json")
	c.Params = gin.Params{{Key: "modelId", Value: "m1"}}
	c.Set("username", "u1")

	HandleUpdateModel(c, NewModelManager(store))

	var resp struct {
		Status int `json:"status"`
	}
	require.NoError(t, json.Unmarshal(recorder.Body.Bytes(), &resp))
	require.Equal(t, 0, resp.Status, "更新应成功: %s", recorder.Body.String())

	stored, err := store.GetModel("m1")
	require.NoError(t, err)

	// 被掩码的键保持原值，密钥没有被 ******** 覆盖
	assert.Equal(t, "Bearer real-secret", stored.ExtraHeaders["Authorization"])
	assert.Equal(t, []any{"anthropic"}, stored.ExtraBody["provider.order"])
	assert.Equal(t, "sk-real-token", stored.Token)

	// 真正新增/修改的部分正常写入
	assert.Equal(t, "AI-Infra-Guard", stored.ExtraHeaders["X-Title"])
	assert.Equal(t, "edited", stored.Note)
}

// TestHandleUpdateModelPlainFieldsAreNotTouched 确认没有掩码值时不会额外读库或改动字段。
func TestHandleUpdateModelPlainFieldsAreNotTouched(t *testing.T) {
	store := newModelAPITestStore(t)

	require.NoError(t, store.CreateModel(&database.Model{
		ModelID:      "m2",
		Username:     "u1",
		ModelName:    "gpt-test",
		Token:        "sk-real-token",
		BaseURL:      "https://api.example.com/v1",
		Note:         "origin",
		Limit:        10,
		ExtraHeaders: map[string]string{"Authorization": "Bearer keep-me"},
	}))

	body := map[string]any{
		"model": map[string]any{
			"model":    "gpt-test",
			"token":    maskedToken,
			"base_url": "https://api.example.com/v1",
			"note":     "changed",
			"limit":    20,
		},
	}
	raw, err := json.Marshal(body)
	require.NoError(t, err)

	gin.SetMode(gin.TestMode)
	recorder := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(recorder)
	c.Request = httptest.NewRequest(http.MethodPut, "/api/v1/models/m2", bytes.NewReader(raw))
	c.Request.Header.Set("Content-Type", "application/json")
	c.Params = gin.Params{{Key: "modelId", Value: "m2"}}
	c.Set("username", "u1")

	HandleUpdateModel(c, NewModelManager(store))

	var resp struct {
		Status int `json:"status"`
	}
	require.NoError(t, json.Unmarshal(recorder.Body.Bytes(), &resp))
	require.Equal(t, 0, resp.Status, "更新应成功: %s", recorder.Body.String())

	stored, err := store.GetModel("m2")
	require.NoError(t, err)
	assert.Equal(t, "Bearer keep-me", stored.ExtraHeaders["Authorization"], "未提交 extra_headers 时不应改动")
	assert.Equal(t, "changed", stored.Note)
	assert.Equal(t, 20, stored.Limit)
}
