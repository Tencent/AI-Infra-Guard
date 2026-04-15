// Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Requirement: Any integration or derivative work must explicitly attribute
// Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
// documentation or user interface, as detailed in the NOTICE file.

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
	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"trpc.group/trpc-go/trpc-go/log"
)

// ModelParams represents model configuration parameters
type ModelParams struct {
	BaseUrl string `json:"base_url" example:"https://api.openai.com/v1"` // Model API base URL
	Token   string `json:"token" example:"sk-xxx"`                       // API access token
	Model   string `json:"model" example:"gpt-4"`                        // Model name
	Limit   int    `json:"limit,omitempty" example:"1000"`               // Request limit
}

// MCPTaskRequest represents MCP task request structure
// @Description MCP (Model Context Protocol) security scan task parameters
type MCPTaskRequest struct {
	Prompt string `json:"prompt,omitempty" example:"Enter a URL for remote MCP scan, or leave empty for source-code scan"` // Scan description or MCP server URL
	Model  struct {
		Model   string `json:"model" example:"gpt-4"`                         // Model name - required
		Token   string `json:"token" example:"sk-xxx"`                                   // API key - required
		BaseUrl string `json:"base_url,omitempty" example:"https://api.openai.com/v1"` // Base URL - optional
	} `json:"model"` // Model configuration - required
	Thread      int               `json:"thread,omitempty" example:"4"`              // Concurrent thread count
	Language    string            `json:"language,omitempty" example:"zh"`           // Language code - optional
	Attachments string            `json:"attachments,omitempty" example:"file1.zip"` // Attachment file path (upload first)
	Headers     map[string]string `json:"headers,omitempty" example:"{\"Authorization\":\"Bearer token\"}"`
}

// AIInfraScanTaskRequest represents AI infrastructure scan task request structure
// @Description AI infrastructure security scan task parameters: target URLs, custom headers, and optional model config for result analysis
type AIInfraScanTaskRequest struct {
	Target  []string          `json:"target" example:"https://example.com"`                   // List of scan target URLs
	Headers map[string]string `json:"headers" example:"{\"Authorization\":\"Bearer token\"}"` // Custom request headers
	Timeout int               `json:"timeout" example:"30"`                                   // Request timeout in seconds
	Model   struct {
		Model   string `json:"model" binding:"required" example:"gpt-4"`               // Model name - required
		Token   string `json:"token" binding:"required" example:"sk-xxx"`              // API key - required
		BaseUrl string `json:"base_url,omitempty" example:"https://api.openai.com/v1"` // Base URL - optional
	} `json:"model,omitempty"` // Model configuration - optional, used for assisted vulnerability analysis
}

// PromptSecurityTaskRequest represents prompt security test task request structure
// @Description Prompt security (red team) task parameters. Supports dataset selection or manual prompt input.
// @Description Supported datasets:
// @Description - JailBench-Tiny: small jailbreak benchmark dataset
// @Description - JailbreakPrompts-Tiny: small jailbreak prompt dataset
// @Description - ChatGPT-Jailbreak-Prompts: ChatGPT jailbreak prompt dataset
// @Description - JADE-db-v3.0: JADE database v3.0
// @Description - HarmfulEvalBenchmark: harmful content evaluation benchmark dataset
type PromptSecurityTaskRequest struct {
	Model     []ModelParams `json:"model"`      // List of models under test
	EvalModel ModelParams   `json:"eval_model"` // Evaluation model configuration
	Datasets  struct {
		DataFile   []string `json:"dataFile" example:"[\"JailBench-Tiny\",\"JailbreakPrompts-Tiny\"]"` // Dataset file list
		NumPrompts int      `json:"numPrompts" example:"100"`                                          // Number of prompts
		RandomSeed int      `json:"randomSeed" example:"42"`                                           // Random seed
	} `json:"dataset"` // Dataset configuration
	Prompt     string   `json:"prompt"`     // Custom test prompt - optional
	Techniques []string `json:"techniques"` // Attack technique list - optional
}

// AgentScanTaskRequest represents Agent security scan task request structure
// @Description Agent security scan task parameters. agent_id and agent_config are mutually exclusive:
// agent_id references a config pre-saved on the server; agent_config passes YAML content inline without prior saving.
type AgentScanTaskRequest struct {
	AgentID     string      `json:"agent_id,omitempty" example:"demo-agent"`                              // Agent config name (mutually exclusive with agent_config)
	AgentConfig string      `json:"agent_config,omitempty" example:"provider: dify\nbase_url: ..."`       // Inline YAML config content (mutually exclusive with agent_id)
	EvalModel   ModelParams `json:"eval_model"`                                                           // Evaluation model config - optional, falls back to system default
	Language    string      `json:"language,omitempty" example:"zh"`                                      // Language code - optional
	Prompt      string      `json:"prompt,omitempty" example:"Focus on privilege escalation and data leakage risks"` // Additional scan instructions - optional
}

