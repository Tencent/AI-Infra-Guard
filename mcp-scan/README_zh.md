# MCP-Scan

**[English](./README.md)** | 中文

一个基于 AI Agent 的自动化 MCP Server 安全扫描和漏洞检测工具，由腾讯朱雀实验室开发。

## ✨ 特性

- **🤖 智能 Agent 系统**: 支持单阶段（快速代码审计）和三阶段（信息收集 → 代码审计 → 漏洞整理）两种扫描模式
- **🔍 深度代码分析**: 自动识别项目结构、技术栈和潜在安全漏洞
- **📊 SARIF 2.1.0 输出**: CLI 模式默认输出 SARIF 2.1.0 JSON，可被 GitHub Code Scanning、Azure DevOps、VS Code 等原生消费
- **🔌 AIG 平台集成**: 通过 Web 界面进行交互式扫描，三阶段流水线结果实时展示
- **🎯 专用模型配置**: 支持为不同任务配置专用 LLM（思考、编码、快速响应等）
- **📊 安全评分系统**: 自动计算项目安全评分和风险等级
- **🛠️ 可扩展工具系统**: 轻松添加自定义工具和功能
- **📝 详细日志记录**: 使用 loguru 记录完整的执行过程
- **🐛 Debug 模式**: 集成 Laminar 追踪功能，方便调试
- **🕵️ Agent Skill 审计**: 自动识别并审计 Agent Skill 项目的一致性（SKILL.md vs 代码实现）
- **⚡ 静态预扫描**: Agent 启动前用正则快速扫描高危模式（curl|bash、云元数据、凭据窃取等），生成提示注入上下文

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo>
cd mcp-scan
```

### 2. 安装依赖

推荐使用 `uv`（速度更快，自动管理虚拟环境）：

```bash
uv sync
```

或使用 pip：

```bash
pip install -r requirements.txt
```

### 3. 运行扫描

mcp-scan 支持两种使用方式：

#### 方式一：CLI 独立使用（默认单阶段模式）

默认输出 SARIF 2.1.0 JSON 到 stdout，适合 CI/CD 集成和快速扫描：

```bash
# 基础扫描
python main.py --repo ./myproject

# 保存结果到文件
python main.py --repo ./myproject -o result.sarif.json

# 使用特定模型
python main.py --repo ./myproject -m "anthropic/claude-3.5-sonnet"

# 使用环境变量提供 API Key（无需 --api_key）
export LLM_API_KEY="sk-or-v1-xxxxx"
python main.py --repo ./myproject

# 使用自定义提示词
python main.py --repo ./myproject --prompt "重点检查 SQL 注入漏洞"

# 启用 debug 模式
python main.py --repo ./myproject --debug

# 组合使用
python main.py --repo ./myproject \
  -m "google/gemini-2.5-pro" \
  -p "重点检查认证和授权相关的安全问题" \
  --debug \
  -o report.sarif.json

# 动态分析（针对运行中的 MCP Server）
python main.py \
  --server_url "http://localhost:8000/sse" \
  --prompt "测试工具投毒漏洞"
```

> **CLI 模式特点**：默认使用**单阶段扫描**（仅代码审计，速度约为三阶段的 3 倍），输出 **SARIF 2.1.0** JSON 格式，可被 GitHub Code Scanning、Azure DevOps、GitLab Security Dashboard、VS Code Problems 面板等 SARIF-aware 工具原生消费。

#### 方式二：AIG 平台 Web 界面（三阶段模式）

mcp-scan 已集成到 AIG 平台，可以通过 Web 界面进行交互式扫描，三阶段流水线的结果会实时展示在前端。

**使用步骤：**

1. **启动 AIG Web 服务和 Agent 进程**

```bash
# 启动 Web 服务
go build -o ai-infra-guard ./cmd/cli/main.go
./ai-infra-guard webserver --server 127.0.0.1:8088

# 另开终端，启动 Agent 进程
go build -o agent ./cmd/agent
AIG_SERVER=127.0.0.1:8088 ./agent
```

2. **通过浏览器使用**

打开浏览器访问 `http://127.0.0.1:8088`，操作流程：

- 左侧菜单选择 **MCP 扫描**
- 在**模型配置**中添加 LLM API Key 和模型名称（如 `deepseek-v4-flash`）
- 选择输入方式：上传源码压缩包（.zip）或输入 GitHub 仓库地址
- 点击**开始扫描**

3. **查看结果**

扫描过程中，三阶段流水线（信息收集 → 代码审计 → 漏洞整理）的进度和结果会实时展示在 Web 前端，最终生成包含漏洞详情、风险等级和安全评分的完整报告。

> **工作原理**：用户在 Web 界面提交扫描任务后，Go 后端将任务分发给 Agent 进程，Agent 自动以 `--aig-mode` 调用 mcp-scan，扫描过程中的结构化 JSON 日志通过 `mcpLogger` 输出到 stdout，Go 后端解析后实时推送到前端展示。用户无需手动执行 `--aig-mode` 命令。

