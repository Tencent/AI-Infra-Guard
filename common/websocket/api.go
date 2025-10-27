// Package websocket provides API endpoints for AI Infrastructure Guard task management
//
// This package implements RESTful APIs for:
// - Task submission and management
// - Task status monitoring
// - Task result retrieval
// - Support for multiple task types: MCP scan, AI infra scan, and model redteam testing
//
// API Endpoints:
// - POST /api/v1/app/taskapi/tasks - Create new tasks
// - GET /api/v1/app/taskapi/status/{id} - Get task status and logs
// - GET /api/v1/app/taskapi/result/{id} - Get task results
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

// ModelParams 模型参数配置
type ModelParams struct {
	BaseUrl string `json:"base_url" example:"https://api.openai.com/v1"` // 模型API基础URL
	Token   string `json:"token" example:"sk-xxx"`                       // API访问令牌
	Model   string `json:"model" example:"gpt-4"`                        // 模型名称
	Limit   int    `json:"limit" example:"1000"`                         // 请求限制
}

// MCPTaskRequest MCP任务请求结构体
// @Description MCP (Model Context Protocol) 安全扫描任务请求参数
type MCPTaskRequest struct {
	Content string `json:"content,omitempty" example:"扫描目标MCP服务器"` // 任务内容描述
	Model   struct {
		Model   string `json:"model" binding:"required" example:"gpt-4"`               // 模型名称 - 必需
		Token   string `json:"token" binding:"required" example:"sk-xxx"`              // API密钥 - 必需
		BaseUrl string `json:"base_url,omitempty" example:"https://api.openai.com/v1"` // 基础URL - 可选
	} `json:"model" binding:"required"` // 模型配置 - 必需
	Thread      int    `json:"thread,omitempty" example:"4"`              // 并发线程数
	Language    string `json:"language,omitempty" example:"zh"`           // 语言代码 - 可选
	Attachments string `json:"attachments,omitempty" example:"file1.zip"` // 附件文件路径
}

// AIInfraScanTaskRequest AI基础设施扫描任务请求结构体
// @Description AI基础设施安全扫描任务请求参数
type AIInfraScanTaskRequest struct {
	Target  []string          `json:"target" example:"https://example.com"`                   // 扫描目标URL列表
	Headers map[string]string `json:"headers" example:"{\"Authorization\":\"Bearer token\"}"` // 自定义请求头
	Timeout int               `json:"timeout" example:"30"`                                   // 请求超时时间(秒)
}

// PromptSecurityTaskRequest 提示词安全测试任务请求结构体
// @Description 提示词安全测试任务请求参数
// @Description 支持的数据集:
// @Description - JailBench-Tiny: 小型越狱基准测试数据集
// @Description - JailbreakPrompts-Tiny: 小型越狱提示词数据集
// @Description - ChatGPT-Jailbreak-Prompts: ChatGPT越狱提示词数据集
// @Description - JADE-db-v3.0: JADE数据库v3.0版本
// @Description - HarmfulEvalBenchmark: 有害内容评估基准数据集
type PromptSecurityTaskRequest struct {
	Model     []ModelParams `json:"model"`      // 测试模型列表
	EvalModel ModelParams   `json:"eval_model"` // 评估模型配置
	Datasets  struct {
		DataFile   []string `json:"dataFile" example:"[\"JailBench-Tiny\",\"JailbreakPrompts-Tiny\"]"` // 数据集文件列表，可选: JailBench-Tiny, JailbreakPrompts-Tiny, ChatGPT-Jailbreak-Prompts, JADE-db-v3.0, HarmfulEvalBenchmark
		NumPrompts int      `json:"numPrompts" example:"100"`                                          // 提示词数量
		RandomSeed int      `json:"randomSeed" example:"42"`                                           // 随机种子
	} `json:"dataset"` // 数据集配置
}

// APIResponse 通用API响应结构
type APIResponse struct {
	Status  int         `json:"status" example:"0"`     // 状态码: 0=成功, 1=失败
	Message string      `json:"message" example:"操作成功"` // 响应消息
	Data    interface{} `json:"data"`                   // 响应数据
}

