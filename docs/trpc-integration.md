# TRPC-Go 集成说明

## 概述

AI-Infra-Guard 项目已集成 TRPC-Go 生态，在保持现有 Gin 框架功能的基础上，复用了 TRPC-Go 的监控、全链路跟踪、日志等能力。

## 集成架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gin Router    │───▶│  TRPC Middleware │───▶│  TRPC Context   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HTTP Handler  │    │   Monitoring    │    │   Tracing       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 核心组件

### 1. TRPC 配置文件 (`trpc_go.yaml`)

```yaml
global:
  namespace: "AI-Infra-Guard"
  log:
    level: "info"
    format: "json"
    output: "stdout"
  container_name: "ai-infra-guard"

server:
  app: "ai-infra-guard"
  server: "webserver"
  service:
    - name: "ai-infra-guard.webserver"
      protocol: "http"
      address: "0.0.0.0:8088"
      timeout: 10000

plugins:
  log:
    default:
      level: "info"
      format: "json"
      output: "stdout"
  metrics:
    default:
      address: "127.0.0.1:8080"
      path: "/metrics"
  tracing:
    default:
      type: "jaeger"
      address: "127.0.0.1:6831"
```

### 2. TRPC 中间件 (`common/middleware/trpc.go`)

```go
func TrpcMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // 创建新的trpc message，用于监控、全链路跟踪等场景
        ctx, msg := codec.WithNewMessage(savedCtx)
        
        // 设置trpc message信息
        msg.WithCalleeApp(trpc.GlobalConfig().Server.App)
        msg.WithCalleeServer(trpc.GlobalConfig().Server.Server)
        msg.WithCalleeMethod(":" + c.FullPath())
        
        // 通过request context传递span、trpc信息
        c.Request = c.Request.WithContext(ctx)
        
        c.Next()
    }
}
```

### 3. TRPC 初始化模块 (`common/trpc/init.go`)

```go
func InitTrpc(configPath string) error {
    // 设置日志
    log.SetLogger(log.NewZapLog())
    
    // 加载全局配置
    err := trpc.LoadGlobalConfig(configPath)
    if err != nil {
        return err
    }
    
    // 创建trpc server（这会加载插件、启动admin等）
    _ = trpc.NewServer()
    
    return nil
}
```

## 使用方法

### 1. 启动服务

```bash
# 编译项目
go build -o ai-infra-guard ./cmd/cli

# 启动webserver模式
./ai-infra-guard webserver --ws-addr 0.0.0.0:8088
```

### 2. 访问监控

- **Metrics**: http://127.0.0.1:8080/metrics
- **Jaeger Tracing**: http://127.0.0.1:16686
- **Web UI**: http://127.0.0.1:8088

### 3. 日志查看

服务启动后，会看到类似以下的日志：

```
{"level":"info","msg":"Initializing trpc-go...","time":"2024-01-01T12:00:00Z"}
{"level":"info","msg":"Trpc-go initialized successfully","time":"2024-01-01T12:00:00Z"}
{"level":"info","msg":"Starting WebServer on http://0.0.0.0:8088","time":"2024-01-01T12:00:00Z"}
```

## 功能特性

### 1. 统一日志
- 使用 TRPC-Go 的日志插件
- 支持结构化日志输出
- 可配置日志级别和格式

### 2. 监控指标
- 自动收集 HTTP 请求指标
- 支持 Prometheus 格式的 metrics
- 可集成到监控系统

### 3. 全链路跟踪
- 自动生成 trace span
- 支持 Jaeger 等分布式追踪系统
- 可追踪请求链路

### 4. 插件生态
- 可复用 TRPC-Go 的所有插件
- 支持 IOA、限流、熔断等插件
- 易于扩展新功能

## 配置说明

### 日志配置

```yaml
global:
  log:
    level: "info"      # debug, info, warn, error
    format: "json"     # json, console
    output: "stdout"   # stdout, stderr, 文件路径
```

### 监控配置

```yaml
plugins:
  metrics:
    default:
      address: "127.0.0.1:8080"
      path: "/metrics"
```

### 追踪配置

```yaml
plugins:
  tracing:
    default:
      type: "jaeger"
      address: "127.0.0.1:6831"
```

## 扩展开发

### 1. 添加新的 TRPC 插件

```go
import (
    _ "git.code.oa.com/trpc-go/trpc-filter/ioa"
    _ "git.code.oa.com/trpc-go/trpc-filter/ratelimit"
)
```

### 2. 自定义中间件

```go
func CustomTrpcMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // 在 TRPC 中间件基础上添加自定义逻辑
        middleware.TrpcMiddleware()(c)
        
        // 自定义逻辑
        c.Next()
    }
}
```

### 3. 使用 TRPC 日志

```go
import "git.code.oa.com/trpc-go/trpc-go/log"

func someHandler(c *gin.Context) {
    log.WithFields(log.Fields{
        "user_id": c.GetString("user_id"),
        "action":  "scan",
    }).Info("User started scan")
}
```

## 注意事项

1. **配置文件路径**: 确保 `trpc_go.yaml` 文件在项目根目录
2. **依赖管理**: 需要配置内部模块的 GOPROXY
3. **端口冲突**: 注意监控端口 (8080) 不要与其他服务冲突
4. **权限要求**: 某些插件可能需要特殊权限

## 故障排除

### 1. TRPC 初始化失败

```bash
# 检查配置文件
cat trpc_go.yaml

# 检查日志
tail -f logs/app.log
```

### 2. 监控端口无法访问

```bash
# 检查端口是否被占用
netstat -tlnp | grep 8080

# 检查防火墙设置
firewall-cmd --list-ports
```

### 3. 日志不输出

```yaml
# 检查日志配置
global:
  log:
    level: "debug"  # 临时设置为 debug 级别
    output: "stdout"
``` 