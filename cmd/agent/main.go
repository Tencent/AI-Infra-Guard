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
	agent6 := agent.ModelJailbreak{Server: server}

	x.RegisterTaskFunc(&agent2)
	x.RegisterTaskFunc(&agent3)
	x.RegisterTaskFunc(&agent4)
	x.RegisterTaskFunc(&agent5)
	x.RegisterTaskFunc(&agent6)

	gologger.Infoln("wait task")
	err := x.Start()
	if err != nil {
		gologger.WithError(err).Errorln("start agent failed")
	}
	x.Stop()
}
