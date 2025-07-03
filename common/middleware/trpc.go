package middleware

import (
	"time"

	"git.code.oa.com/trpc-go/trpc-go"
	"git.code.oa.com/trpc-go/trpc-go/codec"
	"git.code.oa.com/trpc-go/trpc-go/log"
	_ "git.code.oa.com/trpc-go/trpc-log-zhiyan"
	"github.com/Tencent/AI-Infra-Guard/common/monitoring"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// TrpcMiddleware 创建trpc-go集成中间件
func TrpcMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 生成trace_id
		traceID := uuid.New().String()

		// 将trace_id放入gin context
		c.Set("trace_id", traceID)

		// 保存原始context
		savedCtx := c.Request.Context()

		// 创建新的trpc message，用于监控、全链路跟踪等场景
		ctx, msg := codec.WithNewMessage(savedCtx)

		// 设置trpc message信息
		msg.WithCalleeApp(trpc.GlobalConfig().Server.App)
		msg.WithCalleeServer(trpc.GlobalConfig().Server.Server)
		msg.WithCalleeService("")
		msg.WithCalleeServiceName("")
		msg.WithCalleeMethod(":" + c.FullPath())
		msg.WithCalleeContainerName(trpc.GlobalConfig().Global.ContainerName)

		// 通过request context传递span、trpc信息
		c.Request = c.Request.WithContext(ctx)

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

		// 上报HTTP监控数据到智研
		func() {
			defer func() {
				if r := recover(); r != nil {
					log.Errorf("监控函数panic: trace_id=%s, error=%+v", traceID, r)
				}
			}()

			monitoring.ReportHTTPMetrics(monitoring.HTTPMetrics{
				Path:       c.FullPath(),
				Method:     c.Request.Method,
				StatusCode: c.Writer.Status(),
				Duration:   duration,
				ClientIP:   clientIP,
			})
		}()
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
