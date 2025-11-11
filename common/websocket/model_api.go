package websocket

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
	"trpc.group/trpc-go/trpc-go/log"
)

// ModelInfo 模型信息
type ModelInfo struct {
	Model                 string `json:"model" binding:"required"`
	Token                 string `json:"token"`    // 对于HTTP endpoint类型可为空
	BaseURL               string `json:"base_url"` // 对于HTTP endpoint类型可为空
	Limit                 int    `json:"limit"`
	Note                  string `json:"note"`
	ModelType             string `json:"model_type"`              // 模型类型：openai 或 http_endpoint
	HTTPMethod            string `json:"http_method"`             // HTTP方法
	HTTPEndpoint          string `json:"http_endpoint"`           // HTTP端点URL
	HTTPHeaders           string `json:"http_headers"`            // HTTP请求头（JSON格式）
	HTTPRequestBody       string `json:"http_request_body"`       // HTTP请求体模板
	HTTPResponseTransform string `json:"http_response_transform"` // HTTP响应转换逻辑
	RequestInterval       int    `json:"request_interval"`        // 请求频率间隔（毫秒）
}

// CreateModelRequest 创建模型请求
type CreateModelRequest struct {
	ModelID string    `json:"model_id" binding:"required"`
	Model   ModelInfo `json:"model" binding:"required"`
}

// UpdateModelRequest 更新模型请求
type UpdateModelRequest struct {
	Model ModelInfo `json:"model" binding:"required"`
}

// DeleteModelRequest 删除模型请求
type DeleteModelRequest struct {
	ModelIDs []string `json:"model_ids" binding:"required"`
}

// TestModelRequest 测试模型请求
type TestModelRequest struct {
	TestInput string `json:"test_input" binding:"required"`
}

// TestModelResponse 测试模型响应
type TestModelResponse struct {
	StatusCode    int         `json:"status_code"`
	RawResponse   interface{} `json:"raw_response"`
	TransformText string      `json:"transform_text,omitempty"`
	Error         string      `json:"error,omitempty"`
}

// ModelManager 模型管理器
type ModelManager struct {
	modelStore *database.ModelStore
}

// NewModelManager 创建新的ModelManager实例
func NewModelManager(modelStore *database.ModelStore) *ModelManager {
	return &ModelManager{modelStore: modelStore}
}

// HandleGetModelList 获取模型列表接口
func HandleGetModelList(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")

	log.Debugf("获取模型列表: trace_id=%s, username=%s", traceID, username)

	// 从数据库获取模型列表
	models, err := mm.modelStore.GetUserModels(username)
	if err != nil {
		log.Errorf("获取模型列表失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取模型列表失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 转换为响应格式
	var response []map[string]interface{}
	for _, model := range models {
		modelData := map[string]interface{}{
			"model_id": model.ModelID,
			"model": map[string]interface{}{
				"model":                   model.ModelName,
				"model_type":              model.ModelType,
				"token":                   maskToken(model.Token),
				"base_url":                model.BaseURL,
				"limit":                   model.Limit,
				"note":                    model.Note,
				"http_method":             model.HTTPMethod,
				"http_endpoint":           model.HTTPEndpoint,
				"http_headers":            model.HTTPHeaders,
				"http_request_body":       model.HTTPRequestBody,
				"http_response_transform": model.HTTPResponseTransform,
				"request_interval":        model.RequestInterval,
				"created_at":              model.CreatedAt,
				"updated_at":              model.UpdatedAt,
			},
		}
		response = append(response, modelData)
	}

	log.Debugf("获取模型列表成功: trace_id=%s, username=%s, count=%d", traceID, username, len(models))

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取模型列表成功",
		"data":    response,
	})
}

// maskToken 遮蔽Token显示
func maskToken(token string) string {
	if token == "" {
		return ""
	}
	if len(token) <= 8 {
		return "***"
	}
	return token[:4] + "***" + token[len(token)-4:]
}

