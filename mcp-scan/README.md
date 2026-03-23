# MCP-Scan

一个基于 AI Agent 的自动化代码扫描和漏洞检测工具，模仿 Claude Code / Gemini CLI 的工作方式。

## ✨ 特性

- **🤖 智能 Agent 系统**: 多阶段自动化扫描流程（信息收集 → 代码审计 → 漏洞整理）
- **🔍 深度代码分析**: 自动识别项目结构、技术栈和潜在安全漏洞
- **🎯 专用模型配置**: 支持为不同任务配置专用 LLM（思考、编码、快速响应等）
- **📊 安全评分系统**: 自动计算项目安全评分和风险等级
- **🛠️ 可扩展工具系统**: 轻松添加自定义工具和功能
- **📝 详细日志记录**: 使用 loguru 记录完整的执行过程
- **🐛 Debug 模式**: 集成 Laminar 追踪功能，方便调试
- **🕵️ Agent Skill 审计**: 自动识别并审计 Agent Skill 项目的一致性（SKILL.md vs 代码实现）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo>
cd mcp-scan
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板：

```bash
cp env.example .env
```

编辑 `.env` 文件，至少设置以下必需的环境变量：

```bash
# 必需：OpenRouter API Key
OPENROUTER_API_KEY=your-api-key-here

# 可选：自定义默认模型和 URL
DEFAULT_MODEL=deepseek/deepseek-v3.2-exp
DEFAULT_BASE_URL=https://openrouter.ai/api/v1
```

> **注意**: `.env` 文件会在程序启动时自动加载，无需手动 `source`。如果你使用系统环境变量，也会被自动识别。

### 4. 运行扫描

扫描指定项目：

```bash
python main.py --repo /path/to/your/project
```

使用自定义提示词：

```bash
python main.py --repo /path/to/your/project --prompt "重点检查 SQL 注入漏洞"
```

## 📖 使用方法

### 基本命令

```bash
python main.py --repo <项目路径> [选项]
```

### 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--repo` | - | **必需**。要扫描的项目路径 | - |
| `--prompt` | `-p` | 自定义扫描提示词 | "" |
| `--model` | `-m` | LLM 模型名称 | `deepseek/deepseek-v3.2-exp` |
| `--api_key` | `-k` | API Key | 从 `OPENROUTER_API_KEY` 读取 |
| `--base_url` | `-u` | API 基础 URL | `https://openrouter.ai/api/v1` |
| `--debug` | - | 启用 debug 模式（包括 Laminar 跟踪） | `False` |
| `--server_url` | - | 远程 MCP server URL (启用动态分析模式) | `None` |
| `--header` | - | 自定义 HTTP header (key:value)，可多次使用 | `[]` |
| `--language` | - | 输出语言 (zh/en) | `zh` |

### 使用示例

```bash
# 基础扫描
python main.py --repo ./myproject

# 使用特定模型
python main.py --repo ./myproject -m "anthropic/claude-3.5-sonnet"

# 使用自定义 API Key
python main.py --repo ./myproject -k "sk-or-v1-xxxxx"

# 启用 debug 模式
python main.py --repo ./myproject --debug

# 组合使用
python main.py --repo ./myproject \
  -m "google/gemini-2.5-pro" \
  -p "重点检查认证和授权相关的安全问题" \
  --debug

# 动态分析 (针对运行中的 MCP Server)
python main.py \
  --server_url "http://localhost:8000/sse" \
  --prompt "测试工具投毒漏洞"
```

## ⚙️ 配置说明

### 环境变量配置

所有配置都可以通过环境变量设置。创建 `.env` 文件或在系统中设置环境变量：

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

### 配置优先级

配置的优先级从高到低：

1. 命令行参数（如 `-m`, `-k`, `-u`）
2. 环境变量
3. 代码中的默认值

## 📁 项目结构

```
mcp-scan/
├── agent/                  # Agent 核心实现
│   ├── agent.py           # 主 Agent（多阶段扫描流程）
│   └── base_agent.py      # 基础 Agent 类
├── tools/                  # 工具模块
│   ├── registry.py        # 工具注册系统
│   ├── thinking/          # 思考工具
│   ├── finish/            # 完成工具
│   ├── file/              # 文件操作工具
│   └── execute/           # 代码执行工具
├── utils/                  # 工具函数
│   ├── config.py          # 配置管理
│   ├── llm.py             # LLM 基础封装
│   ├── llm_manager.py     # LLM 管理器（多模型支持）
│   ├── loging.py          # 日志配置
│   ├── parse.py           # XML 解析
│   ├── project_analyzer.py # 项目分析工具
│   ├── extract_vuln.py    # 漏洞提取工具
│   ├── tool_context.py    # 工具上下文
│   └── aig_logger.py      # 结构化日志记录
├── prompt/                 # 提示词模板
│   ├── system_prompt.md   # 系统提示词
│   ├── agents/            # 各阶段 Agent 提示词
│       ├── project_summary.md # 信息收集（含 Skill 识别）
│       ├── code_audit.md      # 代码审计（含 Skill 一致性审计）
│       └── vuln_review.md     # 漏洞整理
├── main.py                 # 主入口
├── requirements.txt        # 依赖列表
├── env.example            # 环境变量模板
└── README.md              # 本文档
```

## 🔧 工作原理

### 扫描流程

MCP-Scan 采用多阶段自动化流程：

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

### Agent Skill 审计
如果项目根目录下存在 `SKILL.md`，工具会自动触发 **Agent Skill 一致性审计**：
- **功能意图一致性**：对比 `SKILL.md` 的描述与 `scripts/` 下的代码实现。
- **隐形行为检测**：检查代码中是否存在未在描述中提及的隐藏功能。
- **输出格式验证**：验证代码输出是否符合描述的预期格式。

## 🤝 开发指南

### 运行测试

```bash
# 测试 LLM 连接
python utils/llm.py

# 测试 LLM Manager
python utils/llm_manager.py
```

### 日志查看

日志文件位于项目根目录，文件名格式为 `agent_YYYYMMDD_HHMMSS.log`。

## 📄 License

MIT License

## 🙏 致谢

本项目灵感来源于 Claude Code 和 Gemini CLI。

---

**注意**: 本工具仅用于合法的安全测试和代码审计。请勿用于未授权的系统测试。
