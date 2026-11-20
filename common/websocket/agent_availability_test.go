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

func TestGetAvailableAgentsRequiresRegistration(t *testing.T) {
	am := NewAgentManager()
	unregistered := NewAgentConnection(nil) // isActive defaults to true
	registered := &AgentConnection{agentID: "agent-1", isActive: true}
	inactive := &AgentConnection{agentID: "agent-2", isActive: false}
	am.connections["pending"] = unregistered
	am.connections["agent-1"] = registered
	am.connections["agent-2"] = inactive

	agents := am.GetAvailableAgents()
	if len(agents) != 1 || agents[0] != registered {
		t.Fatalf("available agents = %d, want only the registered connection", len(agents))
	}
}
