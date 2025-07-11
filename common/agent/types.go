package agent

import "encoding/json"

// Agent消息类型常量
const (
	// Agent -> Server 消息类型
	AgentMsgTypeRegister = "register" // 注册消息

	AgentMsgTypeResultUpdate = "resultUpdate" // 结果更新
	AgentMsgTypeActionLog    = "actionLog"    // 插件日志
	AgentMsgTypeToolUsed     = "toolUsed"     // 插件工作状态
	AgentMsgTypeNewPlanStep  = "newPlanStep"  // 新建执行步骤
	AgentMsgTypeStatusUpdate = "statusUpdate" // 更新步骤状态
	AgentMsgTypePlanUpdate   = "planUpdate"   // 更新任务计划

	// Server -> Agent 消息类型
	ServerMsgTypeRegisterResp = "register_ack" // 注册响应
	ServerMsgTypeTaskAssign   = "task_assign"  // 任务分配
)

// 任务状态枚举
const (
	TaskStatusPending  = "pending"  // 等待中
	TaskStatusRunning  = "running"  // 执行中
	TaskStatusComplete = "complete" // 完成
	TaskStatusFailed   = "failed"   // 失败
)

// 插件状态枚举
const (
	ToolStatusDoing = "doing" // 执行中
	ToolStatusDone  = "done"  // 已完成
)

// Agent状态枚举
const (
	AgentStatusRunning   = "running"   // 执行中
	AgentStatusCompleted = "completed" // 已完成
	AgentStatusFailed    = "failed"    // 失败
	AgentStatusIdle      = "idle"      // 空闲
)

type statusString string

// 子任务状态枚举
const (
	SubTaskStatusTodo  statusString = "todo"  // 待办
	SubTaskStatusDoing statusString = "doing" // 执行中
	SubTaskStatusDone  statusString = "done"  // 已完成
)

// 任务类型
const (
	TaskTypeTestDemo           = "Test-Demo"
	TaskTypeAIInfraScan        = "AI-Infra-Scan"
	TaskTypeMcpScan            = "Mcp-Scan"
	TaskTypeModelRedteamReport = "Model-Redteam-Report"
	TaskTypeModelJailbreak     = "Model-Jailbreak"
)

type AgentInfo struct {
	ID           string   `json:"agent_id"` // Agent唯一标识
	HostName     string   `json:"hostname"`
	IP           string   `json:"ip"`           // Agent名称
	Version      string   `json:"version"`      // Agent版本
	Capabilities []string `json:"capabilities"` // Agent能力列表
	Metadata     string   `json:"metadata"`     // 额外元数据
}

// AgentStatus Agent状态信息
type AgentStatus struct {
	Status    string  `json:"status"`     // 当前状态
	Load      float64 `json:"load"`       // 负载指标 (0-1)
	Memory    float64 `json:"memory"`     // 内存使用率
	CPU       float64 `json:"cpu"`        // CPU使用率
	TaskCount int     `json:"task_count"` // 当前任务数量
	Timestamp int64   `json:"timestamp"`  // 时间戳
}

type RequestData struct {
	Type    string      `json:"type"`
	Content interface{} `json:"content"`
}

type ResponseData struct {
	Type    string          `json:"type"`
	Content json.RawMessage `json:"content"`
}

// Disconnect Agent断开
type Disconnect struct {
	AgentID string `json:"agent_id"`
	Reason  string `json:"reason"` // 断开原因
}

// TaskRequest 任务请求
type TaskRequest struct {
	SessionId   string          `json:"sessionId"` // 任务ID
	TaskType    string          `json:"taskType"`  // 任务类型
	Params      json.RawMessage `json:"params"`    // 任务参数
	Timeout     int             `json:"timeout"`   // 超时时间(秒)
	Content     string          `json:"content"`
	Language    string          `json:"countryIsoCode"`
	Attachments []string        `json:"attachments"`
}

