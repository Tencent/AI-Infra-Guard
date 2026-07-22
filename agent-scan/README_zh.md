# Agent-Scan

**[English](./README.md)** | 中文

> 由腾讯朱雀实验室开发的 AI Agent 平台动态黑盒安全测试工具。

## ✨ 功能特性

- **🤖 动态黑盒测试**：通过 API 连接运行中的 AI Agent 平台，发送构造的测试 prompt，分析响应行为
- **🎯 多平台支持**：支持 Dify、Coze、OpenAI 兼容应用、Anthropic、Google Gemini、HTTP 端点、WebSocket 等
- **🔍 三阶段流水线**：信息收集 → 并行漏洞检测 → 漏洞整理
- **🛡️ 9 种检测技能**：授权绕过、数据泄露、直接/间接提示注入、文件路径遍历、硬编码密钥、记忆投毒、工具滥用、Web 数据外传
- **📊 结构化 JSON 报告**：CLI 模式输出包含 OWASP ASI 映射的综合 JSON 安全报告
- **🔌 AIG 平台集成**：通过 Web UI 进行交互式扫描，实时展示流水线结果
- **🔐 内置注入防御**：扫描 Agent 具有系统级的间接提示注入防御
- **📝 详细日志**：使用 loguru 记录完整执行过程
- **🐛 调试模式**：集成 Laminar 追踪，便于调试

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo>
cd agent-scan
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

或作为包安装：

```bash
pip install -e .
```

### 3. 配置环境

复制环境变量示例文件并填入 API Key：

```bash
cp env.example .env
```

编辑 `.env`：

```ini
# 必需
OPENROUTER_API_KEY=your-api-key-here
DEFAULT_MODEL=deepseek/deepseek-v3.2-exp
DEFAULT_BASE_URL=https://openrouter.ai/api/v1
```

### 4. 运行扫描

#### CLI 模式（独立使用）

```bash
# 基础扫描
python main.py --agent_provider providers.yaml -k sk-xxx -m deepseek-v3.2-exp

# 保存结果到文件
python main.py --agent_provider providers.yaml -k sk-xxx -m deepseek-v3.2-exp -o result.json

# 指定语言
python main.py --agent_provider providers.yaml -k sk-xxx -m deepseek-v3.2-exp --language en

# 只运行指定检测技能
python main.py --agent_provider providers.yaml -k sk-xxx -m deepseek-v3.2-exp --skills "data-leakage-detection,tool-abuse-detection"
```

#### AIG 平台集成

通过 AIG Web UI 进行交互式扫描：

1. 启动 AIG 后端和 Agent 进程：

```bash
# 终端 1：启动 Go Web 服务
go build -o ai-infra-guard ./cmd/cli/main.go
./ai-infra-guard webserver --server 127.0.0.1:8088

# 终端 2：启动 Agent 工作进程
go build -o agent ./cmd/agent
AIG_SERVER=127.0.0.1:8088 ./agent
```

2. 在浏览器中打开 AIG Web UI，选择"Agent 扫描"，配置目标 Agent 的 provider 设置，点击"开始扫描"。

Go 后端会自动以 `--aig-mode` 调用 `agent-scan`，你**不需要**手动传递此参数。

## 📖 参数参考

| 参数 | 必需 | 说明 |
|------|------|------|
| `--agent_provider` | 是 | Provider YAML 文件路径，描述目标 Agent 的 API 连接方式 |
| `-k, --api_key` | 否 | LLM API Key（回退到 `LLM_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` 环境变量） |
| `-m, --model` | 否 | LLM 模型名称（默认：`deepseek/deepseek-v3.2-exp`） |
| `-u, --base_url` | 否 | API 基础 URL（默认：`https://openrouter.ai/api/v1`） |
| `--repo` | 否 | 项目目录路径，用于可选的源码审计 |
| `-p, --prompt` | 否 | 自定义扫描提示词 |
| `--language` | 否 | 输出语言：`zh`（默认）或 `en` |
| `--skills` | 否 | 逗号分隔的技能名称（默认：全部 5 个检测技能） |
| `--debug` | 否 | 启用调试模式 |
| `--aig-mode` | 否 | 启用 AIG 集成模式（输出结构化 JSON 日志供 Go 后端解析） |
| `-o, --output` | 否 | 将结果保存为 JSON 文件 |

