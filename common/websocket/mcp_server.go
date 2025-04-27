package websocket

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/gorilla/websocket"
	"io"
	"net/http"
	"os"
	"strings"
)

const (
	WSMsgTypeMcpLog        = "log"
	WSMsgTypeMcpResult     = "result"
	WSMsgTypeMcpREADME     = "readme"
	WSMsgTypeMcpProcessing = "processing"
)

func mcpPlugins(w http.ResponseWriter, r *http.Request) {
	pp := []plugins.McpPlugin{
		plugins.NewCmdInjectionPlugin(),
		plugins.NewAuthBypassPlugin(),
		plugins.NewNameConfusionPlugin(),
		plugins.NewToolPoisoningPlugin(),
		plugins.NewRugPullPlugin(),
		plugins.NewCredentialTheftPlugin(),
		plugins.NewHardcodedApiKeyPlugin(),
		plugins.NewResourcePoisoningPlugin(),
		plugins.NewToolShadowingPlugin(),
	}
	ret := make([]plugins.Plugin, 0)
	for _, p := range pp {
		info := p.GetPlugin()
		ret = append(ret, info)
	}
	resp, err := json.Marshal(&ret)
	if err != nil {
		gologger.Errorln(err)
	}
	w.Write(resp)
	return
}

type ScanMcpRequest struct {
	Path  string `json:"path"`
	Model struct {
		Model   string `json:"model"`
		Token   string `json:"token"`
		BaseUrl string `json:"base_url"`
	} `json:"model"`
	Plugins string `json:"plugins"`
}

type WsReq struct {
	Type string         `json:"type"`
	Data ScanMcpRequest `json:"data"`
}

type WsWrite struct {
	Server *WSServer
	Conn   *websocket.Conn
}

func (w *WsWrite) Write(p []byte) (n int, err error) {
	err = w.Server.SendMessage(w.Conn, WSMsgTypeMcpProcessing, string(p))
	if err != nil {
		return 0, err
	}
	return len(p), nil
}
func (s *WSServer) handleMcpScan(conn *websocket.Conn, req *WsReq) {
	// setlogger
	writer1 := os.Stdout
	writer2 := &WsWrite{Server: s, Conn: conn}
	gologger.Logger.SetOutput(io.MultiWriter(writer1, writer2))

	processFunc := func(data interface{}) {
		switch v := data.(type) {
		case mcp.McpCallbackProcessing:
			s.SendMessage(conn, WSMsgTypeMcpProcessing, v)
		case mcp.McpCallbackReadMe:
			s.SendMessage(conn, WSMsgTypeProcessInfo, v)
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	config := req.Data
	modelConfig := models.NewOpenAI(config.Model.Token, config.Model.Model, config.Model.BaseUrl)
	scanner := mcp.NewScanner(modelConfig)
	rPlugins := strings.Split(config.Plugins, ",")
	scanner.RegisterPlugin(rPlugins)
	scanner.SetCallback(processFunc)
	err := scanner.InputCodePath(config.Path)
	if err != nil {
		gologger.Errorf("输入代码路径失败: %v\n", err)
		return
	}
	ctx := context.Background()
	issues, err := scanner.Scan(ctx)
	if err != nil {
		gologger.Errorf("扫描失败: %v\n", err)
		return
	}
	for _, issue := range issues {
		err = s.SendMessage(conn, WSMsgTypeMcpResult, issue)
		if err != nil {
			gologger.Errorf("发送结果失败: %v\n", err)
			return
		}
	}
}

func (s *WSServer) handleMessages2(conn *websocket.Conn) {
	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			break
		}
		var scanReq WsReq
		if err := json.Unmarshal(message, &scanReq); err != nil {
			fmt.Printf("解析消息失败: %v\n", err)
			continue
		}
		// 处理扫描请求
		go s.handleMcpScan(conn, &scanReq)
	}
}

func (s *WSServer) HandleMcpWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		gologger.Errorln("升级WebSocket连接失败: %v\n", err)
		return
	}
	go s.handleMessages2(conn)
}
