package websocket

import (
	"fmt"
	"mime/multipart"
	"net/http"
	"regexp"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"

	"github.com/gin-gonic/gin"
	"trpc.group/trpc-go/trpc-go/log"
)

// 任务创建请求结构体
// 对应前端创建任务时的输入
// 例如：{"id":..., "sessionId":..., "task":..., ...}
type TaskCreateRequest struct {
	ID             string                 `json:"id" validate:"required"`        // 消息ID（前端生成的对话ID）- 必需
	SessionID      string                 `json:"sessionId" validate:"required"` // 会话ID（任务ID）- 必需
	Username       string                 `json:"username,omitempty"`            // 用户名（可选，不传默认为公共用户）
	Task           string                 `json:"taskType" validate:"required"`  // 任务类型 - 必需
	Timestamp      int64                  `json:"timestamp" validate:"required"` // 时间戳 - 必需
	Content        string                 `json:"content" validate:"required"`   // 任务内容描述 - 必需
	Params         map[string]interface{} `json:"params,omitempty"`              // 任务参数 - 可选
	Attachments    []string               `json:"attachments,omitempty"`         // 附件列表 - 可选
	CountryIsoCode string                 `json:"countryIsoCode,omitempty"`      // 标识语言（可选）
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
	StepID    string `json:"stepId" validate:"required"`    // 步骤ID - 必需
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
	ID        string      `json:"id" validate:"required"`        // 事件ID - 必需
	Type      string      `json:"type" validate:"required"`      // 事件类型 - 必需
	Timestamp int64       `json:"timestamp" validate:"required"` // 时间戳 - 必需
	Result    interface{} `json:"result" validate:"required"`    // 结果信息 - 必需（不同任务类型结果字段各不相同）
}

// 任务分配消息（Server -> Agent）
type TaskAssignMessage struct {
	Type    string      `json:"type" validate:"required"`    // 消息类型 - 必需
	Content TaskContent `json:"content" validate:"required"` // 任务内容 - 必需
}

// 任务内容
type TaskContent struct {
	SessionID      string                 `json:"sessionId" validate:"required"` // 会话ID - 必需
	TaskType       string                 `json:"taskType" validate:"required"`  // 任务类型 - 必需
	Content        string                 `json:"content" validate:"required"`   // 任务内容 - 必需
	Params         map[string]interface{} `json:"params,omitempty"`              // 任务参数 - 可选
	Attachments    []string               `json:"attachments,omitempty"`         // 附件列表 - 可选
	Timeout        int                    `json:"timeout,omitempty"`             // 超时时间 - 可选
	CountryIsoCode string                 `json:"countryIsoCode,omitempty"`      // 语言标识 - 可选
}

// 任务更新请求结构体
type TaskUpdateRequest struct {
	Title string `json:"title" validate:"required"` // 任务标题 - 必需
}

// 辅助函数：从gin context中获取trace_id
func getTraceID(c *gin.Context) string {
	if traceID, exists := c.Get("trace_id"); exists {
		if id, ok := traceID.(string); ok {
			return id
		}
	}
	return "unknown"
}

// isValidSessionID 验证会话ID格式
func isValidSessionID(sessionId string) bool {
	// 只允许字母、数字、下划线、连字符
	matched, _ := regexp.MatchString(`^[a-zA-Z0-9_-]+$`, sessionId)
	return matched && len(sessionId) > 0 && len(sessionId) <= 50
}

// validateFileUpload 验证文件上传
func validateFileUpload(header *multipart.FileHeader) error {
	// 1. 文件名安全验证
	originalName := header.Filename
	if originalName == "" {
		return fmt.Errorf("文件名不能为空")
	}

	// 防止路径遍历攻击
	if strings.Contains(originalName, "..") || strings.Contains(originalName, "/") || strings.Contains(originalName, "\\") {
		return fmt.Errorf("文件名包含非法字符")
	}
	return nil
}

// validateTaskUpdateRequest 验证任务更新请求
func validateTaskUpdateRequest(req *TaskUpdateRequest) error {
	if req.Title != "" {
		// 清理和验证标题
		req.Title = strings.TrimSpace(req.Title)
		if len(req.Title) > 100 {
			return fmt.Errorf("标题长度超过限制")
		}
	}
	return nil
}