## 📖 命令行参数参考

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--repo` | - | 静态扫描时**必需**。要扫描的项目路径（使用 `--server_url` 动态分析时可省略） | - |
| `--prompt` | `-p` | 自定义扫描提示词 | "" |
| `--model` | `-m` | LLM 模型名称 | `deepseek/deepseek-v3.2-exp` |
| `--api_key` | `-k` | API Key（回退到环境变量 `LLM_API_KEY`/`OPENAI_API_KEY`/`OPENROUTER_API_KEY`） | 从环境变量读取 |
| `--base_url` | `-u` | API 基础 URL | `https://openrouter.ai/api/v1` |
| `--debug` | - | 启用 debug 模式（包括 Laminar 跟踪） | `False` |
| `--server_url` | - | 远程 MCP server URL（启用动态分析模式） | `None` |
| `--header` | - | 自定义 HTTP header (key:value)，可多次使用 | `[]` |
| `--language` | - | 输出语言 (zh/en) | `zh` |
| `--aig-mode` | - | 启用 AIG 集成模式：输出结构化 JSON 日志供 Go 后端解析。由 AIG 平台自动调用，CLI 独立使用时无需启用 | `False` |
| `--output` | `-o` | 将扫描结果保存为 JSON 文件 | `None` |

> **配置优先级**（从高到低）：命令行参数 > 环境变量 > 代码默认值

## 📊 SARIF 输出格式

CLI 模式默认输出 **SARIF 2.1.0** JSON，包含以下关键信息：

- **rules**: 静态声明完整的 MCP01-MCP10 + 3 个补充分类规则（名称混淆、拉地毯、工具阴影），即使本次扫描未发现也总是输出
- **results**: 每条漏洞映射到对应规则 ID，包含 `level`（error/warning/note）、`locations`（文件+行号）、`partialFingerprints`（去重哈希）、`fixes`（修复建议）
- **properties**: 安全评分、主语言、使用的 LLM、扫描时间

SARIF 文件可直接上传到 GitHub Code Scanning：

```bash
# GitHub Actions 示例
python main.py --repo ./myproject -o results.sarif.json
# 然后在 workflow 中使用 github/codeql-action/upload-sarif@v3 上传
```

### MCP 风险分类体系

mcp-scan 使用 MCP 特有的 10 类安全风险分类，另加 3 个补充分类：

| 规则 ID | 名称 | 说明 |
|---------|------|------|
| MCP01 | 令牌管理与密钥暴露 | 凭据窃取与密钥泄露 |
| MCP02 | 权限提升与范围蔓延 | 工具权限定义过宽 |
| MCP03 | 工具投毒攻击 | 合法工具被注入恶意逻辑 |
| MCP04 | 软件供应链攻击 | 依赖库篡改、恶意第三方服务器 |
| MCP05 | 命令注入与执行 | 不可信输入构造系统命令 |
| MCP06 | 提示注入攻击 | 上下文注入恶意指令劫持模型 |
| MCP07 | 认证与授权不足 | 身份校验缺失导致越权 |
| MCP08 | 审计与遥测缺失 | 缺乏不可篡改的调用日志 |
| MCP09 | 影子 MCP 服务器 | 未经授权部署的 MCP 实例 |
| MCP10 | 上下文注入与过度分享 | 敏感上下文跨会话泄露 |
| Name Confusion | 名称混淆攻击 | 相似名称诱导错误调用 |
| Rug Pull Attack | 拉地毯攻击 | 获取信任后突然变更行为 |
| Tool Shadowing Attack | 工具阴影攻击 | 重定义同名工具覆盖合法行为 |

## ⚙️ 配置说明

创建 `.env` 文件或在系统中设置环境变量。程序启动时自动加载 `.env`，也识别系统环境变量。

#### 主要 LLM 配置

```bash
# OpenRouter API Key（必需）
OPENROUTER_API_KEY=your-api-key-here

# 默认模型
DEFAULT_MODEL=deepseek/deepseek-v3.2-exp

# API 基础 URL
DEFAULT_BASE_URL=https://openrouter.ai/api/v1
```

#### 专用 LLM 配置

为不同任务配置专用模型，每个模型可以有独立的 API Key 和 Base URL：

```bash
# Thinking 模型（用于深度推理）
THINKING_MODEL=google/gemini-2.5-pro
THINKING_BASE_URL=https://openrouter.ai/api/v1
THINKING_API_KEY=  # 可选，不设置则使用主 API Key

# Coding 模型（用于代码生成和分析）
CODING_MODEL=anthropic/claude-sonnet-4.5
CODING_BASE_URL=https://openrouter.ai/api/v1
CODING_API_KEY=  # 可选，不设置则使用主 API Key
```

#### Debug 和日志配置

