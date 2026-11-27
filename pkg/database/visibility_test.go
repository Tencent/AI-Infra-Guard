package database

import (
	"os"
	"testing"

	"github.com/stretchr/testify/require"
)

func newVisibilityStore(t *testing.T) (*TaskStore, func()) {
	t.Helper()
	f, err := os.CreateTemp("", "aig-vis-*.db")
	require.NoError(t, err)
	f.Close()
	db, err := InitDB(NewConfig(f.Name()))
	require.NoError(t, err)
	ts := NewTaskStore(db)
	require.NoError(t, ts.Init())
	return ts, func() {
		if sqlDB, e := db.DB(); e == nil && sqlDB != nil {
			sqlDB.Close()
		}
		os.Remove(f.Name())
	}
}

func TestVisibleSessionsExcludesReverify(t *testing.T) {
	ts, cleanup := newVisibilityStore(t)
	defer cleanup()

	require.NoError(t, ts.CreateSession(&Session{ID: "n1", Username: "alice", Content: "x", RescanKind: "normal", Status: "done"}))
	require.NoError(t, ts.CreateSession(&Session{ID: "r1", Username: "alice", Content: "x", RescanKind: "reverify", Status: "done"}))

	sessions, err := ts.GetUserSessions("alice")
	require.NoError(t, err)
	ids := map[string]bool{}
	for _, s := range sessions {
		ids[s.ID] = true
	}
	require.True(t, ids["n1"], "normal task must be visible")
	require.False(t, ids["r1"], "reverify derived task must be hidden")

	// Non-empty query exercises the parenthesized LIKE-OR path with the hidden row.
	res, _, err := ts.SearchUserSessionsSimple("alice", SimpleSearchParams{Query: "x", Page: 1, PageSize: 10})
	require.NoError(t, err)
	seen := map[string]bool{}
	for _, s := range res {
		seen[s.ID] = true
	}
	require.True(t, seen["n1"], "normal task should match search")
	require.False(t, seen["r1"], "reverify derived task must not appear in search")
}