// Event 事件结构
type Event struct {
	ID        string                 `json:"id"`        // 消息id
	Type      string                 `json:"type"`      // 消息类型
	Timestamp int64                  `json:"timestamp"` // 时间戳
	Result    map[string]interface{} `json:"result"`    // 任务结果
}

// ResultUpdate 任务结果更新消息（前端格式）
type ResultUpdate struct {
	ID        string `json:"id"`        // 消息id
	Type      string `json:"type"`      // 消息类型，固定为"event"
	SessionId string `json:"sessionId"` // 任务的id
	Timestamp int64  `json:"timestamp"` // 时间戳
	Event     Event  `json:"event"`     // 事件数据
}

// ==================== 插件日志相关结构 ====================

// ActionLogEvent 插件日志事件结构
type ActionLogEvent struct {
	ID         string `json:"id"`         // 消息id
	Type       string `json:"type"`       // 消息类型，固定为"actionLog"
	Timestamp  int64  `json:"timestamp"`  // 时间戳
	ActionId   string `json:"actionId"`   // 插件id
	Tool       string `json:"tool"`       // 插件名
	PlanStepId string `json:"planStepId"` // 执行步骤id
	ActionLog  string `json:"actionLog"`  // 插件日志
}

// ActionLogUpdate 插件日志更新消息（前端格式）
type ActionLogUpdate struct {
	ID        string         `json:"id"`        // 消息id
	Type      string         `json:"type"`      // 消息类型，固定为"event"
	SessionId string         `json:"sessionId"` // 任务的id
	Timestamp int64          `json:"timestamp"` // 时间戳
	Event     ActionLogEvent `json:"event"`     // 事件数据
}

// ActionLogContent Agent发送给服务器的插件日志内容
type ActionLogContent struct {
	Type    string          `json:"type"`    // 固定为"actionLog"
	Content ActionLogUpdate `json:"content"` // 插件日志数据
}

// ==================== 插件工作状态相关结构 ====================

// ToolMessage 插件调用消息
type ToolMessage struct {
	Action string `json:"action"` // 调用插件的动作
	Param  string `json:"param"`  // 调用插件的参数
}

// Tool 插件信息
type Tool struct {
	ToolId  string       `json:"toolId"`  // 插件id
	Tool    string       `json:"tool"`    // 插件名
	Status  statusString `json:"status"`  // 插件执行状态（doing，done）
	Brief   string       `json:"brief"`   // 插件简要描述
	Message ToolMessage  `json:"message"` // 插件调用描述
	Result  string       `json:"result"`  // 插件执行结果
}

// ToolUsedEvent 插件工作状态事件结构
type ToolUsedEvent struct {
	ID          string `json:"id"`          // 消息id
	Type        string `json:"type"`        // 消息类型，固定为"toolUsed"
	Timestamp   int64  `json:"timestamp"`   // 时间戳
	Description string `json:"description"` // 描述信息
	PlanStepId  string `json:"planStepId"`  // 步骤id
	StatusId    string `json:"statusId"`    // 状态id
	Tools       []Tool `json:"tools"`       // 插件列表
}

// ToolUsedUpdate 插件工作状态更新消息（前端格式）
type ToolUsedUpdate struct {
	ID        string        `json:"id"`        // 消息id
	Type      string        `json:"type"`      // 消息类型，固定为"event"
	SessionId string        `json:"sessionId"` // 任务的id
	Timestamp int64         `json:"timestamp"` // 时间戳
	Event     ToolUsedEvent `json:"event"`     // 事件数据
}

// ToolUsedContent Agent发送给服务器的插件工作状态内容
type ToolUsedContent struct {
	Type    string         `json:"type"`    // 固定为"toolUsed"
	Content ToolUsedUpdate `json:"content"` // 插件工作状态数据
}

// ==================== 新建执行步骤相关结构 ====================

