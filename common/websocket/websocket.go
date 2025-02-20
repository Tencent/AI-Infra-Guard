package websocket

import (
	"encoding/json"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/common/runner"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"net/http"
	"sync"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true // 允许所有来源
	},
}

// WSServer WebSocket服务器结构
type WSServer struct {
	broadcast chan []byte
	mu        sync.Mutex
	options   *options.Options
}

// NewWSServer 创建新的WebSocket服务器
func NewWSServer(options *options.Options) *WSServer {
	return &WSServer{
		options: options,
	}
}

// HandleWS 处理WebSocket连接
func (s *WSServer) HandleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		gologger.Errorln("升级WebSocket连接失败: %v\n", err)
		return
	}
	go s.handleMessages(conn)
}

// SendMessage 发送消息给指定客户端
func (s *WSServer) SendMessage(conn *websocket.Conn, msgType string, content interface{}) error {
	msg := WSMessage{
		Type:    msgType,
		Content: content,
	}
	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}
	return conn.WriteMessage(websocket.TextMessage, data)
}

// handleMessages 处理来自客户端的消息
func (s *WSServer) handleMessages(conn *websocket.Conn) {
	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			break
		}
		var scanReq ScanRequest
		if err := json.Unmarshal(message, &scanReq); err != nil {
			fmt.Printf("解析消息失败: %v\n", err)
			continue
		}
		resp := Response{
			Status:  0,
			Message: "success",
		}
		err = s.SendMessage(conn, WSMsgTypeScanRet, resp)
		if err != nil {
			gologger.Errorf("发送消息失败: %v\n", err)
			continue
		}
		// 处理扫描请求
		go s.handleScanRequest(conn, &scanReq)
	}
}

// handleScanRequest 处理扫描请求
func (s *WSServer) handleScanRequest(conn *websocket.Conn, req *ScanRequest) {
	opts := s.options
	switch req.ScanType {
	case "localscan":
		opts.LocalScan = true
	case "netscan":
		opts.Target = req.Target
	}
	mu := sync.Mutex{}
	processFunc := func(data interface{}) {
		mu.Lock()
		defer mu.Unlock()
		switch v := data.(type) {
		case runner.CallbackScanResult:
			s.SendMessage(conn, WSMsgTypeScanResult, v)
		case runner.CallbackProcessInfo:
			s.SendMessage(conn, WSMsgTypeProcessInfo, v)
		case runner.CallbackReportInfo:
			s.SendMessage(conn, WSMsgTypeReportInfo, v)
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	opts.SetCallback(processFunc)
	r, err := runner.New(opts) // 创建runner
	if err != nil {
		s.SendMessage(conn, WSMsgTypeLog, Log{
			Message: "Counld not create runner:" + err.Error(),
			Level:   "error",
		})
		return
	}
	defer r.Close()    // 关闭runner
	r.RunEnumeration() // 执行枚举
}
