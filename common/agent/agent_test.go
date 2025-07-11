package agent

import (
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestAgent(t *testing.T) {
	agent := NewAgent(AgentConfig{
		ServerURL: "ws://21.91.99.91:8088/api/v1/agents/ws",
		Info: AgentInfo{
			ID:       "test",
			HostName: "test",
			IP:       "127.0.0.1",
			Version:  "0.1",
			Metadata: "",
		},
	})
	err := agent.Start()
	assert.NoError(t, err)
	agent1 := TestDemoAgent{}
	agent.RegisterTaskFunc(&agent1)
	defer agent.Stop()
	gologger.Infoln("wait task")
}
