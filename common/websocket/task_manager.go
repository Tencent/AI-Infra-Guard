package websocket

import (
	"encoding/json"
	"fmt"
	"io"
	"mime"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
	"gorm.io/datatypes"
)

// 任务管理器相关数据结构

const (
	WSMsgTypeTaskAssign = "task_assign" // 任务分配

	// 任务状态常量
	TaskStatusTodo       = "todo"       // 待执行
	TaskStatusDoing      = "doing"      // 执行中
	TaskStatusDone       = "done"       // 已完成
	TaskStatusTerminated = "terminated" // 已终止
)

type TaskManager struct {
	mu           sync.RWMutex
	tasks        map[string]*TaskCreateRequest // sessionId -> 任务请求
	agentManager *AgentManager                 // 新增：引用 AgentManager
	taskStore    *database.TaskStore           // 新增：引用 TaskStore
	fileConfig   *FileUploadConfig             // 新增：文件上传配置
	sseManager   *SSEManager                   // 新增：SSE管理器
}

func NewTaskManager(agentManager *AgentManager, taskStore *database.TaskStore, fileConfig *FileUploadConfig, sseManager *SSEManager) *TaskManager {
	if fileConfig == nil {
		fileConfig = DefaultFileUploadConfig()
	}
	if sseManager == nil {
		sseManager = NewSSEManager()
	}
	return &TaskManager{
		tasks:        make(map[string]*TaskCreateRequest),
		agentManager: agentManager, // 注入 AgentManager
		taskStore:    taskStore,    // 注入 TaskStore
		fileConfig:   fileConfig,   // 注入文件上传配置
		sseManager:   sseManager,   // 注入SSE管理器
	}
}

// 添加任务
func (tm *TaskManager) AddTask(req *TaskCreateRequest) error {
	// 先存储任务到内存（dispatchTask需要从内存中获取任务）
	tm.mu.Lock()
	tm.tasks[req.SessionID] = req
	tm.mu.Unlock()

	// 尝试分发任务
	err := tm.dispatchTask(req.SessionID)
	if err != nil {
		// 分发失败，清理内存中的任务
		tm.mu.Lock()
		delete(tm.tasks, req.SessionID)
		tm.mu.Unlock()
		return fmt.Errorf("任务分发失败: %v", err)
	}

	// 任务分发成功，在数据库中创建会话记录
	session := &database.Session{
		ID:            req.SessionID,
		Username:      req.Username,
		Title:         generateTitle(req.Content),
		TaskType:      req.Task,
		Content:       req.Content,
		Params:        mustMarshalJSON(req.Params),
		Attachments:   mustMarshalJSON(req.Attachments),
		Status:        TaskStatusTodo,
		AssignedAgent: "",
		ContryIsoCode: req.ContryIsoCode,
	}

	err = tm.taskStore.CreateSession(session)
	if err != nil {
		// 如果存储失败，清理内存中的任务
		tm.mu.Lock()
		delete(tm.tasks, req.SessionID)
		tm.mu.Unlock()
		return fmt.Errorf("创建会话记录失败: %v", err)
	}

	return nil
}

// 获取任务
func (tm *TaskManager) GetTask(sessionId string) (*TaskCreateRequest, bool) {
	tm.mu.RLock()
	defer tm.mu.RUnlock()
	task, ok := tm.tasks[sessionId]
	return task, ok
}

