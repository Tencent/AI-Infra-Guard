package main

import (
	"flag"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/common/agent"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

func main() {
	var server string
	flag.StringVar(&server, "server", "21.6.190.156:8088", "server")
	flag.Parse()

	serverUrl := fmt.Sprintf("ws://%s/api/v1/agents/ws", server)

	x := agent.NewAgent(agent.AgentConfig{
		ServerURL: serverUrl,
		Info: agent.AgentInfo{
			ID:       "test",
			HostName: "test",
			IP:       "127.0.0.1",
			Version:  "0.1",
			Metadata: "",
		},
	})
	defer x.Disconnect("主动退出")
	agent1 := agent.TestDemoAgent{}
	agent2 := agent.AIInfraScanAgent{}
	agent3 := agent.McpScanAgent{Server: server}
	agent4 := agent.ModelJailbreak{}
	agent5 := agent.ModelRedteamReport{}

	x.RegisterTaskFunc(&agent1)
	x.RegisterTaskFunc(&agent2)
	x.RegisterTaskFunc(&agent3)
	x.RegisterTaskFunc(&agent4)
	x.RegisterTaskFunc(&agent5)

	gologger.Infoln("wait task")
	err := x.Start()
	if err != nil {
		gologger.WithError(err).Fatalln("ok")
	}
	defer x.Stop()
}
