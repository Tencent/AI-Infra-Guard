package websocket

// 任务创建请求结构体
// 对应前端创建任务时的输入
// 例如：{"id":..., "sessionId":..., "task":..., ...}
type TaskCreateRequest struct {
	ID            string                 `json:"id" validate:"required"`        // 消息ID（前端生成的对话ID）- 必需
	SessionID     string                 `json:"sessionId" validate:"required"` // 会话ID（任务ID）- 必需
	Username      string                 `json:"username,omitempty"`            // 用户名（可选，不传默认为公共用户）
	Task          string                 `json:"task" validate:"required"`      // 任务类型 - 必需
	Timestamp     int64                  `json:"timestamp" validate:"required"` // 时间戳 - 必需
	Content       string                 `json:"content" validate:"required"`   // 任务内容描述 - 必需
	Params        map[string]interface{} `json:"params,omitempty"`              // 任务参数 - 可选
	Attachments   []string               `json:"attachments,omitempty"`         // 附件列表 - 可选
	ContryIsoCode string                 `json:"contryIsoCode,omitempty"`       // 标识语言（可选）
}

// 通用事件消息体（SSE推送）
type TaskEventMessage struct {
	ID        string      `json:"id" validate:"required"`        // 事件ID - 必需
	Type      string      `json:"type" validate:"required"`      // 事件类型 - 必需
	SessionID string      `json:"sessionId" validate:"required"` // 会话ID - 必需
	Timestamp int64       `json:"timestamp" validate:"required"` // 时间戳 - 必需
	Event     interface{} `json:"event" validate:"required"`     // 事件数据 - 必需
}

// liveStatus 事件体
// {"type":"liveStatus", ...}
type LiveStatusEvent struct {
	ID        string `json:"id" validate:"required"`        // 事件ID - 必需
	Type      string `json:"type" validate:"required"`      // 事件类型 - 必需
	Timestamp int64  `json:"timestamp" validate:"required"` // 时间戳 - 必需
	Text      string `json:"text" validate:"required"`      // 状态文本 - 必需
}

// planUpdate 事件体
type PlanUpdateEvent struct {
	ID        string         `json:"id" validate:"required"`        // 事件ID - 必需
	Type      string         `json:"type" validate:"required"`      // 事件类型 - 必需
	Timestamp int64          `json:"timestamp" validate:"required"` // 时间戳 - 必需
	Tasks     []PlanTaskItem `json:"tasks" validate:"required"`     // 任务列表 - 必需
}

type PlanTaskItem struct {
	Status    string `json:"status" validate:"required"`    // 任务状态 - 必需
	Title     string `json:"title" validate:"required"`     // 任务标题 - 必需
	StartedAt int64  `json:"startedAt" validate:"required"` // 开始时间 - 必需
}

// newPlanStep 事件体
type NewPlanStepEvent struct {
	ID        string `json:"id" validate:"required"`        // 事件ID - 必需
	Type      string `json:"type" validate:"required"`      // 事件类型 - 必需
	Timestamp int64  `json:"timestamp" validate:"required"` // 时间戳 - 必需
	StepID    string `json:"stepId" validate:"required"`    // 步骤ID - 必需
	Title     string `json:"title" validate:"required"`     // 步骤标题 - 必需
}

// statusUpdate 事件体
type StatusUpdateEvent struct {
	ID          string `json:"id" validate:"required"`          // 事件ID - 必需
	Type        string `json:"type" validate:"required"`        // 事件类型 - 必需
	Timestamp   int64  `json:"timestamp" validate:"required"`   // 时间戳 - 必需
	AgentStatus string `json:"agentStatus" validate:"required"` // Agent状态 - 必需
	Brief       string `json:"brief,omitempty"`                 // 简短描述 - 可选
	Description string `json:"description,omitempty"`           // 详细描述 - 可选
	NoRender    bool   `json:"noRender,omitempty"`              // 是否不渲染 - 可选
	PlanStepID  string `json:"planStepId,omitempty"`            // 计划步骤ID - 可选
}

