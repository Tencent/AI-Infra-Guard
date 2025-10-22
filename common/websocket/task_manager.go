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

	"github.com/Tencent/AI-Infra-Guard/common/agent"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
	"gorm.io/datatypes"
	"trpc.group/trpc-go/trpc-go/log"
)

// 任务管理器相关数据结构

const (
	WSMsgTypeTaskAssign = "task_assign" // 任务分配

	// 任务状态常量
	TaskStatusTodo       = "todo"  // 待执行
	TaskStatusDoing      = "doing" // 执行中
	TaskStatusDone       = "done"  // 已完成
	TaskStatusError      = "error"
	TaskStatusTerminated = "terminated" // 已终止
)

type TaskManager struct {
	mu           sync.RWMutex
	tasks        map[string]*TaskCreateRequest // sessionId -> 任务请求
	agentManager *AgentManager                 // 新增：引用 AgentManager
	taskStore    *database.TaskStore           // 新增：引用 TaskStore
	modelStore   *database.ModelStore          // 新增：引用 ModelStore
	fileConfig   *FileUploadConfig             // 新增：文件上传配置
	sseManager   *SSEManager                   // 新增：SSE管理器
}

func NewTaskManager(agentManager *AgentManager, taskStore *database.TaskStore, modelStore *database.ModelStore, fileConfig *FileUploadConfig, sseManager *SSEManager) *TaskManager {
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
		modelStore:   modelStore,   // 注入 ModelStore
		fileConfig:   fileConfig,   // 注入文件上传配置
		sseManager:   sseManager,   // 注入SSE管理器
	}
}

// 添加任务
func (tm *TaskManager) AddTask(req *TaskCreateRequest, traceID string) error {
	log.Infof("开始添加任务: trace_id=%s, sessionId=%s, taskType=%s, username=%s", traceID, req.SessionID, req.Task, req.Username)

	// 监控相关代码已移除

	// 1. 先检查数据库中是否已存在相同的sessionId
	existingSession, err := tm.taskStore.GetSession(req.SessionID)
	if err == nil && existingSession != nil {
		log.Errorf("任务已存在: trace_id=%s, sessionId=%s, username=%s", traceID, req.SessionID, req.Username)
		return fmt.Errorf("任务已存在，sessionId: %s", req.SessionID)
	}

	// 2. 预存任务到数据库（状态为todo，assigned_agent为空）
	session := &database.Session{
		ID:             req.SessionID,
		Username:       req.Username,
		Title:          tm.generateTaskTitle(req),
		TaskType:       req.Task,
		Content:        req.Content,
		Params:         mustMarshalJSON(req.Params),
		Attachments:    mustMarshalJSON(req.Attachments),
		Status:         TaskStatusDoing,
		AssignedAgent:  "", // 预存时为空
		CountryIsoCode: req.CountryIsoCode,
		Share:          true,
	}

	err = tm.taskStore.CreateSession(session)
	if err != nil {
		log.Errorf("预存任务到数据库失败: trace_id=%s, sessionId=%s, error=%v", traceID, req.SessionID, err)
		return fmt.Errorf("预存任务失败: %v", err)
	}

	log.Infof("任务预存成功: trace_id=%s, sessionId=%s", traceID, req.SessionID)

	// 3. 等待SSE连接建立
	timeout := 100 * time.Second
	start := time.Now()
	for time.Since(start) < timeout {
		if tm.sseManager.HasConnection(req.SessionID) {
			break // 连接已建立
		}
		time.Sleep(500 * time.Millisecond) // 每50ms检查一次
	}

	if !tm.sseManager.HasConnection(req.SessionID) {
		// SSE连接超时，清理预存的任务
		tm.cleanupFailedTask(req.SessionID, traceID)
		log.Errorf("SSE连接建立超时: trace_id=%s, sessionId=%s, username=%s, timeout=%v", traceID, req.SessionID, req.Username, timeout)
		return fmt.Errorf("SSE连接建立超时，请重试，sessionId: %s", req.SessionID)
	}

	// 4. 存储任务到内存（dispatchTask需要从内存中获取任务）
	tm.mu.Lock()
	tm.tasks[req.SessionID] = req
	tm.mu.Unlock()

	// 5. 尝试分发任务
	err = tm.dispatchTask(req.SessionID, traceID)
	if err != nil {
		// 分发失败，清理内存和数据库中的预存内容
		tm.cleanupFailedTask(req.SessionID, traceID)
		log.Errorf("任务分发失败: trace_id=%s, sessionId=%s, error=%v", traceID, req.SessionID, err)
		return fmt.Errorf("任务分发失败: %v", err)
	}

	log.Infof("任务添加成功: trace_id=%s, sessionId=%s, taskType=%s", traceID, req.SessionID, req.Task)
	return nil
}

