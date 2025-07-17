package middleware

import (
	"bytes"
	"encoding/json"
	"io"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"trpc.group/trpc-go/trpc-go/log"
)

// RequestLoggerMiddleware 请求参数日志中间件
func RequestLoggerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()

		// 获取trace_id（如果存在）
		traceID := c.GetString("trace_id")
		if traceID == "" {
			traceID = "unknown"
		}

		// 获取用户信息
		username := c.GetString("username")
		if username == "" {
			username = "unknown"
		}

		// 记录请求基本信息
		requestInfo := map[string]interface{}{
			"method":     c.Request.Method,
			"path":       c.Request.URL.Path,
			"query":      c.Request.URL.RawQuery,
			"client_ip":  c.ClientIP(),
			"user_agent": c.Request.UserAgent(),
			"username":   username,
		}

		// 记录请求头（过滤敏感信息）
		headers := make(map[string]string)
		for key, values := range c.Request.Header {
			// 过滤敏感头信息
			if !isSensitiveHeader(key) {
				headers[key] = strings.Join(values, ", ")
			}
		}
		requestInfo["headers"] = headers

		// 记录路径参数
		if len(c.Params) > 0 {
			pathParams := make(map[string]string)
			for _, param := range c.Params {
				pathParams[param.Key] = param.Value
			}
			requestInfo["path_params"] = pathParams
		}

		// 记录查询参数
		if len(c.Request.URL.Query()) > 0 {
			requestInfo["query_params"] = c.Request.URL.Query()
		}

		// 记录请求体（仅对POST/PUT等方法）
		if shouldLogRequestBody(c.Request.Method) {
			body, err := readRequestBody(c)
			if err != nil {
				log.Warnf("读取请求体失败: trace_id=%s, error=%v", traceID, err)
			} else if body != "" {
				// 尝试解析为JSON以便格式化显示
				var jsonBody interface{}
				if json.Unmarshal([]byte(body), &jsonBody) == nil {
					requestInfo["request_body"] = jsonBody
				} else {
					// 如果不是JSON，直接记录字符串（截断过长内容）
					if len(body) > 1000 {
						requestInfo["request_body"] = body[:1000] + "...(truncated)"
					} else {
						requestInfo["request_body"] = body
					}
				}
			}
		}

		// 序列化请求信息
		requestJSON, _ := json.Marshal(requestInfo)

		log.Infof("请求接收: trace_id=%s, request_info=%s", traceID, string(requestJSON))

		// 继续处理请求
		c.Next()

		// 记录响应信息
		duration := time.Since(start)
		status := c.Writer.Status()

		log.Infof("请求完成: trace_id=%s, status=%d, duration=%v", traceID, status, duration)
	}
}

// 读取请求体内容
func readRequestBody(c *gin.Context) (string, error) {
	if c.Request.Body == nil {
		return "", nil
	}

	// 读取请求体
	bodyBytes, err := io.ReadAll(c.Request.Body)
	if err != nil {
		return "", err
	}

	// 重新设置请求体，以便后续处理可以再次读取
	c.Request.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

	return string(bodyBytes), nil
}

// 判断是否应该记录请求体
func shouldLogRequestBody(method string) bool {
	return method == "POST" || method == "PUT" || method == "PATCH"
}

// 判断是否为敏感头信息
func isSensitiveHeader(headerKey string) bool {
	sensitiveHeaders := []string{
		"authorization",
		"cookie",
		"x-api-key",
		"x-auth-token",
		"password",
		"token",
	}

	headerKeyLower := strings.ToLower(headerKey)
	for _, sensitive := range sensitiveHeaders {
		if strings.Contains(headerKeyLower, sensitive) {
			return true
		}
	}
	return false
}
