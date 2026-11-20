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
	"gorm.io/datatypes"
)

func TestTaskStatusEndpointUsesHeaderFields(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	session := &database.Session{
		ID:       "status-header-session",
		Username: "api_user",
		TaskType: "mcp_scan",
		Content:  "test",
		Title:    "status header title",
		Status:   TaskStatusDoing,
	}
	require.NoError(t, tm.taskStore.CreateSession(session))
	require.NoError(t, tm.taskStore.CreateTaskMessage(&database.TaskMessage{
		ID:        "message-1",
		SessionID: session.ID,
		Type:      "statusUpdate",
		EventData: datatypes.JSON([]byte(`{"agentStatus":"running"}`)),
		Timestamp: 1,
	}))

	request := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/status/"+session.ID, nil)
	recorder := httptest.NewRecorder()
	newRouter(tm).ServeHTTP(recorder, request)
	require.Equal(t, http.StatusOK, recorder.Code)

	var response struct {
		Status int `json:"status"`
		Data   struct {
			SessionID string `json:"session_id"`
			Status    string `json:"status"`
			Title     string `json:"title"`
			CreatedAt int64  `json:"created_at"`
			UpdatedAt int64  `json:"updated_at"`
		} `json:"data"`
	}
	require.NoError(t, json.Unmarshal(recorder.Body.Bytes(), &response))
	require.Equal(t, 0, response.Status)
	require.Equal(t, session.ID, response.Data.SessionID)
	require.Equal(t, TaskStatusDoing, response.Data.Status)
	require.Equal(t, session.Title, response.Data.Title)
	require.NotZero(t, response.Data.CreatedAt)
	require.NotZero(t, response.Data.UpdatedAt)
}