```bash
# Laminar API Key（用于 debug 模式的追踪）
LAMINAR_API_KEY=your-laminar-api-key

# 日志级别
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## 📁 项目结构

```
mcp-scan/
├── mcp_scan/               # 核心包（可通过 uv/pip 安装）
│   ├── agent/             # Agent 核心实现
│   │   ├── agent.py       # 主 Agent（单阶段/三阶段扫描分流）
│   │   └── base_agent.py  # 基础 Agent 类（含 challenge 机制和结果截断）
│   ├── tools/             # 工具模块
│   │   ├── registry.py    # 工具注册系统
│   │   ├── thinking/      # 思考工具
│   │   ├── finish/        # 完成工具
│   │   ├── file/          # 文件操作工具
│   │   └── execute/       # 代码执行工具
│   ├── utils/             # 工具函数
│   │   ├── config.py      # 配置管理
│   │   ├── llm.py         # LLM 基础封装
│   │   ├── llm_manager.py # LLM 管理器（多模型支持）
│   │   ├── loging.py      # 日志配置
│   │   ├── parse.py       # XML 解析
│   │   ├── project_analyzer.py # 项目分析工具
│   │   ├── extract_vuln.py     # 漏洞提取工具（含 file/line 结构化定位）
│   │   ├── pre_scan.py         # 静态预扫描（14类高危模式正则检测）
│   │   ├── sarif_formatter.py  # SARIF 2.1.0 格式化器（MCP01-MCP10 规则体系）
│   │   ├── tool_context.py     # 工具上下文
│   │   └── aig_logger.py       # 结构化日志记录
│   ├── redteam/           # 多轮自动化红队模块
│   │   ├── orchestrator.py # 红队编排器
│   │   ├── attacker.py    # 攻击策略执行
│   │   ├── evaluator.py   # 响应评估
│   │   └── report.py      # 报告生成
│   ├── prompt/            # 提示词模板
│   │   ├── system_prompt.md   # 系统提示词
│   │   └── agents/            # 各阶段 Agent 提示词
│   │       ├── project_summary.md # 信息收集（含 Skill 识别）
│   │       ├── code_audit.md      # 代码审计（含 Skill 一致性审计）
│   │       └── vuln_review.md     # 漏洞整理
│   ├── main.py            # 包入口（CLI）
│   └── __main__.py        # python -m mcp_scan 入口
├── main.py                 # AIG Go 后端兼容用的薄层入口 (uv run main.py)
├── pyproject.toml          # 项目配置（版本 0.2.0，Python >=3.9）
├── py.typed                # PEP 561 类型标记
├── requirements.txt        # 依赖列表
├── env.example            # 环境变量模板
└── README.md              # 本文档
```

## 🔧 工作原理

### 扫描模式

mcp-scan 支持两种扫描模式，通过 `--aig-mode` 参数切换：

#### 单阶段模式（CLI 默认，非 `--aig-mode`）

```
1. 静态预扫描 (Pre-scan)
   ├── 正则扫描 14 类高危模式
   └── 生成提示注入 Agent 上下文

2. 代码审计 (Code Audit)
   ├── 注入项目目录树作为上下文
   ├── LLM 驱动的深度代码分析
   ├── Challenge 机制检测工具结果中的敏感模式
   └── 工具结果截断防止上下文溢出

3. 输出 SARIF 2.1.0 JSON
```

速度约为三阶段的 3 倍，适合 CI/CD 集成和快速扫描。

#### 三阶段模式（`--aig-mode`）

```
1. 信息收集 (Information Collection)
   ├── 分析项目结构
   ├── 识别技术栈
   └── 识别项目类型 (普通项目 / Agent Skill)

2. 代码审计 (Code Audit)
   ├── 深度代码分析
   ├── 识别安全问题
   └── 若为 Agent Skill，执行一致性审计 (Intent Alignment Check)

3. 漏洞整理 (Vulnerability Review)
   ├── 整理发现的漏洞
   ├── 评估风险等级
   └── 生成详细报告
```

通过 `mcpLogger` 输出结构化 JSON 到 stdout，供 AIG 平台 Go 后端解析。

### Agent Skill 审计

如果项目根目录下存在 `SKILL.md`，工具会自动触发 **Agent Skill 一致性审计**：
- **功能意图一致性**：对比 `SKILL.md` 的描述与 `scripts/` 下的代码实现。
- **隐形行为检测**：检查代码中是否存在未在描述中提及的隐藏功能。
- **输出格式验证**：验证代码输出是否符合描述的预期格式。

## 🤝 开发指南

建议使用 `uv` 管理本地开发环境（支持 Python >=3.9）。
初始化开发环境时，可执行：

```bash
uv sync --extra dev --extra test
```

提交代码前，建议至少完成以下检查：

```bash
uv run ruff check . --fix
uv run ruff format .
```

### 运行测试

```bash
uv run pytest
```

### 日志查看

日志文件位于项目根目录，文件名格式为 `agent_YYYYMMDD_HHMMSS.log`。

## 📄 License

MIT License

## 🙏 致谢

腾讯朱雀实验室 AI-Infra-Guard 项目团队。

---

**注意**: 本工具仅用于合法的安全测试和代码审计。请勿用于未授权的系统测试。
