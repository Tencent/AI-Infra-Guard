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

package database

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// newTestDB creates an in-memory SQLite DB for testing.
func newTestDB(t *testing.T) (*TaskStore, *ModelStore, func()) {
	t.Helper()

	// Use a temp file-based DB (pure in-memory ":memory:" doesn't work well
	// with glebarez/sqlite + shared cache, so use a temp file instead).
	f, err := os.CreateTemp("", "testdb-*.db")
	require.NoError(t, err)
	dbPath := f.Name()
	f.Close()

	cfg := NewConfig(dbPath)
	db, err := InitDB(cfg)
	require.NoError(t, err)

	ts := NewTaskStore(db)
	require.NoError(t, ts.Init())

	ms := NewModelStore(db)
	require.NoError(t, ms.Init())

	cleanup := func() {
		sqlDB, _ := db.DB()
		if sqlDB != nil {
			sqlDB.Close()
		}
		os.Remove(dbPath)
	}
	return ts, ms, cleanup
}

// ---------------------------------------------------------------------------
// InitDB / Config
// ---------------------------------------------------------------------------

func TestInitDB_InMemory(t *testing.T) {
	f, err := os.CreateTemp("", "testdb-init-*.db")
	require.NoError(t, err)
	dbPath := f.Name()
	f.Close()
	defer os.Remove(dbPath)

	cfg := NewConfig(dbPath)
	assert.Equal(t, dbPath, cfg.DBPath)

	db, err := InitDB(cfg)
	require.NoError(t, err)
	assert.NotNil(t, db)

	sqlDB, err := db.DB()
	require.NoError(t, err)
	assert.NoError(t, sqlDB.Ping())
	sqlDB.Close()
}

func TestNewConfig(t *testing.T) {
	cfg := NewConfig("/tmp/test.db")
	assert.Equal(t, "/tmp/test.db", cfg.DBPath)
}

func TestLoadConfigFromEnv_Default(t *testing.T) {
	os.Unsetenv("DB_PATH")
	cfg := LoadConfigFromEnv()
	assert.Equal(t, "db/tasks.db", cfg.DBPath)
}

func TestLoadConfigFromEnv_Override(t *testing.T) {
	os.Setenv("DB_PATH", "/tmp/override.db")
	defer os.Unsetenv("DB_PATH")
	cfg := LoadConfigFromEnv()
	assert.Equal(t, "/tmp/override.db", cfg.DBPath)
}

// ---------------------------------------------------------------------------
// TaskStore.Init
// ---------------------------------------------------------------------------

func TestTaskStore_Init(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()
	// Calling Init twice should be idempotent
	assert.NoError(t, ts.Init())
}

// ---------------------------------------------------------------------------
// TaskStore – User operations
// ---------------------------------------------------------------------------

func TestTaskStore_CreateAndGetUser(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	u := &User{
		UserID:   "u-001",
		Username: "alice",
		Email:    "alice@example.com",
		IsActive: true,
	}
	require.NoError(t, ts.CreateUser(u))
	assert.Greater(t, u.CreatedAt, int64(0))

	got, err := ts.GetUser("alice")
	require.NoError(t, err)
	assert.Equal(t, "alice", got.Username)
	assert.Equal(t, "alice@example.com", got.Email)
}

func TestTaskStore_GetUserByEmail(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	u := &User{UserID: "u-002", Username: "bob", Email: "bob@example.com"}
	require.NoError(t, ts.CreateUser(u))

	got, err := ts.GetUserByEmail("bob@example.com")
	require.NoError(t, err)
	assert.Equal(t, "bob", got.Username)
}

func TestTaskStore_GetUser_NotFound(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	_, err := ts.GetUser("nonexistent")
	assert.Error(t, err)
}

func TestTaskStore_CheckUserExists(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	u := &User{UserID: "u-003", Username: "charlie", Email: "charlie@example.com"}
	require.NoError(t, ts.CreateUser(u))

	exists, err := ts.CheckUserExists("charlie@example.com")
	require.NoError(t, err)
	assert.True(t, exists)

	exists, err = ts.CheckUserExists("nobody@example.com")
	require.NoError(t, err)
	assert.False(t, exists)
}