// APIResponse is the common API response structure
type APIResponse struct {
	Status  int         `json:"status" example:"0"`     // Status code: 0=success, 1=failure
	Message string      `json:"message" example:"ok"`     // Response message
	Data    interface{} `json:"data"`     // Response data
}

// TaskStatusResponse holds the task status response
type TaskStatusResponse struct {
	SessionID string `json:"session_id" example:"550e8400-e29b-41d4-a716-446655440000"` // Task session ID
	Status    string `json:"status" example:"running"`                                  // Task status: pending, running, completed, failed
	Title     string `json:"title" example:"MCP Scan Task"`                                   // Task title
	CreatedAt int64  `json:"created_at" example:"1640995200000"`                        // Creation timestamp (ms)
	UpdatedAt int64  `json:"updated_at" example:"1640995200000"`                        // Last update timestamp (ms)
	Log       string `json:"log" example:"Task execution log..."`                           // Task execution log
}

// TaskCreateResponse holds the task creation response
type TaskCreateResponse struct {
	SessionID string `json:"session_id" example:"550e8400-e29b-41d4-a716-446655440000"` // Task session ID
}

func resolveTaskAPIUsername(c *gin.Context) string {
	username := strings.TrimSpace(c.GetString("api_user"))
	if username != "" {
		return username
	}

	username = strings.TrimSpace(c.GetHeader("username"))
	if username != "" {
		return username
	}

	return "api_user"
}

func resolveDefaultTaskAPIModel(tm *TaskManager, username string) (*database.ModelParams, error) {
	if tm == nil || tm.modelStore == nil {
		return nil, nil
	}

	models, err := tm.modelStore.GetUserModels(username)
	if err != nil {
		return nil, err
	}
	if len(models) == 0 {
		return nil, nil
	}

	model := models[0]
	return &database.ModelParams{
		Model:   model.ModelName,
		Token:   model.Token,
		BaseUrl: model.BaseURL,
		Limit:   model.Limit,
	}, nil
}

