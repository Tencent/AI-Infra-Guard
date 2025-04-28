package websocket

import (
	"embed"
	"encoding/json"
	"github.com/Tencent/AI-Infra-Guard/common/runner"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"mime"
	"net/http"
	"path/filepath"
	"strings"
)

//go:embed static/*
var staticFS embed.FS

func RunWebServer(options *options.Options) {
	// 创建WebSocket服务器
	gologger.SetColor(false)
	wsServer := NewWSServer(options)
	// 设置WebSocket路由
	http.HandleFunc("/ws", wsServer.HandleAIInfraWS)
	// 展示漏洞列表
	http.HandleFunc("/show", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		ops := options
		ops.ListVulTemplate = true
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
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		assetPath := "static" + r.RequestURI
		if strings.Contains(r.RequestURI, "..") {
			http.Error(w, "Internal Server Error", http.StatusInternalServerError)
			return
		}
		assetData, err := staticFS.ReadFile(assetPath)
		if err != nil {
			// 如果请求的文件不存在，返回index.html
			var readErr error
			assetPath = "static/index.html"
			assetData, readErr = staticFS.ReadFile("static/index.html")
			if readErr != nil {
				http.Error(w, "Internal Server Error", http.StatusInternalServerError)
				return
			}
		}

		// 设置MIME类型，如果无法确定则默认为text/plain
		mimeType := mime.TypeByExtension(filepath.Ext(assetPath))
		if mimeType == "" {
			mimeType = "text/plain"
		}
		w.Header().Set("Content-Type", mimeType)

		// 写入响应内容
		if _, err := w.Write(assetData); err != nil {
			gologger.Errorln("Error writing response:", err)
		}
	})
	// mcp
	http.HandleFunc("/mcp/plugins", mcpPlugins)
	http.HandleFunc("/mcp_ws", wsServer.HandleMcpWS)
	// 启动HTTP服务器
	gologger.Infof("Starting WebServer on http://%s\n", options.WebServerAddr)
	if err := http.ListenAndServe(options.WebServerAddr, nil); err != nil {
		gologger.Fatalf("Could not start WebSocket server: %s\n", err)
	}
}
