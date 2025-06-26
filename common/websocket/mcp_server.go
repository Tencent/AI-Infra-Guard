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
	"github.com/gorilla/websocket"
)

const (
	WSMsgTypeMcpLog        = "log"
	WSMsgTypeMcpResult     = "result"
	WSMsgTypeMcpREADME     = "readme"
	WSMsgTypeMcpProcessing = "processing"
	WSMsgTypeMcpFinish     = "finish"
	WSMsgTypeMcpStop       = "stop"
	WSMsgTypeMcpError      = "error"
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
func getOrCreateConnection(ctx context.Context, conn *websocket.Conn) *WsConnection {
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
			go processMessages(ctx, wsConn)
		}
		connectionManager.Unlock()
	}

	return wsConn
}

// 处理消息队列
func processMessages(ctx context.Context, wsConn *WsConnection) {
	for {
		select {
		case <-ctx.Done():
			return
		case msg := <-wsConn.sendQueue:
			data, err := json.Marshal(map[string]interface{}{
				"type":    msg.Type,
				"content": msg.Data,
			})
			if err != nil {
				gologger.Errorf("消息序列化失败: %v\n", err)
				continue
			}
			wsConn.lock.Lock()
			err = wsConn.conn.WriteMessage(websocket.TextMessage, data)
			wsConn.lock.Unlock()
			if err != nil {
				gologger.Errorf("发送WebSocket消息失败: %v\n", err)
			}
		}
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
	type plugin struct {
		Name   string `json:"name"`
		Desc   string `json:"desc"`
		NameEn string `json:"name_en"`
		DescEn string `json:"desc_en"`
		ID     string `json:"id"`
	}
	scanner := mcp.NewScanner(nil, nil)
	plugins := make([]plugin, 0)
	for _, p := range scanner.PluginConfigs {
		plugins = append(plugins, plugin{
			Name:   p.Info.Name,
			Desc:   p.Info.Description,
			NameEn: p.Info.Name,
			DescEn: p.Info.Description,
			ID:     p.Info.ID,
		})
	}
	resp, err := json.Marshal(plugins)
	if err != nil {
		w.Write([]byte(err.Error()))
	}
	w.Write(resp)
	return
}

type ScanMcpRequest struct {
	Content string `json:"content"`
	Model   struct {
		Model   string `json:"model"`
		Token   string `json:"token"`
		BaseUrl string `json:"base_url"`
	} `json:"model"`
	Plugins  string `json:"plugins"`
	Language string `json:"language"`
}

type WsReq struct {
	Type string          `json:"type"`
	Data json.RawMessage `json:"data"`
}

type WsWrite struct {
	Server  *WSServer
	Conn    *websocket.Conn
	buffer  []byte
	mu      sync.Mutex
	size    int // 当前缓冲区大小
	maxSize int // 缓冲区最大大小，达到此值时发送
	ctx     context.Context
}

// NewWsWrite 创建一个新的带缓冲的WsWrite
func NewWsWrite(ctx context.Context, server *WSServer, conn *websocket.Conn, maxSize int) *WsWrite {
	if maxSize <= 0 {
		maxSize = 4096 // 默认4KB缓冲区
	}
	return &WsWrite{
		Server:  server,
		Conn:    conn,
		buffer:  make([]byte, 0, maxSize),
		maxSize: maxSize,
		ctx:     ctx,
	}
}

// Flush 立即发送缓冲区中的所有数据
func (w *WsWrite) Flush() error {
	w.mu.Lock()
	defer w.mu.Unlock()

	if w.size == 0 {
		return nil
	}

	err := w.Server.SendMessage2(w.ctx, w.Conn, WSMsgTypeMcpLog, string(w.buffer[:w.size]))
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
		err = w.Server.SendMessage2(w.ctx, w.Conn, WSMsgTypeMcpLog, string(p))
		if err != nil {
			return 0, err
		}
		return len(p), nil
	}

	// 如果当前缓冲区容量不足，先发送缓冲区内容
	if w.size+len(p) > w.maxSize {
		if w.size > 0 {
			err = w.Server.SendMessage2(w.ctx, w.Conn, WSMsgTypeMcpLog, string(w.buffer[:w.size]))
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
func (s *WSServer) SendMessage2(ctx context.Context, conn *websocket.Conn, msgType string, data interface{}) error {
	wsConn := getOrCreateConnection(ctx, conn)
	select {
	case wsConn.sendQueue <- WsMessage{Type: msgType, Data: data}:
		return nil
	}
}

func (s *WSServer) handleMcpScan(ctx context.Context, conn *websocket.Conn, req *ScanMcpRequest) {
	// setlogger
	writer1 := os.Stdout
	writer2 := NewWsWrite(ctx, s, conn, 50)
	logger := gologger.NewLogger()
	logger.Logrus().SetOutput(io.MultiWriter(writer1, writer2))

	// 在扫描结束时确保刷新缓冲区
	defer writer2.Flush()
	mu := sync.Mutex{}

	processFunc := func(data interface{}) {
		mu.Lock()
		defer mu.Unlock()
		switch v := data.(type) {
		case mcp.McpCallbackProcessing:
			s.SendMessage2(ctx, conn, WSMsgTypeMcpProcessing, v)
		case mcp.McpCallbackReadMe:
			s.SendMessage2(ctx, conn, WSMsgTypeMcpREADME, v)
		case mcp.ScannerIssue:
			s.SendMessage2(ctx, conn, WSMsgTypeMcpResult, v)
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	modelConfig := models.NewOpenAI(req.Model.Token, req.Model.Model, req.Model.BaseUrl)
	scanner := mcp.NewScanner(modelConfig, logger)
	scanner.SetLanguage(req.Language)
	scanner.SetCallback(processFunc)
	if strings.HasPrefix(req.Content, "http://") || strings.HasPrefix(req.Content, "https://") {
		url := req.Content
		r, err := scanner.InputUrl(ctx, url)
		if err != nil {
			s.SendMessage(conn, WSMsgTypeMcpError, fmt.Sprintf("输入流链接无效: %v\n", err))
			return
		}
		results, err := scanner.ScanLink(ctx, r, false)
		if err != nil {
			gologger.Errorf("扫描失败: %v\n", err)
			writer2.Flush()
			return
		}
		// 确保所有日志都发送出去
		writer2.Flush()
		s.SendMessage2(ctx, conn, WSMsgTypeMcpFinish, results)
	} else {
		folder := req.Content
		// 判断文件夹是否存在
		if info, err := os.Stat(folder); os.IsNotExist(err) || !info.IsDir() {
			s.SendMessage(conn, WSMsgTypeMcpError, fmt.Sprintf("文件夹不存在: %v\n", err))
			return
		}
		scanner.InputCodePath(req.Content)
		results, err := scanner.ScanCode(ctx, false)
		if err != nil {
			gologger.Errorf("扫描失败: %v\n", err)
			writer2.Flush()
			return
		}
		// 确保所有日志都发送出去
		writer2.Flush()
		s.SendMessage2(ctx, conn, WSMsgTypeMcpFinish, results)
	}
	gologger.Infof("扫描完成\n")
}

func (s *WSServer) handleMessages2(conn *websocket.Conn) {
	ctx, cancel := context.WithCancel(context.Background())
	defer removeConnection(conn)
	defer cancel()

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			break
		}
		var scanReq WsReq
		if err := json.Unmarshal(message, &scanReq); err != nil {
			s.SendMessage(conn, WSMsgTypeMcpError, fmt.Sprintf("解析消息失败: %v\n", err))
			continue
		}
		if scanReq.Type == "start" {
			var data ScanMcpRequest
			if err := json.Unmarshal(scanReq.Data, &data); err != nil {
				s.SendMessage(conn, WSMsgTypeMcpError, fmt.Sprintf("解析消息失败: %v\n", err))
				continue
			}
			// 处理扫描请求
			go s.handleMcpScan(ctx, conn, &data)
		} else if scanReq.Type == "stop" {
			s.SendMessage(conn, WSMsgTypeMcpStop, "扫描已停止")
			cancel()
		}
	}
}

func (s *WSServer) HandleMcpWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		gologger.Errorf("升级WebSocket连接失败: %v\n", err)
		return
	}
	go s.handleMessages2(conn)
}