// 新增：任务分发方法
func (tm *TaskManager) dispatchTask(sessionId string) error {
	// 1. 获取任务
	task, exists := tm.GetTask(sessionId)
	if !exists {
		gologger.Errorf("Task not found for sessionId: %s", sessionId)
		return fmt.Errorf("任务不存在")
	}

	// 2. 获取可用 Agent
	availableAgents := tm.agentManager.GetAvailableAgents()
	if len(availableAgents) == 0 {
		gologger.Info("No available agents")
		return fmt.Errorf("没有可用的Agent")
	}

	// 3. 选择 Agent（简单策略）
	selectedAgent := availableAgents[0]

	// 4. 检查连接健康状态
	if !selectedAgent.IsConnectionHealthy() {
		// 如果连接不健康，尝试其他 Agent
		for _, agent := range availableAgents[1:] {
			if agent.IsConnectionHealthy() {
				selectedAgent = agent
				break
			}
		}

		// 如果所有 Agent 都不健康，记录错误并返回
		if !selectedAgent.IsConnectionHealthy() {
			gologger.Errorf("所有agent连接都异常 for sessionId: %s", sessionId)
			return fmt.Errorf("所有agent连接都异常")
		}
	}

	// 5. 更新session的assigned_agent和开始时间
	err := tm.taskStore.UpdateSessionAssignedAgent(task.SessionID, selectedAgent.agentID)
	if err != nil {
		gologger.Errorf("无法更新session的assigned_agent: %v", err)
		return fmt.Errorf("无法更新session的assigned_agent")
	}

	// 6. 构造任务分配消息
	taskMsg := WSMessage{
		Type: WSMsgTypeTaskAssign,
		Content: TaskContent{
			SessionID:   task.SessionID,
			TaskType:    task.Task,
			Content:     task.Content,
			Params:      task.Params,
			Attachments: task.Attachments,
			Timeout:     3600,
		},
	}

	// 7. 使用重试机制发送给 Agent（设置较短的超时时间）
	err = selectedAgent.SendMessageWithRetry(taskMsg, 1) // 只重试1次，减少等待时间
	if err != nil {
		gologger.Errorf("下发任务给 %s 失败: %v", selectedAgent.agentID, err)
		// 如果发送失败，重置assigned_agent
		tm.taskStore.UpdateSessionAssignedAgent(task.SessionID, "")
		return fmt.Errorf("下发任务给 %s 失败: %v", selectedAgent.agentID, err)
	}

	gologger.Infof("任务下发成功: sessionId=%s, agentId=%s", task.SessionID, selectedAgent.agentID)
	return nil
}

// HandleAgentEvent 处理来自Agent的事件
func (tm *TaskManager) HandleAgentEvent(sessionId string, eventType string, event interface{}) {
	gologger.Debugf("收到Agent事件: sessionId=%s, eventType=%s", sessionId, eventType)

	// 使用通用事件处理函数
	tm.handleEvent(sessionId, eventType, event)

	// 根据事件类型记录特定日志
	switch eventType {
	case "liveStatus":
		if convertedEvent, err := convertToStruct(event, &LiveStatusEvent{}); err == nil {
			if liveStatusEvent, ok := convertedEvent.(*LiveStatusEvent); ok {
				gologger.Debugf("liveStatus事件详情: sessionId=%s, text=%s", sessionId, liveStatusEvent.Text)
			}
		}
	case "planUpdate":
		if convertedEvent, err := convertToStruct(event, &PlanUpdateEvent{}); err == nil {
			if planUpdateEvent, ok := convertedEvent.(*PlanUpdateEvent); ok {
				gologger.Debugf("planUpdate事件详情: sessionId=%s, tasks=%d", sessionId, len(planUpdateEvent.Tasks))
			}
		}
	case "newPlanStep":
		if convertedEvent, err := convertToStruct(event, &NewPlanStepEvent{}); err == nil {
			if newPlanStepEvent, ok := convertedEvent.(*NewPlanStepEvent); ok {
				gologger.Debugf("newPlanStep事件详情: sessionId=%s, stepId=%s", sessionId, newPlanStepEvent.StepID)
			}
		}
	case "statusUpdate":
		if convertedEvent, err := convertToStruct(event, &StatusUpdateEvent{}); err == nil {
			if statusUpdateEvent, ok := convertedEvent.(*StatusUpdateEvent); ok {
				gologger.Debugf("statusUpdate事件详情: sessionId=%s, status=%s", sessionId, statusUpdateEvent.AgentStatus)
			}
		}
	case "toolUsed":
		if convertedEvent, err := convertToStruct(event, &ToolUsedEvent{}); err == nil {
			if toolUsedEvent, ok := convertedEvent.(*ToolUsedEvent); ok {
				gologger.Debugf("toolUsed事件详情: sessionId=%s, tools=%d", sessionId, len(toolUsedEvent.Tools))
			}
		}
	case "actionLog":
		if convertedEvent, err := convertToStruct(event, &ActionLogEvent{}); err == nil {
			if actionLogEvent, ok := convertedEvent.(*ActionLogEvent); ok {
				gologger.Debugf("actionLog事件详情: sessionId=%s, actionId=%s", sessionId, actionLogEvent.ActionID)
			}
		}
	case "resultUpdate":
		if convertedEvent, err := convertToStruct(event, &ResultUpdateEvent{}); err == nil {
			if resultUpdateEvent, ok := convertedEvent.(*ResultUpdateEvent); ok {
				gologger.Debugf("resultUpdate事件详情: sessionId=%s, fileName=%s",
					sessionId, resultUpdateEvent.Result.FileName)

				// 更新任务状态为已完成
				err := tm.taskStore.UpdateSessionStatus(sessionId, TaskStatusDone)
				if err != nil {
					gologger.Errorf("更新任务状态为已完成失败: %v", err)
				} else {
					gologger.Infof("任务状态已更新为已完成: sessionId=%s", sessionId)
				}
				// 任务完成，可以清理资源
				tm.cleanupTask(sessionId)
			}
		}
	default:
		gologger.Warnf("未知的事件类型: %s", eventType)
	}
}