// HandleGetModelDetail 获取模型详情接口
func HandleGetModelDetail(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")
	modelID := c.Param("modelId")

	log.Debugf("获取模型详情: trace_id=%s, username=%s, modelID=%s", traceID, username, modelID)

	// 从数据库获取模型详情
	model, err := mm.modelStore.GetModelByUser(modelID, username)
	if err != nil {
		log.Errorf("获取模型详情失败: trace_id=%s, username=%s, modelID=%s, error=%v", traceID, username, modelID, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取模型详情失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	if model == nil {
		log.Errorf("模型不存在: trace_id=%s, username=%s, modelID=%s", traceID, username, modelID)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型不存在",
			"data":    nil,
		})
		return
	}

	// 转换为响应格式
	response := map[string]interface{}{
		"model_id": model.ModelID,
		"model": map[string]interface{}{
			"model":                   model.ModelName,
			"model_type":              model.ModelType,
			"token":                   maskToken(model.Token),
			"base_url":                model.BaseURL,
			"limit":                   model.Limit,
			"note":                    model.Note,
			"http_method":             model.HTTPMethod,
			"http_endpoint":           model.HTTPEndpoint,
			"http_headers":            model.HTTPHeaders,
			"http_request_body":       model.HTTPRequestBody,
			"http_response_transform": model.HTTPResponseTransform,
			"created_at":              model.CreatedAt,
			"updated_at":              model.UpdatedAt,
		},
	}

	log.Debugf("获取模型详情成功: trace_id=%s, username=%s, modelID=%s", traceID, username, modelID)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取模型详情成功",
		"data":    response,
	})
}

// HandleCreateModel 创建模型接口
func HandleCreateModel(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")

	// 1. 字段校验
	var req CreateModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.Errorf("请求参数解析失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 2. 验证必填字段
	if req.ModelID == "" {
		log.Errorf("模型ID为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型ID不能为空",
			"data":    nil,
		})
		return
	}

	if req.Model.Model == "" {
		log.Errorf("模型名称为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型名称不能为空",
			"data":    nil,
		})
		return
	}

	// 根据模型类型进行不同的校验
	modelType := req.Model.ModelType
	if modelType == "" {
		modelType = "openai" // 默认为openai类型
	}

	// 对于openai类型，token和base_url是必需的
	if modelType == "openai" && (req.Model.Token == "" || req.Model.BaseURL == "") {
		log.Errorf("OpenAI模型参数不完整: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "OpenAI模型必须提供Token和BaseURL",
			"data":    nil,
		})
		return
	}

	// 对于http_endpoint类型，http_endpoint是必需的
	if modelType == "http_endpoint" && req.Model.HTTPEndpoint == "" {
		log.Errorf("HTTP端点模型参数不完整: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "HTTP端点模型必须提供HTTP端点URL",
			"data":    nil,
		})
		return
	}

	// 设置默认值
	if req.Model.Limit <= 0 {
		req.Model.Limit = 1000
	}
	if req.Model.HTTPMethod == "" {
		req.Model.HTTPMethod = "POST"
	}

	log.Debugf("创建模型请求: trace_id=%s, username=%s, modelID=%s, modelType=%s", traceID, username, req.ModelID, modelType)

	// 3. 验证模型连接（仅对OpenAI类型）
	if modelType == "openai" {
		// 验证OpenAI模型连接
		ai := models.NewOpenAI(req.Model.Token, req.Model.Model, req.Model.BaseURL)
		if err := ai.Vaild(context.Background()); err != nil {
			log.Errorf("OpenAI模型校验失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "模型校验失败: " + err.Error(),
				"data":    nil,
			})
			return
		}
	}
	// HTTP端点模型暂时跳过连接验证，在测试时进行

	// 4. 创建模型数据
	model := &database.Model{
		ModelID:               req.ModelID,
		Username:              username,
		ModelName:             req.Model.Model,
		Token:                 req.Model.Token,
		BaseURL:               req.Model.BaseURL,
		Note:                  req.Model.Note,
		Limit:                 req.Model.Limit,
		ModelType:             modelType,
		HTTPMethod:            req.Model.HTTPMethod,
		HTTPEndpoint:          req.Model.HTTPEndpoint,
		HTTPHeaders:           req.Model.HTTPHeaders,
		HTTPRequestBody:       req.Model.HTTPRequestBody,
		HTTPResponseTransform: req.Model.HTTPResponseTransform,
		RequestInterval:       req.Model.RequestInterval,
	}

	// 5. 保存到数据库
	err := mm.modelStore.CreateModel(model)
	if err != nil {
		log.Errorf("创建模型失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, req.ModelID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "创建模型失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Debugf("创建模型成功: trace_id=%s, modelID=%s, modelName=%s, username=%s", traceID, req.ModelID, req.Model.Model, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "模型创建成功",
		"data":    nil,
	})
}

