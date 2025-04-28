package websocket

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/gorilla/websocket"
)

const (
	WSMsgTypeMcpLog        = "log"
	WSMsgTypeMcpResult     = "result"
	WSMsgTypeMcpREADME     = "readme"
	WSMsgTypeMcpProcessing = "processing"
	WSMsgTypeMcpFinish     = "finish"
)

// 添加消息队列和锁相关结构
type WsMessage struct {
	Type string
	Data interface{}
}

type WsConnection struct {
	conn      *websocket.Conn
	sendQueue chan WsMessage
	lock      sync.Mutex
}

// 连接管理器映射表
var connectionManager = struct {
	sync.RWMutex
	connections map[*websocket.Conn]*WsConnection
}{
	connections: make(map[*websocket.Conn]*WsConnection),
}

// 获取或创建连接
func getOrCreateConnection(conn *websocket.Conn) *WsConnection {
	connectionManager.RLock()
	wsConn, exists := connectionManager.connections[conn]
	connectionManager.RUnlock()

	if !exists {
		connectionManager.Lock()
		// 双重检查避免竞态条件
		if wsConn, exists = connectionManager.connections[conn]; !exists {
			wsConn = &WsConnection{
				conn:      conn,
				sendQueue: make(chan WsMessage, 100), // 消息队列缓冲区
				lock:      sync.Mutex{},
			}
			connectionManager.connections[conn] = wsConn

			// 启动消息处理goroutine
			go processMessages(wsConn)
		}
		connectionManager.Unlock()
	}

	return wsConn
}

// 处理消息队列
func processMessages(wsConn *WsConnection) {
	for msg := range wsConn.sendQueue {
		wsConn.lock.Lock()
		data, err := json.Marshal(map[string]interface{}{
			"type":    msg.Type,
			"content": msg.Data,
		})
		if err != nil {
			gologger.Errorf("消息序列化失败: %v\n", err)
			wsConn.lock.Unlock()
			continue
		}

		err = wsConn.conn.WriteMessage(websocket.TextMessage, data)
		if err != nil {
			gologger.Errorf("发送WebSocket消息失败: %v\n", err)
		}
		wsConn.lock.Unlock()
	}
}

// 移除连接
func removeConnection(conn *websocket.Conn) {
	connectionManager.Lock()
	if wsConn, exists := connectionManager.connections[conn]; exists {
		close(wsConn.sendQueue)
		delete(connectionManager.connections, conn)
	}
	connectionManager.Unlock()
}

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
	Server  *WSServer
	Conn    *websocket.Conn
	buffer  []byte
	mu      sync.Mutex
	size    int // 当前缓冲区大小
	maxSize int // 缓冲区最大大小，达到此值时发送
}

// NewWsWrite 创建一个新的带缓冲的WsWrite
func NewWsWrite(server *WSServer, conn *websocket.Conn, maxSize int) *WsWrite {
	if maxSize <= 0 {
		maxSize = 4096 // 默认4KB缓冲区
	}
	return &WsWrite{
		Server:  server,
		Conn:    conn,
		buffer:  make([]byte, 0, maxSize),
		maxSize: maxSize,
	}
}

// Flush 立即发送缓冲区中的所有数据
func (w *WsWrite) Flush() error {
	w.mu.Lock()
	defer w.mu.Unlock()

	if w.size == 0 {
		return nil
	}

	err := w.Server.SendMessage2(w.Conn, WSMsgTypeMcpLog, string(w.buffer[:w.size]))
	if err != nil {
		return err
	}

	// 清空缓冲区
	w.size = 0
	w.buffer = make([]byte, 0, w.maxSize)
	return nil
}

func (w *WsWrite) Write(p []byte) (n int, err error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	// 如果数据过大，直接发送不缓存
	if len(p) > w.maxSize {
		err = w.Server.SendMessage2(w.Conn, WSMsgTypeMcpLog, string(p))
		if err != nil {
			return 0, err
		}
		return len(p), nil
	}

	// 如果当前缓冲区容量不足，先发送缓冲区内容
	if w.size+len(p) > w.maxSize {
		if w.size > 0 {
			err = w.Server.SendMessage2(w.Conn, WSMsgTypeMcpLog, string(w.buffer[:w.size]))
			if err != nil {
				return 0, err
			}
			w.size = 0
			w.buffer = make([]byte, 0, w.maxSize)
		}
	}

	// 添加数据到缓冲区
	if cap(w.buffer) < w.size+len(p) {
		// 扩容
		newBuf := make([]byte, w.size, w.maxSize)
		copy(newBuf, w.buffer[:w.size])
		w.buffer = newBuf
	}

	// 追加数据
	w.buffer = append(w.buffer[:w.size], p...)
	w.size += len(p)

	return len(p), nil
}

// 更新SendMessage2方法
func (s *WSServer) SendMessage2(conn *websocket.Conn, msgType string, data interface{}) error {
	wsConn := getOrCreateConnection(conn)
	select {
	case wsConn.sendQueue <- WsMessage{Type: msgType, Data: data}:
		return nil
	}
}

func (s *WSServer) handleMcpScan(conn *websocket.Conn, req *WsReq) {
	// setlogger
	writer1 := os.Stdout
	writer2 := NewWsWrite(s, conn, 50)
	gologger.Logger.SetOutput(io.MultiWriter(writer1, writer2))

	// 在扫描结束时确保刷新缓冲区
	defer writer2.Flush()

	processFunc := func(data interface{}) {
		switch v := data.(type) {
		case mcp.McpCallbackProcessing:
			s.SendMessage2(conn, WSMsgTypeMcpProcessing, v)
		case mcp.McpCallbackReadMe:
			s.SendMessage2(conn, WSMsgTypeMcpREADME, v)
		case mcp.ScannerIssue:
			s.SendMessage2(conn, WSMsgTypeMcpResult, v)
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
	_, err = scanner.Scan(ctx)
	if err != nil {
		gologger.Errorf("扫描失败: %v\n", err)
		writer2.Flush() // 确保错误信息立即发送
		return
	}

	// 确保所有日志都发送出去
	writer2.Flush()
	gologger.Infof("扫描完成\n")
	s.SendMessage2(conn, WSMsgTypeMcpFinish, nil)
}

func (s *WSServer) handleMessages2(conn *websocket.Conn) {
	defer removeConnection(conn)

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
