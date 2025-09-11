package main

import (
	"flag"
	"fmt"
	"os"
	"time"

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

	// 新增：初始化默认模型
	initDefaultModels()

	gologger.Infoln("connect server:", server)
	serverUrl := fmt.Sprintf("ws://%s/api/v1/agents/ws", server)
	for {
		time.Sleep(time.Millisecond * 1200)
		func() {
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
			agent3 := agent.McpScanAgent{Server: server}
			agent4 := agent.ModelJailbreak{Server: server}
			agent5 := agent.ModelRedteamReport{Server: server}

			x.RegisterTaskFunc(&agent2)
			x.RegisterTaskFunc(&agent3)
			x.RegisterTaskFunc(&agent4)
			x.RegisterTaskFunc(&agent5)

			gologger.Infoln("wait task")
			err := x.Start()
			if err != nil {
				gologger.WithError(err).Errorln("start agent failed")
			}
			defer x.Stop()
		}()
		gologger.Infoln("reconnect...")
	}
}

// 新增：初始化默认模型
func initDefaultModels() {
	// 检查环境变量
	model := os.Getenv("OPENAI_MODEL")
	token := os.Getenv("OPENAI_API_KEY")
	baseUrl := os.Getenv("OPENAI_BASE_URL")
	
	if model != "" && token != "" && baseUrl != "" {
		gologger.Infoln("检测到默认模型配置，模型:", model)
		// 设置全局环境变量，供 Agent 任务执行时使用
		os.Setenv("DEFAULT_MODEL_NAME", model)
		os.Setenv("DEFAULT_MODEL_TOKEN", token)
		os.Setenv("DEFAULT_MODEL_BASE_URL", baseUrl)
	} else {
		gologger.Warnln("未检测到默认模型配置，Agent 可能无法正常工作")
		gologger.Warnln("请设置环境变量：OPENAI_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL")
	}
}