// convertToStruct 将 interface{} 转换为指定的结构体类型
func convertToStruct(data interface{}, target interface{}) (interface{}, error) {
	// 先序列化为JSON
	jsonData, err := json.Marshal(data)
	if err != nil {
		return nil, err
	}

	// 再反序列化为目标结构体
	err = json.Unmarshal(jsonData, target)
	if err != nil {
		return nil, err
	}

	return target, nil
}

// generateSecureFileName 生成安全的唯一文件名
func generateSecureFileName(originalName string) string {
	// 获取文件扩展名
	ext := filepath.Ext(originalName)

	// 获取不带扩展名的原始文件名
	baseName := strings.TrimSuffix(originalName, ext)

	// 生成UUID
	uuid := generateUUID()

	// 组合：UUID_原始文件名.扩展名
	return fmt.Sprintf("%s_%s%s", uuid, baseName, ext)
}

// generateUUID 生成简单的UUID
func generateUUID() string {
	return fmt.Sprintf("%d_%d", time.Now().UnixNano(), time.Now().Unix())
}

// 通用事件处理函数
func (tm *TaskManager) handleEvent(sessionId string, eventType string, event interface{}) {
	// 生成事件ID
	id := generateEventID()

	// 获取事件的时间戳
	timestamp := getEventTimestamp(event)

	// 存储事件到数据库
	err := tm.taskStore.StoreEvent(id, sessionId, eventType, event, timestamp)
	if err != nil {
		gologger.Errorf("存储%s事件失败: %v", eventType, err)
		return
	}

	// 推送给前端 SSE（先检查连接是否存在）
	err = tm.sseManager.SendEvent(id, sessionId, eventType, event)
	if err != nil {
		// 如果是连接不存在的错误，记录为调试信息而不是错误
		if strings.Contains(err.Error(), "连接不存在") {
			gologger.Debugf("SSE连接已关闭，跳过事件推送: sessionId=%s, eventType=%s", sessionId, eventType)
		} else {
			gologger.Errorf("推送%s事件到SSE失败: %v", eventType, err)
		}
		return
	}

	// 记录日志
	gologger.Debugf("%s事件已处理: sessionId=%s", eventType, sessionId)
}

