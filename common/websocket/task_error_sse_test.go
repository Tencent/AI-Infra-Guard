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
	"net/http/httptest"
	"testing"
	"time"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/stretchr/testify/require"
)

func TestErrorEventClosesSSESession(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	session := &database.Session{
		ID:            "error-sse-session",
		Username:      "public_user",
		TaskType:      "mcp_scan",
		Content:       "test",
		Status:        TaskStatusDoing,
		AssignedAgent: "agent-1",
		Share:         true,
	}
	require.NoError(t, tm.taskStore.CreateSession(session))

	rec := httptest.NewRecorder()
	closed := make(chan bool)
	tm.sseManager.connections[session.ID] = &SSEConnection{
		SessionID: session.ID,
		Writer:    rec,
		Flusher:   rec,
		CloseChan: closed,
	}

	tm.HandleAgentEvent(session.ID, "error", map[string]string{"message": "boom"})

	deadline := time.Now().Add(time.Second)
	for time.Now().Before(deadline) {
		if _, exists := tm.sseManager.connections[session.ID]; !exists {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	if _, exists := tm.sseManager.connections[session.ID]; exists {
		t.Fatal("terminal error task left its SSE connection registered")
	}
	select {
	case <-closed:
	default:
		t.Fatal("terminal error task did not close its SSE connection")
	}

	status, err := tm.taskStore.GetSessionStatus(session.ID)
	require.NoError(t, err)
	require.Equal(t, TaskStatusError, status)
}
