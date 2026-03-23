package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/Tencent/AI-Infra-Guard/common/agent"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

func main() {
	var server string
	flag.StringVar(&server, "server", "", "server")
	flag.Parse()
	if server == "" {
		v := os.Getenv("AIG_SERVER")
		if v != "" {
			server = v
		}
	}
	if server == "" {
		gologger.Errorln("server is empty")
		return
	}
	gologger.Infoln("connect server:", server)
	serverUrl := fmt.Sprintf("ws://%s/api/v1/agents/ws", server)
	x := agent.NewAgent(agent.AgentConfig{
		ServerURL: serverUrl,
		Info: agent.AgentInfo{
			ID:       "test_id",
			HostName: "test_hostname",
			IP:       "127.0.0.1",
			Version:  "0.1",
			Metadata: "",
		},
	})
	agent2 := agent.AIInfraScanAgent{
		Server: server,
	}
	agent3 := agent.McpTask{Server: server}
	agent4 := agent.ModelRedteamReport{Server: server}
	agent5 := agent.AgentTask{Server: server}

	x.RegisterTaskFunc(&agent2)
	x.RegisterTaskFunc(&agent3)
	x.RegisterTaskFunc(&agent4)
	x.RegisterTaskFunc(&agent5)

	gologger.Infoln("wait task")
	err := x.Start()
	if err != nil {
		gologger.WithError(err).Errorln("start agent failed")
	}
	x.Stop()
}