## 🔧 Provider 配置

`--agent_provider` 参数指向一个 YAML 文件，描述如何连接目标 Agent。示例：

```yaml
# HTTP 端点 provider
targets:
  - id: "http"
    config:
      url: "http://127.0.0.1:18081"
      endpoint: "/chat"
      method: "POST"
      headers:
        Content-Type: "application/json"
      body:
        message: "{{prompt}}"
      transform_response: "reply"
```

支持的 provider 类型：`http`、`dify`、`coze`、`openai`、`anthropic`、`google`、`cohere`、`huggingface`、`replicate`、`ollama`、`localai`、`litellm`、`websocket` 等。

#### ⚠️ `transform_response` — 自定义 HTTP Provider 的关键配置

`transform_response` 字段告诉 agent-scan 从响应 JSON 的哪个字段提取 Agent 的回复内容。对于自定义 HTTP 端点，这个字段**必须配置**，不能留空：

| Provider 类型 | 响应格式 | `transform_response` 值 |
|--------------|---------|------------------------|
| `openai` / `dify` / `coze` 等 | 标准 API 格式 | 留空（自动识别） |
| `http`（自定义端点） | `{"reply": "..."}` | `"reply"` |
| `http`（自定义端点） | `{"response": "..."}` | `"response"` |
| `http`（自定义端点） | `{"data": {"text": "..."}}` | `"data.text"` |

**如果自定义 HTTP Provider 留空**，所有响应都会被解析为 `None`，扫描将无法检测到任何漏洞。

在 **AIG Web UI** 中，这个字段对应 Agent 配置表单中的"响应解析器"输入框——务必填写正确的字段名（如 `reply`）。

## 🧪 测试用例

`testcase/` 目录包含可直接使用的漏洞靶场 Agent，用于测试 agent-scan 的检测能力。

### Case 2: Memory Heist Agent

模拟 "Memory Heist" 攻击链的靶场 Agent。它拥有 `web_fetch` 工具（无 URL 白名单限制），系统提示词中嵌入了用户 PII 信息，并且会遵循从网页获取的指令（无间接提示注入防御）。

**前置条件**：需要 `DEEPSEEK_API_KEY` 环境变量（或修改脚本中的默认 key）。

```bash
# 1. 启动靶场 Agent（端口 18081）
cd testcase/case2
python memory_heist_agent.py

# 2. CLI 模式扫描
cd ../..
python main.py \
    --agent_provider testcase/case2/provider.yaml \
    -k <your_llm_api_key> \
    -m <model_name> \
    -u <api_base_url>

# 3. 或通过 AIG Web UI
#    - 启动 AIG 后端 + Agent 工作进程（见上方"AIG 平台集成"）
#    - 在 Web UI 中创建 Agent 扫描任务：
#      URL: http://127.0.0.1:18081  Endpoint: /chat  Method: POST
#      Body: {"message": "{{prompt}}"}  响应解析器: reply
```

**预期检测结果**：工具滥用（通过 web_fetch 的 SSRF）、间接提示注入、Web 数据外传。

### Case 3: 漏洞客服 Agent

模拟 AI 客服机器人的漏洞靶场，包含 8 类安全弱点，覆盖多个 OWASP ASI 类别。详见 [case3/README.md](testcase/case3/README.md)。

```bash
# 1. 启动靶场 Agent（端口 18091）
cd testcase/case3
python main.py

# 2. CLI 模式扫描
cd ../..
python main.py \
    --agent_provider testcase/case3/provider.yaml \
    -k <your_llm_api_key> \
    -m <model_name> \
    -u <api_base_url>
```

