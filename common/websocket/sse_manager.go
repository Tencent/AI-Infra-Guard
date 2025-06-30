package websocket

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

// SSEConnection 表示一个SSE连接
type SSEConnection struct {
	SessionID string
	Username  string
	Writer    http.ResponseWriter
	Flusher   http.Flusher
	CloseChan chan bool
	LastPing  time.Time
}

// SSEManager 管理SSE连接和事件推送
type SSEManager struct {
	connections map[string]*SSEConnection // sessionId -> connection
	mutex       sync.RWMutex
}

// NewSSEManager 创建新的SSE管理器
func NewSSEManager() *SSEManager {
	return &SSEManager{
		connections: make(map[string]*SSEConnection),
	}
}

// AddConnection 添加新的SSE连接
func (sm *SSEManager) AddConnection(sessionID, username string, w http.ResponseWriter) error {
	sm.mutex.Lock()
	defer sm.mutex.Unlock()

	// 检查是否已存在相同sessionId的连接
	if existing, exists := sm.connections[sessionID]; exists {
		// 关闭现有连接
		close(existing.CloseChan)
		gologger.Infof("关闭现有连接: sessionId=%s", sessionID)
	}

	// 检查是否支持SSE
	flusher, ok := w.(http.Flusher)
	if !ok {
		return fmt.Errorf("streaming unsupported")
	}

	// 设置SSE响应头
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Headers", "Cache-Control")

	// 创建连接
	conn := &SSEConnection{
		SessionID: sessionID,
		Username:  username,
		Writer:    w,
		Flusher:   flusher,
		CloseChan: make(chan bool),
		LastPing:  time.Now(),
	}

	sm.connections[sessionID] = conn
	gologger.Infof("添加SSE连接: sessionId=%s, username=%s", sessionID, username)

	// 发送连接成功消息
	sm.sendEventToConnection(conn, "connected", "connected", map[string]interface{}{
		"message":   "SSE连接已建立",
		"sessionId": sessionID,
	})

	// 启动心跳和连接保持
	go sm.keepConnectionAlive(conn)

	return nil
}

// keepConnectionAlive 保持连接活跃
func (sm *SSEManager) keepConnectionAlive(conn *SSEConnection) {
	ticker := time.NewTicker(10 * time.Second) // 改为10秒心跳，提高频率
	defer ticker.Stop()

	for {
		select {
		case <-conn.CloseChan:
			gologger.Infof("SSE连接已关闭: sessionId=%s", conn.SessionID)
			return
		case <-ticker.C:
			// 发送liveStatus心跳消息
			heartbeat := TaskEventMessage{
				ID:        fmt.Sprintf("heartbeat_%d", time.Now().Unix()),
				Type:      "liveStatus", // 改为liveStatus类型
				SessionID: conn.SessionID,
				Timestamp: time.Now().Unix(),
				Event: LiveStatusEvent{
					ID:        fmt.Sprintf("heartbeat_%d", time.Now().Unix()),
					Type:      "liveStatus",
					Timestamp: time.Now().UnixMilli(),
					Text:      "思考中...", // 默认状态文本
				},
			}

			eventData, err := json.Marshal(heartbeat)
			if err != nil {
				gologger.Errorf("心跳序列化失败: %v", err)
				continue
			}

			_, err = fmt.Fprintf(conn.Writer, "data: %s\n\n", eventData)
			if err != nil {
				gologger.Errorf("发送心跳失败: %v", err)
				sm.RemoveConnection(conn.SessionID)
				return
			}

			conn.Flusher.Flush()
			conn.LastPing = time.Now()
		}
	}
}

// RemoveConnection 移除SSE连接
func (sm *SSEManager) RemoveConnection(sessionID string) {
	sm.mutex.Lock()
	defer sm.mutex.Unlock()

	if conn, exists := sm.connections[sessionID]; exists {
		close(conn.CloseChan)
		delete(sm.connections, sessionID)
		gologger.Infof("移除SSE连接: sessionId=%s", sessionID)
	}
}

// SendEvent 向指定会话发送事件
func (sm *SSEManager) SendEvent(id string, sessionID string, eventType string, event interface{}) error {
	sm.mutex.RLock()
	conn, exists := sm.connections[sessionID]
	sm.mutex.RUnlock()

	if !exists {
		return fmt.Errorf("连接不存在: sessionId=%s", sessionID)
	}

	return sm.sendEventToConnection(conn, id, eventType, event)
}

// sendEventToConnection 向单个连接发送事件
func (sm *SSEManager) sendEventToConnection(conn *SSEConnection, id string, eventType string, event interface{}) error {
	// 创建事件消息
	eventMessage := TaskEventMessage{
		ID:        id,
		Type:      eventType,
		SessionID: conn.SessionID,
		Timestamp: time.Now().Unix(),
		Event:     event,
	}

	// 序列化事件
	eventData, err := json.Marshal(eventMessage)
	if err != nil {
		return fmt.Errorf("序列化事件失败: %v", err)
	}

	// 按照SSE规范发送消息
	// 格式: id: <id>\nevent: <event_type>\ndata: <json_data>\n\n
	_, err = fmt.Fprintf(conn.Writer, "id: %s\nevent: %s\ndata: %s\n\n",
		id, eventType, eventData)
	if err != nil {
		return fmt.Errorf("发送事件失败: %v", err)
	}

	// 刷新缓冲区
	conn.Flusher.Flush()
	conn.LastPing = time.Now()

	gologger.Infof("发送事件: sessionId=%s, eventType=%s", conn.SessionID, eventType)
	return nil
}

// GetConnectionCount 获取当前连接数
func (sm *SSEManager) GetConnectionCount() int {
	sm.mutex.RLock()
	defer sm.mutex.RUnlock()
	return len(sm.connections)
}

// GetConnectionsByUser 获取指定用户的连接
func (sm *SSEManager) GetConnectionsByUser(username string) []string {
	sm.mutex.RLock()
	defer sm.mutex.RUnlock()

	var sessionIDs []string
	for sessionID, conn := range sm.connections {
		if conn.Username == username {
			sessionIDs = append(sessionIDs, sessionID)
		}
	}
	return sessionIDs
}