// 一键添加任务并执行
func (tm *TaskManager) AddTaskApi(req *TaskCreateRequest) error {
	// 1. 先检查数据库中是否已存在相同的sessionId
	existingSession, err := tm.taskStore.GetSession(req.SessionID)
	if err == nil && existingSession != nil {
		return fmt.Errorf("任务已存在，sessionId: %s", req.SessionID)
	}

	// 2. 预存任务到数据库（状态为todo，assigned_agent为空）
	session := &database.Session{
		ID:             req.SessionID,
		Username:       req.Username,
		Title:          tm.generateTaskTitle(req),
		TaskType:       req.Task,
		Content:        req.Content,
		Params:         mustMarshalJSON(req.Params),
		Attachments:    mustMarshalJSON(req.Attachments),
		Status:         TaskStatusTodo,
		AssignedAgent:  "", // 预存时为空
		CountryIsoCode: req.CountryIsoCode,
		Share:          true,
	}
	err = tm.taskStore.CreateSession(session)
	if err != nil {
		return fmt.Errorf("预存任务失败: %v", err)
	}

	// 获取可用 Agent（简化：不做额外健康检查）
	availableAgents := tm.agentManager.GetAvailableAgents()
	if len(availableAgents) == 0 {
		return fmt.Errorf("没有可用的Agent")
	}

	// 3. 选择 Agent（简单策略：选择第一个，相信GetAvailableAgents的过滤结果）
	selectedAgent := availableAgents[0]

	// 4. 更新session的assigned_agent和开始时间
	err = tm.taskStore.UpdateSessionAssignedAgent(req.SessionID, selectedAgent.agentID)
	if err != nil {
		return fmt.Errorf("无法更新session的assigned_agent")
	}

	// 6. 构造任务分配消息
	taskMsg := WSMessage{
		Type: WSMsgTypeTaskAssign,
		Content: TaskContent{
			SessionID:      req.SessionID,
			TaskType:       req.Task,
			Content:        req.Content,
			Params:         req.Params,
			Attachments:    req.Attachments,
			Timeout:        3600,
			CountryIsoCode: req.CountryIsoCode,
		},
	}

	// 7. 直接发送给 Agent（简化：无重试，无额外健康检查）
	selectedAgent.stateMu.RLock()
	agentID := selectedAgent.agentID
	selectedAgent.stateMu.RUnlock()

	// 设置写超时并直接发送
	selectedAgent.conn.SetWriteDeadline(time.Now().Add(writeWait))
	err = selectedAgent.conn.WriteJSON(taskMsg)
	if err != nil {
		return fmt.Errorf("下发任务给 %s 失败: %v", agentID, err)
	}

	log.Infof("任务分发成功:  sessionId=%s, agentId=%s", req.SessionID, agentID)
	return nil
}

