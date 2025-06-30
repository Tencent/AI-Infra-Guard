package websocket

import (
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
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
	WSMsgTypeResultUpdate = "resultUpdate" // 结果更新
	WSMsgTypeActionLog    = "actionLog"    // 日志
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
	conn          *websocket.Conn
	agentID       string
	currentTaskID string // 当前执行的任务ID

	// 细粒度的锁控制
	stateMu sync.RWMutex // 保护连接状态（agentID, isActive, currentTaskID）
	writeMu sync.Mutex   // 保护写操作（发送消息）

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
	AgentID      string   `json:"agent_id" validate:"required"` // 必需字段
	Hostname     string   `json:"hostname" validate:"required"` // 必需字段
	IP           string   `json:"ip" validate:"required,ip"`    // 必需且必须是IP格式
	Version      string   `json:"version" validate:"required"`  // 必需字段
	Capabilities []string `json:"capabilities,omitempty"`       // 可选字段
	Meta         string   `json:"meta,omitempty"`               // 可选字段
}

// 断开连接消息内容
type DisconnectContent struct {
	AgentID string `json:"agent_id" validate:"required"` // 必需字段
	Reason  string `json:"reason,omitempty"`             // 可选字段
}

// 全局验证器实例
var validate *validator.Validate

// 初始化验证器
func init() {
	validate = validator.New()
}

// formatValidationErrors 格式化验证错误信息
func formatValidationErrors(err error) string {
	if validationErrors, ok := err.(validator.ValidationErrors); ok {
		var errorMessages []string
		for _, fieldError := range validationErrors {
			fieldName := fieldError.Field()
			switch fieldError.Tag() {
			case "required":
				errorMessages = append(errorMessages,
					fmt.Sprintf("缺少必需字段: %s", fieldName))
			case "ip":
				errorMessages = append(errorMessages,
					fmt.Sprintf("字段 %s 必须是有效的IP地址", fieldName))
			case "email":
				errorMessages = append(errorMessages,
					fmt.Sprintf("字段 %s 必须是有效的邮箱格式", fieldName))
			case "url":
				errorMessages = append(errorMessages,
					fmt.Sprintf("字段 %s 必须是有效的URL", fieldName))
			case "min":
				errorMessages = append(errorMessages,
					fmt.Sprintf("字段 %s 长度不能小于 %s", fieldName, fieldError.Param()))
			case "max":
				errorMessages = append(errorMessages,
					fmt.Sprintf("字段 %s 长度不能大于 %s", fieldName, fieldError.Param()))
			default:
				errorMessages = append(errorMessages,
					fmt.Sprintf("字段 %s 验证失败: %s", fieldName, fieldError.Tag()))
			}
		}
		return fmt.Sprintf("验证失败: %s", strings.Join(errorMessages, "; "))
	}
	return "验证失败"
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
			// 发送错误响应但不断开连接
			ac.sendError("消息格式错误请检查JSON格式")
			continue
		}

		// 验证消息类型
		if wsMsg.Type == "" {
			ac.sendError("消息类型不能为空")
			continue
		}

		switch wsMsg.Type {
		case WSMsgTypeRegister:
			ac.handleRegister(am, wsMsg.Content)
		case WSMsgTypeDisconnect:
			// 只有在身份验证成功时才断开连接
			ac.handleDisconnect(am, wsMsg.Content)
			// 检查连接是否仍然活跃，如果不活跃则退出
			ac.stateMu.RLock()
			if !ac.isActive {
				ac.stateMu.RUnlock()
				return
			}
			ac.stateMu.RUnlock()
		case WSMsgTypeLiveStatus, WSMsgTypePlanUpdate, WSMsgTypeNewPlanStep, WSMsgTypeStatusUpdate, WSMsgTypeToolUsed, WSMsgTypeResultUpdate, WSMsgTypeActionLog:
			// 所有事件类型都统一处理
			ac.handleAgentEvent(am, wsMsg.Content, wsMsg.Type)
		default:
			ac.sendError(fmt.Sprintf("未知的消息类型: %s。支持的类型: register, disconnect, liveStatus, planUpdate, newPlanStep, statusUpdate, toolUsed, resultUpdate, actionLog", wsMsg.Type))
		}
	}
}