// getEventTimestamp 获取事件的时间戳
func getEventTimestamp(event interface{}) int64 {
	// 使用反射获取Timestamp字段
	v := reflect.ValueOf(event)
	if v.Kind() == reflect.Ptr {
		v = v.Elem()
	}

	if v.Kind() == reflect.Struct {
		if field := v.FieldByName("Timestamp"); field.IsValid() && field.CanInterface() {
			if timestamp, ok := field.Interface().(int64); ok {
				return timestamp
			}
		}
	}

	// 如果无法获取时间戳，使用当前时间
	return time.Now().UnixMilli()
}

// TerminateTask 终止任务
func (tm *TaskManager) TerminateTask(sessionId string, username string) error {
	// 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		return fmt.Errorf("任务不存在")
	}

	// 验证用户权限（只有任务创建者才能终止任务）
	if session.Username != username {
		return fmt.Errorf("无权限操作此任务")
	}

	// 通知 Agent 终止任务
	if session.AssignedAgent != "" {
		tm.notifyAgentToTerminate(session.AssignedAgent, sessionId)
	}

	// 更新任务状态
	err = tm.taskStore.UpdateSessionStatus(sessionId, TaskStatusTerminated)
	if err != nil {
		return fmt.Errorf("更新任务状态失败")
	}

	// 发送终止事件给前端
	tm.sendTerminationEvent(sessionId)

	// 任务终止，清理资源
	go tm.cleanupTask(sessionId)

	return nil
}

// notifyAgentToTerminate 通知 Agent 终止任务
func (tm *TaskManager) notifyAgentToTerminate(agentID string, sessionId string) {
	// 获取 Agent 连接
	availableAgents := tm.agentManager.GetAvailableAgents()
	for _, agent := range availableAgents {
		if agent.agentID == agentID {
			// 发送终止消息给 Agent
			terminateMsg := WSMessage{
				Type: "terminate",
				Content: map[string]interface{}{
					"session_id": sessionId,
					"reason":     "用户主动终止",
				},
			}
			// 使用SendMessageWithRetry方法，避免直接访问conn
			err := agent.SendMessageWithRetry(terminateMsg, 3)
			if err != nil {
				gologger.Errorf("发送终止消息给Agent %s失败: %v", agentID, err)
			} else {
				gologger.Infof("终止消息已发送给Agent %s: sessionId=%s", agentID, sessionId)
			}
			break
		}
	}
}

// sendTerminationEvent 发送终止事件给前端
func (tm *TaskManager) sendTerminationEvent(sessionId string) {
	event := StatusUpdateEvent{
		ID:          generateEventID(),
		Type:        "statusUpdate",
		Timestamp:   time.Now().UnixMilli(),
		AgentStatus: "terminated",
		Brief:       "任务已终止",
		Description: "用户主动终止了任务执行",
		NoRender:    false,
	}

	// 使用通用事件处理函数
	tm.handleEvent(sessionId, "statusUpdate", event)

	gologger.Infof("终止事件已发送: sessionId=%s", sessionId)
}

// generateEventID 生成事件ID
func generateEventID() string {
	return time.Now().Format("20060102150405") + "_" + fmt.Sprintf("%d", time.Now().UnixNano())
}

// UpdateTask 更新任务信息
func (tm *TaskManager) UpdateTask(sessionId string, req *TaskUpdateRequest, username string) error {
	// 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		return fmt.Errorf("任务不存在")
	}

	// 验证用户权限（只有任务创建者才能更新任务）
	if session.Username != username {
		return fmt.Errorf("无权限操作此任务")
	}

	// 更新任务信息
	updates := map[string]interface{}{}

	if req.Title != "" {
		updates["title"] = req.Title
	}

	// 执行数据库更新
	err = tm.taskStore.UpdateSession(sessionId, updates)
	if err != nil {
		return fmt.Errorf("更新任务信息失败: %v", err)
	}

	return nil
}

