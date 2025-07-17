# 第一阶段：构建阶段
FROM golang:1.23.2-alpine AS builder

# 安装必要的系统依赖
RUN apk add --no-cache git ca-certificates

# 设置工作目录
WORKDIR /app

# 复制 go.mod 和 go.sum 文件
COPY go.mod go.sum /app/

# 下载依赖
RUN go mod download

# 复制源代码
COPY . /app/

# 构建应用程序
RUN GOOS=linux go build -a -o agent ./cmd/agent

# AIG-PromptSecurity
FROM python:3.12-slim

WORKDIR /app/AIG-PromptSecurity

RUN apt-get update --allow-releaseinfo-change && apt-get install -y --no-install-recommends --allow-unauthenticated git curl \
    && rm -rf /var/lib/apt/lists/* \
    && (command -v uv >/dev/null 2>&1 || pip install --no-cache-dir uv)

COPY ./AIG-PromptSecurity /app/AIG-PromptSecurity/
WORKDIR /app/AIG-PromptSecurity
RUN uv pip install --system -r requirements.txt

# 从builder阶段复制agent
COPY --from=builder /app/agent /app/agent
COPY --from=builder /app/data /app/data

ENTRYPOINT ["/app/agent"]