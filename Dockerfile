# 多阶段构建Dockerfile
# 第一阶段：构建阶段
FROM golang:1.23.2-alpine AS builder

# 设置工作目录
WORKDIR /ai-infra-guard

# 安装必要的构建工具
RUN apk add --no-cache git ca-certificates tzdata gcc musl-dev

# 配置Go代理（使用用户实际的配置）
ENV GOPROXY=https://lakeicehu:WVmubU5W@goproxy.woa.com,direct
ENV GOSUMDB=sum.woa.com+643d7a06+Ac5f5VOC4N8NUXdmhbm8pZSXIWfhek5JSmWdWrq7pLX4
ENV CGO_ENABLED=1

# 复制源代码（包含go.mod和go.sum）
COPY . .

# 下载依赖
RUN go mod download

# 构建应用
RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -a -installsuffix cgo -o ai-infra-guard ./cmd/cli/main.go

# 第二阶段：运行阶段
FROM alpine:latest

# 安装运行时依赖
RUN apk --no-cache add ca-certificates tzdata sqlite bash

# 创建非root用户
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# 设置工作目录
WORKDIR /ai-infra-guard

# 从构建阶段复制二进制文件和配置文件
COPY --from=builder /ai-infra-guard/ai-infra-guard .
COPY --from=builder /ai-infra-guard/trpc_go.yaml .

# 创建必要的目录并设置权限
RUN mkdir -p /ai-infra-guard/uploads /ai-infra-guard/db /ai-infra-guard/logs /ai-infra-guard/polaris/log && \
    chown -R appuser:appgroup /ai-infra-guard && \
    chmod -R 755 /ai-infra-guard

# 设置环境变量
ENV APP_ENV=production
ENV UPLOAD_DIR=/ai-infra-guard/uploads
ENV DB_PATH=/ai-infra-guard/db/tasks.db
ENV LOG_DIR=/ai-infra-guard/logs

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8088

# 声明卷挂载点
VOLUME ["/ai-infra-guard/uploads", "/ai-infra-guard/db", "/ai-infra-guard/logs", "/ai-infra-guard/polaris/log"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8088/health || exit 1

# 启动命令
CMD ["./ai-infra-guard", "webserver", "--ws-addr", "0.0.0.0:8088"] 