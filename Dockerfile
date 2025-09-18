# 多阶段构建Dockerfile
# 第一阶段：构建阶段
FROM golang:1.23.2-alpine AS builder

# 设置工作目录
WORKDIR /ai-infra-guard

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
WORKDIR /ai-infra-guard

# 从构建阶段复制二进制文件和配置文件
COPY --from=builder /ai-infra-guard/ai-infra-guard .
COPY --from=builder /ai-infra-guard/trpc_go.yaml .

# 复制数据文件到容器中
COPY --from=builder /ai-infra-guard/data ./data

# 复制启动脚本到镜像中
COPY start.sh /ai-infra-guard/start.sh
RUN chmod +x /ai-infra-guard/start.sh && chown root:root /ai-infra-guard/start.sh

# 创建必要的目录并设置权限（仅对镜像内有效）
RUN mkdir -p /ai-infra-guard/uploads \
    /ai-infra-guard/db && \
    chown -R root:root /ai-infra-guard && \
    chmod -R 755 /ai-infra-guard

# 设置环境变量
ENV APP_ENV=production
ENV UPLOAD_DIR=/ai-infra-guard/uploads
ENV DB_PATH=/ai-infra-guard/db/tasks.db
ENV TZ=Asia/Shanghai

# 暴露端口
EXPOSE 8088

# 声明卷挂载点
VOLUME ["/ai-infra-guard/uploads", "/ai-infra-guard/db", "/ai-infra-guard/data", "/ai-infra-guard/logs"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD pgrep ai-infra-guard || exit 1

# 启动命令
CMD ["/ai-infra-guard/start.sh"] 