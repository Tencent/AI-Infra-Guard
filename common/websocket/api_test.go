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

package websocket

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

// newTestTaskManager builds a minimal TaskManager backed by an in-memory DB.
func newTestTaskManager(t *testing.T) (*TaskManager, func()) {
	t.Helper()

	f, err := os.CreateTemp("", "ws-testdb-*.db")
	require.NoError(t, err)
	dbPath := f.Name()
	f.Close()

	cfg := database.NewConfig(dbPath)
	db, err := database.InitDB(cfg)
	require.NoError(t, err)

	ts := database.NewTaskStore(db)
	require.NoError(t, ts.Init())

	ms := database.NewModelStore(db)
	require.NoError(t, ms.Init())

	am := NewAgentManager()
	sseM := NewSSEManager()
	tm := NewTaskManager(am, ts, ms, nil, sseM)

	cleanup := func() {
		sqlDB, _ := db.DB()
		if sqlDB != nil {
			sqlDB.Close()
		}
		os.Remove(dbPath)
	}
	return tm, cleanup
}

// newRouter wires the three task-API handlers onto a minimal gin engine.
func newRouter(tm *TaskManager) *gin.Engine {
	r := gin.New()
	r.POST("/api/v1/app/taskapi/tasks", func(c *gin.Context) {
		SubmitTask(c, tm)
	})
	r.GET("/api/v1/app/taskapi/status/:id", func(c *gin.Context) {
		GetTaskStatus(c, tm)
	})
	r.GET("/api/v1/app/taskapi/result/:id", func(c *gin.Context) {
		GetTaskResult(c, tm)
	})
	return r
}

// postJSON sends a JSON POST and returns the recorder.
func postJSON(t *testing.T, r *gin.Engine, path string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	b, err := json.Marshal(body)
	require.NoError(t, err)
	req := httptest.NewRequest(http.MethodPost, path, bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	return w
}

// decodeAPIResponse decodes the response body into an APIResponse-like map.
func decodeAPIResponse(t *testing.T, w *httptest.ResponseRecorder) map[string]interface{} {
	t.Helper()
	var resp map[string]interface{}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &resp))
	return resp
}

// ---------------------------------------------------------------------------
// isValidSessionID (internal helper, white-box test)
// ---------------------------------------------------------------------------

func TestIsValidSessionID(t *testing.T) {
	cases := []struct {
		id    string
		valid bool
	}{
		{"abc123", true},
		{"abc-123_XYZ", true},
		{"a", true},
		// Exactly 50 chars – valid
		{"12345678901234567890123456789012345678901234567890", true},
		// 51 chars – invalid
		{"123456789012345678901234567890123456789012345678901", false},
		{"", false},
		{"has space", false},
		{"has/slash", false},
		{"has.dot", false},
		{"has@at", false},
	}
	for _, tc := range cases {
		t.Run(tc.id, func(t *testing.T) {
			assert.Equal(t, tc.valid, isValidSessionID(tc.id))
		})
	}
}

// ---------------------------------------------------------------------------
// SubmitTask – invalid / missing body
// ---------------------------------------------------------------------------

func TestSubmitTask_InvalidJSON(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/app/taskapi/tasks",
		bytes.NewBufferString("not-json"))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
}

func TestSubmitTask_InvalidTaskType(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	body := map[string]interface{}{
		"type":    "unknown_type",
		"content": map[string]interface{}{},
	}
	w := postJSON(t, r, "/api/v1/app/taskapi/tasks", body)
	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
	assert.Contains(t, resp["message"], "无效的任务类型")
}

func TestSubmitTask_MCPScan_MissingModelFields(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	// model.model and model.token are required for mcp_scan
	body := map[string]interface{}{
		"type": "mcp_scan",
		"content": map[string]interface{}{
			"prompt": "scan this",
			"model":  map[string]interface{}{}, // empty – missing required fields
		},
	}
	w := postJSON(t, r, "/api/v1/app/taskapi/tasks", body)
	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
	assert.Contains(t, resp["message"], "model.model")
}

func TestSubmitTask_MCPScan_MissingToken(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	body := map[string]interface{}{
		"type": "mcp_scan",
		"content": map[string]interface{}{
			"prompt": "scan this",
			"model": map[string]interface{}{
				"model": "gpt-4",
				// token intentionally omitted
			},
		},
	}
	w := postJSON(t, r, "/api/v1/app/taskapi/tasks", body)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
}

func TestSubmitTask_AIInfraScan_NoAgents(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	// ai_infra_scan is valid but no agents are registered → should fail at dispatch
	body := map[string]interface{}{
		"type": "ai_infra_scan",
		"content": map[string]interface{}{
			"target":  []string{"http://127.0.0.1:9999"},
			"timeout": 5,
		},
	}
	w := postJSON(t, r, "/api/v1/app/taskapi/tasks", body)
	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	// No agents available → status=1, message contains "Agent"
	assert.Equal(t, float64(1), resp["status"])
}