// HandleTestModel 测试HTTP endpoint模型接口
func HandleTestModel(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")
	modelID := c.Param("modelId")

	log.Debugf("测试模型: trace_id=%s, username=%s, modelID=%s", traceID, username, modelID)

	// 1. 解析请求参数
	var req TestModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.Errorf("请求参数解析失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 2. 获取模型信息
	model, err := mm.modelStore.GetModelByUser(modelID, username)
	if err != nil || model == nil {
		log.Errorf("获取模型信息失败: trace_id=%s, username=%s, modelID=%s, error=%v", traceID, username, modelID, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型不存在",
			"data":    nil,
		})
		return
	}

	// 3. 只支持http_endpoint类型的测试
	if model.ModelType != "http_endpoint" {
		log.Errorf("不支持的模型类型: trace_id=%s, username=%s, modelID=%s, modelType=%s", traceID, username, modelID, model.ModelType)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "只支持HTTP端点模型的测试",
			"data":    nil,
		})
		return
	}

	// 4. 执行测试
	result := testHTTPEndpointModel(model, req.TestInput, traceID)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "测试完成",
		"data":    result,
	})
}

// testHTTPEndpointModel 测试HTTP端点模型
func testHTTPEndpointModel(model *database.Model, testInput, traceID string) TestModelResponse {
	// 1. 构建请求体
	requestBody := model.HTTPRequestBody
	if requestBody == "" {
		requestBody = `{"message": "{{.Prompt}}"}`
	}

	// 变量替换
	requestBody = strings.ReplaceAll(requestBody, "{{.Prompt}}", testInput)
	requestBody = strings.ReplaceAll(requestBody, "{{prompt}}", testInput)
	requestBody = strings.ReplaceAll(requestBody, "{{user_message}}", testInput)

	// 2. 构建请求头
	headers := make(map[string]string)
	if model.HTTPHeaders != "" {
		if err := json.Unmarshal([]byte(model.HTTPHeaders), &headers); err != nil {
			log.Errorf("解析HTTP头部失败: trace_id=%s, headers=%s, error=%v", traceID, model.HTTPHeaders, err)
			return TestModelResponse{
				Error: "HTTP头部格式错误: " + err.Error(),
			}
		}
	}

	// 确保有Content-Type
	if _, exists := headers["Content-Type"]; !exists {
		headers["Content-Type"] = "application/json"
	}

	// 3. 发送HTTP请求
	client := &http.Client{Timeout: 30 * time.Second}

	var req *http.Request
	var err error

	if strings.ToUpper(model.HTTPMethod) == "GET" {
		req, err = http.NewRequest("GET", model.HTTPEndpoint, nil)
	} else {
		req, err = http.NewRequest(strings.ToUpper(model.HTTPMethod), model.HTTPEndpoint, bytes.NewBufferString(requestBody))
	}

	if err != nil {
		log.Errorf("创建HTTP请求失败: trace_id=%s, error=%v", traceID, err)
		return TestModelResponse{
			Error: "创建HTTP请求失败: " + err.Error(),
		}
	}

	// 设置请求头
	for key, value := range headers {
		req.Header.Set(key, value)
	}

	// 发送请求
	resp, err := client.Do(req)
	if err != nil {
		log.Errorf("HTTP请求失败: trace_id=%s, error=%v", traceID, err)
		return TestModelResponse{
			StatusCode: 0,
			Error:      "HTTP请求失败: " + err.Error(),
		}
	}
	defer resp.Body.Close()

	// 4. 读取响应
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Errorf("读取响应失败: trace_id=%s, error=%v", traceID, err)
		return TestModelResponse{
			StatusCode: resp.StatusCode,
			Error:      "读取响应失败: " + err.Error(),
		}
	}

	// 5. 解析响应
	var rawResponse interface{}
	if err := json.Unmarshal(body, &rawResponse); err != nil {
		// 如果不是JSON，直接使用字符串
		rawResponse = string(body)
	}

	// 6. 应用响应转换
	transformText := ""
	if model.HTTPResponseTransform != "" && rawResponse != nil {
		log.Infof("开始应用响应转换: trace_id=%s, transform=%s", traceID, model.HTTPResponseTransform)
		if responseMap, ok := rawResponse.(map[string]interface{}); ok {
			transformText = applySimpleResponseTransform(responseMap, model.HTTPResponseTransform)
			log.Infof("响应转换结果: trace_id=%s, result_length=%d", traceID, len(transformText))
		} else {
			transformText = fmt.Sprintf("%v", rawResponse)
			log.Infof("非map响应转换: trace_id=%s, result_length=%d", traceID, len(transformText))
		}
	} else {
		log.Infof("跳过响应转换: trace_id=%s, transform_empty=%v, response_nil=%v", traceID, model.HTTPResponseTransform == "", rawResponse == nil)
	}

	return TestModelResponse{
		StatusCode:    resp.StatusCode,
		RawResponse:   rawResponse,
		TransformText: transformText,
	}
}