// SSE接口（实时事件推送）
func HandleTaskSSE(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "sessionId不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "无效的sessionId格式",
			"data":    nil,
		})
		return
	}

	username := c.GetString("username")

	// 建立SSE连接
	err := tm.EstablishSSEConnection(c.Writer, sessionId, username, traceID)
	if err != nil {
		log.Errorf("建立SSE连接失败: trace_id=%s, sessionId=%s, username=%s, error=%v", traceID, sessionId, username, err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "建立SSE连接失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("SSE连接建立成功: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 保持连接活跃，等待客户端断开
	<-c.Request.Context().Done()

	// 客户端断开连接时，清理SSE连接
	tm.CloseSSESession(sessionId)
	log.Infof("SSE连接已断开: trace_id=%s, sessionId=%s", traceID, sessionId)
}

// 新建任务接口
func HandleTaskCreate(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	var req TaskCreateRequest
	log.Infof("开始创建任务: trace_id=%s, req=%+v", traceID, req)
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "参数错误",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(req.SessionID) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	// 从中间件获取用户名
	username := c.GetString("username")

	// 设置用户名到请求中
	req.Username = username

	log.Infof("开始创建任务: trace_id=%s, sessionId=%s, username=%s, taskType=%s", traceID, req.SessionID, username, req.Task)

	// 调用TaskManager
	err := tm.AddTask(&req, traceID)
	if err != nil {
		log.Errorf("任务创建失败: trace_id=%s, sessionId=%s, username=%s, error=%v", traceID, req.SessionID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务创建失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("任务创建成功: trace_id=%s, sessionId=%s, username=%s", traceID, req.SessionID, username)

	// 生成任务标题
	title := tm.generateTaskTitle(&req)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务创建成功",
		"data": gin.H{
			"sessionId": req.SessionID,
			"title":     title,
		},
	})
}

// 终止任务接口
func HandleTerminateTask(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "会话ID不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	// 从中间件获取用户名
	username := c.GetString("username")

	log.Infof("用户请求终止任务: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 调用TaskManager（包含权限验证）
	err := tm.TerminateTask(sessionId, username, traceID)
	if err != nil {
		log.Errorf("任务终止失败: trace_id=%s, sessionId=%s, username=%s, error=%v", traceID, sessionId, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务终止失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("任务终止成功: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务终止成功",
		"data":    nil,
	})
}

// 更新任务信息接口
func HandleUpdateTask(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "会话ID不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	var req TaskUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 验证任务更新请求
	if err := validateTaskUpdateRequest(&req); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数验证失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 从中间件获取用户名
	username := c.GetString("username")

	log.Infof("开始更新任务: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 执行任务信息更新（包含权限验证）
	err := tm.UpdateTask(sessionId, &req, username, traceID)
	if err != nil {
		log.Errorf("任务信息更新失败: trace_id=%s, sessionId=%s, username=%s, error=%v", traceID, sessionId, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务信息更新失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("任务信息更新成功: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务信息更新成功",
		"data":    nil,
	})
}

// 删除任务接口
func HandleDeleteTask(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "会话ID不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	// 从中间件获取用户名
	username := c.GetString("username")

	log.Infof("开始删除任务: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 执行任务删除（包含权限验证）
	err := tm.DeleteTask(sessionId, username, traceID)
	if err != nil {
		log.Errorf("任务删除失败: trace_id=%s, sessionId=%s, username=%s, error=%v", traceID, sessionId, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务删除失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("任务删除成功: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务删除成功",
		"data":    nil,
	})
}

// HandleUploadFile 文件上传接口
// @Summary Upload file
// @Description Upload a file for task processing. Supports various file formats including zip, json, txt, etc.
// @Description The uploaded file will be stored securely and can be referenced in task creation.
// @Tags taskapi
// @Accept multipart/form-data
// @Produce json
// @Param file formData file true "File to upload" example:"example.zip"
// @Success 200 {object} object{status=int,message=string,data=object{fileUrl=string,filename=string,size=int}} "File uploaded successfully"
// @Failure 400 {object} object{status=int,message=string,data=object} "Invalid file or upload parameters"
// @Failure 500 {object} object{status=int,message=string,data=object} "Internal server error"
// @Router /api/v1/app/taskapi/upload [post]
func HandleUploadFile(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	// 获取上传的文件
	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取上传文件失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 验证文件,包含文件名和文件内容以及文件扩展的校验，不存在文件路径遍历风险
	if err := validateFileUpload(file); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "文件验证失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	username := c.GetString("username")
	log.Infof("开始文件上传: trace_id=%s, filename=%s, size=%d, username=%s", traceID, file.Filename, file.Size, username)

	// 执行文件上传
	uploadResult, err := tm.UploadFile(file, traceID)
	if err != nil {
		log.Errorf("文件上传失败: trace_id=%s, filename=%s, username=%s, error=%v", traceID, file.Filename, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "文件上传失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("文件上传成功: trace_id=%s, filename=%s, fileUrl=%s, username=%s", traceID, file.Filename, uploadResult.FileURL, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "文件上传成功",
		"data":    uploadResult,
	})
}

// 获取任务列表接口
func HandleGetTaskList(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	// 从中间件获取用户名
	username := c.GetString("username")
	query := c.Query("q")
	taskType := c.DefaultQuery("taskType", "")
	var err error

	log.Debugf("开始获取任务列表: trace_id=%s, username=%s, taskType=%s", traceID, username, taskType)
	var results []map[string]interface{}
	if query != "" {
		log.Debugf("搜索参数: trace_id=%s, username=%s, query=%s, taskType=%s", traceID, username, query, taskType)
		var searchParams database.SimpleSearchParams

		// 从查询字符串获取搜索关键词和任务类型
		searchParams.Query = query
		searchParams.TaskType = taskType
		searchParams.Page = 1
		searchParams.PageSize = 999
		// 调用TaskManager进行简化搜索
		results, err = tm.SearchUserTasksSimple(username, searchParams, traceID)
		if err != nil {
			log.Errorf("搜索任务失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "搜索任务失败: " + err.Error(),
				"data":    nil,
			})
			return
		}

	} else {
		// 获取用户的任务列表（支持taskType过滤）
		results, err = tm.GetUserTasksByType(username, taskType, traceID)
		if err != nil {
			log.Errorf("获取任务列表失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "获取任务列表失败: " + err.Error(),
				"data":    nil,
			})
			return
		}
	}

	log.Debugf("获取任务列表成功: trace_id=%s, username=%s, taskCount=%d", traceID, username, len(results))

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取任务列表成功",
		"data": gin.H{
			"tasks": results,
		},
	})
}

// HandleShare 分享任务
func HandleShare(c *gin.Context, tm *TaskManager) {
	var params struct {
		Session string `json:"sessionId" binding:"required"`
	}
	if err := c.ShouldBindJSON(&params); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}
	if params.Session == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "sessionId不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(params.Session) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "无效的sessionId格式",
			"data":    nil,
		})
		return
	}

	// 获取用户信息
	username := c.GetString("username")
	session, err := tm.taskStore.GetSession(params.Session)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "获取任务详情失败: " + err.Error(),
			"data":    nil,
		})
		return
	}
	if username != session.Username {
		c.JSON(http.StatusForbidden, gin.H{
			"status":  1,
			"message": "无权限访问",
			"data":    nil,
		})
		return
	}
	err = tm.taskStore.SetShare(params.Session, true)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "设置分享失败: " + err.Error(),
			"data":    nil,
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "设置分享成功",
		"data":    nil,
	})
}