// handleRegister 处理注册消息
func (ac *AgentConnection) handleRegister(am *AgentManager, content interface{}) {
	contentBytes, _ := json.Marshal(content)
	var reg AgentRegisterContent
	if err := json.Unmarshal(contentBytes, &reg); err != nil {
		ac.sendError("注册消息格式错误")
		return
	}

	// 使用validator验证结构体
	if err := validate.Struct(reg); err != nil {
		errorMsg := formatValidationErrors(err)
		ac.sendError(errorMsg)
		return
	}

	// 检查是否已存在同ID的连接
	am.mu.Lock()
	if existingConn, exists := am.connections[reg.AgentID]; exists {
		// 关闭旧连接
		existingConn.stateMu.Lock()
		existingConn.isActive = false
		existingConn.stateMu.Unlock()
		existingConn.conn.Close()
		delete(am.connections, reg.AgentID)
	}
	am.mu.Unlock()

	// 设置连接状态
	ac.stateMu.Lock()
	ac.agentID = reg.AgentID
	ac.currentTaskID = "" // 重置当前任务ID
	ac.stateMu.Unlock()

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

// handleDisconnect 处理主动断开连接
func (ac *AgentConnection) handleDisconnect(am *AgentManager, content interface{}) {
	contentBytes, _ := json.Marshal(content)
	var dc DisconnectContent
	if err := json.Unmarshal(contentBytes, &dc); err != nil {
		ac.sendError("断开连接消息格式错误")
		return
	}

	// 使用validator验证结构体
	if err := validate.Struct(dc); err != nil {
		errorMsg := formatValidationErrors(err)
		ac.sendError(errorMsg)
		return
	}

	// 验证身份一致性
	ac.stateMu.RLock()
	agentID := ac.agentID
	ac.stateMu.RUnlock()

	if agentID == "" || agentID != dc.AgentID {
		ac.sendError("断开连接消息身份验证失败")
		return
	}

	// 从连接管理器中移除
	am.mu.Lock()
	delete(am.connections, agentID)
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
	ac.stateMu.Lock()
	ac.isActive = false
	ac.stateMu.Unlock()
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
			ac.stateMu.RLock()
			if !ac.isActive {
				ac.stateMu.RUnlock()
				return
			}

			// 设置写超时
			ac.conn.SetWriteDeadline(time.Now().Add(writeWait))

			// 尝试发送ping消息
			err := ac.conn.WriteMessage(websocket.PingMessage, nil)
			if err != nil {
				ac.stateMu.RUnlock()

				// 尝试重试一次
				time.Sleep(1 * time.Second)
				ac.stateMu.RLock()
				if !ac.isActive {
					ac.stateMu.RUnlock()
					return
				}
				ac.conn.SetWriteDeadline(time.Now().Add(writeWait))
				err = ac.conn.WriteMessage(websocket.PingMessage, nil)
				if err != nil {
					ac.stateMu.RUnlock()
					ac.stateMu.Lock()
					ac.isActive = false
					ac.stateMu.Unlock()
					return
				}
			}

			ac.stateMu.RUnlock()
		}
	}
}

// cleanup 清理连接
func (ac *AgentConnection) cleanup(am *AgentManager) {
	ac.stateMu.Lock()
	agentID := ac.agentID
	ac.stateMu.Unlock()

	if agentID != "" {
		am.mu.Lock()
		delete(am.connections, agentID)
		am.mu.Unlock()

		// ac.store.UpdateOnlineStatus(ac.agentID, false)
	}

	ac.stateMu.Lock()
	ac.isActive = false
	ac.stateMu.Unlock()
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

	// 设置写超时
	ac.conn.SetWriteDeadline(time.Now().Add(writeWait))

	err := ac.conn.WriteJSON(response)
	if err != nil {
		// 如果发送错误响应都失败，说明连接可能有问题
		ac.stateMu.Lock()
		ac.isActive = false
		ac.stateMu.Unlock()
	}
}