// TaskStatusResponse 任务状态响应结构
type TaskStatusResponse struct {
	SessionID string `json:"session_id" example:"550e8400-e29b-41d4-a716-446655440000"` // 任务会话ID
	Status    string `json:"status" example:"running"`                                  // 任务状态: pending, running, completed, failed
	Title     string `json:"title" example:"MCP安全扫描任务"`                                 // 任务标题
	CreatedAt int64  `json:"created_at" example:"1640995200000"`                        // 创建时间戳(毫秒)
	UpdatedAt int64  `json:"updated_at" example:"1640995200000"`                        // 更新时间戳(毫秒)
	Log       string `json:"log" example:"任务执行日志..."`                                   // 任务执行日志
}

// TaskCreateResponse 任务创建响应结构
type TaskCreateResponse struct {
	SessionID string `json:"session_id" example:"550e8400-e29b-41d4-a716-446655440000"` // 任务会话ID
}

// Task Types and Parameters Documentation:
//
// 1. MCP Scan Task (type: "mcp_scan")
//    - Purpose: Model Context Protocol security scanning
//    - Request structure:
//      {
//        "type": "mcp_scan",
//        "content": {
//          "content": "任务描述",              // 可选: 任务内容描述
//          "model": {
//            "model": "gpt-4",               // 必需: 模型名称
//            "token": "sk-xxx",             // 必需: API密钥
//            "base_url": "https://api.openai.com/v1"  // 可选: 基础URL
//          },
//          "thread": 4,                     // 可选: 并发线程数
//          "language": "zh",             // 可选: 语言代码
//          "attachments": "file.zip"       // 可选: 附件文件路径
//        }
//      }
//
// 2. AI Infra Scan Task (type: "ai_infra_scan")
//    - Purpose: AI infrastructure security scanning
//    - Request structure:
//      {
//        "type": "ai_infra_scan",
//        "content": {
//          "target": ["https://example.com"],  // 必需: 扫描目标URL列表
//          "headers": {                        // 可选: 自定义请求头
//            "Authorization": "Bearer token"
//          },
//          "timeout": 30                       // 可选: 请求超时时间(秒)
//        }
//      }
//
// 3. Model Redteam Task (type: "model_redteam_report")
//    - Purpose: AI model red team testing and security assessment
//    - Request structure:
//      {
//        "type": "model_redteam_report",
//        "content": {
//          "model": [                        // 必需: 测试模型列表
//            {
//              "model": "gpt-4",
//              "token": "sk-xxx",
//              "base_url": "https://api.openai.com/v1"
//            }
//          ],
//          "eval_model": {                   // 必需: 评估模型配置
//            "model": "gpt-4",
//            "token": "sk-xxx"
//          },
//          "dataset": {                      // 必需: 数据集配置
//            "dataFile": ["JailBench-Tiny", "JailbreakPrompts-Tiny"],   // 数据集文件列表，可选: JailBench-Tiny, JailbreakPrompts-Tiny, ChatGPT-Jailbreak-Prompts, JADE-db-v3.0, HarmfulEvalBenchmark
//            "numPrompts": 100,              // 提示词数量
//            "randomSeed": 42                // 随机种子
//          }
//        }
//      }

