package websocket

import (
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator/v10"
	"github.com/gorilla/websocket"
	"trpc.group/trpc-go/trpc-go/log"
	// "gorm.io/datatypes"
)

const (
	// WebSocket相关常量
	maxMessageSize    = 512 * 1024 * 1024 // 512MB
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
	conn    *websocket.Conn
	agentID string

	// 细粒度的锁控制
	stateMu sync.RWMutex // 保护连接状态（agentID, isActive）
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
			log.Errorf("WebSocket升级失败: error=%v", err)
			return
		}

		// ac := NewAgentConnection(conn, am.store)
		ac := NewAgentConnection(conn)
		log.Infof("新的Agent连接建立: remoteAddr=%s", conn.RemoteAddr().String())
		go ac.handleConnection(am)
	}
}

// handleConnection 处理单个连接的消息
func (ac *AgentConnection) handleConnection(am *AgentManager) {
	defer func() {
		ac.stateMu.RLock()
		agentID := ac.agentID
		remoteAddr := ac.conn.RemoteAddr().String()
		ac.stateMu.RUnlock()

		ac.cleanup(am)
		log.Infof("Agent连接处理结束: agentId=%s, remoteAddr=%s", agentID, remoteAddr)
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
			ac.stateMu.RLock()
			agentID := ac.agentID
			ac.stateMu.RUnlock()

			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Errorf("Agent连接异常断开: agentId=%s, error=%v", agentID, err)
			} else {
				log.Infof("Agent连接正常断开: agentId=%s, closeCode=%v", agentID, err)
			}
			break
		}

		var wsMsg WSMessage
		if err := json.Unmarshal(message, &wsMsg); err != nil {
			log.Errorf("Agent消息解析失败: agentId=%s, error=%v", ac.agentID, err)
			// 发送错误响应但不断开连接
			ac.sendError("消息格式错误请检查JSON格式")
			continue
		}

		// 验证消息类型
		if wsMsg.Type == "" {
			log.Errorf("Agent消息类型为空: agentId=%s", ac.agentID)
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
			log.Warnf("Agent发送未知消息类型: agentId=%s, type=%s", ac.agentID, wsMsg.Type)
			ac.sendError(fmt.Sprintf("未知的消息类型: %s。支持的类型: register, disconnect, liveStatus, planUpdate, newPlanStep, statusUpdate, toolUsed, resultUpdate, actionLog", wsMsg.Type))
		}
	}
}

// handleRegister 处理注册消息
func (ac *AgentConnection) handleRegister(am *AgentManager, content interface{}) {
	contentBytes, _ := json.Marshal(content)
	var rc AgentRegisterContent
	if err := json.Unmarshal(contentBytes, &rc); err != nil {
		log.Errorf("Agent注册消息解析失败: error=%v", err)
		ac.sendError("注册消息格式错误")
		return
	}

	// 使用validator验证结构体
	if err := validate.Struct(rc); err != nil {
		errorMsg := formatValidationErrors(err)
		log.Errorf("Agent注册验证失败: agentId=%s, error=%s", rc.AgentID, errorMsg)
		ac.sendError(errorMsg)
		return
	}

	// 检查是否已存在相同ID的Agent
	am.mu.Lock()
	if existingConn, exists := am.connections[rc.AgentID]; exists {
		am.mu.Unlock()
		log.Warnf("Agent ID已存在，断开旧连接: agentId=%s", rc.AgentID)
		// 断开旧连接
		existingConn.stateMu.Lock()
		existingConn.isActive = false
		existingConn.stateMu.Unlock()
		existingConn.conn.Close()
	} else {
		am.mu.Unlock()
	}

	// 注册新连接
	am.mu.Lock()
	am.connections[rc.AgentID] = ac
	am.mu.Unlock()

	// 更新连接状态
	ac.stateMu.Lock()
	ac.agentID = rc.AgentID
	ac.isActive = true
	ac.stateMu.Unlock()

	log.Infof("Agent注册成功: agentId=%s, hostname=%s, ip=%s, version=%s", rc.AgentID, rc.Hostname, rc.IP, rc.Version)
	// 发送注册成功响应
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
		log.Infof("Agent心跳检测已停止: agentId=%s", ac.agentID)
	}()

	log.Infof("Agent心跳检测已启动: agentId=%s, pingPeriod=%v", ac.agentID, pingPeriod)

	for range ticker.C {
		ac.stateMu.RLock()
		if !ac.isActive {
			ac.stateMu.RUnlock()
			log.Infof("Agent连接已标记为非活跃,停止心跳检测: agentId=%s", ac.agentID)
			return
		}
		agentID := ac.agentID
		ac.stateMu.RUnlock()

		// 设置写超时
		ac.conn.SetWriteDeadline(time.Now().Add(writeWait))

		// 尝试发送ping消息
		err := ac.conn.WriteMessage(websocket.PingMessage, nil)
		if err != nil {
			log.Warnf("Agent心跳发送失败,准备重试: agentId=%s, error=%v", agentID, err)

			// 尝试重试一次
			time.Sleep(1 * time.Second)
			ac.stateMu.RLock()
			if !ac.isActive {
				ac.stateMu.RUnlock()
				log.Infof("Agent连接在重试期间已标记为非活跃: agentId=%s", agentID)
				return
			}
			ac.stateMu.RUnlock()

			ac.conn.SetWriteDeadline(time.Now().Add(writeWait))
			err = ac.conn.WriteMessage(websocket.PingMessage, nil)
			if err != nil {
				log.Errorf("Agent心跳重试失败,连接已失效: agentId=%s, error=%v", agentID, err)

				// 标记连接为非活跃
				ac.stateMu.Lock()
				ac.isActive = false
				ac.stateMu.Unlock()

				log.Errorf("Agent连接已标记为失效: agentId=%s, 原因=心跳失败", agentID)
				return
			} else {
				log.Infof("Agent心跳重试成功: agentId=%s", agentID)
			}
		} else {
			log.Debugf("Agent心跳发送成功: agentId=%s", agentID)
		}
	}
}

