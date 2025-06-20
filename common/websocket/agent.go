package websocket

import (
	"encoding/json"
	"sync"
	"time"

	// "github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	// "gorm.io/datatypes"
)

const (
	// WebSocket相关常量
	maxMessageSize    = 512 * 1024 // 512KB
	pongWait          = 60 * time.Second
	pingPeriod        = (pongWait * 9) / 10
	writeWait         = 10 * time.Second
	WSMsgTypeRegister = "register"
	// WSMsgTypeTaskAssign = "task_assign" // 任务分配
	WSMsgTypeDisconnect = "disconnect" // 主动断开连接的消息类型

	// Agent 端事件类型（与前端 SSE 事件类型一致）
	WSMsgTypeLiveStatus   = "liveStatus"   // 存活状态
	WSMsgTypePlanUpdate   = "planUpdate"   // 计划更新
	WSMsgTypeNewPlanStep  = "newPlanStep"  // 新计划步骤
	WSMsgTypeStatusUpdate = "statusUpdate" // 状态更新
	WSMsgTypeToolUsed     = "toolUsed"     // 工具使用
)

// Agent 端事件消息（Agent -> Server，直接使用 task.go 中的结构体）
// 注意：Agent 端返回的事件体直接使用 task.go 中定义的结构体：
// - LiveStatusEvent
// - PlanUpdateEvent
// - PlanTaskItem
// - NewPlanStepEvent
// - StatusUpdateEvent
// - ToolUsedEvent
// 这样可以确保格式完全一致，避免重复定义

// AgentConnection 管理单个agent的连接
type AgentConnection struct {
	conn    *websocket.Conn
	agentID string
	// store    *database.AgentStore // 注释掉数据库字段
	mu       sync.Mutex
	isActive bool
}

// AgentManager 管理所有agent连接
type AgentManager struct {
	connections map[string]*AgentConnection
	mu          sync.RWMutex
	taskManager *TaskManager // 新增：引用 TaskManager
	// store       *database.AgentStore // 注释掉数据库字段
}

// 注册/心跳消息内容
type AgentRegisterContent struct {
	AgentID      string   `json:"agent_id"`
	Hostname     string   `json:"hostname,omitempty"`
	IP           string   `json:"ip,omitempty"`
	Version      string   `json:"version,omitempty"`
	Capabilities []string `json:"capabilities,omitempty"`
	Meta         string   `json:"meta,omitempty"`
}

// 断开连接消息内容
type DisconnectContent struct {
	AgentID string `json:"agent_id"`
	Reason  string `json:"reason,omitempty"`
}

// NewAgentManager 创建新的AgentManager
// func NewAgentManager(store *database.AgentStore) *AgentManager {
func NewAgentManager() *AgentManager {
	return &AgentManager{
		connections: make(map[string]*AgentConnection),
		// store:       store,
	}
}

// NewAgentConnection 创建新的AgentConnection
// func NewAgentConnection(conn *websocket.Conn, store *database.AgentStore) *AgentConnection {
func NewAgentConnection(conn *websocket.Conn) *AgentConnection {
	return &AgentConnection{
		conn: conn,
		// store:    store,
		isActive: true,
	}
}

// HandleAgentWebSocket 处理agent的WebSocket连接
func (am *AgentManager) HandleAgentWebSocket() gin.HandlerFunc {

	return func(c *gin.Context) {
		conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
		if err != nil {
			return
		}

		// ac := NewAgentConnection(conn, am.store)
		ac := NewAgentConnection(conn)
		go ac.handleConnection(am)
	}
}