// toolUsed 事件体（支持多工具并行）
type ToolUsedEvent struct {
	ID          string      `json:"id" validate:"required"`          // 事件ID - 必需
	Type        string      `json:"type" validate:"required"`        // 事件类型 - 必需
	Timestamp   int64       `json:"timestamp" validate:"required"`   // 时间戳 - 必需
	Description string      `json:"description" validate:"required"` // 描述 - 必需
	PlanStepID  string      `json:"planStepId,omitempty"`            // 计划步骤ID - 可选
	StatusID    string      `json:"statusId,omitempty"`              // 状态ID - 可选
	Tools       []ToolInfo  `json:"tools" validate:"required"`       // 工具列表 - 必需
	Detail      interface{} `json:"detail,omitempty"`                // 详细信息 - 可选
}

// 工具信息
type ToolInfo struct {
	ToolID  string      `json:"toolId" validate:"required"` // 工具ID - 必需
	Tool    string      `json:"tool" validate:"required"`   // 工具名称 - 必需
	Status  string      `json:"status" validate:"required"` // 状态 - 必需
	Brief   string      `json:"brief,omitempty"`            // 简短描述 - 可选
	Message interface{} `json:"message,omitempty"`          // 消息 - 可选
	Result  string      `json:"result,omitempty"`           // 结果 - 可选
}

// actionLog 事件体
type ActionLogEvent struct {
	ID         string `json:"id" validate:"required"`        // 事件ID - 必需
	Type       string `json:"type" validate:"required"`      // 事件类型 - 必需
	Timestamp  int64  `json:"timestamp" validate:"required"` // 时间戳 - 必需
	ActionID   string `json:"actionId" validate:"required"`  // 动作ID - 必需
	Tool       string `json:"tool" validate:"required"`      // 工具名称 - 必需
	PlanStepID string `json:"planStepId,omitempty"`          // 计划步骤ID - 可选
	ActionLog  string `json:"actionLog" validate:"required"` // 动作日志 - 必需
}

// resultUpdate 事件体（任务完成结果）
type ResultUpdateEvent struct {
	ID        string     `json:"id" validate:"required"`        // 事件ID - 必需
	Type      string     `json:"type" validate:"required"`      // 事件类型 - 必需
	Timestamp int64      `json:"timestamp" validate:"required"` // 时间戳 - 必需
	Result    ResultInfo `json:"result" validate:"required"`    // 结果信息 - 必需
}

// 结果信息
type ResultInfo struct {
	Brief       string `json:"brief" validate:"required"` // 简短描述 - 必需
	Description string `json:"description,omitempty"`     // 详细描述 - 可选
	FileName    string `json:"fileName,omitempty"`        // 文件名 - 可选
	FileURL     string `json:"fileUrl,omitempty"`         // 文件访问URL - 可选
}

// 任务分配消息（Server -> Agent）
type TaskAssignMessage struct {
	Type    string      `json:"type" validate:"required"`    // 消息类型 - 必需
	Content TaskContent `json:"content" validate:"required"` // 任务内容 - 必需
}

// 任务内容
type TaskContent struct {
	SessionID   string                 `json:"session_id" validate:"required"` // 会话ID - 必需
	TaskType    string                 `json:"task_type" validate:"required"`  // 任务类型 - 必需
	Content     string                 `json:"content" validate:"required"`    // 任务内容 - 必需
	Params      map[string]interface{} `json:"params,omitempty"`               // 任务参数 - 可选
	Attachments []string               `json:"attachments,omitempty"`          // 附件列表 - 可选
	Timeout     int                    `json:"timeout,omitempty"`              // 超时时间 - 可选
}

// 任务更新请求结构体
type TaskUpdateRequest struct {
	Title string `json:"title" validate:"required"` // 任务标题 - 必需
}
