package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
)

// Agent 客户端结构
type Agent struct {
	// 基本信息
	info      AgentInfo
	serverURL string
	conn      *websocket.Conn

	// 任务管理
	Tasks    []*TaskContext
	taskFunc []TaskInterface

	// 通信管理
	sendChan chan interface{}
	ctx      context.Context
	cancel   context.CancelFunc

	// 配置
	mutex sync.RWMutex
}

// TaskContext 任务上下文
type TaskContext struct {
	Request   TaskRequest
	Status    string
	Progress  int
	StartTime time.Time
	Cancel    context.CancelFunc
	Result    interface{}
	Error     error
}

// AgentConfig Agent配置
type AgentConfig struct {
	ServerURL string
	Info      AgentInfo
}

// NewAgent 创建新的Agent实例
func NewAgent(config AgentConfig) *Agent {
	ctx, cancel := context.WithCancel(context.Background())
	agent := &Agent{
		info:      config.Info,
		serverURL: config.ServerURL,
		conn:      nil,
		Tasks:     make([]*TaskContext, 0),
		sendChan:  make(chan interface{}, 100),
		ctx:       ctx,
		cancel:    cancel,
		mutex:     sync.RWMutex{},
		taskFunc:  make([]TaskInterface, 0),
	}
	return agent
}

func (a *Agent) RegisterTaskFunc(taskFunc TaskInterface) {
	a.mutex.Lock()
	defer a.mutex.Unlock()
	a.taskFunc = append(a.taskFunc, taskFunc)
	a.info.Capabilities = append(a.info.Capabilities, taskFunc.GetName())
}

// Start 启动Agent
func (a *Agent) Start() error {
	// 尝试连接到服务器
	if err := a.connect(); err != nil {
		return fmt.Errorf("failed to connect to server: %v", err)
	}
	// 启动各种协程
	go a.handleSend()
	a.handleReceive()
	return nil
}

// Stop 停止Agent
func (a *Agent) Stop() {
	a.mutex.Lock()
	defer a.mutex.Unlock()

	// 取消所有运行中的任务
	for _, task := range a.Tasks {
		if task.Cancel != nil {
			task.Cancel()
		}
	}
	// 发送停止信号
	a.cancel()

	// 关闭连接
	if a.conn != nil {
		a.conn.Close()
	}
}

// connect 连接到服务器
func (a *Agent) connect() error {
	u, err := url.Parse(a.serverURL)
	if err != nil {
		return err
	}
	dialer := websocket.DefaultDialer
	conn, _, err := dialer.Dial(u.String(), nil)
	if err != nil {
		return err
	}
	conn.SetReadLimit(1024 * 1024 * 5)
	a.conn = conn

	// 设置ping处理器：收到ping消息后自动回复pong
	a.conn.SetPingHandler(func(appData string) error {
		gologger.Debugln("Received ping message, sending pong response", appData)
		return a.conn.WriteControl(websocket.PongMessage, []byte(""), time.Now().Add(time.Second*60))
	})

	// 设置pong处理器：收到pong消息时的处理逻辑
	a.conn.SetPongHandler(func(appData string) error {
		gologger.Debugln("Received pong message")
		// 更新读取超时时间，保持连接活跃
		return a.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	})

	// 发送注册消息
	return a.register()
}

// register 向服务器注册
func (a *Agent) register() error {
	registerMsg := RequestData{
		Type:    AgentMsgTypeRegister,
		Content: a.info,
	}
	a.sendChan <- registerMsg
	return nil
}

// Disconnect 断开连接
func (a *Agent) Disconnect(reason string) error {
	msg := Disconnect{
		AgentID: a.info.ID,
		Reason:  reason,
	}
	return a.sendMessage(msg)
}

// sendMessage 发送消息
func (a *Agent) sendMessage(msg interface{}) error {
	if a.conn == nil {
		return fmt.Errorf("connection is nil")
	}

	data, err := json.Marshal(msg)
	if err != nil {
		return err
	}

	return a.conn.WriteMessage(websocket.TextMessage, data)
}

