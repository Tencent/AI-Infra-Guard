# AGENTS.md

## 项目定位
AI-Infra-Guard 是一个混合技术栈的 AI 安全扫描平台，核心由以下部分组成：

- Go 主应用（Web 服务、CLI、任务管理、规则引擎）
- Python 子模块（`mcp-scan`、`agent-scan`、`AIG-PromptSecurity`）
- 规则与知识库数据（`data/fingerprints`、`data/vuln`、`data/vuln_en`、`data/mcp`、`data/eval`）
- Docker 部署编排（`docker-compose.yml`、`docker-compose.images.yml`）

## 目录速览
- `cmd/cli`：Go CLI 入口（`scan`、`webserver`）
- `common/websocket`：Web/API 服务与任务接口
- `internal/mcp`：MCP 扫描与插件机制
- `pkg/`：数据库、HTTP、漏洞结构等基础库
- `cmd/agent`：Agent 进程入口（通过 WebSocket 接入主服务）
- `agent-scan/`：Agent 工作流扫描框架（Python）
- `mcp-scan/`：MCP 代码/动态扫描框架（Python）
- `AIG-PromptSecurity/`：提示词安全评测组件（Python）

## 本地开发常用命令

### Go 服务
```bash
# 构建主程序
go build -o ai-infra-guard ./cmd/cli/main.go

# 启动 Web 服务
./ai-infra-guard webserver --server 127.0.0.1:8088

# 或执行基础扫描
./ai-infra-guard scan -t http://127.0.0.1:8088
```

### Agent 进程
```bash
go build -o agent ./cmd/agent
AIG_SERVER=127.0.0.1:8088 ./agent
```

### Docker 启动
```bash
# 使用预构建镜像
docker-compose -f docker-compose.images.yml up -d

# 使用本地源码构建镜像
docker-compose up -d
```

### Python 子模块
```bash
# MCP 扫描
pip install -r mcp-scan/requirements.txt
python mcp-scan/main.py --repo /path/to/project

# Agent 扫描
pip install -r agent-scan/requirements.txt
python agent-scan/main.py --repo /path/to/project --agent_provider /path/to/provider.yaml

# Prompt Security
pip install -r AIG-PromptSecurity/requirements.txt
```

## 测试与校验要求

### 必做校验（按改动范围执行）
```bash
# Go 单测
go test ./...

# YAML 规则格式校验（与 CI 保持一致）
go build -o yamlcheck ./cmd/yamlcheck
./yamlcheck data/fingerprints data/vuln data/vuln_en
```

### 说明
- 修改 `data/` 下规则时，必须通过 `yamlcheck`。
- 修改 API/任务结构时，需同步检查 `api.md`、`api_zh.md` 与 `docs/swagger.yaml`。
- 修改 Python 子模块时，至少完成对应入口脚本的冒烟运行。

## 代码与提交流程约定
- 优先做最小必要改动，避免无关重构。
- 保持现有中英双语风格（注释/文档按周边文件风格保持一致）。
- 不要提交敏感信息（API Key、Token、真实地址、日志隐私数据）。
- 不要删除或覆盖现有规则库文件，除非任务明确要求。
- 新增规则文件时，遵循现有目录与命名习惯。

## 安全注意事项（项目特性）
- 当前 Web 平台默认不含完整鉴权机制，不应直接暴露公网。
- `webserver` 监听非 `127.0.0.1` 地址会带来额外风险，需明确隔离环境。
- 涉及扫描目标、附件上传、模型配置时，注意日志中不要泄露密钥。

## CI/CD 关联约束
- `.github/workflows/yaml-lint.yml` 会对 `data/**` 变更执行 YAML 校验。
- 镜像发布由 `.github/workflows/docker-publish.yml` 管理。
- Release 打包由 `.github/workflows/create-release.yml` 管理。

修改构建、发布、数据结构相关逻辑时，请先确认不会破坏以上流程。