// 通用事件处理函数
func (ac *AgentConnection) handleAgentEvent(am *AgentManager, content interface{}, eventType string) {
	contentBytes, err := json.Marshal(content)
	if err != nil {
		ac.sendError(fmt.Sprintf("%s事件序列化失败: %v", eventType, err))
		return
	}

	var eventMessage TaskEventMessage
	if err := json.Unmarshal(contentBytes, &eventMessage); err != nil {
		ac.sendError(fmt.Sprintf("%s事件格式错误: %v", eventType, err))
		return
	}

	// 使用validator验证TaskEventMessage
	if err := validate.Struct(eventMessage); err != nil {
		errorMsg := formatValidationErrors(err)
		ac.sendError(fmt.Sprintf("%s事件验证失败: %s", eventType, errorMsg))
		return
	}

	// 从TaskEventMessage中提取sessionId和事件数据
	sessionId := eventMessage.SessionID
	event := eventMessage.Event

	// 转发给 TaskManager 处理
	am.mu.RLock()
	if am.taskManager != nil {
		am.taskManager.HandleAgentEvent(sessionId, eventType, event)
	}
	am.mu.RUnlock()
}

// 添加获取可用 Agent 的方法
func (am *AgentManager) GetAvailableAgents() []*AgentConnection {
	am.mu.RLock()
	defer am.mu.RUnlock()

	var availableAgents []*AgentConnection
	for _, conn := range am.connections {
		conn.stateMu.RLock()
		if conn.isActive {
			availableAgents = append(availableAgents, conn)
		}
		conn.stateMu.RUnlock()
	}
	return availableAgents
}

// IsConnectionHealthy 检查连接是否健康
func (ac *AgentConnection) IsConnectionHealthy() bool {
	ac.stateMu.RLock()
	if !ac.isActive {
		ac.stateMu.RUnlock()
		return false
	}
	ac.stateMu.RUnlock()

	// 尝试发送一个 ping 消息来测试连接
	ac.conn.SetWriteDeadline(time.Now().Add(5 * time.Second)) // 5秒超时
	err := ac.conn.WriteMessage(websocket.PingMessage, nil)
	if err != nil {
		// 连接不可用，标记为非活跃
		ac.stateMu.Lock()
		ac.isActive = false
		ac.stateMu.Unlock()
		return false
	}

	return true
}

// SendMessageWithRetry 发送消息并处理重试
func (ac *AgentConnection) SendMessageWithRetry(message interface{}, maxRetries int) error {
	ac.stateMu.RLock()
	if !ac.isActive {
		ac.stateMu.RUnlock()
		return fmt.Errorf("连接不活跃")
	}
	ac.stateMu.RUnlock()

	var lastErr error
	for i := 0; i < maxRetries; i++ {
		// 设置写超时
		ac.conn.SetWriteDeadline(time.Now().Add(writeWait))

		err := ac.conn.WriteJSON(message)
		if err == nil {
			return nil // 发送成功
		}

		lastErr = err

		// 如果是超时错误，等待一下再重试
		if strings.Contains(err.Error(), "timeout") || strings.Contains(err.Error(), "i/o timeout") {
			time.Sleep(time.Duration(i+1) * time.Second) // 递增等待时间
			continue
		}

		// 其他错误直接返回
		break
	}

	// 所有重试都失败了，标记连接为非活跃
	ac.stateMu.Lock()
	ac.isActive = false
	ac.stateMu.Unlock()
	return fmt.Errorf("发送消息失败，已重试 %d 次: %v", maxRetries, lastErr)
}

// SetTaskManager 设置 TaskManager 引用
func (am *AgentManager) SetTaskManager(taskManager *TaskManager) {
	am.mu.Lock()
	defer am.mu.Unlock()
	am.taskManager = taskManager
}

// StartConnectionMonitor 启动连接监控
func (am *AgentManager) StartConnectionMonitor() {
	go func() {
		ticker := time.NewTicker(30 * time.Second) // 每30秒检查一次
		defer ticker.Stop()

		for range ticker.C {
			am.mu.RLock()
			connections := make([]*AgentConnection, 0, len(am.connections))
			for _, conn := range am.connections {
				connections = append(connections, conn)
			}
			am.mu.RUnlock()

			for _, conn := range connections {
				conn.stateMu.RLock()
				if conn.isActive {
					// 检查连接健康状态
					if !conn.IsConnectionHealthy() {
						gologger.Printf("Agent %s 连接不健康，标记为非活跃", conn.agentID)
						conn.stateMu.RUnlock()
						conn.stateMu.Lock()
						conn.isActive = false
						conn.stateMu.Unlock()
					} else {
						conn.stateMu.RUnlock()
					}
				} else {
					conn.stateMu.RUnlock()
				}
			}
		}
	}()
}