// applySimpleResponseTransform 应用简单的响应转换
func applySimpleResponseTransform(rawResponse map[string]interface{}, transform string) string {
	if transform == "" {
		return ""
	}

	// 支持特殊转换逻辑
	if strings.HasPrefix(transform, "smart_extract:") {
		return applySmartExtraction(rawResponse, transform[14:])
	}

	// 支持简单的JSON路径，如 "data.choices[0].message.content"
	if strings.Contains(transform, ".") {
		return getNestedValue(rawResponse, transform)
	}

	// 直接字段访问
	if value, exists := rawResponse[transform]; exists {
		return fmt.Sprintf("%v", value)
	}

	return ""
}

// getNestedValue 获取嵌套的JSON值
func getNestedValue(data map[string]interface{}, path string) string {
	parts := strings.Split(path, ".")
	current := data

	for _, part := range parts {
		if strings.Contains(part, "[") && strings.Contains(part, "]") {
			// 处理数组索引，如 choices[0]
			fieldName := part[:strings.Index(part, "[")]
			indexStr := part[strings.Index(part, "[")+1 : strings.Index(part, "]")]

			if arr, ok := current[fieldName].([]interface{}); ok {
				index := 0
				fmt.Sscanf(indexStr, "%d", &index)
				if index >= 0 && index < len(arr) {
					if nextMap, ok := arr[index].(map[string]interface{}); ok {
						current = nextMap
					} else {
						return fmt.Sprintf("%v", arr[index])
					}
				} else {
					return ""
				}
			} else {
				return ""
			}
		} else {
			// 普通字段访问
			if value, exists := current[part]; exists {
				if nextMap, ok := value.(map[string]interface{}); ok {
					current = nextMap
				} else {
					return fmt.Sprintf("%v", value)
				}
			} else {
				return ""
			}
		}
	}

	return ""
}

// applySmartExtraction 智能提取响应内容
func applySmartExtraction(rawResponse map[string]interface{}, extractType string) string {
	switch extractType {
	case "alipay_message":
		return extractAlipayMessage(rawResponse)
	case "antom_copilot":
		return extractAntomCopilotMessage(rawResponse)
	case "best_text_content":
		return extractBestTextContent(rawResponse)
	default:
		return ""
	}
}