// handleSend 处理发送队列
func (a *Agent) handleSend() {
	for {
		select {
		case <-a.ctx.Done():
			return
		case msg := <-a.sendChan:
			if err := a.sendMessage(msg); err != nil {
				gologger.WithError(err).Errorln("Failed to send message")
			}
		}
	}
}

// handleReceive 处理接收消息
func (a *Agent) handleReceive() {
	for {
		select {
		case <-a.ctx.Done():
			return
		default:
			if a.conn == nil {
				break
			}
			_, message, err := a.conn.ReadMessage()
			if err != nil {
				gologger.WithError(err).Errorln("Failed to read message")
				a.conn = nil
				return
			}
			gologger.Debugln("recv", string(message))
			if err = a.processMessage(message); err != nil {
				gologger.WithError(err).Errorln("Failed to send message")
			}
		}
	}
}

// processMessage 处理接收到的消息
func (a *Agent) processMessage(data []byte) error {
	var baseMsg ResponseData

	if err := json.Unmarshal(data, &baseMsg); err != nil {
		return err
	}

	switch baseMsg.Type {
	case ServerMsgTypeRegisterResp:
	case ServerMsgTypeTaskAssign:
		var task TaskRequest
		if err := json.Unmarshal(baseMsg.Content, &task); err != nil {
			return err
		}
		taskType := task.TaskType
		taskCtx, cancel := context.WithCancel(a.ctx)
		// 创建任务上下文
		if task.Timeout > 0 {
			//taskCtx, cancel = context.WithTimeout(taskCtx, time.Duration(task.Timeout)*time.Second)
		}
		// 加入task 上下文
		taskContext := &TaskContext{
			Request:   task,
			Status:    TaskStatusPending,
			Progress:  0,
			StartTime: time.Now(),
			Cancel:    cancel,
		}
		a.Tasks = append(a.Tasks, taskContext)
		for _, taskFunc := range a.taskFunc {
			if taskType == taskFunc.GetName() {
				gologger.Debugln("执行任务", taskFunc.GetName())
				taskContext.Status = TaskStatusRunning
				// 创建回调函数集合
				callbacks := TaskCallbacks{
					ResultCallback: func(result map[string]interface{}) {
						gologger.Debugln("ResultCallback", result)
						a.SendTaskResult(task.SessionId, result)
						gologger.Debugln("ResultCallback end")
					},
					ToolUseLogCallback: func(actionId, tool, planStepId, actionLog string) {
						a.SendsToolUsedLog(task.SessionId, actionId, tool, planStepId, actionLog)
						gologger.Debugln("ToolUseLogCallback", actionId, tool, planStepId, actionLog)
					},
					ToolUsedCallback: func(planStepId, statusId, description string, tools []Tool) {
						a.SendToolUsed(task.SessionId, planStepId, statusId, description, tools)
						gologger.Debugln("ToolUsedCallback", planStepId, statusId, description, tools)
					},
					NewPlanStepCallback: func(stepId, title string) {
						a.SendNewPlanStep(task.SessionId, stepId, title)
						gologger.Debugln("NewPlanStepCallback", stepId, title)
					},
					StepStatusUpdateCallback: func(planStepId, statusId, agentStatus, brief, description string) {
						a.SendStepStatusUpdate(task.SessionId, planStepId, statusId, agentStatus, brief, description)
						gologger.Debugln("StepStatusUpdateCallback", planStepId, statusId, agentStatus, brief, description)
					},
					PlanUpdateCallback: func(tasks []SubTask) {
						a.SendPlanUpdate(task.SessionId, tasks)
						gologger.Debugln("PlanUpdateCallback", tasks)
					},
					ErrorCallback: func(error string) {
						a.SendError(task.SessionId, error)
						gologger.Debugln("ErrorCallback", error)
					},
				}
				go func() {
					err := taskFunc.Execute(taskCtx, task, callbacks)
					if err != nil {
						a.SendError(task.SessionId, err.Error())
					}
				}()
				break
			}
		}
	default:
		return nil
	}
	return nil
}

