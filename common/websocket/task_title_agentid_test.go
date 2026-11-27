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

	"github.com/Tencent/AI-Infra-Guard/common/agent"
	"github.com/stretchr/testify/require"
)

// TestGenerateTaskTitleAgentScanNonStringID: params come straight from request
// JSON, so agent_id can be null (nil) or a number. Asserting .(string) on it
// panicked task creation; the title builder must tolerate it.
func TestGenerateTaskTitleAgentScanNonStringID(t *testing.T) {
	tm, cleanup := newTestTaskManager(t)
	defer cleanup()

	cases := []interface{}{nil, float64(42), "agent-1"}
	for _, agentID := range cases {
		req := &TaskCreateRequest{
			Task:   agent.TaskTypeAgentScan,
			Params: map[string]interface{}{"agent_id": agentID},
		}
		require.NotPanics(t, func() {
			_ = tm.generateTaskTitle(req)
		}, "agent_id=%v must not panic", agentID)
	}
}
