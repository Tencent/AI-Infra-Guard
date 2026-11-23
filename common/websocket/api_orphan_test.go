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
	"time"

	"github.com/stretchr/testify/require"
)

func TestAddTaskApiWithoutAgentsLeavesNoSession(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	req := &TaskCreateRequest{
		ID:        "message-1",
		SessionID: "orphan-session",
		Username:  "api_user",
		Task:      "mcp_scan",
		Content:   "test",
		Timestamp: time.Now().UnixMilli(),
	}
	require.Error(t, tm.AddTaskApi(req))

	_, err := tm.taskStore.GetSession(req.SessionID)
	require.Error(t, err, "failed task creation must not leave a session row")
}
