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

// A stale connection may send disconnect after a replacement has registered.
// The disconnect must not remove the new connection from the map.
func TestHandleDisconnectKeepsReplacementConnection(t *testing.T) {
	am := NewAgentManager()
	oldConn := &AgentConnection{agentID: "agent-1", isActive: true}
	replacement := &AgentConnection{agentID: "agent-1", isActive: true}
	am.connections["agent-1"] = replacement

	oldConn.handleDisconnect(am, map[string]string{"agent_id": "agent-1"})

	if got := am.connections["agent-1"]; got != replacement {
		t.Fatal("stale disconnect removed the replacement connection")
	}
	if oldConn.isActive {
		t.Fatal("stale connection should be marked inactive")
	}
}
