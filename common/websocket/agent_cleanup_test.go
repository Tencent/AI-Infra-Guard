package websocket

import "testing"

func TestRemoveConnectionIfCurrentKeepsReplacement(t *testing.T) {
	am := NewAgentManager()
	oldConn := &AgentConnection{agentID: "agent-1"}
	replacement := &AgentConnection{agentID: "agent-1"}
	am.connections["agent-1"] = replacement

	removed, replaced := am.removeConnectionIfCurrent("agent-1", oldConn)
	if removed || !replaced {
		t.Fatalf("removed=%v replaced=%v, want false/true", removed, replaced)
	}
	if got := am.connections["agent-1"]; got != replacement {
		t.Fatal("replacement connection was removed by the old connection's cleanup")
	}
}

func TestRemoveConnectionIfCurrentRemovesOwnEntry(t *testing.T) {
	am := NewAgentManager()
	conn := &AgentConnection{agentID: "agent-1"}
	am.connections["agent-1"] = conn

	removed, replaced := am.removeConnectionIfCurrent("agent-1", conn)
	if !removed || replaced {
		t.Fatalf("removed=%v replaced=%v, want true/false", removed, replaced)
	}
	if _, exists := am.connections["agent-1"]; exists {
		t.Fatal("connection still registered after cleanup")
	}
}

func TestRemoveConnectionIfCurrentMissingEntry(t *testing.T) {
	am := NewAgentManager()
	removed, replaced := am.removeConnectionIfCurrent("agent-1", &AgentConnection{agentID: "agent-1"})
	if removed || replaced {
		t.Fatalf("removed=%v replaced=%v, want false/false", removed, replaced)
	}
}

func TestCurrentAgentIDReadsRegisteredValue(t *testing.T) {
	ac := &AgentConnection{agentID: "agent-1"}
	if got := ac.currentAgentID(); got != "agent-1" {
		t.Fatalf("currentAgentID = %q", got)
	}
}
