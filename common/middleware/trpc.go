package middleware

import (
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"trpc.group/trpc-go/trpc-go/log"
)

// TrpcMiddleware 创建trpc-go集成中间件
func TrpcMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 生成trace_id
		traceID := uuid.New().String()

		// 将trace_id放入gin context
		c.Set("trace_id", traceID)

		// 记录请求开始时间
		startTime := time.Now()

		// 记录请求开始日志
		log.Infof("请求开始: trace_id=%s, method=%s, path=%s, client_ip=%s",
			traceID, c.Request.Method, c.FullPath(), getClientIP(c))

		// 继续处理请求
		c.Next()

		// 计算请求耗时
		duration := time.Since(startTime)

		// 记录请求结束日志
		log.Infof("请求结束: trace_id=%s, method=%s, path=%s, status=%d, duration=%v",
			traceID, c.Request.Method, c.FullPath(), c.Writer.Status(), duration)

		// 获取客户端IP
		clientIP := getClientIP(c)

		// 监控相关代码已移除
		_ = clientIP // 避免未使用变量警告
	}
}

// getClientIP 获取客户端真实IP
func getClientIP(c *gin.Context) string {
	// 优先从X-Real-IP获取
	if ip := c.GetHeader("X-Real-IP"); ip != "" {
		return ip
	}

	// 其次从X-Forwarded-For获取
	if ip := c.GetHeader("X-Forwarded-For"); ip != "" {
		return ip
	}

	// 最后从RemoteAddr获取
	return c.ClientIP()
}