func TestTaskStore_DeleteUser(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	u := &User{UserID: "u-004", Username: "dave", Email: "dave@example.com"}
	require.NoError(t, ts.CreateUser(u))
	require.NoError(t, ts.DeleteUser("dave@example.com"))

	exists, err := ts.CheckUserExists("dave@example.com")
	require.NoError(t, err)
	assert.False(t, exists)
}

func TestTaskStore_UpdateUserFirstLogin(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	u := &User{UserID: "u-005", Username: "eve", Email: "eve@example.com", FirstLogin: true}
	require.NoError(t, ts.CreateUser(u))

	require.NoError(t, ts.UpdateUserFirstLogin("eve", false))

	got, err := ts.GetUser("eve")
	require.NoError(t, err)
	assert.False(t, got.FirstLogin)
}

// ---------------------------------------------------------------------------
// TaskStore – Session (CreateSession / GetSession / UpdateSession / ListSessions)
// ---------------------------------------------------------------------------

func newTestSession(id, username, taskType string) *Session {
	return &Session{
		ID:       id,
		Username: username,
		Title:    "Test session " + id,
		TaskType: taskType,
		Content:  "test content",
		Status:   "todo",
	}
}

func TestTaskStore_CreateSession(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	// Need a user first (foreign key)
	require.NoError(t, ts.CreateUser(&User{UserID: "u1", Username: "testuser", Email: "t@t.com"}))

	s := newTestSession("sess-001", "testuser", "ai_infra_scan")
	require.NoError(t, ts.CreateSession(s))
	assert.Greater(t, s.CreatedAt, int64(0))
	assert.Greater(t, s.UpdatedAt, int64(0))
}

func TestTaskStore_GetSession(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u2", Username: "user2", Email: "u2@t.com"}))
	s := newTestSession("sess-002", "user2", "mcp_scan")
	require.NoError(t, ts.CreateSession(s))

	got, err := ts.GetSession("sess-002")
	require.NoError(t, err)
	assert.Equal(t, "sess-002", got.ID)
	assert.Equal(t, "mcp_scan", got.TaskType)
	assert.Equal(t, "todo", got.Status)
}

func TestTaskStore_GetSession_NotFound(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	_, err := ts.GetSession("does-not-exist")
	assert.Error(t, err)
}

func TestTaskStore_UpdateSessionStatus(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u3", Username: "user3", Email: "u3@t.com"}))
	s := newTestSession("sess-003", "user3", "ai_infra_scan")
	require.NoError(t, ts.CreateSession(s))

	require.NoError(t, ts.UpdateSessionStatus("sess-003", "doing"))
	got, err := ts.GetSession("sess-003")
	require.NoError(t, err)
	assert.Equal(t, "doing", got.Status)
	assert.NotNil(t, got.StartedAt)

	require.NoError(t, ts.UpdateSessionStatus("sess-003", "done"))
	got, err = ts.GetSession("sess-003")
	require.NoError(t, err)
	assert.Equal(t, "done", got.Status)
	assert.NotNil(t, got.CompletedAt)
}

func TestTaskStore_UpdateSession(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u4", Username: "user4", Email: "u4@t.com"}))
	s := newTestSession("sess-004", "user4", "ai_infra_scan")
	require.NoError(t, ts.CreateSession(s))

	require.NoError(t, ts.UpdateSession("sess-004", map[string]interface{}{"title": "Updated Title"}))
	got, err := ts.GetSession("sess-004")
	require.NoError(t, err)
	assert.Equal(t, "Updated Title", got.Title)
}

func TestTaskStore_DeleteSession(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u5", Username: "user5", Email: "u5@t.com"}))
	s := newTestSession("sess-005", "user5", "ai_infra_scan")
	require.NoError(t, ts.CreateSession(s))

	require.NoError(t, ts.DeleteSession("sess-005"))
	_, err := ts.GetSession("sess-005")
	assert.Error(t, err)
}

func TestTaskStore_ListSessions(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u6", Username: "user6", Email: "u6@t.com"}))
	for i, id := range []string{"sess-a", "sess-b", "sess-c"} {
		s := newTestSession(id, "user6", "mcp_scan")
		s.Title = "Session " + string(rune('A'+i))
		require.NoError(t, ts.CreateSession(s))
	}

	sessions, err := ts.GetUserSessions("user6")
	require.NoError(t, err)
	assert.Len(t, sessions, 3)
}