// cleanupFailedTask 清理失败的任务（内存和数据库）
func (tm *TaskManager) cleanupFailedTask(sessionId string, traceID string) {
	log.Infof("开始清理失败任务: trace_id=%s, sessionId=%s", traceID, sessionId)

	// 清理内存中的任务
	tm.mu.Lock()
	delete(tm.tasks, sessionId)
	tm.mu.Unlock()

	// 清理数据库中的预存任务
	err := tm.taskStore.DeleteSession(sessionId)
	if err != nil {
		log.Errorf("清理数据库中的失败任务失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
	} else {
		log.Infof("失败任务清理完成: trace_id=%s, sessionId=%s", traceID, sessionId)
	}
}

// 获取任务
func (tm *TaskManager) GetTask(sessionId string) (*TaskCreateRequest, bool) {
	tm.mu.RLock()
	defer tm.mu.RUnlock()
	task, ok := tm.tasks[sessionId]
	return task, ok
}

// 新增：任务分发方法（简化版本，减少死锁风险）
func (tm *TaskManager) dispatchTask(sessionId string, traceID string) error {
	log.Infof("开始分发任务: trace_id=%s, sessionId=%s", traceID, sessionId)

	// 1. 获取任务
	task, exists := tm.GetTask(sessionId)
	if !exists {
		log.Errorf("任务不存在: trace_id=%s, sessionId=%s", traceID, sessionId)
		return fmt.Errorf("任务不存在")
	}

	// 2. 获取可用 Agent（简化：不做额外健康检查）
	availableAgents := tm.agentManager.GetAvailableAgents()
	if len(availableAgents) == 0 {
		log.Warnf("没有可用的Agent: trace_id=%s, sessionId=%s", traceID, sessionId)
		return fmt.Errorf("没有可用的Agent")
	}

	log.Infof("找到可用Agent数量: trace_id=%s, sessionId=%s, count=%d", traceID, sessionId, len(availableAgents))

	// 3. 选择 Agent（简单策略：选择第一个，相信GetAvailableAgents的过滤结果）
	selectedAgent := availableAgents[0]

	// 4. 更新session的assigned_agent和开始时间
	err := tm.taskStore.UpdateSessionAssignedAgent(task.SessionID, selectedAgent.agentID)
	if err != nil {
		log.Errorf("无法更新session的assigned_agent: trace_id=%s, sessionId=%s, agentId=%s, error=%v", traceID, task.SessionID, selectedAgent.agentID, err)
		return fmt.Errorf("无法更新session的assigned_agent")
	}

	// 5. 处理params中的modelid，获取模型信息
	enhancedParams := make(map[string]interface{})
	for k, v := range task.Params {
		enhancedParams[k] = v
	}
	addModel := func(modelId string) (*database.ModelParams, error) {
		model, err := tm.modelStore.GetModel(modelId)
		if err != nil {
			// 检查是否是记录不存在的错误
			if err.Error() == "record not found" {
				log.Errorf("模型不存在: trace_id=%s, sessionId=%s, modelID=%s", traceID, sessionId, modelId)
				return nil, fmt.Errorf("模型ID '%s' 不存在，请检查模型配置", modelId)
			}
			log.Errorf("获取模型信息失败: trace_id=%s, sessionId=%s, modelID=%s, error=%v", traceID, sessionId, modelId, err)
			return nil, fmt.Errorf("获取模型信息失败: %v", err)
		}
		// 测试模型是否有效
		//ai := models.NewOpenAI(model.Token, model.ModelName, model.BaseURL)
		//err = ai.Vaild(context.Background())
		//if err != nil {
		//	log.Errorf("模型无效: trace_id=%s, sessionId=%s, modelID=%s, error=%v", traceID, sessionId, modelId, err)
		//	return nil, fmt.Errorf("模型无效: %v", err)
		//}
		p := database.ModelParams{
			Model:   model.ModelName,
			Token:   model.Token,
			BaseUrl: model.BaseURL,
			Limit:   model.Limit,
		}
		return &p, nil
	}
	if task.Params != nil {
		if modelID, exists := task.Params["model_id"]; exists {
			log.Infof("找到模型ID: trace_id=%s, sessionId=%s, modelID=%v", traceID, sessionId, modelID)
			switch v := modelID.(type) {
			case string:
				modelInfo, err := addModel(v)
				if err != nil {
					return err
				}
				enhancedParams["model"] = modelInfo
			case []interface{}:
				modelsList := make([]*database.ModelParams, 0)
				log.Infof("找到多个模型ID: trace_id=%s, sessionId=%s, modelID=%v", traceID, sessionId, v)
				for _, vv := range v {
					vv, ok := vv.(string)
					if !ok {
						log.Errorf("无效的模型ID类型: trace_id=%s, sessionId=%s, modelID=%v", traceID, sessionId, vv)
						continue
					}
					modelInfo, err := addModel(vv)
					if err != nil {
						return err
					}
					modelsList = append(modelsList, modelInfo)
				}
				enhancedParams["model"] = modelsList
			default:
				log.Errorf("无效的模型ID类型: trace_id=%s, sessionId=%s, modelID=%v", traceID, sessionId, v)
			}
		}
		if evalModelStr, exists := task.Params["eval_model_id"]; exists {
			evalModelId, ok := evalModelStr.(string)
			if ok {
				evalModelInfo, err := addModel(evalModelId)
				if err != nil {
					return err
				}
				enhancedParams["eval_model"] = evalModelInfo
			}
		}
	}

	// 6. 构造任务分配消息
	taskMsg := WSMessage{
		Type: WSMsgTypeTaskAssign,
		Content: TaskContent{
			SessionID:      task.SessionID,
			TaskType:       task.Task,
			Content:        task.Content,
			Params:         enhancedParams,
			Attachments:    task.Attachments,
			Timeout:        3600,
			CountryIsoCode: task.CountryIsoCode,
		},
	}
	log.Infof("任务分配消息: trace_id=%s, sessionId=%s, taskMsg=%+v", traceID, sessionId, taskMsg)

	// 7. 直接发送给 Agent（简化：无重试，无额外健康检查）
	selectedAgent.stateMu.RLock()
	agentID := selectedAgent.agentID
	isActive := selectedAgent.isActive
	selectedAgent.stateMu.RUnlock()

	if !isActive {
		log.Errorf("选中的Agent已不活跃: trace_id=%s, sessionId=%s, agentId=%s", traceID, sessionId, agentID)
		// 重置assigned_agent
		tm.taskStore.UpdateSessionAssignedAgent(task.SessionID, "")
		return fmt.Errorf("选中的Agent已不活跃: %s", agentID)
	}

	// 设置写超时并直接发送
	selectedAgent.conn.SetWriteDeadline(time.Now().Add(writeWait))
	err = selectedAgent.conn.WriteJSON(taskMsg)
	if err != nil {
		log.Errorf("下发任务给Agent失败: trace_id=%s, sessionId=%s, agentId=%s, error=%v", traceID, task.SessionID, agentID, err)
		return fmt.Errorf("下发任务给 %s 失败: %v", agentID, err)
	}

	log.Infof("任务分发成功: trace_id=%s, sessionId=%s, agentId=%s", traceID, task.SessionID, agentID)
	return nil
}

// HandleAgentEvent 处理来自Agent的事件
func (tm *TaskManager) HandleAgentEvent(sessionId string, eventType string, event interface{}) {
	log.Debugf("收到Agent事件: sessionId=%s, eventType=%s", sessionId, eventType)

	// 使用通用事件处理函数
	tm.handleEvent(sessionId, eventType, event)

	// 根据事件类型记录特定日志
	switch eventType {
	case "liveStatus":
		if convertedEvent, err := convertToStruct(event, &LiveStatusEvent{}); err == nil {
			if liveStatusEvent, ok := convertedEvent.(*LiveStatusEvent); ok {
				log.Debugf("liveStatus事件详情: sessionId=%s, text=%s", sessionId, liveStatusEvent.Text)
			}
		}
	case "planUpdate":
		if convertedEvent, err := convertToStruct(event, &PlanUpdateEvent{}); err == nil {
			if planUpdateEvent, ok := convertedEvent.(*PlanUpdateEvent); ok {
				log.Infof("收到计划更新: sessionId=%s, tasks=%d", sessionId, len(planUpdateEvent.Tasks))
			}
		}
	case "newPlanStep":
		if convertedEvent, err := convertToStruct(event, &NewPlanStepEvent{}); err == nil {
			if newPlanStepEvent, ok := convertedEvent.(*NewPlanStepEvent); ok {
				log.Infof("新计划步骤: sessionId=%s, stepId=%s", sessionId, newPlanStepEvent.StepID)
			}
		}
	case "statusUpdate":
		if convertedEvent, err := convertToStruct(event, &StatusUpdateEvent{}); err == nil {
			if statusUpdateEvent, ok := convertedEvent.(*StatusUpdateEvent); ok {
				log.Infof("状态更新: sessionId=%s, status=%s", sessionId, statusUpdateEvent.AgentStatus)
			}
		}
	case "toolUsed":
		if convertedEvent, err := convertToStruct(event, &ToolUsedEvent{}); err == nil {
			if toolUsedEvent, ok := convertedEvent.(*ToolUsedEvent); ok {
				log.Infof("工具使用: sessionId=%s, tools=%d", sessionId, len(toolUsedEvent.Tools))
			}
		}
	case "actionLog":
		if convertedEvent, err := convertToStruct(event, &ActionLogEvent{}); err == nil {
			if actionLogEvent, ok := convertedEvent.(*ActionLogEvent); ok {
				log.Debugf("动作日志: sessionId=%s, actionId=%s", sessionId, actionLogEvent.ActionID)
			}
		}
	case "error":
		log.Errorf("错误事件: sessionId=%s %v", sessionId, event)
		updates := map[string]interface{}{
			"status": "error",
		}
		err := tm.taskStore.UpdateSession(sessionId, updates)
		if err != nil {
			log.Errorf("更新任务失败: sessionId=%s, error=%v", sessionId, err)
		}
	case "resultUpdate":
		if convertedEvent, err := convertToStruct(event, &ResultUpdateEvent{}); err == nil {
			if _, ok := convertedEvent.(*ResultUpdateEvent); ok {
				log.Infof("任务完成: sessionId=%s", sessionId)

				// 监控相关代码已移除

				// 更新任务状态为已完成
				err := tm.taskStore.UpdateSessionStatus(sessionId, TaskStatusDone)
				if err != nil {
					log.Errorf("更新任务状态为已完成失败: sessionId=%s, error=%v", sessionId, err)
				} else {
					log.Infof("任务状态已更新为已完成: sessionId=%s", sessionId)
				}
				// 任务完成，可以清理资源
				go tm.cleanupTask(sessionId)
			}
		}
	default:
		log.Debugf("未知事件类型: sessionId=%s, eventType=%s", sessionId, eventType)
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
	log.Debugf("开始处理事件: sessionId=%s, eventType=%s", sessionId, eventType)

	// 生成事件ID
	id := generateEventID()

	// 获取事件的时间戳
	timestamp := getEventTimestamp(event)

	// 存储事件到数据库
	err := tm.taskStore.StoreEvent(id, sessionId, eventType, event, timestamp)
	if err != nil {
		log.Errorf("存储事件失败: sessionId=%s, eventType=%s, error=%v", sessionId, eventType, err)
		return
	}

	// 推送事件到SSE
	err = tm.sseManager.SendEvent(id, sessionId, eventType, event)
	if err != nil {
		// 如果是连接不存在的错误，记录为调试信息而不是错误
		if strings.Contains(err.Error(), "连接不存在") {
			log.Debugf("SSE连接已关闭，跳过事件推送: sessionId=%s, eventType=%s", sessionId, eventType)
		} else {
			log.Errorf("推送事件到SSE失败: sessionId=%s, eventType=%s, error=%v", sessionId, eventType, err)
		}
		return
	}

	// 记录日志
	log.Debugf("事件处理完成: sessionId=%s, eventType=%s", sessionId, eventType)
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

	// 监控相关代码已移除

	// 异步清理任务资源
	go tm.cleanupTask(sessionId)

	return nil
}

// notifyAgentToTerminate 通知 Agent 终止任务（简化版本）
func (tm *TaskManager) notifyAgentToTerminate(agentID string, sessionId string, traceID string) {
	// 异步通知Agent，避免阻塞
	go func() {
		// 获取 Agent 连接
		availableAgents := tm.agentManager.GetAvailableAgents()
		for _, agent := range availableAgents {
			agent.stateMu.RLock()
			currentAgentID := agent.agentID
			isActive := agent.isActive
			agent.stateMu.RUnlock()

			if currentAgentID == agentID && isActive {
				// 发送终止消息给 Agent
				terminateMsg := WSMessage{
					Type: "terminate",
					Content: map[string]interface{}{
						"session_id": sessionId,
						"reason":     "用户主动终止",
					},
				}

				// 直接发送，无重试机制
				agent.conn.SetWriteDeadline(time.Now().Add(writeWait))
				err := agent.conn.WriteJSON(terminateMsg)
				if err != nil {
					log.Errorf("发送终止消息给Agent %s失败: %v", agentID, err)
				} else {
					log.Infof("终止消息已发送给Agent %s: trace_id=%s, sessionId=%s", agentID, traceID, sessionId)
				}
				break
			}
		}
	}()
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
	tm.handleEvent(sessionId, "statusUpdate", event)

	log.Infof("终止事件已发送: trace_id=%s, sessionId=%s", traceID, sessionId)
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
		// 附件删除失败不影响主流程，只记录警告
	}

	// 清理内存中的任务数据
	tm.mu.Lock()
	delete(tm.tasks, sessionId)
	tm.mu.Unlock()

	// 关闭SSE连接
	tm.CloseSSESession(sessionId)

	log.Infof("任务删除完成: trace_id=%s, sessionId=%s", traceID, sessionId)
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
			}
		} else {
			log.Debugf("删除附件文件成功: %s", filePath)
		}
	}

	return nil
}

