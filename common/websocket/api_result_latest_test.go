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
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/stretchr/testify/require"
)

func TestTaskResultEndpointReturnsLatestResult(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	require.NoError(t, tm.taskStore.CreateSession(&database.Session{
		ID:       "result-latest-session",
		Username: "api_user",
		TaskType: "mcp_scan",
		Content:  "test",
		Status:   TaskStatusDone,
	}))
	require.NoError(t, tm.taskStore.StoreEvent("old-result", "result-latest-session", "resultUpdate",
		map[string]any{"result": map[string]string{"value": "old"}}, 1))
	require.NoError(t, tm.taskStore.StoreEvent("new-result", "result-latest-session", "resultUpdate",
		map[string]any{"result": map[string]string{"value": "new"}}, 2))

	request := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/result/result-latest-session", nil)
	recorder := httptest.NewRecorder()
	newRouter(tm).ServeHTTP(recorder, request)
	require.Equal(t, http.StatusOK, recorder.Code)

	var response struct {
		Status int `json:"status"`
		Data   struct {
			Result struct {
				Value string `json:"value"`
			} `json:"result"`
		} `json:"data"`
	}
	require.NoError(t, json.Unmarshal(recorder.Body.Bytes(), &response))
	require.Equal(t, 0, response.Status)
	require.Equal(t, "new", response.Data.Result.Value)
}