func TestTaskStore_GetUserSessionsByType(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u7", Username: "user7", Email: "u7@t.com"}))
	require.NoError(t, ts.CreateSession(newTestSession("s7-1", "user7", "mcp_scan")))
	require.NoError(t, ts.CreateSession(newTestSession("s7-2", "user7", "ai_infra_scan")))
	require.NoError(t, ts.CreateSession(newTestSession("s7-3", "user7", "mcp_scan")))

	mcpSessions, err := ts.GetUserSessionsByType("user7", "mcp_scan")
	require.NoError(t, err)
	assert.Len(t, mcpSessions, 2)

	allSessions, err := ts.GetUserSessionsByType("user7", "")
	require.NoError(t, err)
	assert.Len(t, allSessions, 3)
}

func TestTaskStore_SetShare(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u8", Username: "user8", Email: "u8@t.com"}))
	s := newTestSession("sess-share", "user8", "mcp_scan")
	require.NoError(t, ts.CreateSession(s))

	require.NoError(t, ts.SetShare("sess-share", true))
	got, err := ts.GetSession("sess-share")
	require.NoError(t, err)
	assert.True(t, got.Share)
}

func TestTaskStore_DeleteSessionWithMessages(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u9", Username: "user9", Email: "u9@t.com"}))
	s := newTestSession("sess-del", "user9", "ai_infra_scan")
	require.NoError(t, ts.CreateSession(s))

	// Add a message
	require.NoError(t, ts.StoreEvent("msg-1", "sess-del", "liveStatus", map[string]string{"text": "hello"}, 1000))

	require.NoError(t, ts.DeleteSessionWithMessages("sess-del"))
	_, err := ts.GetSession("sess-del")
	assert.Error(t, err)

	msgs, err := ts.GetSessionMessages("sess-del")
	require.NoError(t, err)
	assert.Empty(t, msgs)
}

func TestTaskStore_ResetRunningTasks(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u10", Username: "user10", Email: "u10@t.com"}))
	s := newTestSession("sess-run", "user10", "mcp_scan")
	s.Status = "doing"
	require.NoError(t, ts.CreateSession(s))

	require.NoError(t, ts.ResetRunningTasks())

	got, err := ts.GetSession("sess-run")
	require.NoError(t, err)
	assert.Equal(t, "error", got.Status)
}

func TestTaskStore_SearchUserSessionsSimple(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u11", Username: "srchuser", Email: "srch@t.com"}))
	s1 := newTestSession("srch-1", "srchuser", "mcp_scan")
	s1.Title = "important scan"
	require.NoError(t, ts.CreateSession(s1))

	s2 := newTestSession("srch-2", "srchuser", "ai_infra_scan")
	s2.Title = "other task"
	require.NoError(t, ts.CreateSession(s2))

	// Search by keyword
	results, total, err := ts.SearchUserSessionsSimple("srchuser", SimpleSearchParams{
		Query: "important", Page: 1, PageSize: 10,
	})
	require.NoError(t, err)
	assert.Equal(t, int64(1), total)
	assert.Len(t, results, 1)
	assert.Equal(t, "srch-1", results[0].ID)

	// Search with task type filter
	results, total, err = ts.SearchUserSessionsSimple("srchuser", SimpleSearchParams{
		TaskType: "ai_infra_scan", Page: 1, PageSize: 10,
	})
	require.NoError(t, err)
	assert.Equal(t, int64(1), total)
	assert.Equal(t, "ai_infra_scan", results[0].TaskType)
}

// ---------------------------------------------------------------------------
// TaskStore – Messages (AddMessage / GetMessages)
// ---------------------------------------------------------------------------