// UploadFileResult 文件上传结果
type UploadFileResult struct {
	Filename string `json:"filename"` // 原始文件名
	FileURL  string `json:"fileUrl"`  // 文件访问URL
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
		Filename: originalName,
		FileURL:  fileURL,
	}, nil
}

// GetUserTasks 获取指定用户的任务列表，只返回属于该用户的会话，确保用户只能看到自己的任务。
func (tm *TaskManager) GetUserTasks(username string, traceID string) ([]map[string]interface{}, error) {
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
			"sessionId":      session.ID,
			"title":          session.Title,
			"taskType":       session.TaskType,
			"status":         session.Status,
			"countryIsoCode": session.CountryIsoCode,
			"updatedAt":      session.UpdatedAt, // 直接使用时间戳毫秒级
			"createdAt":      session.CreatedAt, // 任务创建时间
		}

		// 添加完成时间（如果任务已完成）
		if session.CompletedAt != nil {
			task["completedAt"] = *session.CompletedAt
		} else {
			task["completedAt"] = nil
		}

		tasks = append(tasks, task)
	}
	return tasks, nil
}

// GetUserTasksByType 获取指定用户的任务列表，支持可选的任务类型过滤
func (tm *TaskManager) GetUserTasksByType(username string, taskType string, traceID string) ([]map[string]interface{}, error) {
	// 从数据库获取用户的任务列表（支持类型过滤）
	sessions, err := tm.taskStore.GetUserSessionsByType(username, taskType)
	if err != nil {
		log.Errorf("获取用户任务列表失败: trace_id=%s, username=%s, taskType=%s, error=%v", traceID, username, taskType, err)
		return nil, fmt.Errorf("获取任务列表失败: %v", err)
	}

	// 转换为前端需要的格式
	var tasks []map[string]interface{}
	for _, session := range sessions {
		task := map[string]interface{}{
			"sessionId":      session.ID,
			"title":          session.Title,
			"taskType":       session.TaskType,
			"status":         session.Status,
			"countryIsoCode": session.CountryIsoCode,
			"updatedAt":      session.UpdatedAt, // 直接使用时间戳毫秒级
			"createdAt":      session.CreatedAt, // 任务创建时间
		}

		// 添加完成时间（如果任务已完成）
		if session.CompletedAt != nil {
			task["completedAt"] = *session.CompletedAt
		} else {
			task["completedAt"] = nil
		}

		tasks = append(tasks, task)
	}
	return tasks, nil
}