// HandleGetTaskDetail 获取任务详情
func HandleGetTaskDetail(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "sessionId不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "无效的sessionId格式",
			"data":    nil,
		})
		return
	}

	// 获取用户信息
	username := c.GetString("username")

	log.Infof("开始获取任务详情: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 调用TaskManager获取任务详情
	detail, err := tm.GetTaskDetail(sessionId, username, traceID)
	if err != nil {
		log.Errorf("获取任务详情失败: trace_id=%s, sessionId=%s, username=%s, error=%v", traceID, sessionId, username, err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "获取任务详情失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("获取任务详情成功: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取任务详情成功",
		"data":    detail,
	})
}

// HandleDownloadFile 文件下载接口
func HandleDownloadFile(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "sessionId不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	// 解析请求体
	var req struct {
		FileURL string `json:"fileUrl" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 验证fileUrl格式
	if req.FileURL == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "文件URL不能为空",
			"data":    nil,
		})
		return
	}

	// 获取用户信息
	username := c.GetString("username")

	log.Infof("开始文件下载: trace_id=%s, sessionId=%s, fileUrl=%s, username=%s", traceID, sessionId, req.FileURL, username)

	// 执行文件下载
	err := tm.DownloadFile(sessionId, req.FileURL, username, c, traceID)
	if err != nil {
		log.Errorf("文件下载失败: trace_id=%s, sessionId=%s, fileUrl=%s, username=%s, error=%v", traceID, sessionId, req.FileURL, username, err)
		// 根据错误类型返回不同的状态码
		switch err.Error() {
		case "任务不存在":
			c.JSON(http.StatusNotFound, gin.H{
				"status":  1,
				"message": "任务不存在",
				"data":    nil,
			})
		case "文件不存在于此任务中":
			c.JSON(http.StatusNotFound, gin.H{
				"status":  1,
				"message": "文件不存在于此任务中",
				"data":    nil,
			})
		case "文件不存在":
			c.JSON(http.StatusNotFound, gin.H{
				"status":  1,
				"message": "文件不存在",
				"data":    nil,
			})
		default:
			c.JSON(http.StatusInternalServerError, gin.H{
				"status":  1,
				"message": "文件下载失败: " + err.Error(),
				"data":    nil,
			})
		}
		return
	}

	log.Infof("文件下载成功: trace_id=%s, sessionId=%s, fileUrl=%s, username=%s", traceID, sessionId, req.FileURL, username)

	// 文件下载成功，响应头已在DownloadFile方法中设置
}
