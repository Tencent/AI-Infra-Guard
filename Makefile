# AI-Infra-Guard Makefile
# 项目变量
PROJECT_NAME = aig
MODULE_NAME = github.com/Tencent/AI-Infra-Guard
GO_VERSION = 1.23.2

# 构建变量
GOOS = linux
GOARCH = amd64
CGO_ENABLED = 1

# Docker 变量
DOCKER_REGISTRY ?= mirrors.tencent.com/aig
IMAGE_TAG ?= latest
WEBSERVER_IMAGE = $(DOCKER_REGISTRY)/$(PROJECT_NAME)-webserver:$(IMAGE_TAG)
AGENT_IMAGE = $(DOCKER_REGISTRY)/$(PROJECT_NAME)-agent:$(IMAGE_TAG)

# 二进制文件
AGENT_BINARY = agent
SERVER_BINARY = server

# 目录变量
BUILD_DIR = build
DIST_DIR = dist

.PHONY: help all clean build build-linux build-docker

# 默认目标
all: clean build

help: ## 显示帮助信息
	@echo "可用的 make 目标："
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# 构建相关
# =============================================================================

build: ## 本地构建二进制文件
	@echo "构建本地二进制文件..."
	go build -o $(AGENT_BINARY) cmd/agent/main.go
	go build -o $(SERVER_BINARY) cmd/cli/main.go

build-linux: ## 构建 Linux 二进制文件
	@echo "构建 Linux 二进制文件..."
	@mkdir -p $(BUILD_DIR)
	GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(BUILD_DIR)/$(AGENT_BINARY) cmd/agent/main.go
	GOOS=$(GOOS) GOARCH=$(GOARCH) go build -o $(BUILD_DIR)/$(SERVER_BINARY) cmd/cli/main.go
	@echo "Linux 二进制文件构建完成: $(BUILD_DIR)/"

build-docker: ## 构建 Docker 镜像
	@echo "构建 Docker 镜像..."
	docker build -t $(WEBSERVER_IMAGE) -f Dockerfile .
	docker build -t $(AGENT_IMAGE) -f Dockerfile_Agent .
	@echo "Docker 镜像构建完成"
	@echo "Webserver: $(WEBSERVER_IMAGE)"
	@echo "Agent: $(AGENT_IMAGE)"

build-docker-local: ## 构建本地 Docker 镜像（不带registry前缀）
	@echo "构建本地 Docker 镜像..."
	docker build -t $(PROJECT_NAME)-webserver:$(IMAGE_TAG) -f Dockerfile .
	docker build -t $(PROJECT_NAME)-agent:$(IMAGE_TAG) -f Dockerfile_Agent .

# =============================================================================
# Docker 推送相关
# =============================================================================

push: build-docker ## 构建并推送 Docker 镜像到仓库
	@echo "推送 Docker 镜像到仓库..."
	docker push $(WEBSERVER_IMAGE)
	docker push $(AGENT_IMAGE)
	@echo "镜像推送完成"

clean: ## 清理构建文件
	@echo "清理构建文件..."
	rm -rf $(BUILD_DIR)
	rm -rf $(DIST_DIR)
	rm -f $(AGENT_BINARY) $(SERVER_BINARY)
	rm -f coverage.out coverage.html
	@echo "清理完成"

clean-docker: ## 清理 Docker 镜像
	@echo "清理 Docker 镜像..."
	-docker rmi $(WEBSERVER_IMAGE) 2>/dev/null || true
	-docker rmi $(AGENT_IMAGE) 2>/dev/null || true
	-docker rmi $(PROJECT_NAME)-webserver:$(IMAGE_TAG) 2>/dev/null || true
	-docker rmi $(PROJECT_NAME)-agent:$(IMAGE_TAG) 2>/dev/null || true
	@echo "Docker 镜像清理完成"