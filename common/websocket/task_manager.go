package websocket

import (
	"fmt"
	"io"
	"mime/multipart"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/pkg/database"
)

// 任务管理器相关数据结构

const (
	WSMsgTypeTaskAssign = "task_assign" // 任务分配
)

type TaskManager struct {
	mu           sync.RWMutex
	tasks        map[string]*TaskCreateRequest // sessionId -> 任务请求
	agentManager *AgentManager                 // 新增：引用 AgentManager
	taskStore    *database.TaskStore           // 新增：引用 TaskStore
}

func NewTaskManager(agentManager *AgentManager, taskStore *database.TaskStore) *TaskManager {
	return &TaskManager{
		tasks:        make(map[string]*TaskCreateRequest),
		agentManager: agentManager, // 注入 AgentManager
		taskStore:    taskStore,    // 注入 TaskStore
	}
}

// 添加任务
func (tm *TaskManager) AddTask(req *TaskCreateRequest) error {
	tm.mu.Lock()
	defer tm.mu.Unlock()

	// 存储任务
	tm.tasks[req.SessionID] = req

	// 异步分发任务
	go tm.dispatchTask(req.SessionID)

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
func (tm *TaskManager) dispatchTask(sessionId string) {
	// 1. 获取任务
	task, exists := tm.GetTask(sessionId)
	if !exists {
		return
	}

	// 2. 获取可用 Agent
	availableAgents := tm.agentManager.GetAvailableAgents()
	if len(availableAgents) == 0 {
		gologger.Info("No available agents")
		return
	}

	// 3. 选择 Agent（简单策略）
	selectedAgent := availableAgents[0]

	// 4. 构造任务分配消息
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

	// 5. 发送给 Agent
	selectedAgent.conn.WriteJSON(taskMsg)
}

// 处理 Agent 返回的事件
func (tm *TaskManager) HandleAgentEvent(eventType string, event interface{}) {
	// 根据事件类型处理
	switch eventType {
	case "liveStatus":
		if liveEvent, ok := event.(LiveStatusEvent); ok {
			tm.handleLiveStatusEvent(liveEvent)
		}
	case "planUpdate":
		if planEvent, ok := event.(PlanUpdateEvent); ok {
			tm.handlePlanUpdateEvent(planEvent)
		}
	case "newPlanStep":
		if stepEvent, ok := event.(NewPlanStepEvent); ok {
			tm.handleNewPlanStepEvent(stepEvent)
		}
	case "statusUpdate":
		if statusEvent, ok := event.(StatusUpdateEvent); ok {
			tm.handleStatusUpdateEvent(statusEvent)
		}
	case "toolUsed":
		if toolEvent, ok := event.(ToolUsedEvent); ok {
			tm.handleToolUsedEvent(toolEvent)
		}
	}
}

// 处理各种事件的具体方法
func (tm *TaskManager) handleLiveStatusEvent(event LiveStatusEvent) {
	// 这里可以添加事件存储逻辑
	// tm.storeEvent(event)

	// 推送给前端 SSE（需要实现 SSE 连接管理）
	// tm.pushEventToSSE(event)

	// 更新任务状态
	// tm.updateTaskStatus(event.SessionID, "running")
}

func (tm *TaskManager) handlePlanUpdateEvent(event PlanUpdateEvent) {
	// 处理计划更新事件
}

func (tm *TaskManager) handleNewPlanStepEvent(event NewPlanStepEvent) {
	// 处理新计划步骤事件
}

func (tm *TaskManager) handleStatusUpdateEvent(event StatusUpdateEvent) {
	// 处理状态更新事件
}

func (tm *TaskManager) handleToolUsedEvent(event ToolUsedEvent) {
	// 处理插件使用事件
}

// TerminateTask 终止任务
func (tm *TaskManager) TerminateTask(sessionId string) error {
	// 1. 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		return fmt.Errorf("任务不存在")
	}
	// 2. 通知 Agent 终止任务
	if session.AssignedAgent != "" {
		tm.notifyAgentToTerminate(session.AssignedAgent, sessionId)
	}
	// 3. 更新任务状态
	err = tm.taskStore.UpdateSessionStatus(sessionId, "terminated")
	if err != nil {
		return fmt.Errorf("更新任务状态失败")
	}

	// 4. 发送终止事件给前端
	tm.sendTerminationEvent(sessionId)

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
			agent.conn.WriteJSON(terminateMsg)
			break
		}
	}
}