// SubmitTask 创建任务接口
// @Summary Create a new task
// @Description Submit a new task for processing. Supports three types of tasks:
// @Description 1. MCP Scan (mcp_scan): Model Context Protocol security scanning
// @Description 2. AI Infra Scan (ai_infra_scan): AI infrastructure security scanning
// @Description 3. Model Redteam Report (model_redteam_report): AI model red team testing
// @Description
// @Description Request Body Examples:
// @Description
// @Description MCP Scan Task:
// @Description {
// @Description   "type": "mcp_scan",
// @Description   "content": {
// @Description     "content": "扫描MCP服务器",
// @Description     "model": {
// @Description       "model": "gpt-4",
// @Description       "token": "sk-xxx",
// @Description       "base_url": "https://api.openai.com/v1"
// @Description     },
// @Description     "thread": 4,
// @Description     "language": "zh",
// @Description     "attachments": "file.zip"
// @Description   }
// @Description }
// @Description
// @Description AI Infra Scan Task:
// @Description {
// @Description   "type": "ai_infra_scan",
// @Description   "content": {
// @Description     "target": ["https://example.com"],
// @Description     "headers": {
// @Description       "Authorization": "Bearer token"
// @Description     },
// @Description     "timeout": 30
// @Description   }
// @Description }
// @Description
// @Description Model Redteam Task:
// @Description {
// @Description   "type": "model_redteam_report",
// @Description   "content": {
// @Description     "model": [{
// @Description       "model": "gpt-4",
// @Description       "token": "sk-xxx",
// @Description       "base_url": "https://api.openai.com/v1"
// @Description     }],
// @Description     "eval_model": {
// @Description       "model": "gpt-4",
// @Description       "token": "sk-xxx"
// @Description     },
// @Description     "dataset": {
// @Description       "dataFile": ["JailBench-Tiny", "JailbreakPrompts-Tiny"],
// @Description       "numPrompts": 100,
// @Description       "randomSeed": 42
// @Description     }
// @Description   }
// @Description }
// @Tags taskapi
// @Accept json
// @Produce json
// @Param request body object{content=object,type=string} true "Task request body. Content should be JSON object containing task-specific parameters based on type"
// @Success 200 {object} APIResponse{data=TaskCreateResponse} "Task created successfully"
// @Failure 400 {object} APIResponse "Invalid request parameters"
// @Failure 500 {object} APIResponse "Internal server error"
// @Router /api/v1/app/taskapi/tasks [post]
func SubmitTask(c *gin.Context, tm *TaskManager) {
	var content struct {
		Content json.RawMessage `json:"content"`
		Type    string          `json:"type"`
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
	// content interface to byte

	switch content.Type {
	case "mcp_scan":
		var req MCPTaskRequest
		err := json.Unmarshal(content.Content, &req)
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
	case "ai_infra_scan":
		var req AIInfraScanTaskRequest
		err := json.Unmarshal(content.Content, &req)
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
	case "model_redteam_report":
		var req PromptSecurityTaskRequest
		err := json.Unmarshal(content.Content, &req)
		if err != nil {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "参数错误: " + err.Error(),
				"data":    nil,
			})
			return
		}
		params := map[string]interface{}{
			"model":      req.Model,
			"eval_model": req.EvalModel,
			"dataset":    req.Datasets,
		}
		taskReq = TaskCreateRequest{
			ID:          messageId,
			SessionID:   sessionId,
			Username:    username,
			Task:        agent.TaskTypeModelRedteamReport,
			Timestamp:   time.Now().UnixMilli(),
			Content:     "",
			Attachments: []string{},
			Params:      params,
		}
	default:
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的任务类型",
			"data":    nil,
		})
		return
	}
	err := tm.AddTaskApi(&taskReq)
	if err != nil {
		log.Errorf("任务创建失败: sessionId=%s, error=%v", sessionId, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务创建失败: " + err.Error(),
			"data":    nil,
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务创建成功，正在后台处理",
		"data": gin.H{
			"session_id": sessionId,
		},
	})
}

// GetTaskStatus 获取任务状态接口（开发者API）
// @Summary Get task status
// @Description Retrieve the current status and logs of a task by session ID. Returns task metadata and execution logs.
// @Tags taskapi
// @Produce json
// @Param id path string true "Task Session ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 200 {object} APIResponse{data=TaskStatusResponse} "Task status retrieved successfully"
// @Failure 400 {object} APIResponse "Invalid session ID format"
// @Failure 404 {object} APIResponse "Task not found"
// @Failure 500 {object} APIResponse "Internal server error"
// @Router /api/v1/app/taskapi/status/{id} [get]
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
// @Summary Get task result
// @Description Retrieve the final result of a completed task. Returns detailed scan results, vulnerabilities found, and security assessment data.
// @Tags taskapi
// @Produce json
// @Param id path string true "Task Session ID" example:"550e8400-e29b-41d4-a716-446655440000"
// @Success 200 {object} APIResponse "Task result retrieved successfully. Data contains scan results, vulnerabilities, and security findings"
// @Failure 400 {object} APIResponse "Invalid session ID format"
// @Failure 404 {object} APIResponse "Task not found or not completed"
// @Failure 500 {object} APIResponse "Internal server error"
// @Router /api/v1/app/taskapi/result/{id} [get]
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
