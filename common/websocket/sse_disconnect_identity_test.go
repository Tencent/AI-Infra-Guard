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
	"testing"

	"github.com/stretchr/testify/require"
)

// TestSSEDisconnectKeepsReplacement reproduces the handler-teardown race that
// #792 did not cover: AddConnection replaces an SSE stream on reconnect, but the
// old request handler only returns when its own client disconnects. If that
// teardown removes the session by ID, it deletes the live replacement and the
// browser stops receiving events while the task keeps running.
func TestSSEDisconnectKeepsReplacement(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	conn1, err := tm.EstablishSSEConnection(&overlapWriter{}, "sess-1", "alice", "test")
	require.NoError(t, err)

	conn2, err := tm.EstablishSSEConnection(&overlapWriter{}, "sess-1", "alice", "test")
	require.NoError(t, err)
	require.NotSame(t, conn1, conn2)

	// The first client's request context finishes after the second already
	// reconnected; its teardown must not remove the live stream.
	tm.CloseSSESessionIfCurrent("sess-1", conn1)

	if !tm.sseManager.HasConnection("sess-1") {
		t.Fatal("old handler teardown removed the replacement SSE connection")
	}
	require.NoError(t, tm.sseManager.SendEvent("evt-1", "sess-1", "liveStatus", map[string]string{"k": "v"}))

	// The replacement's own teardown still removes it.
	tm.CloseSSESessionIfCurrent("sess-1", conn2)
	if tm.sseManager.HasConnection("sess-1") {
		t.Fatal("current connection should have been removed by its own teardown")
	}
}
