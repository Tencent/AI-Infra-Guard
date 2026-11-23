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

import "testing"

func TestRemoveConnectionIfCurrentKeepsSSEReplacement(t *testing.T) {
	sm := NewSSEManager()
	oldConn := &SSEConnection{SessionID: "sse-1", CloseChan: make(chan bool)}
	replacement := &SSEConnection{SessionID: "sse-1", CloseChan: make(chan bool)}
	sm.connections["sse-1"] = replacement

	if sm.removeConnectionIfCurrent("sse-1", oldConn) {
		t.Fatal("old connection removed a replacement")
	}
	if got := sm.connections["sse-1"]; got != replacement {
		t.Fatal("replacement SSE connection was removed")
	}
	select {
	case <-replacement.CloseChan:
		t.Fatal("replacement connection was closed")
	default:
	}

	if !sm.removeConnectionIfCurrent("sse-1", replacement) {
		t.Fatal("current connection was not removed")
	}
	if _, exists := sm.connections["sse-1"]; exists {
		t.Fatal("current connection remains in the map")
	}
	select {
	case <-replacement.CloseChan:
	default:
		t.Fatal("current connection was not closed")
	}
}