// SendTaskResult 发送任务最终结果
func (a *Agent) SendTaskResult(sessionId string, result map[string]interface{}) error {
	timestamp := time.Now().Unix()
	msgId := uuid.New().String()

	// 构建事件数据
	event := Event{
		ID:        msgId,
		Type:      "resultUpdate",
		Timestamp: timestamp,
		Result:    result,
	}

	// 构建结果更新消息
	resultUpdate := ResultUpdate{
		ID:        msgId,
		Type:      "event",
		SessionId: sessionId,
		Timestamp: timestamp,
		Event:     event,
	}

	// 构建发送给服务器的消息
	resultUpdateContent := RequestData{
		Type:    AgentMsgTypeResultUpdate,
		Content: resultUpdate,
	}

	// 通过发送通道发送消息
	a.sendChan <- resultUpdateContent
	return nil
}

// GetTaskBySessionId 根据SessionId获取任务上下文
func (a *Agent) GetTaskBySessionId(sessionId string) *TaskContext {
	a.mutex.RLock()
	defer a.mutex.RUnlock()

	for _, task := range a.Tasks {
		if task.Request.SessionId == sessionId {
			return task
		}
	}
	return nil
}

func (a *Agent) SendsToolUsedLog(sessionId, actionId, tool, planStepId, actionLog string) error {
	timestamp := time.Now().Unix()
	msgId := uuid.New().String()

	// 构建插件日志事件数据
	event := ActionLogEvent{
		ID:         msgId,
		Type:       "actionLog",
		Timestamp:  timestamp,
		ActionId:   actionId,
		Tool:       tool,
		PlanStepId: planStepId,
		ActionLog:  actionLog,
	}

	// 构建插件日志更新消息
	actionLogUpdate := ActionLogUpdate{
		ID:        msgId,
		Type:      "event",
		SessionId: sessionId,
		Timestamp: timestamp,
		Event:     event,
	}

	// 构建发送给服务器的消息
	actionLogContent := ActionLogContent{
		Type:    AgentMsgTypeActionLog,
		Content: actionLogUpdate,
	}

	// 通过发送通道发送消息
	a.sendChan <- actionLogContent
	return nil
}

func (a *Agent) SendToolUsed(sessionId, planStepId, statusId, description string, tools []Tool) error {
	timestamp := time.Now().Unix()
	msgId := uuid.New().String()

	// 构建插件工作状态事件数据
	event := ToolUsedEvent{
		ID:          msgId,
		Type:        "toolUsed",
		Timestamp:   timestamp,
		Description: description,
		PlanStepId:  planStepId,
		StatusId:    statusId,
		Tools:       tools,
	}

	// 构建插件工作状态更新消息
	toolUsedUpdate := ToolUsedUpdate{
		ID:        msgId,
		Type:      "event",
		SessionId: sessionId,
		Timestamp: timestamp,
		Event:     event,
	}

	// 构建发送给服务器的消息
	toolUsedContent := ToolUsedContent{
		Type:    AgentMsgTypeToolUsed,
		Content: toolUsedUpdate,
	}

	// 通过发送通道发送消息
	a.sendChan <- toolUsedContent
	return nil
}

// CreateTool 创建工具使用信息
func CreateTool(toolId, tool string, status statusString, brief, action, param, result string) Tool {
	return Tool{
		ToolId: toolId,
		Tool:   tool,
		Status: status,
		Brief:  brief,
		Message: ToolMessage{
			Action: action,
			Param:  param,
		},
		Result: result,
	}
}