// extractAlipayMessage 提取支付宝API消息内容
func extractAlipayMessage(rawResponse map[string]interface{}) string {
	// 尝试获取 data.messageList 数组
	if data, ok := rawResponse["data"].(map[string]interface{}); ok {
		if messageList, ok := data["messageList"].([]interface{}); ok {
			// 遍历消息列表，寻找最佳回复
			for _, msg := range messageList {
				if msgMap, ok := msg.(map[string]interface{}); ok {
					// 检查消息类型是否为输出
					if ioType, ok := msgMap["ioType"].(string); ok && ioType == "OUTPUT" {
						// 检查内容数组
						if content, ok := msgMap["content"].([]interface{}); ok && len(content) > 0 {
							if contentItem, ok := content[0].(map[string]interface{}); ok {
								if text, ok := contentItem["text"].(string); ok {
									// 过滤掉JSON格式的状态消息
									if !strings.HasPrefix(text, "{") && !strings.Contains(text, "\"status\"") {
										return text
									}
								}
							}
						}
					}
				}
			}

			// 如果没找到合适的消息，返回第一个文本消息
			for _, msg := range messageList {
				if msgMap, ok := msg.(map[string]interface{}); ok {
					if content, ok := msgMap["content"].([]interface{}); ok && len(content) > 0 {
						if contentItem, ok := content[0].(map[string]interface{}); ok {
							if text, ok := contentItem["text"].(string); ok && text != "" {
								return text
							}
						}
					}
				}
			}
		}
	}
	return ""
}

// extractBestTextContent 提取最佳文本内容（通用）
func extractBestTextContent(rawResponse map[string]interface{}) string {
	// 递归搜索包含实质内容的文本字段
	return findBestTextInResponse(rawResponse, 0)
}

// findBestTextInResponse 在响应中递归查找最佳文本内容
func findBestTextInResponse(data interface{}, depth int) string {
	if depth > 5 { // 防止无限递归
		return ""
	}

	switch v := data.(type) {
	case map[string]interface{}:
		// 优先查找常见的文本字段
		priorities := []string{"text", "content", "message", "answer", "response", "reply"}
		for _, key := range priorities {
			if value, exists := v[key]; exists {
				if str, ok := value.(string); ok && len(str) > 10 && !strings.HasPrefix(str, "{") {
					return str
				}
			}
		}

		// 递归搜索所有字段
		for _, value := range v {
			if result := findBestTextInResponse(value, depth+1); result != "" {
				return result
			}
		}
	case []interface{}:
		// 搜索数组中的每个元素
		for _, item := range v {
			if result := findBestTextInResponse(item, depth+1); result != "" {
				return result
			}
		}
	case string:
		// 如果是字符串且长度合适，检查是否为有效内容
		if len(v) > 10 && !strings.HasPrefix(v, "{") && !strings.Contains(v, "\"status\"") {
			return v
		}
	}

	return ""
}

