package websocket

import (
	"encoding/json"
	"net/http"
	"strings"
	"time"

	"github.com/Tencent/AI-Infra-Guard/common/agent"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"trpc.group/trpc-go/trpc-go/log"
)

type ModelParams struct {
	BaseUrl string `json:"base_url"`
	Token   string `json:"token"`
	Model   string `json:"model"`
	Limit   int    `json:"limit"`
}

// MCPTaskRequest MCP任务请求结构体
type MCPTaskRequest struct {
	Content string `json:"content,omitempty"` // 任务内容 - 必需
	Model   struct {
		Model   string `json:"model" binding:"required"` // 模型名称 - 必需
		Token   string `json:"token" binding:"required"` // API密钥 - 必需
		BaseUrl string `json:"base_url,omitempty"`       // 基础URL - 可选
	} `json:"model" binding:"required"` // 模型配置 - 必需
	Thread      int    `json:"thread,omitempty"`
	Language    string `json:"language,omitempty"` // 语言代码 - 可选
	Attachments string `json:"attachments,omitempty"`
}
type AIInfraScanTaskRequest struct {
	Target  []string          `json:"-"`
	Headers map[string]string `json:"headers"`
	Timeout int               `json:"timeout"`
}
type PromptSecurityTaskRequest struct {
	Model     []ModelParams `json:"model"`
	EvalModel ModelParams   `json:"eval_model"`
	Datasets  struct {
		DataFile   []string `json:"dataFile"`
		NumPrompts int      `json:"numPrompts"`
		RandomSeed int      `json:"randomSeed"`
	} `json:"dataset"`
}

// SubmitTask 创建任务接口
func SubmitTask(c *gin.Context, tm *TaskManager) {
	var content struct {
		Content string `json:"content"`
		Type    string `json:"type"`
	}
	if err := c.ShouldBindJSON(&content); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}
	// 生成sessionId
	sessionId := uuid.New().String()

	// 生成消息ID
	messageId := uuid.New().String()

	// 设置默认用户名为开发者API用户
	username := c.GetString("api_user")

	var taskReq TaskCreateRequest
	switch content.Type {
	case agent.TaskTypeMcpScan:
		var req MCPTaskRequest
		err := json.Unmarshal([]byte(content.Content), &req)
		if err != nil {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "参数错误: " + err.Error(),
				"data":    nil,
			})
			return
		}
		// 构建任务参数
		params := map[string]interface{}{
			"model": map[string]interface{}{
				"model":    req.Model.Model,
				"token":    req.Model.Token,
				"base_url": req.Model.BaseUrl,
			},
			"quick": false,
			"plugins": []string{
				"auth_bypass", "cmd_injection", "credential_theft", "hardcoded_api_key", "indirect_prompt_injection", "name_confusion", "rug_pull", "tool_poisoning", "tool_shadowing",
			},
		}
		var attachments []string
		if req.Attachments != "" {
			attachments = append(attachments, req.Attachments)
		}

		// 构建TaskCreateRequest
		taskReq = TaskCreateRequest{
			ID:          messageId,
			SessionID:   sessionId,
			Username:    username,
			Task:        agent.TaskTypeMcpScan,
			Timestamp:   time.Now().UnixMilli(),
			Content:     req.Content,
			Params:      params,
			Attachments: attachments,
		}
	case agent.TaskTypeAIInfraScan:
		var req AIInfraScanTaskRequest
		err := json.Unmarshal([]byte(content.Content), &req)
		if err != nil {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "参数错误: " + err.Error(),
				"data":    nil,
			})
			return
		}
		scanParams := map[string]interface{}{
			"headers": req.Headers,
			"timeout": req.Timeout,
		}

		taskReq = TaskCreateRequest{
			ID:          messageId,
			SessionID:   sessionId,
			Username:    username,
			Task:        agent.TaskTypeAIInfraScan,
			Timestamp:   time.Now().UnixMilli(),
			Params:      scanParams,
			Content:     strings.Join(req.Target, "\n"),
			Attachments: []string{},
		}
	case agent.TaskTypeModelRedteamReport:
		var req map[string]interface{}
		err := json.Unmarshal([]byte(content.Content), &req)
		if err != nil {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "参数错误: " + err.Error(),
				"data":    nil,
			})
			return
		}
		taskReq = TaskCreateRequest{
			ID:          messageId,
			SessionID:   sessionId,
			Username:    username,
			Task:        agent.TaskTypeModelRedteamReport,
			Timestamp:   time.Now().UnixMilli(),
			Content:     "",
			Attachments: []string{},
			Params:      req,
		}
	}

	// 调用TaskManager异步创建任务
	go func() {
		err := tm.AddTaskApi(&taskReq)
		if err != nil {
			log.Errorf("异步任务创建失败: sessionId=%s, error=%v", sessionId, err)
		} else {
			log.Infof("异步任务创建成功: sessionId=%s", sessionId)
		}
	}()

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务创建成功，正在后台处理",
		"data": gin.H{
			"session_id": sessionId,
			"task_type":  agent.TaskTypeMcpScan,
		},
	})
}

// GetTaskStatus 获取任务状态接口（开发者API）
func GetTaskStatus(c *gin.Context, tm *TaskManager) {
	sessionId := c.Param("id")

	if sessionId == "" {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务ID不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的任务ID格式",
			"data":    nil,
		})
		return
	}

	// 从数据库获取任务信息
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务不存在",
			"data":    nil,
		})
		return
	}

	// 获取任务的所有消息/事件
	messages, err := tm.taskStore.GetSessionEventsByType(sessionId, "actionLog")
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取任务结果失败",
			"data":    nil,
		})
		return
	}

	msg := ""
	type logStruct struct {
		ActionLog string `json:"actionLog"`
	}
	for _, m := range messages {
		var x logStruct
		err = json.Unmarshal([]byte(m.EventData.String()), &x)
		if err != nil {
			continue
		}
		msg += x.ActionLog
	}

	// 构建状态响应
	statusData := gin.H{
		"session_id": session.ID,
		"status":     session.Status,
		"title":      session.Title,
		"created_at": session.CreatedAt,
		"updated_at": session.UpdatedAt,
		"log":        msg,
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取任务状态成功",
		"data":    statusData,
	})
}

// GetTaskResult 获取任务结果接口（开发者API）
func GetTaskResult(c *gin.Context, tm *TaskManager) {
	traceID := getTraceID(c)
	sessionId := c.Param("id")

	if sessionId == "" {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务ID不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的任务ID格式",
			"data":    nil,
		})
		return
	}

	log.Infof("开始获取任务结果: trace_id=%s, sessionId=%s", traceID, sessionId)

	// 获取任务的所有消息/事件
	messages, err := tm.taskStore.GetSessionEventsByType(sessionId, "resultUpdate")
	if err != nil || len(messages) == 0 {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取任务结果失败,任务可能尚未完成",
			"data":    nil,
		})
		return
	}
	msg := messages[0]
	// 解析事件数据
	var eventData map[string]interface{}
	if err := json.Unmarshal(msg.EventData, &eventData); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取任务结果失败",
			"data":    nil,
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "ok",
		"data":    eventData,
	})
}