// NewPlanStepEvent 新建执行步骤事件结构
type NewPlanStepEvent struct {
	ID        string `json:"id"`        // 消息id
	Type      string `json:"type"`      // 消息类型，固定为"newPlanStep"
	Timestamp int64  `json:"timestamp"` // 时间戳
	StepId    string `json:"stepId"`    // 步骤id
	Title     string `json:"title"`     // 步骤名称
}

// NewPlanStepUpdate 新建执行步骤更新消息（前端格式）
type NewPlanStepUpdate struct {
	ID        string           `json:"id"`        // 消息id
	Type      string           `json:"type"`      // 消息类型，固定为"event"
	SessionId string           `json:"sessionId"` // 任务的id
	Timestamp int64            `json:"timestamp"` // 时间戳
	Event     NewPlanStepEvent `json:"event"`     // 事件数据
}

// NewPlanStepContent Agent发送给服务器的新建执行步骤内容
type NewPlanStepContent struct {
	Type    string            `json:"type"`    // 固定为"newPlanStep"
	Content NewPlanStepUpdate `json:"content"` // 新建执行步骤数据
}

// ==================== 更新步骤状态相关结构 ====================

// StatusUpdateEvent 更新步骤状态事件结构
type StatusUpdateEvent struct {
	ID          string `json:"id"`          // 消息id
	Type        string `json:"type"`        // 消息类型，固定为"statusUpdate"
	Timestamp   int64  `json:"timestamp"`   // 时间戳
	AgentStatus string `json:"agentStaus"`  // agent执行状态(注意：文档中是agentStaus，保持一致)
	Brief       string `json:"brief"`       // 简要描述
	Description string `json:"description"` // 状态描述
	NoRender    bool   `json:"noRender"`    // 是否不渲染
	PlanStepId  string `json:"planStepId"`  // 执行步骤id
}

// StatusUpdateUpdate 更新步骤状态更新消息（前端格式）
type StatusUpdateUpdate struct {
	ID        string            `json:"id"`        // 消息id
	Type      string            `json:"type"`      // 消息类型，固定为"event"
	SessionId string            `json:"sessionId"` // 任务的id
	Timestamp int64             `json:"timestamp"` // 时间戳
	Event     StatusUpdateEvent `json:"event"`     // 事件数据
}

// StatusUpdateContent Agent发送给服务器的更新步骤状态内容
type StatusUpdateContent struct {
	Type    string             `json:"type"`    // 固定为"statusUpdate"
	Content StatusUpdateUpdate `json:"content"` // 更新步骤状态数据
}

// ==================== 更新任务计划相关结构 ====================

// SubTask 子任务结构
type SubTask struct {
	Status    statusString `json:"status"`    // 子任务进度（todo，doing，done）
	Title     string       `json:"title"`     // 子任务名称
	StartedAt int64        `json:"startedAt"` // 子任务开始时间
	StepId    string       `json:"stepId"`    // 子任务id
}

// PlanUpdateEvent 更新任务计划事件结构
type PlanUpdateEvent struct {
	ID        string    `json:"id"`        // 消息id
	Type      string    `json:"type"`      // 消息类型，固定为"planUpdate"
	Timestamp int64     `json:"timestamp"` // 时间戳
	Tasks     []SubTask `json:"tasks"`     // 子任务列表
}

// PlanUpdateUpdate 更新任务计划更新消息（前端格式）
type PlanUpdateUpdate struct {
	ID        string          `json:"id"`        // 消息id
	Type      string          `json:"type"`      // 消息类型，固定为"event"
	SessionId string          `json:"sessionId"` // 任务的id
	Timestamp int64           `json:"timestamp"` // 时间戳
	Event     PlanUpdateEvent `json:"event"`     // 事件数据
}

// PlanUpdateContent Agent发送给服务器的更新任务计划内容
type PlanUpdateContent struct {
	Type    string           `json:"type"`    // 固定为"planUpdate"
	Content PlanUpdateUpdate `json:"content"` // 更新任务计划数据
}