func TestSubmitTask_ModelRedteam_NoAgents(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	body := map[string]interface{}{
		"type": "model_redteam_report",
		"content": map[string]interface{}{
			"model": []map[string]interface{}{
				{"model": "gpt-4", "token": "sk-x", "base_url": "https://api.openai.com/v1"},
			},
			"eval_model": map[string]interface{}{
				"model": "gpt-4", "token": "sk-x",
			},
			"dataset": map[string]interface{}{
				"dataFile": []string{"JailBench-Tiny"}, "numPrompts": 10, "randomSeed": 42,
			},
		},
	}
	w := postJSON(t, r, "/api/v1/app/taskapi/tasks", body)
	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	// No agents → fail
	assert.Equal(t, float64(1), resp["status"])
}

func TestSubmitTask_AgentScan_EmptyAgentID(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	body := map[string]interface{}{
		"type": "agent_scan",
		"content": map[string]interface{}{
			"agent_id": "",
		},
	}
	w := postJSON(t, r, "/api/v1/app/taskapi/tasks", body)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
	assert.Contains(t, resp["message"], "agent_id")
}

// ---------------------------------------------------------------------------
// GetTaskStatus
// ---------------------------------------------------------------------------

func TestGetTaskStatus_EmptyID(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	// Gin will not match the route with empty param; test with placeholder
	req := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/status/", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	// No route match → 404
	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestGetTaskStatus_InvalidIDFormat(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/status/invalid@id!", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
	assert.Contains(t, resp["message"], "无效的任务ID格式")
}

func TestGetTaskStatus_NotFound(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/status/no-such-id", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
	assert.Contains(t, resp["message"], "任务不存在")
}

func TestGetTaskStatus_ExistingSession(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	// Seed DB directly
	require.NoError(t, tm.taskStore.CreateUser(&database.User{
		UserID: "api-u1", Username: "apiuser", Email: "api@t.com",
	}))
	require.NoError(t, tm.taskStore.CreateSession(&database.Session{
		ID:       "valid-session-id",
		Username: "apiuser",
		Title:    "Test API Task",
		TaskType: "ai_infra_scan",
		Content:  "http://127.0.0.1",
		Status:   "todo",
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/status/valid-session-id", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(0), resp["status"])
	data, ok := resp["data"].(map[string]interface{})
	require.True(t, ok)
	assert.Equal(t, "valid-session-id", data["session_id"])
	assert.Equal(t, "todo", data["status"])
}

// ---------------------------------------------------------------------------
// GetTaskResult
// ---------------------------------------------------------------------------

func TestGetTaskResult_InvalidIDFormat(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/result/bad-id-here!", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
	assert.Contains(t, resp["message"], "无效的任务ID格式")
}

func TestGetTaskResult_NoResults(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	// Session exists but no resultUpdate events
	require.NoError(t, tm.taskStore.CreateUser(&database.User{
		UserID: "api-u2", Username: "apiuser2", Email: "api2@t.com",
	}))
	require.NoError(t, tm.taskStore.CreateSession(&database.Session{
		ID:       "session-no-result",
		Username: "apiuser2",
		Title:    "Task without result",
		TaskType: "mcp_scan",
		Content:  "test",
		Status:   "doing",
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/result/session-no-result", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(1), resp["status"])
}

func TestGetTaskResult_WithResult(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()
	r := newRouter(tm)

	require.NoError(t, tm.taskStore.CreateUser(&database.User{
		UserID: "api-u3", Username: "apiuser3", Email: "api3@t.com",
	}))
	require.NoError(t, tm.taskStore.CreateSession(&database.Session{
		ID:       "session-with-result",
		Username: "apiuser3",
		Title:    "Done Task",
		TaskType: "ai_infra_scan",
		Content:  "test",
		Status:   "done",
	}))

	// Store a resultUpdate event
	resultPayload := map[string]interface{}{
		"findings": []string{"vuln-A", "vuln-B"},
		"score":    99,
	}
	eventJSON, err := json.Marshal(resultPayload)
	require.NoError(t, err)

	require.NoError(t, tm.taskStore.CreateTaskMessage(&database.TaskMessage{
		ID:        "result-ev-1",
		SessionID: "session-with-result",
		Type:      "resultUpdate",
		EventData: datatypes.JSON(eventJSON),
		Timestamp: 1000,
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/v1/app/taskapi/result/session-with-result", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	resp := decodeAPIResponse(t, w)
	assert.Equal(t, float64(0), resp["status"])
	data, ok := resp["data"].(map[string]interface{})
	require.True(t, ok)
	findings, ok := data["findings"].([]interface{})
	require.True(t, ok)
	assert.Len(t, findings, 2)
	assert.Equal(t, float64(99), data["score"])
}

// ---------------------------------------------------------------------------
// resolveTaskAPIUsername
// ---------------------------------------------------------------------------

func TestResolveTaskAPIUsername_Default(t *testing.T) {
	c, _ := gin.CreateTestContext(httptest.NewRecorder())
	c.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	assert.Equal(t, "api_user", resolveTaskAPIUsername(c))
}

func TestResolveTaskAPIUsername_FromHeader(t *testing.T) {
	c, _ := gin.CreateTestContext(httptest.NewRecorder())
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set("username", "header-user")
	c.Request = req
	assert.Equal(t, "header-user", resolveTaskAPIUsername(c))
}

func TestResolveTaskAPIUsername_FromContext(t *testing.T) {
	c, _ := gin.CreateTestContext(httptest.NewRecorder())
	c.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	c.Set("api_user", "ctx-user")
	assert.Equal(t, "ctx-user", resolveTaskAPIUsername(c))
}