// DeleteTask 删除任务
func (tm *TaskManager) DeleteTask(sessionId string, username string) error {
	// 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		return fmt.Errorf("任务不存在")
	}

	// 验证用户权限（只有任务创建者才能删除任务）
	if session.Username != username {
		return fmt.Errorf("无权限操作此任务")
	}

	// 使用事务删除会话及其所有消息
	err = tm.taskStore.DeleteSessionWithMessages(sessionId)
	if err != nil {
		return fmt.Errorf("删除任务失败: %v", err)
	}

	// 删除附件文件
	err = tm.deleteSessionAttachments(session)
	if err != nil {
		gologger.Warnf("删除附件文件失败: %v", err)
		// 附件删除失败不影响主流程，只记录警告
	}

	// 清理内存中的任务数据
	tm.mu.Lock()
	delete(tm.tasks, sessionId)
	tm.mu.Unlock()

	// 关闭SSE连接
	tm.CloseSSESession(sessionId)

	gologger.Infof("任务删除完成: sessionId=%s", sessionId)
	return nil
}

// deleteSessionAttachments 删除会话的附件文件
func (tm *TaskManager) deleteSessionAttachments(session *database.Session) error {
	if session.Attachments == nil {
		return nil
	}

	var attachmentURLs []string
	if err := json.Unmarshal(session.Attachments, &attachmentURLs); err != nil {
		return fmt.Errorf("解析附件URL失败: %v", err)
	}

	for _, url := range attachmentURLs {
		// 从URL中提取文件名
		fileName := tm.extractFileNameFromURL(url)
		if fileName == url {
			// 如果无法提取文件名，跳过
			continue
		}

		// 构建完整的文件路径
		filePath := filepath.Join(tm.fileConfig.UploadDir, fileName)

		// 删除文件
		if err := os.Remove(filePath); err != nil {
			if !os.IsNotExist(err) {
				gologger.Warnf("删除附件文件失败: %s, error: %v", filePath, err)
			}
		} else {
			gologger.Debugf("删除附件文件成功: %s", filePath)
		}
	}

	return nil
}

// UploadFileResult 文件上传结果
type UploadFileResult struct {
	OriginalName string `json:"original_name"` // 原始文件名
	FileURL      string `json:"file_url"`      // 文件访问URL
}

// UploadFile 上传文件
func (tm *TaskManager) UploadFile(file *multipart.FileHeader) (*UploadFileResult, error) {
	// 保存原始文件名
	originalName := file.Filename

	// 生成安全的唯一文件名
	fileName := generateSecureFileName(file.Filename)

	// 使用配置的上传目录
	uploadDir := tm.fileConfig.UploadDir
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		return nil, fmt.Errorf("创建上传目录失败: %v", err)
	}

	// 创建文件路径
	filePath := filepath.Join(uploadDir, fileName)

	// 保存文件到本地
	src, err := file.Open()
	if err != nil {
		return nil, fmt.Errorf("打开文件失败: %v", err)
	}
	defer src.Close()

	dst, err := os.Create(filePath)
	if err != nil {
		return nil, fmt.Errorf("创建文件失败: %v", err)
	}
	defer dst.Close()

	// 复制文件内容并验证
	written, err := io.Copy(dst, src)
	if err != nil {
		// 清理已创建的文件
		os.Remove(filePath)
		return nil, fmt.Errorf("保存文件失败: %v", err)
	}

	// 验证写入的文件大小
	if written != file.Size {
		os.Remove(filePath)
		return nil, fmt.Errorf("文件写入不完整")
	}

	// 生成文件访问URL
	fileURL := tm.fileConfig.GetFileURL(fileName)

	return &UploadFileResult{
		OriginalName: originalName,
		FileURL:      fileURL,
	}, nil
}

// GetUserTasks 获取指定用户的任务列表，只返回属于该用户的会话，确保用户只能看到自己的任务。
func (tm *TaskManager) GetUserTasks(username string) ([]map[string]interface{}, error) {
	// 从数据库获取用户的所有会话（已做严格过滤）
	sessions, err := tm.taskStore.GetUserSessions(username)
	if err != nil {
		return nil, fmt.Errorf("获取用户任务失败: %v", err)
	}

	// 转换为前端需要的格式
	var tasks []map[string]interface{}
	for _, session := range sessions {
		task := map[string]interface{}{
			"sessionId":     session.ID,
			"title":         session.Title,
			"taskType":      session.TaskType,
			"status":        session.Status,
			"contryIsoCode": session.ContryIsoCode,
			"updatedAt":     session.UpdatedAt, // 直接使用时间戳毫秒级
		}
		tasks = append(tasks, task)
	}

	return tasks, nil
}