func TestTaskStore_AddAndGetMessages(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u12", Username: "msguser", Email: "msg@t.com"}))
	require.NoError(t, ts.CreateSession(newTestSession("msg-sess", "msguser", "mcp_scan")))

	require.NoError(t, ts.StoreEvent("ev-1", "msg-sess", "liveStatus", map[string]string{"text": "starting"}, 1000))
	require.NoError(t, ts.StoreEvent("ev-2", "msg-sess", "actionLog", map[string]string{"actionLog": "step 1"}, 2000))
	require.NoError(t, ts.StoreEvent("ev-3", "msg-sess", "resultUpdate", map[string]interface{}{"result": 42}, 3000))

	msgs, err := ts.GetSessionMessages("msg-sess")
	require.NoError(t, err)
	assert.Len(t, msgs, 3)

	// Should be ordered by timestamp ASC
	assert.Equal(t, "ev-1", msgs[0].ID)
	assert.Equal(t, "ev-2", msgs[1].ID)
	assert.Equal(t, "ev-3", msgs[2].ID)
}

func TestTaskStore_GetSessionEventsByType(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u13", Username: "typeuser", Email: "type@t.com"}))
	require.NoError(t, ts.CreateSession(newTestSession("type-sess", "typeuser", "mcp_scan")))

	require.NoError(t, ts.StoreEvent("t1", "type-sess", "liveStatus", map[string]string{"text": "a"}, 100))
	require.NoError(t, ts.StoreEvent("t2", "type-sess", "actionLog", map[string]string{"actionLog": "b"}, 200))
	require.NoError(t, ts.StoreEvent("t3", "type-sess", "liveStatus", map[string]string{"text": "c"}, 300))

	lsEvents, err := ts.GetSessionEventsByType("type-sess", "liveStatus")
	require.NoError(t, err)
	assert.Len(t, lsEvents, 2)

	alEvents, err := ts.GetSessionEventsByType("type-sess", "actionLog")
	require.NoError(t, err)
	assert.Len(t, alEvents, 1)
}

func TestTaskStore_CreateTaskMessage(t *testing.T) {
	ts, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "u14", Username: "tmuser", Email: "tm@t.com"}))
	require.NoError(t, ts.CreateSession(newTestSession("tm-sess", "tmuser", "mcp_scan")))

	msg := &TaskMessage{
		ID:        "manual-msg",
		SessionID: "tm-sess",
		Type:      "planUpdate",
		EventData: []byte(`{"tasks":[]}`),
		Timestamp: 999,
	}
	require.NoError(t, ts.CreateTaskMessage(msg))
	assert.Greater(t, msg.CreatedAt, int64(0))

	msgs, err := ts.GetSessionEvents("tm-sess")
	require.NoError(t, err)
	assert.Len(t, msgs, 1)
	assert.Equal(t, "manual-msg", msgs[0].ID)
}

// ---------------------------------------------------------------------------
// ModelStore – Init, basic CRUD
// ---------------------------------------------------------------------------

func TestModelStore_Init(t *testing.T) {
	_, ms, cleanup := newTestDB(t)
	defer cleanup()
	// Calling Init twice should be idempotent
	assert.NoError(t, ms.Init())
}

func TestModelStore_CreateAndGetModel(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu1", Username: "muser1", Email: "muser1@t.com"}))

	m := &Model{
		ModelID:   "model-001",
		Username:  "muser1",
		ModelName: "gpt-4",
		Token:     "sk-test",
		BaseURL:   "https://api.openai.com/v1",
	}
	require.NoError(t, ms.CreateModel(m))
	assert.Greater(t, m.CreatedAt, int64(0))
	assert.Greater(t, m.UpdatedAt, int64(0))

	got, err := ms.GetModel("model-001")
	require.NoError(t, err)
	assert.Equal(t, "gpt-4", got.ModelName)
	assert.Equal(t, "sk-test", got.Token)
}

func TestModelStore_GetModel_NotFound(t *testing.T) {
	_, ms, cleanup := newTestDB(t)
	defer cleanup()

	_, err := ms.GetModel("nonexistent-model")
	assert.Error(t, err)
}

func TestModelStore_GetModelByUser(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu2", Username: "muser2", Email: "muser2@t.com"}))
	m := &Model{
		ModelID:   "model-002",
		Username:  "muser2",
		ModelName: "gpt-3.5",
		Token:     "sk-test2",
		BaseURL:   "https://api.openai.com/v1",
	}
	require.NoError(t, ms.CreateModel(m))

	got, err := ms.GetModelByUser("model-002", "muser2")
	require.NoError(t, err)
	assert.Equal(t, "gpt-3.5", got.ModelName)

	_, err = ms.GetModelByUser("model-002", "wronguser")
	assert.Error(t, err)
}

