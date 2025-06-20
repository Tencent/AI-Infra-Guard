package websocket

// 任务创建请求结构体
// 对应前端创建任务时的输入
// 例如：{"id":..., "sessionId":..., "task":..., ...}
type TaskCreateRequest struct {
	ID             string                 `json:"id"`
	SessionID      string                 `json:"sessionId"`
	Task           string                 `json:"task"`
	Timestamp      int64                  `json:"timestamp"`
	Content        string                 `json:"content"`
	Params         map[string]interface{} `json:"params"`
	Attachments    []string               `json:"attachments"`
	CountryIsoCode string                 `json:"countryIsoCode"`
}

// 通用事件消息体（SSE推送）
type TaskEventMessage struct {
	ID        string      `json:"id"`
	Type      string      `json:"type"`
	SessionID string      `json:"sessionId"`
	Timestamp int64       `json:"timestamp"`
	Event     interface{} `json:"event"`
}

// liveStatus 事件体
// {"type":"liveStatus", ...}
type LiveStatusEvent struct {
	ID        string `json:"id"`
	Type      string `json:"type"`
	Timestamp int64  `json:"timestamp"`
	Text      string `json:"text"`
}

// planUpdate 事件体
type PlanUpdateEvent struct {
	ID        string         `json:"id"`
	Type      string         `json:"type"`
	Timestamp int64          `json:"timestamp"`
	Tasks     []PlanTaskItem `json:"tasks"`
}

type PlanTaskItem struct {
	Status    string `json:"status"`
	Title     string `json:"title"`
	StartedAt int64  `json:"startedAt"`
}

// newPlanStep 事件体
type NewPlanStepEvent struct {
	ID        string `json:"id"`
	Type      string `json:"type"`
	Timestamp int64  `json:"timestamp"`
	StepID    string `json:"stepId"`
	Title     string `json:"title"`
}

// statusUpdate 事件体
type StatusUpdateEvent struct {
	ID          string `json:"id"`
	Type        string `json:"type"`
	Timestamp   int64  `json:"timestamp"`
	AgentStatus string `json:"agentStatus"`
	Brief       string `json:"brief"`
	Description string `json:"description"`
	NoRender    bool   `json:"noRender"`
	PlanStepID  string `json:"planStepId"`
}

// toolUsed 事件体
type ToolUsedEvent struct {
	ID          string      `json:"id"`
	Type        string      `json:"type"`
	Timestamp   int64       `json:"timestamp"`
	ActionID    string      `json:"actionId"`
	Tool        string      `json:"tool"`
	Status      string      `json:"status"`
	PlanStepID  string      `json:"planStepId"`
	Brief       string      `json:"brief"`
	Description string      `json:"description"`
	Message     interface{} `json:"message"`
	Detail      interface{} `json:"detail"`
}

// 任务分配消息（Server -> Agent）
type TaskAssignMessage struct {
	Type    string      `json:"type"`
	Content TaskContent `json:"content"`
}

// 任务内容
type TaskContent struct {
	SessionID   string                 `json:"session_id"`
	TaskType    string                 `json:"task_type"`
	Content     string                 `json:"content"`
	Params      map[string]interface{} `json:"params"`
	Attachments []string               `json:"attachments"`
	Timeout     int                    `json:"timeout"`
}

// 任务更新请求结构体
type TaskUpdateRequest struct {
	Title string `json:"title"` // 任务标题
}