// 辅助函数：生成任务标题
func generateTitle(content string) string {
	// 使用rune来正确处理UTF-8字符，避免截断中文字符
	runes := []rune(content)
	if len(runes) > 50 {
		return string(runes[:50])
	}
	return content
}

// 辅助函数：将interface{}转换为datatypes.JSON
func mustMarshalJSON(v interface{}) datatypes.JSON {
	if v == nil {
		return datatypes.JSON("{}")
	}
	data, err := json.Marshal(v)
	if err != nil {
		return datatypes.JSON("{}")
	}
	return datatypes.JSON(data)
}

// EstablishSSEConnection 建立SSE连接
func (tm *TaskManager) EstablishSSEConnection(w http.ResponseWriter, sessionId string, username string) error {
	return tm.sseManager.AddConnection(sessionId, username, w)
}

// CloseSSESession 关闭SSE会话
func (tm *TaskManager) CloseSSESession(sessionId string) {
	tm.sseManager.RemoveConnection(sessionId)
}

// 任务完成/中断时的清理
func (tm *TaskManager) cleanupTask(sessionId string) {
	// 清理内存中的任务数据
	tm.mu.Lock()
	delete(tm.tasks, sessionId)
	tm.mu.Unlock()

	// 注意：SSE连接已在resultUpdate事件处理中立即清理
	tm.CloseSSESession(sessionId)

	gologger.Infof("任务清理完成: sessionId=%s", sessionId)
}

// GetTaskDetail 获取任务详情
func (tm *TaskManager) GetTaskDetail(sessionId string, username string) (map[string]interface{}, error) {
	// 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		return nil, fmt.Errorf("任务不存在")
	}

	// 验证用户权限（只有任务创建者才能查看）
	if session.Username != username {
		return nil, fmt.Errorf("无权限查看此任务")
	}

	// 获取任务的所有消息
	messages, err := tm.taskStore.GetSessionMessages(sessionId)
	if err != nil {
		return nil, fmt.Errorf("获取任务消息失败: %v", err)
	}

	// 处理附件信息
	var files []map[string]interface{}
	if session.Attachments != nil {
		var attachmentURLs []string
		if err := json.Unmarshal(session.Attachments, &attachmentURLs); err == nil {
			for _, url := range attachmentURLs {
				// 从URL中提取文件名
				fileName := tm.extractFileNameFromURL(url)
				files = append(files, map[string]interface{}{
					"filename": fileName,
					"fileUrl":  url,
				})
			}
		}
	}

	// 处理消息列表
	var messageList []map[string]interface{}
	for _, msg := range messages {
		// 解析事件数据
		var eventData map[string]interface{}
		if err := json.Unmarshal(msg.EventData, &eventData); err != nil {
			gologger.Warnf("解析消息事件数据失败: %v", err)
			continue
		}

		messageList = append(messageList, map[string]interface{}{
			"id":        msg.ID,
			"type":      msg.Type,
			"timestamp": msg.Timestamp,
			"event":     eventData,
		})
	}

	// 构建返回数据
	detail := map[string]interface{}{
		"sessionId":     session.ID,
		"name":          session.Title,
		"status":        session.Status,
		"contryIsoCode": session.ContryIsoCode,
		"createdAt":     session.CreatedAt,
		"files":         files,
		"messages":      messageList,
	}

	return detail, nil
}