func TestModelStore_GetAllModels(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu3", Username: "muser3", Email: "muser3@t.com"}))
	for i, id := range []string{"m1", "m2", "m3"} {
		require.NoError(t, ms.CreateModel(&Model{
			ModelID:   id,
			Username:  "muser3",
			ModelName: "model-" + string(rune('A'+i)),
			Token:     "tok",
			BaseURL:   "https://example.com",
		}))
	}

	all, err := ms.GetAllModels()
	require.NoError(t, err)
	assert.Len(t, all, 3)
}

func TestModelStore_UpdateModel(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu4", Username: "muser4", Email: "muser4@t.com"}))
	require.NoError(t, ms.CreateModel(&Model{
		ModelID:   "model-upd",
		Username:  "muser4",
		ModelName: "old-model",
		Token:     "tok",
		BaseURL:   "https://example.com",
	}))

	require.NoError(t, ms.UpdateModel("model-upd", "muser4", map[string]interface{}{"model_name": "new-model"}))
	got, err := ms.GetModel("model-upd")
	require.NoError(t, err)
	assert.Equal(t, "new-model", got.ModelName)
}

func TestModelStore_DeleteModel(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu5", Username: "muser5", Email: "muser5@t.com"}))
	require.NoError(t, ms.CreateModel(&Model{
		ModelID:   "model-del",
		Username:  "muser5",
		ModelName: "to-delete",
		Token:     "tok",
		BaseURL:   "https://example.com",
	}))

	require.NoError(t, ms.DeleteModel("model-del", "muser5"))

	exists, err := ms.CheckModelExists("model-del")
	require.NoError(t, err)
	assert.False(t, exists)
}

func TestModelStore_BatchDeleteModels(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu6", Username: "muser6", Email: "muser6@t.com"}))
	ids := []string{"bm1", "bm2", "bm3"}
	for _, id := range ids {
		require.NoError(t, ms.CreateModel(&Model{
			ModelID:   id,
			Username:  "muser6",
			ModelName: id,
			Token:     "tok",
			BaseURL:   "https://example.com",
		}))
	}

	n, err := ms.BatchDeleteModels(ids, "muser6")
	require.NoError(t, err)
	assert.Equal(t, int64(3), n)
}

func TestModelStore_CheckModelExists(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu7", Username: "muser7", Email: "muser7@t.com"}))
	require.NoError(t, ms.CreateModel(&Model{
		ModelID:   "model-chk",
		Username:  "muser7",
		ModelName: "chk",
		Token:     "tok",
		BaseURL:   "https://example.com",
	}))

	exists, err := ms.CheckModelExists("model-chk")
	require.NoError(t, err)
	assert.True(t, exists)

	exists, err = ms.CheckModelExists("nope")
	require.NoError(t, err)
	assert.False(t, exists)
}

func TestModelStore_CheckModelExistsByUser(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu8", Username: "muser8", Email: "muser8@t.com"}))
	require.NoError(t, ms.CreateModel(&Model{
		ModelID:   "model-u",
		Username:  "muser8",
		ModelName: "u",
		Token:     "tok",
		BaseURL:   "https://example.com",
	}))

	exists, err := ms.CheckModelExistsByUser("model-u", "muser8")
	require.NoError(t, err)
	assert.True(t, exists)

	exists, err = ms.CheckModelExistsByUser("model-u", "other")
	require.NoError(t, err)
	assert.False(t, exists)
}

func TestModelStore_GetUserModels(t *testing.T) {
	ts, ms, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, ts.CreateUser(&User{UserID: "mu9", Username: "muser9", Email: "muser9@t.com"}))
	for _, id := range []string{"um1", "um2"} {
		require.NoError(t, ms.CreateModel(&Model{
			ModelID:   id,
			Username:  "muser9",
			ModelName: id,
			Token:     "tok",
			BaseURL:   "https://example.com",
		}))
	}

	models, err := ms.GetUserModels("muser9")
	require.NoError(t, err)
	// At least the two created (yaml models may also appear if file exists)
	assert.GreaterOrEqual(t, len(models), 2)
}