// SendNewPlanStep 新建执行步骤
func (a *Agent) SendNewPlanStep(sessionId, stepId, title string) error {
	timestamp := time.Now().Unix()
	msgId := uuid.New().String()

	// 构建新建执行步骤事件数据
	event := NewPlanStepEvent{
		ID:        msgId,
		Type:      AgentMsgTypeNewPlanStep,
		Timestamp: timestamp,
		StepId:    stepId,
		Title:     title,
	}

	// 构建新建执行步骤更新消息
	newPlanStepUpdate := NewPlanStepUpdate{
		ID:        msgId,
		Type:      "event",
		SessionId: sessionId,
		Timestamp: timestamp,
		Event:     event,
	}

	// 构建发送给服务器的消息
	newPlanStepContent := NewPlanStepContent{
		Type:    AgentMsgTypeNewPlanStep,
		Content: newPlanStepUpdate,
	}

	// 通过发送通道发送消息
	a.sendChan <- newPlanStepContent
	return nil
}

// SendStepStatusUpdate 发送更新步骤状态
func (a *Agent) SendStepStatusUpdate(sessionId, planStepId, statusId, agentStatus, brief, description string) error {
	timestamp := time.Now().Unix()

	// 构建更新步骤状态事件数据
	event := StatusUpdateEvent{
		ID:          statusId,
		Type:        AgentMsgTypeStatusUpdate,
		Timestamp:   timestamp,
		AgentStatus: agentStatus,
		Brief:       brief,
		Description: description,
		NoRender:    false,
		PlanStepId:  planStepId,
	}

	// 构建更新步骤状态更新消息
	statusUpdateUpdate := StatusUpdateUpdate{
		ID:        statusId,
		Type:      "event",
		SessionId: sessionId,
		Timestamp: timestamp,
		Event:     event,
	}

	// 构建发送给服务器的消息
	statusUpdateContent := StatusUpdateContent{
		Type:    AgentMsgTypeStatusUpdate,
		Content: statusUpdateUpdate,
	}

	// 通过发送通道发送消息
	a.sendChan <- statusUpdateContent
	return nil
}

// SendPlanUpdate 整体计划更新
func (a *Agent) SendPlanUpdate(sessionId string, tasks []SubTask) error {
	timestamp := time.Now().Unix()
	msgId := uuid.New().String()

	// 构建更新任务计划事件数据
	event := PlanUpdateEvent{
		ID:        msgId,
		Type:      "planUpdate",
		Timestamp: timestamp,
		Tasks:     tasks,
	}

	// 构建更新任务计划更新消息
	planUpdateUpdate := PlanUpdateUpdate{
		ID:        msgId,
		Type:      "event",
		SessionId: sessionId,
		Timestamp: timestamp,
		Event:     event,
	}

	// 构建发送给服务器的消息
	planUpdateContent := PlanUpdateContent{
		Type:    AgentMsgTypePlanUpdate,
		Content: planUpdateUpdate,
	}

	// 通过发送通道发送消息
	a.sendChan <- planUpdateContent
	return nil
}

// CreateSubTask 创建子任务的便捷方法
func CreateSubTask(status statusString, title string, startedAt int64, stepId string) SubTask {
	return SubTask{
		Status:    status,
		Title:     title,
		StartedAt: startedAt,
		StepId:    stepId,
	}
}

// SendError 发送错误
func (a *Agent) SendError(sessionId, msg string) error {
	timestamp := time.Now().Unix()
	msgId := uuid.New().String()

	// 构建更新任务计划事件数据
	event := ErrorEvent{
		Id:        msgId,
		Type:      "error",
		Timestamp: timestamp,
		Message:   msg,
	}

	// 构建更新任务计划更新消息
	planUpdateUpdate := ErrorUpdate{
		ID:        msgId,
		Type:      "event",
		SessionID: sessionId,
		Timestamp: timestamp,
		Event:     event,
	}

	// 构建发送给服务器的消息
	planUpdateContent := ErrorUpdateContent{
		Type:    AgentMsgTypeError,
		Content: planUpdateUpdate,
	}

	// 通过发送通道发送消息
	a.sendChan <- planUpdateContent
	return nil

}
