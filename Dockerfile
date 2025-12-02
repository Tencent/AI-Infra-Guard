# 多阶段构建Dockerfile
# 第一阶段：构建阶段
FROM golang:1.23.2-alpine AS builder

# 设置工作目录
WORKDIR /app

# 安装必要的构建工具
RUN apk add --no-cache git ca-certificates tzdata gcc musl-dev

# 复制源代码（包含go.mod和go.sum）
COPY . .

# 下载依赖
RUN go mod download

# 构建应用
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o ai-infra-guard ./cmd/cli/main.go

# 第二阶段：运行阶段
FROM alpine:3.19

# 安装运行时依赖
RUN apk --no-cache add ca-certificates tzdata sqlite bash curl

# 设置工作目录
WORKDIR /app

# 从构建阶段复制二进制文件和配置文件
COPY --from=builder /app/ai-infra-guard .
COPY --from=builder /app/trpc_go.yaml .

# 复制数据文件到容器中
COPY --from=builder /app/data ./data

# 复制启动脚本到镜像中
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh && chown root:root /app/start.sh

# 创建必要的目录并设置权限（仅对镜像内有效）
RUN mkdir -p /app/uploads \
    /app/db && \
    chown -R root:root /app && \
    chmod -R 755 /app && \
    mkdir -p /app/AIG-PromptSecurity/utils \

COPY ./AIG-PromptSecurity/utils/strategy_map.json /app/AIG-PromptSecurity/utils/strategy_map.json

# 设置环境变量
ENV APP_ENV=production
ENV UPLOAD_DIR=/app/uploads
ENV DB_PATH=/app/db/tasks.db
ENV TZ=Asia/Shanghai

# 暴露端口
EXPOSE 8088

# 声明卷挂载点
VOLUME ["/app/uploads", "/app/db", "/app/data", "/app/logs"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD pgrep ai-infra-guard || exit 1

# 启动命令
CMD ["/app/start.sh"] 