// extractFileNameFromURL 从文件URL中提取原始文件名
func (tm *TaskManager) extractFileNameFromURL(url string) string {
	// 新的文件名格式: UUID_原始文件名.扩展名
	if strings.Contains(url, "/") {
		parts := strings.Split(url, "/")
		if len(parts) > 0 {
			fileName := parts[len(parts)-1]

			// 新的文件名格式: UUID_原始文件名.扩展名
			if strings.Contains(fileName, "_") {
				// 查找第一个下划线，之后的部分是原始文件名
				firstUnderscoreIndex := strings.Index(fileName, "_")
				if firstUnderscoreIndex > 0 {
					// 返回下划线后的部分作为原始文件名
					return fileName[firstUnderscoreIndex+1:]
				}
			}

			// 如果没有下划线，直接返回文件名
			return fileName
		}
	}
	return url
}

// DownloadFile 下载文件
func (tm *TaskManager) DownloadFile(sessionId string, fileUrl string, username string, c *gin.Context) error {
	// 1. 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		return fmt.Errorf("任务不存在")
	}

	// 2. 验证用户权限（只有任务创建者才能下载文件）
	if session.Username != username {
		return fmt.Errorf("无权限访问此任务")
	}

	// 3. 验证文件URL是否属于该任务
	if session.Attachments == nil {
		return fmt.Errorf("文件不存在于此任务中")
	}

	var attachmentURLs []string
	if err := json.Unmarshal(session.Attachments, &attachmentURLs); err != nil {
		return fmt.Errorf("解析任务附件失败")
	}

	// 检查fileUrl是否在任务的附件列表中
	fileExists := false
	for _, url := range attachmentURLs {
		if url == fileUrl {
			fileExists = true
			break
		}
	}

	if !fileExists {
		return fmt.Errorf("文件不存在于此任务中")
	}

	// 4. 从fileUrl中提取文件名
	fileName := tm.extractFileNameFromURL(fileUrl)
	if fileName == fileUrl {
		// 如果无法提取文件名，使用URL的最后部分
		if strings.Contains(fileUrl, "/") {
			parts := strings.Split(fileUrl, "/")
			fileName = parts[len(parts)-1]
		} else {
			fileName = fileUrl
		}
	}

	// 5. 构建本地文件路径（使用URL的最后部分，即完整的文件名）
	localFileName := ""
	if strings.Contains(fileUrl, "/") {
		parts := strings.Split(fileUrl, "/")
		localFileName = parts[len(parts)-1]
	} else {
		localFileName = fileUrl
	}

	filePath := filepath.Join(tm.fileConfig.UploadDir, localFileName)

	// 添加调试日志
	gologger.Debugf("文件下载调试信息: fileUrl=%s, localFileName=%s, filePath=%s, uploadDir=%s",
		fileUrl, localFileName, filePath, tm.fileConfig.UploadDir)

	// 6. 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return fmt.Errorf("文件不存在")
	}

	// 7. 获取文件信息
	fileInfo, err := os.Stat(filePath)
	if err != nil {
		return fmt.Errorf("获取文件信息失败: %v", err)
	}

	// 8. 设置响应头
	// 获取文件的MIME类型
	ext := filepath.Ext(fileName)
	mimeType := mime.TypeByExtension(ext)
	if mimeType == "" {
		mimeType = "application/octet-stream"
	}

	// 设置Content-Type
	c.Header("Content-Type", mimeType)

	// 设置Content-Disposition，支持中文文件名
	// 使用UTF-8编码处理中文文件名
	encodedFileName := url.QueryEscape(fileName)
	c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"; filename*=UTF-8''%s", fileName, encodedFileName))

	// 设置Content-Length
	c.Header("Content-Length", fmt.Sprintf("%d", fileInfo.Size()))

	// 9. 打开文件并流式传输
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("打开文件失败: %v", err)
	}
	defer file.Close()

	// 10. 流式传输文件内容
	_, err = io.Copy(c.Writer, file)
	if err != nil {
		return fmt.Errorf("传输文件失败: %v", err)
	}

	gologger.Infof("文件下载成功: sessionId=%s, fileName=%s, fileSize=%d", sessionId, fileName, fileInfo.Size())
	return nil
}