// SubmitTask is the task creation handler
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
// @Description     "prompt": "Custom prompt for scan",
// @Description     "model": {
// @Description       "model": "gpt-4",
// @Description       "token": "sk-xxx",
// @Description       "base_url": "https://api.openai.com/v1"
// @Description     },
// @Description     "thread": 4,
// @Description     "language": "zh",
// @Description     "attachments": "file.zip",
// @Description     "headers": {
// @Description       "Authorization": "Bearer token"
// @Description     }
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
// @Description     "timeout": 30,
// @Description     "model": {
// @Description       "model": "gpt-4",
// @Description       "token": "sk-xxx",
// @Description       "base_url": "https://api.openai.com/v1"
// @Description     }
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
// @Description     },
// @Description     "prompt": "How to make a bomb?",
// @Description     "techniques": [""]
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
			"message": "invalid parameters: " + err.Error(),
			"data":    nil,
		})
		return
	}
	// Generate session and message IDs
	sessionId := uuid.New().String()
	messageId := uuid.New().String()

	// Resolve username: prefer auth middleware, fall back to explicit header
	username := resolveTaskAPIUsername(c)

	var taskReq TaskCreateRequest
	// content interface to byte

	switch content.Type {
	case "mcp_scan":
		var req MCPTaskRequest
		err := json.Unmarshal(content.Content, &req)
		if err != nil {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "invalid parameters: " + err.Error(),
				"data":    nil,
			})
			return
		}
		if strings.TrimSpace(req.Model.Model) == "" || strings.TrimSpace(req.Model.Token) == "" {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "invalid parameters: mcp_scan requires model.model and model.token",
				"data":    nil,
			})
			return
		}
		// Build task params
		params := map[string]interface{}{
			"model": map[string]interface{}{
				"model":    req.Model.Model,
				"token":    req.Model.Token,
				"base_url": req.Model.BaseUrl,
			},
			"headers": req.Headers,
		}
		var attachments []string
		if req.Attachments != "" {
			attachments = append(attachments, req.Attachments)
		}

		// Build TaskCreateRequest
		taskReq = TaskCreateRequest{
			ID:          messageId,
			SessionID:   sessionId,
			Username:    username,
			Task:        agent.TaskTypeMcpScan,
			Timestamp:   time.Now().UnixMilli(),
			Content:     req.Prompt,
			Params:      params,
			Attachments: attachments,
		}
	case "ai_infra_scan":
		var req AIInfraScanTaskRequest
		err := json.Unmarshal(content.Content, &req)
		if err != nil {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "invalid parameters: " + err.Error(),
				"data":    nil,
			})
			return
		}
		scanParams := map[string]interface{}{
			"headers": req.Headers,
			"timeout": req.Timeout,
			"model": map[string]interface{}{
				"model":    req.Model.Model,
				"token":    req.Model.Token,
				"base_url": req.Model.BaseUrl,
			},
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
				"message": "invalid parameters: " + err.Error(),
				"data":    nil,
			})
			return
		}
		params := map[string]interface{}{
			"model":      req.Model,
			"eval_model": req.EvalModel,
			"dataset":    req.Datasets,
			"techniques": req.Techniques,
		}
		taskReq = TaskCreateRequest{
			ID:          messageId,
			SessionID:   sessionId,
			Username:    username,
			Task:        agent.TaskTypeModelRedteamReport,
			Timestamp:   time.Now().UnixMilli(),
			Content:     req.Prompt,
			Attachments: []string{},
			Params:      params,
		}
	case "agent_scan":
		var req AgentScanTaskRequest
		err := json.Unmarshal(content.Content, &req)
		if err != nil {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "invalid parameters: " + err.Error(),
				"data":    nil,
			})
			return
		}

		// Resolve agent YAML: inline content takes priority over stored config.
		var agentData []byte
		if strings.TrimSpace(req.AgentConfig) != "" {
			// Method A: caller supplies YAML inline — no file lookup needed.
			agentData = []byte(strings.TrimSpace(req.AgentConfig))
		} else if strings.TrimSpace(req.AgentID) != "" {
			// Method B: look up pre-saved config by agent_id.
			agentData, err = readAgentConfigContent(username, req.AgentID)
			if err != nil {
				c.JSON(http.StatusOK, gin.H{
					"status":  1,
					"message": "invalid parameters: failed to load agent config: " + err.Error(),
					"data":    nil,
				})
				return
			}
		} else {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "invalid parameters: agent_id or agent_config must be provided",
				"data":    nil,
			})
			return
		}

		evalModel := req.EvalModel
		if strings.TrimSpace(evalModel.Model) == "" ||
			strings.TrimSpace(evalModel.Token) == "" ||
			strings.TrimSpace(evalModel.BaseUrl) == "" {
			defaultModel, err := resolveDefaultTaskAPIModel(tm, username)
			if err != nil {
				c.JSON(http.StatusOK, gin.H{
					"status":  1,
					"message": "invalid parameters: failed to resolve default model: " + err.Error(),
					"data":    nil,
				})
				return
			}
			if defaultModel == nil {
				c.JSON(http.StatusOK, gin.H{
					"status":  1,
					"message": "invalid parameters: no default model configured",
					"data":    nil,
				})
				return
			}
			evalModel = ModelParams{
				Model:   defaultModel.Model,
				Token:   defaultModel.Token,
				BaseUrl: defaultModel.BaseUrl,
				Limit:   defaultModel.Limit,
			}
		}

		params := map[string]interface{}{
			"agent_id":   req.AgentID,
			"agent_data": string(agentData),
			"eval_model": map[string]interface{}{
				"model":    evalModel.Model,
				"token":    evalModel.Token,
				"base_url": evalModel.BaseUrl,
				"limit":    evalModel.Limit,
			},
		}

		taskReq = TaskCreateRequest{
			ID:             messageId,
			SessionID:      sessionId,
			Username:       username,
			Task:           agent.TaskTypeAgentScan,
			Timestamp:      time.Now().UnixMilli(),
			Content:        req.Prompt,
			Attachments:    []string{},
			Params:         params,
			CountryIsoCode: req.Language,
		}
	default:
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "unsupported task type",
			"data":    nil,
		})
		return
	}
	err := tm.AddTaskApi(&taskReq)
	if err != nil {
		log.Errorf("task creation failed: sessionId=%s, error=%v", sessionId, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "task creation failed: " + err.Error(),
			"data":    nil,
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "task created successfully",
		"data": gin.H{
			"session_id": sessionId,
		},
	})
}

// GetTaskStatus retrieves task status (developer API)
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
			"message": "session ID is required",
			"data":    nil,
		})
		return
	}

	// Validate session ID format
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "invalid session ID format",
			"data":    nil,
		})
		return
	}

	// Fetch task from store
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "task not found",
			"data":    nil,
		})
		return
	}

	// Fetch all task events
	messages, err := tm.taskStore.GetSessionEventsByType(sessionId, "actionLog")
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "failed to retrieve task data",
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

	// Build status response
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
		"message": "ok",
		"data":    statusData,
	})
}

// GetTaskResult retrieves task result (developer API)
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
			"message": "session ID is required",
			"data":    nil,
		})
		return
	}

	// Validate session ID format
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "invalid session ID format",
			"data":    nil,
		})
		return
	}

	log.Infof("fetching task result: trace_id=%s, sessionId=%s", traceID, sessionId)

	// Fetch all task events
	messages, err := tm.taskStore.GetSessionEventsByType(sessionId, "resultUpdate")
	if err != nil || len(messages) == 0 {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "task result not available yet",
			"data":    nil,
		})
		return
	}
	msg := messages[0]
	// Parse event data
	var eventData map[string]interface{}
	if err := json.Unmarshal(msg.EventData, &eventData); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "failed to retrieve task result",
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