// handleConnection 处理单个连接的消息
func (ac *AgentConnection) handleConnection(am *AgentManager) {
	defer func() {
		ac.cleanup(am)
	}()

	// 设置连接参数
	ac.conn.SetReadLimit(maxMessageSize)
	ac.conn.SetReadDeadline(time.Now().Add(pongWait))
	ac.conn.SetPongHandler(func(string) error {
		ac.conn.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

	// 启动心跳检测
	go ac.writePump()

	// 处理消息
	for {
		_, message, err := ac.conn.ReadMessage()
		if err != nil {
			break
		}

		var wsMsg WSMessage
		if err := json.Unmarshal(message, &wsMsg); err != nil {
			ac.sendError("消息格式错误")
			continue
		}

		switch wsMsg.Type {
		case WSMsgTypeRegister:
			ac.handleRegister(am, wsMsg.Content)
		case WSMsgTypeLiveStatus:
			ac.handleLiveStatus(am, wsMsg.Content)
		case WSMsgTypePlanUpdate:
			ac.handlePlanUpdate(am, wsMsg.Content)
		case WSMsgTypeNewPlanStep:
			ac.handleNewPlanStep(am, wsMsg.Content)
		case WSMsgTypeStatusUpdate:
			ac.handleStatusUpdate(am, wsMsg.Content)
		case WSMsgTypeToolUsed:
			ac.handleToolUsed(am, wsMsg.Content)
		case WSMsgTypeDisconnect:
			// 只有在身份验证成功时才断开连接
			ac.handleDisconnect(am, wsMsg.Content)
			// 检查连接是否仍然活跃，如果不活跃则退出
			ac.mu.Lock()
			if !ac.isActive {
				ac.mu.Unlock()
				return
			}
			ac.mu.Unlock()
		}
	}
}

// handleRegister 处理注册消息
func (ac *AgentConnection) handleRegister(am *AgentManager, content interface{}) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	contentBytes, _ := json.Marshal(content)
	var reg AgentRegisterContent
	if err := json.Unmarshal(contentBytes, &reg); err != nil {
		ac.sendError("注册消息格式错误")
		return
	}

	// 检查是否已存在同ID的连接
	am.mu.Lock()
	if existingConn, exists := am.connections[reg.AgentID]; exists {
		// 关闭旧连接
		existingConn.isActive = false
		existingConn.conn.Close()
		delete(am.connections, reg.AgentID)
	}
	am.mu.Unlock()

	// capabilitiesJSON, _ := json.Marshal(reg.Capabilities)
	// agent := &database.Agent{
	// 	ID:           reg.AgentID,
	// 	Hostname:     reg.Hostname,
	// 	IP:           reg.IP,
	// 	Version:      reg.Version,
	// 	Capabilities: datatypes.JSON(capabilitiesJSON),
	// 	Meta:         reg.Meta,
	// 	Online:       true,
	// }

	// if err := ac.store.Register(agent); err != nil {
	// 	ac.sendError("注册失败: " + err.Error())
	// 	return
	// }

	ac.agentID = reg.AgentID
	am.mu.Lock()
	am.connections[reg.AgentID] = ac
	am.mu.Unlock()

	response := WSMessage{
		Type: "register_ack",
		Content: Response{
			Status:  0,
			Message: "注册成功",
		},
	}
	ac.conn.WriteJSON(response)
}

// handleHeartbeat 处理心跳消息
// func (ac *AgentConnection) handleHeartbeat(content interface{}) {
// 	ac.mu.Lock()
// 	defer ac.mu.Unlock()

// 	contentBytes, _ := json.Marshal(content)
// 	var hb AgentRegisterContent
// 	if err := json.Unmarshal(contentBytes, &hb); err != nil {
// 		ac.sendError("心跳消息格式错误")
// 		return
// 	}

// 	// 验证身份一致性
// 	if ac.agentID == "" || ac.agentID != hb.AgentID {
// 		ac.sendError("心跳消息身份验证失败")
// 		return
// 	}

// 	// ac.store.UpdateLastSeen(hb.AgentID)
// 	// ac.store.UpdateOnlineStatus(hb.AgentID, true)
// }

// handleDisconnect 处理主动断开连接
func (ac *AgentConnection) handleDisconnect(am *AgentManager, content interface{}) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	contentBytes, _ := json.Marshal(content)
	var dc DisconnectContent
	if err := json.Unmarshal(contentBytes, &dc); err != nil {
		ac.sendError("断开连接消息格式错误")
		return
	}

	// 验证身份一致性
	if ac.agentID == "" || ac.agentID != dc.AgentID {
		ac.sendError("断开连接消息身份验证失败")
		return
	}

	// ac.store.UpdateOnlineStatus(ac.agentID, false)

	// 从连接管理器中移除
	am.mu.Lock()
	delete(am.connections, ac.agentID)
	am.mu.Unlock()

	// 发送断开确认
	response := WSMessage{
		Type: "disconnect_ack",
		Content: Response{
			Status:  0,
			Message: "断开连接成功",
		},
	}
	ac.conn.WriteJSON(response)

	// 标记连接为非活跃
	ac.isActive = false
}

// writePump 发送心跳包
func (ac *AgentConnection) writePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
	}()

	for {
		select {
		case <-ticker.C:
			ac.mu.Lock()
			if !ac.isActive {
				ac.mu.Unlock()
				return
			}
			ac.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := ac.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				ac.mu.Unlock()
				return
			}
			ac.mu.Unlock()
		}
	}
}