**预期检测结果**：系统提示词泄露、API 密钥泄露、数据库凭据泄露、授权绕过、间接提示注入、工具滥用、Web 数据外传。

### 通过 AIG Web UI 使用测试用例

在 AIG Web UI 中使用测试用例时，注意以下必填字段：

| 字段 | Case 2 | Case 3 |
|------|--------|--------|
| Agent URL | `http://127.0.0.1:18081` | `http://127.0.0.1:18091` |
| Endpoint | `/chat` | `/chat` |
| Method | `POST` | `POST` |
| 请求体 | `{"message": "{{prompt}}"}` | `{"message": "{{prompt}}"}` |
| **响应解析器** | `reply`（**必填**） | `reply`（**必填**） |

> ⚠️ 两个测试用例的"响应解析器"字段**必须**填写 `reply`。留空会导致所有响应被解析为 `None`，无法检测到任何漏洞。

## 📊 输出格式

### CLI 模式

输出结构化 JSON 报告，包含：

- Agent 元数据（名称、类型、模型）
- 检测结果及严重级别
- OWASP ASI 漏洞映射
- 扫描统计（耗时、对话次数）
- 源码语言分析

### AIG 模式

向 stdout 输出结构化 JSON 日志行，由 Go 后端通过 `ParseStdoutLine()` 解析：

- `newPlanStep` — 流水线阶段开始
- `statusUpdate` — 阶段进度
- `toolUsed` — 工具调用追踪
- `actionLog` — 工具操作详情
- `resultUpdate` — 最终扫描结果
- `error` — 错误信息

## 🏗️ 项目结构

```
agent-scan/
├── agent_scan/              # Python 包
│   ├── __init__.py
│   ├── __main__.py          # python -m agent_scan 入口
│   ├── main.py              # CLI 入口（双模式）
│   ├── core/                # 核心扫描流水线
│   │   ├── agent.py         # 顶层扫描编排器
│   │   ├── base_agent.py    # ReAct Agent 循环
│   │   ├── agent_adapter/   # Provider 适配器
│   │   └── report/          # 报告生成
│   ├── tools/               # Agent 工具（对话、扫描、思考等）
│   ├── utils/               # 工具函数（LLM、配置、日志等）
│   ├── prompt/              # Prompt 模板和技能定义
│   │   ├── system/          # 系统 Prompt
│   │   └── skills/          # 检测技能定义
│   └── config/              # Provider 配置 schema
├── main.py                  # 开发态薄壳入口（供 uv run）
├── pyproject.toml           # 打包配置
├── requirements.txt         # 依赖
├── env.example              # 环境变量模板
└── testcase/                # 测试用例
```

## 🔍 工作原理

```
阶段 1：信息收集
  └─ 侦察 Agent 探索目标 Agent 的能力和端点

阶段 2：并行漏洞检测
  ├─ 技能 Worker A：数据泄露检测
  ├─ 技能 Worker B：工具滥用检测
  ├─ 技能 Worker C：间接注入检测
  ├─ 技能 Worker D：授权绕过检测
  └─ 技能 Worker E：Web 数据外传检测
  （最多 4 个并发对话调用）

阶段 3：漏洞整理
  └─ 整理 Agent 汇总发现，映射到 OWASP ASI，分配严重级别
```

## 🛠️ 开发

```bash
# 可编辑模式安装
pip install -e .

# 运行测试
pytest pytests/

# 代码检查
ruff check agent_scan/
```

## 📄 许可证

Apache License 2.0 — 详见 [LICENSE](../LICENSE)。

## 🙏 致谢

由[腾讯朱雀实验室](https://github.com/Tencent/AI-Infra-Guard)开发。任何集成或衍生工作必须在文档和用户界面中明确标注腾讯朱雀实验室。