// sendTerminationEvent 发送终止事件给前端
func (tm *TaskManager) sendTerminationEvent(sessionId string) {
	event := StatusUpdateEvent{
		ID:          generateEventID(),
		Type:        "statusUpdate",
		Timestamp:   time.Now().Unix(),
		AgentStatus: "terminated",
		Brief:       "任务已终止",
		Description: "用户主动终止了任务执行",
		NoRender:    false,
	}

	// 存储事件
	tm.taskStore.StoreEvent(sessionId, "statusUpdate", event, event.Timestamp)

	// 推送给前端 SSE（需要实现 SSE 推送逻辑）
	// tm.pushEventToSSE(sessionId, "statusUpdate", event)
}

// generateEventID 生成事件ID
func generateEventID() string {
	return time.Now().Format("20060102150405") + "_" + fmt.Sprintf("%d", time.Now().UnixNano())
}

// UpdateTask 更新任务信息
func (tm *TaskManager) UpdateTask(sessionId string, req *TaskUpdateRequest) error {
	// 1. 检查任务是否存在
	_, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		return fmt.Errorf("任务不存在")
	}

	// 2. 更新任务信息
	updates := map[string]interface{}{
		"updated_at": time.Now(),
	}

	if req.Title != "" {
		updates["title"] = req.Title
	}

	// 3. 执行数据库更新
	// err = tm.taskStore.UpdateSession(sessionId, updates)
	if err != nil {
		return fmt.Errorf("更新任务信息失败")
	}

	return nil
}

// DeleteTask 删除任务
func (tm *TaskManager) DeleteTask(sessionId string) error {
	// 1. 检查任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		return fmt.Errorf("任务不存在")
	}

	// 2. 检查任务状态是否允许删除
	if session.Status == "running" {
		return fmt.Errorf("任务正在执行中，无法删除")
	}

	// 3. 删除相关的消息记录
	// 数据库操作：删除该会话下的所有 TaskMessage 记录
	// err = tm.taskStore.DeleteSessionMessages(sessionId)
	// if err != nil {
	//     return fmt.Errorf("删除任务消息失败: %v", err)
	// }

	// 4. 删除会话记录
	// 数据库操作：删除 Session 记录
	// err = tm.taskStore.DeleteSession(sessionId)
	// if err != nil {
	//     return fmt.Errorf("删除任务失败: %v", err)
	// }

	// 5. 清理内存中的任务数据
	tm.mu.Lock()
	delete(tm.tasks, sessionId)
	tm.mu.Unlock()

	return nil
}

// UploadFile 上传文件
func (tm *TaskManager) UploadFile(file *multipart.FileHeader) (string, error) {
	// 1. 生成唯一的文件名
	ext := filepath.Ext(file.Filename)
	fileName := generateFileName() + ext

	// 2. 创建上传目录
	uploadDir := "./uploads"
	if err := os.MkdirAll(uploadDir, 0755); err != nil {
		return "", fmt.Errorf("创建上传目录失败: %v", err)
	}

	// 3. 创建文件路径
	filePath := filepath.Join(uploadDir, fileName)

	// 4. 保存文件到本地
	src, err := file.Open()
	if err != nil {
		return "", fmt.Errorf("打开文件失败: %v", err)
	}
	defer src.Close()

	dst, err := os.Create(filePath)
	if err != nil {
		return "", fmt.Errorf("创建文件失败: %v", err)
	}
	defer dst.Close()

	if _, err = io.Copy(dst, src); err != nil {
		return "", fmt.Errorf("保存文件失败: %v", err)
	}

	// 6. 返回文件URL
	fileUrl := fmt.Sprintf("/uploads/%s", fileName)

	return fileUrl, nil
}

// generateFileName 生成唯一文件名
func generateFileName() string {
	return time.Now().Format("20060102150405") + "_" + fmt.Sprintf("%d", time.Now().UnixNano())
}