// SearchUserTasksSimple 使用简化参数搜索指定用户的任务，支持单个查询关键词和分页
func (tm *TaskManager) SearchUserTasksSimple(username string, searchParams database.SimpleSearchParams, traceID string) ([]map[string]interface{}, error) {
	log.Infof("开始简化搜索用户任务: trace_id=%s, username=%s, query=%s, taskType=%s", traceID, username, searchParams.Query, searchParams.TaskType)

	// 验证和设置默认分页参数
	if searchParams.Page < 1 {
		searchParams.Page = 1
	}
	if searchParams.PageSize < 1 {
		searchParams.PageSize = 10
	}
	if searchParams.PageSize > 100 {
		searchParams.PageSize = 100 // 限制最大页面大小
	}

	// 从数据库搜索用户的任务列表
	sessions, _, err := tm.taskStore.SearchUserSessionsSimple(username, searchParams)
	if err != nil {
		log.Errorf("简化搜索用户任务失败: trace_id=%s, username=%s, taskType=%s, error=%v", traceID, username, searchParams.TaskType, err)
		return nil, fmt.Errorf("搜索任务失败: %v", err)
	}

	// 转换为前端需要的格式
	var tasks []map[string]interface{}
	for _, session := range sessions {
		task := map[string]interface{}{
			"sessionId":      session.ID,
			"title":          session.Title,
			"taskType":       session.TaskType,
			"status":         session.Status,
			"countryIsoCode": session.CountryIsoCode,
			"updatedAt":      session.UpdatedAt, // 直接使用时间戳毫秒级
			"createdAt":      session.CreatedAt, // 任务创建时间
		}

		// 添加完成时间（如果任务已完成）
		if session.CompletedAt != nil {
			task["completedAt"] = *session.CompletedAt
		} else {
			task["completedAt"] = nil
		}

		tasks = append(tasks, task)
	}
	return tasks, nil
}

