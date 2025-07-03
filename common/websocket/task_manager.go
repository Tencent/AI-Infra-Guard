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

	"git.code.oa.com/trpc-go/trpc-go/log"
	_ "git.code.oa.com/trpc-go/trpc-log-zhiyan"
	"github.com/Tencent/AI-Infra-Guard/common/monitoring"
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
func (tm *TaskManager) AddTask(req *TaskCreateRequest, traceID string) error {
	log.Infof("开始添加任务: trace_id=%s, sessionId=%s, taskType=%s, username=%s", traceID, req.SessionID, req.Task, req.Username)

	// 开始任务监控（记录开始时间）
	monitoring.StartTaskMonitoring(req.SessionID)

	// 先存储任务到内存（dispatchTask需要从内存中获取任务）
	tm.mu.Lock()
	tm.tasks[req.SessionID] = req
	tm.mu.Unlock()

	// 尝试分发任务
	err := tm.dispatchTask(req.SessionID, traceID)
	if err != nil {
		// 分发失败，清理内存中的任务
		tm.mu.Lock()
		delete(tm.tasks, req.SessionID)
		tm.mu.Unlock()
		log.Errorf("任务分发失败: trace_id=%s, sessionId=%s, error=%v", traceID, req.SessionID, err)
		gologger.Errorf("任务分发失败: %v", err)

		// 上报任务创建失败监控
		monitoring.EndTaskCreationMonitoring(req.Task, "failed", req.SessionID)

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
		log.Errorf("创建会话记录失败: trace_id=%s, sessionId=%s, error=%v", traceID, req.SessionID, err)
		gologger.Errorf("创建会话记录失败: %v", err)

		// 上报任务创建失败监控
		monitoring.EndTaskCreationMonitoring(req.Task, "failed", req.SessionID)

		return fmt.Errorf("创建会话记录失败: %v", err)
	}

	log.Infof("任务添加成功: trace_id=%s, sessionId=%s, taskType=%s", traceID, req.SessionID, req.Task)
	gologger.Infof("任务添加成功: sessionId=%s, taskType=%s", req.SessionID, req.Task)

	// 上报任务创建成功监控
	monitoring.EndTaskCreationMonitoring(req.Task, "created", req.SessionID)

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
func (tm *TaskManager) dispatchTask(sessionId string, traceID string) error {
	log.Infof("开始分发任务: trace_id=%s, sessionId=%s", traceID, sessionId)

	// 1. 获取任务
	task, exists := tm.GetTask(sessionId)
	if !exists {
		log.Errorf("任务不存在: trace_id=%s, sessionId=%s", traceID, sessionId)
		gologger.Errorf("Task not found for sessionId: %s", sessionId)
		return fmt.Errorf("任务不存在")
	}

	// 2. 获取可用 Agent
	availableAgents := tm.agentManager.GetAvailableAgents()
	if len(availableAgents) == 0 {
		log.Warnf("没有可用的Agent: trace_id=%s, sessionId=%s", traceID, sessionId)
		gologger.Info("No available agents")
		return fmt.Errorf("没有可用的Agent")
	}

	log.Infof("找到可用Agent数量: trace_id=%s, sessionId=%s, count=%d", traceID, sessionId, len(availableAgents))

	// 3. 选择 Agent（简单策略）
	selectedAgent := availableAgents[0]

	// 4. 检查连接健康状态
	if !selectedAgent.IsConnectionHealthy() {
		log.Warnf("首选Agent连接不健康，尝试其他Agent: trace_id=%s, sessionId=%s, agentId=%s", traceID, sessionId, selectedAgent.agentID)
		// 如果连接不健康，尝试其他 Agent
		for _, agent := range availableAgents[1:] {
			if agent.IsConnectionHealthy() {
				selectedAgent = agent
				log.Infof("选择备用Agent: trace_id=%s, sessionId=%s, agentId=%s", traceID, sessionId, selectedAgent.agentID)
				break
			}
		}

		// 如果所有 Agent 都不健康，记录错误并返回
		if !selectedAgent.IsConnectionHealthy() {
			log.Errorf("所有agent连接都异常: trace_id=%s, sessionId=%s", traceID, sessionId)
			gologger.Errorf("所有agent连接都异常 for sessionId: %s", sessionId)
			return fmt.Errorf("所有agent连接都异常")
		}
	}

	// 5. 更新session的assigned_agent和开始时间
	err := tm.taskStore.UpdateSessionAssignedAgent(task.SessionID, selectedAgent.agentID)
	if err != nil {
		log.Errorf("无法更新session的assigned_agent: trace_id=%s, sessionId=%s, agentId=%s, error=%v", traceID, task.SessionID, selectedAgent.agentID, err)
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
		log.Errorf("下发任务给Agent失败: trace_id=%s, sessionId=%s, agentId=%s, error=%v", traceID, task.SessionID, selectedAgent.agentID, err)
		gologger.Errorf("下发任务给 %s 失败: %v", selectedAgent.agentID, err)
		// 如果发送失败，重置assigned_agent
		tm.taskStore.UpdateSessionAssignedAgent(task.SessionID, "")
		return fmt.Errorf("下发任务给 %s 失败: %v", selectedAgent.agentID, err)
	}

	log.Infof("任务分发成功: trace_id=%s, sessionId=%s, agentId=%s", traceID, task.SessionID, selectedAgent.agentID)
	gologger.Infof("任务下发成功: sessionId=%s, agentId=%s", task.SessionID, selectedAgent.agentID)
	return nil
}

// HandleAgentEvent 处理来自Agent的事件
func (tm *TaskManager) HandleAgentEvent(sessionId string, eventType string, event interface{}, traceID string) {
	log.Debugf("收到Agent事件: trace_id=%s, sessionId=%s, eventType=%s", traceID, sessionId, eventType)
	gologger.Debugf("收到Agent事件: trace_id=%s, sessionId=%s, eventType=%s", traceID, sessionId, eventType)

	// 使用通用事件处理函数
	tm.handleEvent(sessionId, eventType, event, traceID)

	// 根据事件类型记录特定日志
	switch eventType {
	case "liveStatus":
		if convertedEvent, err := convertToStruct(event, &LiveStatusEvent{}); err == nil {
			if liveStatusEvent, ok := convertedEvent.(*LiveStatusEvent); ok {
				log.Debugf("liveStatus事件详情: trace_id=%s, sessionId=%s, text=%s", traceID, sessionId, liveStatusEvent.Text)
				gologger.Debugf("liveStatus事件详情: trace_id=%s, sessionId=%s, text=%s", traceID, sessionId, liveStatusEvent.Text)
			}
		}
	case "planUpdate":
		if convertedEvent, err := convertToStruct(event, &PlanUpdateEvent{}); err == nil {
			if planUpdateEvent, ok := convertedEvent.(*PlanUpdateEvent); ok {
				log.Infof("收到计划更新: trace_id=%s, sessionId=%s, tasks=%d", traceID, sessionId, len(planUpdateEvent.Tasks))
				gologger.Debugf("planUpdate事件详情: trace_id=%s, sessionId=%s, tasks=%d", traceID, sessionId, len(planUpdateEvent.Tasks))
			}
		}
	case "newPlanStep":
		if convertedEvent, err := convertToStruct(event, &NewPlanStepEvent{}); err == nil {
			if newPlanStepEvent, ok := convertedEvent.(*NewPlanStepEvent); ok {
				log.Infof("新计划步骤: trace_id=%s, sessionId=%s, stepId=%s", traceID, sessionId, newPlanStepEvent.StepID)
				gologger.Debugf("newPlanStep事件详情: trace_id=%s, sessionId=%s, stepId=%s", traceID, sessionId, newPlanStepEvent.StepID)
			}
		}
	case "statusUpdate":
		if convertedEvent, err := convertToStruct(event, &StatusUpdateEvent{}); err == nil {
			if statusUpdateEvent, ok := convertedEvent.(*StatusUpdateEvent); ok {
				log.Infof("状态更新: trace_id=%s, sessionId=%s, status=%s", traceID, sessionId, statusUpdateEvent.AgentStatus)
				gologger.Debugf("statusUpdate事件详情: trace_id=%s, sessionId=%s, status=%s", traceID, sessionId, statusUpdateEvent.AgentStatus)
			}
		}
	case "toolUsed":
		if convertedEvent, err := convertToStruct(event, &ToolUsedEvent{}); err == nil {
			if toolUsedEvent, ok := convertedEvent.(*ToolUsedEvent); ok {
				log.Infof("工具使用: trace_id=%s, sessionId=%s, tools=%d", traceID, sessionId, len(toolUsedEvent.Tools))
				gologger.Debugf("toolUsed事件详情: trace_id=%s, sessionId=%s, tools=%d", traceID, sessionId, len(toolUsedEvent.Tools))
			}
		}
	case "actionLog":
		if convertedEvent, err := convertToStruct(event, &ActionLogEvent{}); err == nil {
			if actionLogEvent, ok := convertedEvent.(*ActionLogEvent); ok {
				log.Debugf("动作日志: trace_id=%s, sessionId=%s, actionId=%s", traceID, sessionId, actionLogEvent.ActionID)
				gologger.Debugf("actionLog事件详情: trace_id=%s, sessionId=%s, actionId=%s", traceID, sessionId, actionLogEvent.ActionID)
			}
		}
	case "resultUpdate":
		if convertedEvent, err := convertToStruct(event, &ResultUpdateEvent{}); err == nil {
			if resultUpdateEvent, ok := convertedEvent.(*ResultUpdateEvent); ok {
				log.Infof("任务完成: trace_id=%s, sessionId=%s, fileName=%s", traceID, sessionId, resultUpdateEvent.Result.FileName)
				gologger.Debugf("resultUpdate事件详情: trace_id=%s, sessionId=%s, fileName=%s",
					traceID, sessionId, resultUpdateEvent.Result.FileName)

				// 获取任务信息用于监控
				task, exists := tm.GetTask(sessionId)
				if exists {
					// 上报任务完成监控
					monitoring.EndTaskMonitoring(task.Task, "completed", sessionId)
				}

				// 更新任务状态为已完成
				err := tm.taskStore.UpdateSessionStatus(sessionId, TaskStatusDone)
				if err != nil {
					log.Errorf("更新任务状态为已完成失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
					gologger.Errorf("更新任务状态为已完成失败: %v", err)
				} else {
					log.Infof("任务状态已更新为已完成: trace_id=%s, sessionId=%s", traceID, sessionId)
					gologger.Infof("任务状态已更新为已完成: trace_id=%s, sessionId=%s", traceID, sessionId)
				}
				// 任务完成，可以清理资源
				go tm.cleanupTask(sessionId, traceID)
			}
		}
	default:
		log.Debugf("未知事件类型: trace_id=%s, sessionId=%s, eventType=%s", traceID, sessionId, eventType)
		gologger.Debugf("未知事件类型: trace_id=%s, sessionId=%s, eventType=%s", traceID, sessionId, eventType)
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
func (tm *TaskManager) handleEvent(sessionId string, eventType string, event interface{}, traceID string) {
	log.Debugf("开始处理事件: trace_id=%s, sessionId=%s, eventType=%s", traceID, sessionId, eventType)

	// 生成事件ID
	id := generateEventID()

	// 获取事件的时间戳
	timestamp := getEventTimestamp(event)

	// 存储事件到数据库
	err := tm.taskStore.StoreEvent(id, sessionId, eventType, event, timestamp)
	if err != nil {
		log.Errorf("存储事件失败: trace_id=%s, sessionId=%s, eventType=%s, error=%v", traceID, sessionId, eventType, err)
		gologger.Errorf("存储%s事件失败: %v", eventType, err)
		return
	}

	// 推送事件到SSE
	err = tm.sseManager.SendEvent(id, sessionId, eventType, event)
	if err != nil {
		// 如果是连接不存在的错误，记录为调试信息而不是错误
		if strings.Contains(err.Error(), "连接不存在") {
			log.Debugf("SSE连接已关闭，跳过事件推送: trace_id=%s, sessionId=%s, eventType=%s", traceID, sessionId, eventType)
			gologger.Debugf("SSE连接已关闭，跳过事件推送: trace_id=%s, sessionId=%s, eventType=%s", traceID, sessionId, eventType)
		} else {
			log.Errorf("推送事件到SSE失败: trace_id=%s, sessionId=%s, eventType=%s, error=%v", traceID, sessionId, eventType, err)
			gologger.Errorf("推送%s事件到SSE失败: %v", eventType, err)
		}
		return
	}

	// 记录日志
	log.Debugf("事件处理完成: trace_id=%s, sessionId=%s, eventType=%s", traceID, sessionId, eventType)
	gologger.Debugf("%s事件已处理: trace_id=%s, sessionId=%s", eventType, traceID, sessionId)
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
func (tm *TaskManager) TerminateTask(sessionId string, username string, traceID string) error {
	log.Infof("开始终止任务: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		log.Errorf("任务不存在: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)
		return fmt.Errorf("任务不存在")
	}

	// 验证用户权限（只有任务创建者才能终止任务）
	if session.Username != username {
		log.Errorf("无权限终止任务: trace_id=%s, sessionId=%s, username=%s, owner=%s", traceID, sessionId, username, session.Username)
		return fmt.Errorf("无权限操作此任务")
	}

	// 通知 Agent 终止任务
	if session.AssignedAgent != "" {
		log.Infof("通知Agent终止任务: trace_id=%s, sessionId=%s, agentId=%s", traceID, sessionId, session.AssignedAgent)
		tm.notifyAgentToTerminate(session.AssignedAgent, sessionId, traceID)
	}

	// 发送终止事件给前端
	tm.sendTerminationEvent(sessionId, traceID)

	// 更新任务状态为已终止
	err = tm.taskStore.UpdateSessionStatus(sessionId, TaskStatusTerminated)
	if err != nil {
		log.Errorf("更新任务状态失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
		return fmt.Errorf("更新任务状态失败")
	}

	log.Infof("任务终止完成: trace_id=%s, sessionId=%s", traceID, sessionId)

	// 上报任务终止监控
	monitoring.EndTaskMonitoring(session.TaskType, "terminated", sessionId)

	// 异步清理任务资源
	go tm.cleanupTask(sessionId, traceID)

	return nil
}

// notifyAgentToTerminate 通知 Agent 终止任务
func (tm *TaskManager) notifyAgentToTerminate(agentID string, sessionId string, traceID string) {
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
				log.Errorf("发送终止消息给Agent %s失败: %v", agentID, err)
				gologger.Errorf("发送终止消息给Agent %s失败: %v", agentID, err)
			} else {
				log.Infof("终止消息已发送给Agent %s: trace_id=%s, sessionId=%s", agentID, traceID, sessionId)
				gologger.Infof("终止消息已发送给Agent %s: trace_id=%s, sessionId=%s", agentID, traceID, sessionId)
			}
			break
		}
	}
}

// sendTerminationEvent 发送终止事件给前端
func (tm *TaskManager) sendTerminationEvent(sessionId string, traceID string) {
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
	tm.handleEvent(sessionId, "statusUpdate", event, traceID)

	log.Infof("终止事件已发送: trace_id=%s, sessionId=%s", traceID, sessionId)
	gologger.Infof("终止事件已发送: trace_id=%s, sessionId=%s", traceID, sessionId)
}

// generateEventID 生成事件ID
func generateEventID() string {
	return time.Now().Format("20060102150405") + "_" + fmt.Sprintf("%d", time.Now().UnixNano())
}

// UpdateTask 更新任务信息
func (tm *TaskManager) UpdateTask(sessionId string, req *TaskUpdateRequest, username string, traceID string) error {
	log.Infof("开始更新任务: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 1. 验证任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		log.Errorf("任务不存在: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)
		return fmt.Errorf("任务不存在")
	}

	// 2. 验证权限（只有任务创建者才能更新）
	if session.Username != username {
		log.Errorf("无权限操作此任务: trace_id=%s, sessionId=%s, username=%s, owner=%s", traceID, sessionId, username, session.Username)
		return fmt.Errorf("无权限操作此任务")
	}

	// 3. 更新任务信息
	updates := map[string]interface{}{
		"title": req.Title,
	}
	err = tm.taskStore.UpdateSession(sessionId, updates)
	if err != nil {
		log.Errorf("更新任务信息失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
		return fmt.Errorf("更新任务信息失败: %v", err)
	}

	log.Infof("任务信息更新成功: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)
	return nil
}

// DeleteTask 删除任务
func (tm *TaskManager) DeleteTask(sessionId string, username string, traceID string) error {
	log.Infof("开始删除任务: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		log.Errorf("任务不存在: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)
		return fmt.Errorf("任务不存在")
	}

	// 验证用户权限（只有任务创建者才能删除任务）
	if session.Username != username {
		log.Errorf("无权限操作此任务: trace_id=%s, sessionId=%s, username=%s, owner=%s", traceID, sessionId, username, session.Username)
		return fmt.Errorf("无权限操作此任务")
	}

	// 使用事务删除会话及其所有消息
	err = tm.taskStore.DeleteSessionWithMessages(sessionId)
	if err != nil {
		log.Errorf("删除任务失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
		return fmt.Errorf("删除任务失败: %v", err)
	}

	// 删除附件文件
	err = tm.deleteSessionAttachments(session)
	if err != nil {
		log.Errorf("删除附件文件失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
		gologger.Warnf("删除附件文件失败: %v", err)
		// 附件删除失败不影响主流程，只记录警告
	}

	// 清理内存中的任务数据
	tm.mu.Lock()
	delete(tm.tasks, sessionId)
	tm.mu.Unlock()

	// 关闭SSE连接
	tm.CloseSSESession(sessionId, traceID)

	log.Infof("任务删除完成: trace_id=%s, sessionId=%s", traceID, sessionId)
	gologger.Infof("任务删除完成: trace_id=%s, sessionId=%s", traceID, sessionId)
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
				log.Errorf("删除附件文件失败: %s, error: %v", filePath, err)
				gologger.Warnf("删除附件文件失败: %s, error: %v", filePath, err)
			}
		} else {
			log.Debugf("删除附件文件成功: %s", filePath)
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
func (tm *TaskManager) UploadFile(file *multipart.FileHeader, traceID string) (*UploadFileResult, error) {
	log.Infof("开始文件上传: trace_id=%s, originalName=%s, size=%d", traceID, file.Filename, file.Size)

	// 保存原始文件名
	originalName := file.Filename

	// 生成安全的唯一文件名
	fileName := generateSecureFileName(file.Filename)
	log.Debugf("生成安全文件名: trace_id=%s, originalName=%s, secureName=%s", traceID, originalName, fileName)

	// 使用配置的上传目录
	uploadDir := tm.fileConfig.UploadDir
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		log.Errorf("创建上传目录失败: trace_id=%s, path=%s, error=%v", traceID, uploadDir, err)
		return nil, fmt.Errorf("创建上传目录失败: %v", err)
	}

	// 创建文件路径
	filePath := filepath.Join(uploadDir, fileName)

	// 保存文件到本地
	src, err := file.Open()
	if err != nil {
		log.Errorf("打开上传文件失败: trace_id=%s, originalName=%s, error=%v", traceID, originalName, err)
		return nil, fmt.Errorf("打开文件失败: %v", err)
	}
	defer src.Close()

	dst, err := os.Create(filePath)
	if err != nil {
		log.Errorf("创建目标文件失败: trace_id=%s, filePath=%s, error=%v", traceID, filePath, err)
		return nil, fmt.Errorf("创建文件失败: %v", err)
	}
	defer dst.Close()

	// 复制文件内容并验证
	written, err := io.Copy(dst, src)
	if err != nil {
		// 清理已创建的文件
		os.Remove(filePath)
		log.Errorf("文件写入失败: trace_id=%s, filePath=%s, error=%v", traceID, filePath, err)
		return nil, fmt.Errorf("保存文件失败: %v", err)
	}

	// 验证写入的文件大小
	if written != file.Size {
		os.Remove(filePath)
		log.Errorf("文件写入不完整: trace_id=%s, expected=%d, actual=%d, filePath=%s", traceID, file.Size, written, filePath)
		return nil, fmt.Errorf("文件写入不完整")
	}

	// 生成文件访问URL
	fileURL := tm.fileConfig.GetFileURL(fileName)

	log.Infof("文件上传成功: trace_id=%s, originalName=%s, secureName=%s, size=%d, fileURL=%s", traceID, originalName, fileName, written, fileURL)

	return &UploadFileResult{
		OriginalName: originalName,
		FileURL:      fileURL,
	}, nil
}

// GetUserTasks 获取指定用户的任务列表，只返回属于该用户的会话，确保用户只能看到自己的任务。
func (tm *TaskManager) GetUserTasks(username string, traceID string) ([]map[string]interface{}, error) {
	log.Infof("开始获取用户任务列表: trace_id=%s, username=%s", traceID, username)

	// 从数据库获取用户的任务列表
	sessions, err := tm.taskStore.GetUserSessions(username)
	if err != nil {
		log.Errorf("获取用户任务列表失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		return nil, fmt.Errorf("获取任务列表失败: %v", err)
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

	log.Infof("获取用户任务列表成功: trace_id=%s, username=%s, taskCount=%d", traceID, username, len(tasks))
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
func (tm *TaskManager) EstablishSSEConnection(w http.ResponseWriter, sessionId string, username string, traceID string) error {
	log.Infof("建立SSE连接: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)
	err := tm.sseManager.AddConnection(sessionId, username, w)
	if err != nil {
		log.Errorf("建立SSE连接失败: trace_id=%s, sessionId=%s, username=%s, error=%v", traceID, sessionId, username, err)
	} else {
		log.Infof("SSE连接建立成功: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)
	}
	return err
}

// CloseSSESession 关闭SSE会话
func (tm *TaskManager) CloseSSESession(sessionId string, traceID string) {
	log.Infof("关闭SSE会话: trace_id=%s, sessionId=%s", traceID, sessionId)
	tm.sseManager.RemoveConnection(sessionId)
	log.Infof("SSE会话已关闭: trace_id=%s, sessionId=%s", traceID, sessionId)
}

// 任务完成/中断时的清理
func (tm *TaskManager) cleanupTask(sessionId string, traceID string) {
	log.Infof("开始清理任务资源: trace_id=%s, sessionId=%s", traceID, sessionId)

	// 清理内存中的任务数据
	tm.mu.Lock()
	delete(tm.tasks, sessionId)
	tm.mu.Unlock()

	// 注意：SSE连接已在resultUpdate事件处理中立即清理
	tm.CloseSSESession(sessionId, traceID)

	log.Infof("任务清理完成: trace_id=%s, sessionId=%s", traceID, sessionId)
	gologger.Infof("任务清理完成: trace_id=%s, sessionId=%s", traceID, sessionId)
}

// GetTaskDetail 获取任务详情
func (tm *TaskManager) GetTaskDetail(sessionId string, username string, traceID string) (map[string]interface{}, error) {
	log.Infof("开始获取任务详情: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)

	// 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		log.Errorf("获取任务详情失败: trace_id=%s, sessionId=%s, username=%s, error=%v", traceID, sessionId, username, err)
		return nil, fmt.Errorf("任务不存在")
	}

	// 验证用户权限（只有任务创建者才能查看）
	if session.Username != username {
		log.Errorf("无权限访问任务详情: trace_id=%s, sessionId=%s, username=%s, owner=%s", traceID, sessionId, username, session.Username)
		return nil, fmt.Errorf("无权限查看此任务")
	}

	// 获取任务的所有消息
	messages, err := tm.taskStore.GetSessionMessages(sessionId)
	if err != nil {
		log.Errorf("获取任务消息失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
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

	log.Infof("获取任务详情成功: trace_id=%s, sessionId=%s, username=%s", traceID, sessionId, username)
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
func (tm *TaskManager) DownloadFile(sessionId string, fileUrl string, username string, c *gin.Context, traceID string) error {
	log.Infof("开始文件下载: trace_id=%s, sessionId=%s, fileUrl=%s, username=%s", traceID, sessionId, fileUrl, username)

	// 1. 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		log.Errorf("任务不存在: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
		return fmt.Errorf("任务不存在")
	}

	// 2. 验证用户权限（只有任务创建者才能下载文件）
	if session.Username != username {
		log.Warnf("用户权限验证失败: trace_id=%s, sessionId=%s, requestUser=%s, owner=%s", traceID, sessionId, username, session.Username)
		return fmt.Errorf("无权限访问此任务")
	}

	// 3. 验证文件URL是否属于该任务
	if session.Attachments == nil {
		log.Errorf("任务无附件: trace_id=%s, sessionId=%s", traceID, sessionId)
		return fmt.Errorf("文件不存在于此任务中")
	}

	var attachmentURLs []string
	if err := json.Unmarshal(session.Attachments, &attachmentURLs); err != nil {
		log.Errorf("解析任务附件失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
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
		log.Warnf("文件不在任务附件列表中: trace_id=%s, sessionId=%s, fileUrl=%s", traceID, sessionId, fileUrl)
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

	log.Debugf("文件下载路径信息: trace_id=%s, fileUrl=%s, fileName=%s, localFileName=%s, filePath=%s",
		traceID, fileUrl, fileName, localFileName, filePath)
	// 添加调试日志
	gologger.Debugf("文件下载调试信息: trace_id=%s, fileUrl=%s, localFileName=%s, filePath=%s, uploadDir=%s",
		traceID, fileUrl, localFileName, filePath, tm.fileConfig.UploadDir)

	// 6. 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		log.Errorf("本地文件不存在: trace_id=%s, filePath=%s", traceID, filePath)
		return fmt.Errorf("文件不存在")
	}

	// 7. 获取文件信息
	fileInfo, err := os.Stat(filePath)
	if err != nil {
		log.Errorf("获取文件信息失败: trace_id=%s, filePath=%s, error=%v", traceID, filePath, err)
		return fmt.Errorf("获取文件信息失败: %v", err)
	}

	log.Debugf("文件信息获取成功: trace_id=%s, filePath=%s, size=%d", traceID, filePath, fileInfo.Size())

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
		log.Errorf("打开文件失败: trace_id=%s, filePath=%s, error=%v", traceID, filePath, err)
		return fmt.Errorf("打开文件失败: %v", err)
	}
	defer file.Close()

	// 10. 流式传输文件内容
	written, err := io.Copy(c.Writer, file)
	if err != nil {
		log.Errorf("文件传输失败: trace_id=%s, filePath=%s, error=%v", traceID, filePath, err)
		return fmt.Errorf("传输文件失败: %v", err)
	}

	log.Infof("文件下载成功: trace_id=%s, sessionId=%s, fileName=%s, fileSize=%d, transmittedSize=%d",
		traceID, sessionId, fileName, fileInfo.Size(), written)
	gologger.Infof("文件下载成功: trace_id=%s, sessionId=%s, fileName=%s, fileSize=%d", traceID, sessionId, fileName, fileInfo.Size())

	return nil
}