// extractAntomCopilotMessage 提取Antom Copilot API消息内容
func extractAntomCopilotMessage(rawResponse map[string]interface{}) string {
	// 尝试获取 data.messageList 数组
	if data, ok := rawResponse["data"].(map[string]interface{}); ok {
		if messageList, ok := data["messageList"].([]interface{}); ok {
			// 策略1: 查找包含实际用户回复的消息（非JSON结构）
			for _, msg := range messageList {
				if msgMap, ok := msg.(map[string]interface{}); ok {
					if content, ok := msgMap["content"].([]interface{}); ok && len(content) > 0 {
						if contentItem, ok := content[0].(map[string]interface{}); ok {
							if text, ok := contentItem["text"].(string); ok {
								// 寻找不以{开头且长度大于50的文本
								if !strings.HasPrefix(strings.TrimSpace(text), "{") && len(text) > 50 {
									return text
								}
							}
						}
					}
				}
			}

			// 策略2: 查找agentResult类型的消息，提取agentAnswer
			for _, msg := range messageList {
				if msgMap, ok := msg.(map[string]interface{}); ok {
					if content, ok := msgMap["content"].([]interface{}); ok && len(content) > 0 {
						if contentItem, ok := content[0].(map[string]interface{}); ok {
							if text, ok := contentItem["text"].(string); ok {
								if strings.Contains(text, "agentAnswer") {
									// 尝试解析JSON并提取agentAnswer
									var agentData map[string]interface{}
									if err := json.Unmarshal([]byte(text), &agentData); err == nil {
										if agentAnswer, ok := agentData["agentAnswer"].(string); ok && len(agentAnswer) > 10 {
											return agentAnswer
										}
									}
								}
							}
						}
					}
				}
			}

			// 策略3: 使用现有的默认逻辑，但跳过纯JSON消息
			for _, msg := range messageList {
				if msgMap, ok := msg.(map[string]interface{}); ok {
					if content, ok := msgMap["content"].([]interface{}); ok && len(content) > 0 {
						if contentItem, ok := content[0].(map[string]interface{}); ok {
							if text, ok := contentItem["text"].(string); ok {
								if !strings.HasPrefix(strings.TrimSpace(text), "{") && len(text) > 0 {
									return text
								}
							}
						}
					}
				}
			}
		}
	}
	return ""
}

// HandleUpdateModel 更新模型接口
func HandleUpdateModel(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")
	modelID := c.Param("modelId")

	log.Debugf("更新模型: trace_id=%s, username=%s, modelID=%s", traceID, username, modelID)

	// 1. 字段校验
	var req UpdateModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.Errorf("请求参数解析失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 2. 构建更新字段
	updates := make(map[string]interface{})

	if req.Model.Model != "" {
		updates["model_name"] = req.Model.Model
	}
	if req.Model.Token != "" {
		updates["token"] = req.Model.Token
	}
	if req.Model.BaseURL != "" {
		updates["base_url"] = req.Model.BaseURL
	}
	if req.Model.Limit > 0 {
		updates["limit"] = req.Model.Limit
	}
	updates["note"] = req.Model.Note

	if req.Model.ModelType != "" {
		updates["model_type"] = req.Model.ModelType
	}
	if req.Model.HTTPMethod != "" {
		updates["http_method"] = req.Model.HTTPMethod
	}
	if req.Model.HTTPEndpoint != "" {
		updates["http_endpoint"] = req.Model.HTTPEndpoint
	}
	updates["http_headers"] = req.Model.HTTPHeaders
	updates["http_request_body"] = req.Model.HTTPRequestBody
	updates["http_response_transform"] = req.Model.HTTPResponseTransform

	// 添加request_interval字段的更新
	updates["request_interval"] = req.Model.RequestInterval

	// 3. 保存更新
	err := mm.modelStore.UpdateModel(modelID, username, updates)
	if err != nil {
		log.Errorf("更新模型失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, modelID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "更新模型失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Debugf("更新模型成功: trace_id=%s, modelID=%s, username=%s", traceID, modelID, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "模型更新成功",
		"data":    nil,
	})
}

// HandleDeleteModel 删除模型接口
func HandleDeleteModel(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")

	log.Debugf("删除模型: trace_id=%s, username=%s", traceID, username)

	// 1. 字段校验
	var req DeleteModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.Errorf("请求参数解析失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	if len(req.ModelIDs) == 0 {
		log.Errorf("模型ID列表为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型ID列表不能为空",
			"data":    nil,
		})
		return
	}

	// 2. 删除模型
	_, err := mm.modelStore.BatchDeleteModels(req.ModelIDs, username)
	if err != nil {
		log.Errorf("删除模型失败: trace_id=%s, username=%s, modelIDs=%v, error=%v", traceID, username, req.ModelIDs, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "删除模型失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Debugf("删除模型成功: trace_id=%s, username=%s, modelIDs=%v", traceID, username, req.ModelIDs)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "模型删除成功",
		"data":    nil,
	})
}