// generateTaskTitle 生成任务标题（用于任务创建API）
func (tm *TaskManager) generateTaskTitle(req *TaskCreateRequest) string {
	ret := ""
	var ModelName = ""
	language := req.CountryIsoCode
	if language == "" {
		language = "zh"
	}

	// 定义语言相关的文本
	var texts struct {
		// 任务类型标题
		aiInfraScan, mcpScan, modelJailbreak, modelRedteamReport, otherTask string
		// 其他文本
		model, prompt, github, sse string
	}

	if language == "en" {
		texts.aiInfraScan = "AI Infra Scan - "
		texts.mcpScan = "MCP Scan - "
		texts.modelJailbreak = "LLM Jailbreaking - "
		texts.modelRedteamReport = "Jailbreak Evaluation - "
		texts.otherTask = "Other Task - "
		texts.model = "Model:"
		texts.prompt = "Prompt:"
		texts.github = "Github:"
		texts.sse = "SSE:"
	} else {
		texts.aiInfraScan = "AI基础设施扫描 - "
		texts.mcpScan = "MCP扫描 - "
		texts.modelJailbreak = "一键越狱任务 - "
		texts.modelRedteamReport = "大模型安全体检 - "
		texts.otherTask = "其他任务 - "
		texts.model = "模型:"
		texts.prompt = "prompt:"
		texts.github = "Github:"
		texts.sse = "SSE:"
	}
	if modelID, exists := req.Params["model_id"]; exists {
		switch v := modelID.(type) {
		case string:
			model, err := tm.modelStore.GetModel(v)
			if err == nil {
				ModelName = model.ModelName
			}
		case []interface{}:
			modelStr := make([]string, 0)
			for _, mid := range v {
				mid, ok := mid.(string)
				if !ok {
					continue
				}
				model, err := tm.modelStore.GetModel(mid)
				if err == nil {
					modelStr = append(modelStr, model.ModelName)
				}
			}
			ModelName = strings.Join(modelStr, ",")
		}
	}
	// 1. AI基础 ip/域名 ，文件形式：取第一行等xx个
	// 2. MCP：文件名以文件展示，github取项目名，sse取链接
	// 3. 评测：模型名 eg：qwen3模型评测任务
	// 4. 一键越狱：模型名+prompt
	switch req.Task {
	case agent.TaskTypeAIInfraScan:
		ret = texts.aiInfraScan
		if len(req.Attachments) > 0 && req.Attachments[0] != "" {
			ret += tm.extractFileNameFromURL(req.Attachments[0])
		}
		if req.Content != "" {
			ret += req.Content
		}
	case agent.TaskTypeMcpScan:
		ret = texts.mcpScan
		if len(req.Attachments) > 0 && req.Attachments[0] != "" {
			// 直接调用现有的extractFileNameFromURL方法
			ret += tm.extractFileNameFromURL(req.Attachments[0])
		} else if strings.Contains(req.Content, "github.com") {
			ret += texts.github + tm.extractFileNameFromURL(req.Content)
		} else {
			ret += texts.sse + req.Content
		}
	case agent.TaskTypeModelJailbreak:
		ret = texts.modelJailbreak + fmt.Sprintf("%s%s, %s%s", texts.model, ModelName, texts.prompt, req.Content)
	case agent.TaskTypeModelRedteamReport:
		ret = texts.modelRedteamReport + ModelName
	default:
		ret = texts.otherTask + req.Content
	}
	// 如果content为空，尝试从附件中提取第一个URL的文件名作为title
	return ret
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
func (tm *TaskManager) CloseSSESession(sessionId string) {
	log.Infof("关闭SSE会话: sessionId=%s", sessionId)
	tm.sseManager.RemoveConnection(sessionId)
	log.Infof("SSE会话已关闭: sessionId=%s", sessionId)
}

// 任务完成/中断时的清理
func (tm *TaskManager) cleanupTask(sessionId string) {
	log.Infof("开始清理任务资源: sessionId=%s", sessionId)

	// 清理内存中的任务数据
	tm.mu.Lock()
	delete(tm.tasks, sessionId)
	tm.mu.Unlock()

	// 注意：SSE连接已在resultUpdate事件处理中立即清理
	tm.CloseSSESession(sessionId)

	log.Infof("任务清理完成: sessionId=%s", sessionId)
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
	if !session.Share && session.Username != username {
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
	var attachments []map[string]interface{}
	if session.Attachments != nil {
		var attachmentURLs []string
		if err := json.Unmarshal(session.Attachments, &attachmentURLs); err == nil {
			for _, url := range attachmentURLs {
				// 从URL中提取文件名
				fileName := tm.extractFileNameFromURL(url)
				attachments = append(attachments, map[string]interface{}{
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
			continue
		}

		messageList = append(messageList, map[string]interface{}{
			"id":        msg.ID,
			"type":      msg.Type,
			"timestamp": msg.Timestamp,
			"event":     eventData,
		})
	}

	// 处理任务参数
	var params map[string]interface{}
	if session.Params != nil {
		if err := json.Unmarshal(session.Params, &params); err != nil {
			log.Warnf("解析任务参数失败: trace_id=%s, sessionId=%s, error=%v", traceID, sessionId, err)
			params = make(map[string]interface{})
		}
	} else {
		params = make(map[string]interface{})
	}

	// 构建返回数据
	detail := map[string]interface{}{
		"sessionId":      session.ID,
		"title":          session.Title,
		"status":         session.Status,
		"countryIsoCode": session.CountryIsoCode,
		"createdAt":      session.CreatedAt,
		"content":        session.Content,
		"params":         params,
		"taskType":       session.TaskType,
		"attachments":    attachments,
		"messages":       messageList,
	}
	if session.Username != username {
		delete(detail, "attachments")
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

	filename := strings.TrimLeft(fileUrl, "/")
	filePath, _ := filepath.Abs(filepath.Join(tm.fileConfig.UploadDir, filename))

	if !strings.HasPrefix(filePath, tm.fileConfig.UploadDir) {
		return fmt.Errorf("文件路径不合法")
	}

	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		log.Errorf("本地文件不存在: trace_id=%s, filePath=%s", traceID, filePath)
		return fmt.Errorf("文件不存在")
	}

	fileInfo, err := os.Stat(filePath)
	if err != nil {
		log.Errorf("获取文件信息失败: trace_id=%s, filePath=%s, error=%v", traceID, filePath, err)
		return fmt.Errorf("获取文件信息失败: %v", err)
	}

	log.Debugf("文件信息获取成功: trace_id=%s, filePath=%s, size=%d", traceID, filePath, fileInfo.Size())

	// 8. 设置响应头
	// 获取文件的MIME类型
	ext := filepath.Ext(filePath)
	mimeType := mime.TypeByExtension(ext)
	if mimeType == "" {
		mimeType = "application/octet-stream"
	}

	// 设置Content-Type
	c.Header("Content-Type", mimeType)

	// 设置Content-Disposition，支持中文文件名
	// 使用UTF-8编码处理中文文件名
	encodedFileName := url.QueryEscape(filepath.Base(filePath))
	c.Header("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"; filename*=UTF-8''%s", encodedFileName, encodedFileName))

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
		traceID, sessionId, filePath, fileInfo.Size(), written)
	return nil
}
