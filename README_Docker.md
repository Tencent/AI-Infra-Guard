AI-Infra-Guard Docker 部署指南

概述

AI-Infra-Guard 是一个基于 Docker 的 AI 基础设施安全扫描工具。本指南将帮助您快速部署和运行该服务。

系统要求

- Docker 20.10 或更高版本
- 至少 2GB 可用内存
- 至少 1GB 可用磁盘空间

快速开始

1. 构建镜像

```bash
# 克隆项目
git clone <repository-url>
cd AI-Infra-Guard

# 构建 Docker 镜像
docker build -t ai-infra-guard:latest .
```

2. 创建必要的目录

```bash
# 创建数据目录
mkdir -p ./uploads ./db ./data ./logs

### 3. 运行容器

#### 方式一：后台运行

```bash
##权限不够加sudo
docker run -d \
  --name ai-infra-guard \
  -p 8088:8088 \
  -v $(pwd)/uploads:/ai-infra-guard/uploads \
  -v $(pwd)/db:/ai-infra-guard/db \
  -v $(pwd)/data:/ai-infra-guard/data \
  -v $(pwd)/logs:/ai-infra-guard/logs \
  ai-infra-guard:latest
```

#### 方式二：前台运行（查看实时日志）

```bash
##权限不够加sudo
docker run --rm -it \
  --name ai-infra-guard \
  -p 8088:8088 \
  -v $(pwd)/uploads:/ai-infra-guard/uploads \
  -v $(pwd)/db:/ai-infra-guard/db \
  -v $(pwd)/data:/ai-infra-guard/data \
  -v $(pwd)/logs:/ai-infra-guard/logs \
  ai-infra-guard:latest
```

**注意**：日志文件现在存储在 `./logs/trpc.log` 目录中，支持持久化。


目录说明

| 目录/文件 | 说明 | 挂载路径 |
|-----------|------|----------|
| `uploads/` | 上传文件存储目录 | `/ai-infra-guard/uploads` |
| `db/` | 数据库文件目录 | `/ai-infra-guard/db` |
| `data/` | 知识库数据目录（指纹库、漏洞库） | `/ai-infra-guard/data` |
| `logs/` | 应用日志目录 | `/ai-infra-guard/logs` |

访问服务

服务启动后，您可以通过以下方式访问：

- **Web 界面**: http://localhost:8088
- **API 接口**: http://localhost:8088/api/

常用操作

查看容器状态

```bash
# 查看运行中的容器
docker ps

# 查看容器日志
docker logs ai-infra-guard

# 查看容器健康状态
docker inspect ai-infra-guard | grep Health -A 10
```

停止和重启

```bash
# 停止容器
docker stop ai-infra-guard

# 启动容器
docker start ai-infra-guard

# 重启容器
docker restart ai-infra-guard
```

进入容器

```bash
# 进入运行中的容器
docker exec -it ai-infra-guard /bin/bash
```

查看日志

```bash
# 查看容器日志
docker logs -f ai-infra-guard

# 查看本地日志文件
tail -f ./logs/trpc.log
```

数据持久化

所有重要数据都会持久化到宿主机：

- **数据库**: `./db/tasks.db` - 任务和配置数据
- **上传文件**: `./uploads/` - 用户上传的文件
- **知识库**: `./data/` - 指纹库和漏洞库数据
- **应用日志**: `./trpc.log` - 应用运行日志