// cleanup 清理连接
func (ac *AgentConnection) cleanup(am *AgentManager) {
	ac.stateMu.Lock()
	agentID := ac.agentID
	wasActive := ac.isActive
	ac.isActive = false
	ac.stateMu.Unlock()

	log.Infof("开始清理Agent连接: agentId=%s, wasActive=%v", agentID, wasActive)

	if agentID != "" {
		am.mu.Lock()
		// 检查是否真的存在于连接管理器中
		if _, exists := am.connections[agentID]; exists {
			delete(am.connections, agentID)
			log.Infof("Agent已从连接管理器中移除: agentId=%s", agentID)
		} else {
			log.Warnf("Agent不在连接管理器中，可能已被移除: agentId=%s", agentID)
		}
		am.mu.Unlock()

		// ac.store.UpdateOnlineStatus(ac.agentID, false)
	} else {
		log.Warnf("清理未注册的Agent连接: remoteAddr=%s", ac.conn.RemoteAddr().String())
	}

	// 关闭WebSocket连接
	err := ac.conn.Close()
	if err != nil {
		log.Warnf("关闭Agent连接时出错: agentId=%s, error=%v", agentID, err)
	} else {
		log.Infof("Agent连接已关闭: agentId=%s", agentID)
	}

	log.Infof("Agent连接清理完成: agentId=%s", agentID)
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
		log.Errorf("Agent事件序列化失败: agentId=%s, eventType=%s, error=%v", ac.agentID, eventType, err)
		ac.sendError(fmt.Sprintf("%s事件序列化失败: %v", eventType, err))
		return
	}

	var eventMessage TaskEventMessage
	if err := json.Unmarshal(contentBytes, &eventMessage); err != nil {
		log.Errorf("Agent事件格式错误: agentId=%s, eventType=%s, error=%v", ac.agentID, eventType, err)
		ac.sendError(fmt.Sprintf("%s事件格式错误: %v", eventType, err))
		return
	}

	// 使用validator验证TaskEventMessage
	if err := validate.Struct(eventMessage); err != nil {
		errorMsg := formatValidationErrors(err)
		log.Errorf("Agent事件验证失败: agentId=%s, eventType=%s, error=%s", ac.agentID, eventType, errorMsg)
		ac.sendError(fmt.Sprintf("%s事件验证失败: %s", eventType, errorMsg))
		return
	}

	// 从TaskEventMessage中提取sessionId和事件数据
	sessionId := eventMessage.SessionID
	event := eventMessage.Event

	log.Debugf("收到Agent事件: agentId=%s, sessionId=%s, eventType=%s", ac.agentID, sessionId, eventType)

	// 转发给 TaskManager 处理
	am.mu.RLock()
	if am.taskManager != nil {
		am.taskManager.HandleAgentEvent(sessionId, eventType, event)
	} else {
		log.Errorf("TaskManager未初始化，无法处理Agent事件: agentId=%s, sessionId=%s", ac.agentID, sessionId)
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

// SetTaskManager 设置 TaskManager 引用
func (am *AgentManager) SetTaskManager(taskManager *TaskManager) {
	am.mu.Lock()
	defer am.mu.Unlock()
	am.taskManager = taskManager
}
