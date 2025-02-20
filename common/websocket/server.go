package websocket

import (
	"encoding/json"
	"github.com/Tencent/AI-Infra-Guard/common/runner"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"net/http"
)

func RunWebServer(options *options.Options) {
	// 创建WebSocket服务器
	wsServer := NewWSServer(options)
	// 设置WebSocket路由
	http.HandleFunc("/ws", wsServer.HandleWS)
	http.HandleFunc("/show", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		ops := options
		ops.ListVulTemplate = true
		ops.ListFpsTemplate = true
		instance, err := runner.New(ops) // 创建runner
		if err != nil {
			ret := Response{
				Status:  1,
				Message: err.Error(),
				Data:    nil,
			}
			resp, err := json.Marshal(&ret)
			if err != nil {
				gologger.Errorln(err)
			}
			w.Write(resp)
			return
		}
		defer instance.Close() // 关闭runner
		ret := Response{
			Status:  0,
			Message: "success",
			Data:    instance.GetFpAndVulList(),
		}
		resp, err := json.Marshal(&ret)
		if err != nil {
			gologger.Errorln(err)
		}
		w.Write(resp)
		return
	})
	// 启动HTTP服务器
	gologger.Infof("Starting WebServer on %s\n", options.WebServerAddr)
	if err := http.ListenAndServe(options.WebServerAddr, nil); err != nil {
		gologger.Fatalf("Could not start WebSocket server: %s\n", err)
	}
}