// cleanup 清理连接
func (ac *AgentConnection) cleanup(am *AgentManager) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	if ac.agentID != "" {
		am.mu.Lock()
		delete(am.connections, ac.agentID)
		am.mu.Unlock()

		// ac.store.UpdateOnlineStatus(ac.agentID, false)
	}

	ac.isActive = false
	ac.conn.Close()
}

// sendError 发送错误响应
func (ac *AgentConnection) sendError(message string) {
	response := WSMessage{
		Type: "error",
		Content: Response{
			Status:  1,
			Message: message,
		},
	}
	ac.conn.WriteJSON(response)
}

// handleLiveStatus 处理存活状态事件
func (ac *AgentConnection) handleLiveStatus(am *AgentManager, content interface{}) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	contentBytes, _ := json.Marshal(content)
	var event LiveStatusEvent
	if err := json.Unmarshal(contentBytes, &event); err != nil {
		ac.sendError("存活状态事件格式错误")
		return
	}

	// 转发给 TaskManager 处理
	am.mu.RLock()
	if am.taskManager != nil {
		am.taskManager.HandleAgentEvent(WSMsgTypeLiveStatus, event)
	}
	am.mu.RUnlock()
}

// handlePlanUpdate 处理计划更新事件
func (ac *AgentConnection) handlePlanUpdate(am *AgentManager, content interface{}) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	contentBytes, _ := json.Marshal(content)
	var event PlanUpdateEvent
	if err := json.Unmarshal(contentBytes, &event); err != nil {
		ac.sendError("计划更新事件格式错误")
		return
	}

	// 转发给 TaskManager 处理
	am.mu.RLock()
	if am.taskManager != nil {
		am.taskManager.HandleAgentEvent(WSMsgTypePlanUpdate, event)
	}
	am.mu.RUnlock()
}

// handleNewPlanStep 处理新计划步骤事件
func (ac *AgentConnection) handleNewPlanStep(am *AgentManager, content interface{}) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	contentBytes, _ := json.Marshal(content)
	var event NewPlanStepEvent
	if err := json.Unmarshal(contentBytes, &event); err != nil {
		ac.sendError("新计划步骤事件格式错误")
		return
	}

	// 转发给 TaskManager 处理
	am.mu.RLock()
	if am.taskManager != nil {
		am.taskManager.HandleAgentEvent(WSMsgTypeNewPlanStep, event)
	}
	am.mu.RUnlock()
}

// handleStatusUpdate 处理状态更新事件
func (ac *AgentConnection) handleStatusUpdate(am *AgentManager, content interface{}) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	contentBytes, _ := json.Marshal(content)
	var event StatusUpdateEvent
	if err := json.Unmarshal(contentBytes, &event); err != nil {
		ac.sendError("状态更新事件格式错误")
		return
	}

	// 转发给 TaskManager 处理
	am.mu.RLock()
	if am.taskManager != nil {
		am.taskManager.HandleAgentEvent(WSMsgTypeStatusUpdate, event)
	}
	am.mu.RUnlock()
}

// handleToolUsed 处理工具使用事件
func (ac *AgentConnection) handleToolUsed(am *AgentManager, content interface{}) {
	ac.mu.Lock()
	defer ac.mu.Unlock()

	contentBytes, _ := json.Marshal(content)
	var event ToolUsedEvent
	if err := json.Unmarshal(contentBytes, &event); err != nil {
		ac.sendError("工具使用事件格式错误")
		return
	}

	// 转发给 TaskManager 处理
	am.mu.RLock()
	if am.taskManager != nil {
		am.taskManager.HandleAgentEvent(WSMsgTypeToolUsed, event)
	}
	am.mu.RUnlock()
}

// 添加获取可用 Agent 的方法
func (am *AgentManager) GetAvailableAgents() []*AgentConnection {
	am.mu.RLock()
	defer am.mu.RUnlock()

	var availableAgents []*AgentConnection
	for _, conn := range am.connections {
		conn.mu.Lock()
		if conn.isActive {
			availableAgents = append(availableAgents, conn)
		}
		conn.mu.Unlock()
	}
	return availableAgents
}

// SetTaskManager 设置 TaskManager 引用
func (am *AgentManager) SetTaskManager(taskManager *TaskManager) {
	am.mu.Lock()
	defer am.mu.Unlock()
	am.taskManager = taskManager
}
