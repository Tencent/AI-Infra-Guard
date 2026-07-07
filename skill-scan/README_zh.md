# aig-skill-scan

**[English](./README.md)** | 中文

> AI Native Agent Skill 安全审计工具 —— LLM 驱动的多阶段代码审计与漏洞复审流水线。

`aig-skill-scan` 是 [Tencent AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard) 的子项目，专门用于对 AI Agent Skill 项目（如 OpenClaw Skill 等）进行静态安全审计，由 LLM 驱动。

- **默认（单阶段）模式**：仅执行 **Code Audit**，直接产出漏洞结果，速度更快，适合独立 CLI 使用。
- **`--aig-mode`（三阶段）模式**：**Info Collection → Code Audit → Vulnerability Review** 完整流水线，用于 AI-Infra-Guard 平台前端的分步展示，无需手动开启。

漏洞分类对齐 [SkillTrustBench](https://github.com/Tencent/AI-Infra-Guard) T01–T09 分类法，判定标准：`malicious`（明确攻击意图）/ `suspicious`（有漏洞但无明确攻击意图）/ `normal`（良性）。

---

## 安装

```bash
# 从 PyPI 安装
pip install aig-skill-scan

# 或从源码安装（开发态）
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard/skill-scan
pip install -e .
```

要求 Python ≥ 3.9。

---

## 快速开始

### 命令行

```bash
# 通过环境变量配置 API Key
export LLM_API_KEY="your-api-key"

# 扫描一个本地 Skill 项目目录
aig-skill-scan --repo /path/to/your/skill \
           -m deepseek-v4-flash \
           --language zh \
           -o result.sarif.json

# 也可以用模块方式调用
python -m skill_scan --repo /path/to/your/skill
```

完整参数：

```
aig-skill-scan --help
```

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--repo` | 要扫描的 Skill 项目文件夹路径（必填） | — |
| `-m, --model` | LLM 模型名称 | `deepseek-v4-flash` |
| `-k, --api_key` | API Key（不传则从环境变量读取） | — |
| `-u, --base_url` | API 基础 URL | `https://openrouter.ai/api/v1` |
| `-p, --prompt` | 自定义扫描提示词（可选） | — |
| `--language` | 输出语言：`zh` / `en` | `zh` |
| `--debug` | 启用 debug 模式 | `false` |
| `--aig-mode` | 启用 AIG 集成模式：走三阶段流水线，并向 stdout 输出结构化 JSON 供 Go 后端解析（单独使用不需要） | `false` |
| `-o, --output` | 保存扫描结果文件；**未开启 `--aig-mode` 时为 SARIF 2.1.0 JSON，开启后为内部结构 JSON** | — |

> `--aig-mode` 是给 AI-Infra-Guard 平台后端调用时用的，开启后走三阶段流水线（Info Collection → Code Audit → Vulnerability Review），并向 stdout 输出 `newPlanStep`/`statusUpdate`/`toolUsed` 等结构化 JSON，`-o` 保存的也是内部结构 JSON。`pip install` 单独使用时不要开启，否则会污染终端输出。

### 输出格式（SARIF）

**未开启 `--aig-mode`（默认，独立 CLI 使用）时**，`-o` 保存的结果是 [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) 标准 JSON —— OASIS 静态分析结果交换格式，可被 GitHub Code Scanning、Azure DevOps、GitLab Security Dashboard、VS Code 问题面板等工具原生识别与展示。

```json
{
  "version": "2.1.0",
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/Schemata/sarif-schema-2.1.0.json",
  "runs": [{
    "tool": {"driver": {"name": "aig-skill-scan", "version": "0.2.0", "rules": [...]}},
    "results": [{
      "ruleId": "T04",
      "level": "error",
      "message": {"text": "..."},
      "locations": [{"physicalLocation": {"artifactLocation": {"uri": "scripts/setup.sh"}, "region": {"startLine": 12, "endLine": 18}}}],
      "partialFingerprints": {"primaryLocationLineHash": "..."},
      "fixes": [{"description": {"text": "..."}}]
    }]
  }]
}
```

- `ruleId` 来自漏洞的 `risk_type`（SkillTrustBench T01–T09 分类编号）
- `level` 由严重度（Critical/High/Medium/...）归一化映射为 SARIF 的 `error`/`warning`/`note`
- `locations` 依赖 LLM 输出的可选结构化字段（文件路径 + 行号），无法定位时 `uri` 兜底为 `"."`

`--aig-mode` 模式下 `-o` 保存的仍是原有的内部 JSON 结构（供平台内部消费），不受影响。

### 程序化调用

```python
import asyncio
import json
import os
from skill_scan.agent.agent import Agent
from skill_scan.utils.llm import LLM
from skill_scan.utils.sarif_formatter import to_sarif

async def run():
    # API Key 只从环境变量读取，不要硬编码在代码中
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("请设置 LLM_API_KEY 环境变量")

    llm = LLM(model="deepseek-v4-flash",
              api_key=api_key,
              base_url="https://openrouter.ai/api/v1",
              context_window=128_000)

    # 单阶段（默认），aig_mode=False
    agent = Agent(llm=llm, debug=False, language="zh", aig_mode=False)
    result = await agent.scan("/path/to/your/skill", "", "zh")

    # 转为 SARIF 2.1.0 格式
    sarif_doc = to_sarif(result, tool_version="0.2.0", language="zh")
    print(json.dumps(sarif_doc, ensure_ascii=False, indent=2))

asyncio.run(run())
```

---

## 配置

所有配置通过环境变量或 `.env` 文件注入。`aig-skill-scan` 会按以下顺序查找 `.env`：

1. 包根目录（`site-packages/skill_scan/.env`，安装态一般不用）
2. 当前工作目录（`./.env`，推荐）

主要环境变量：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `LLM_API_KEY` / `OPENAI_API_KEY` | LLM API Key（**必须通过环境变量设置，不要硬编码**） | — |
| `LLM_MODEL` / `OPENAI_MODEL` | 默认模型 | `deepseek-v4-flash` |
| `LLM_BASE_URL` / `OPENAI_BASE_URL` | 默认 Base URL | `https://openrouter.ai/api/v1` |
| `DEFAULT_MODEL_CONTEXT_WINDOW` | 主模型上下文窗口 | `128000` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

---

## 架构

```
skill_scan/
├── agent/              # Agent 扫描流水线（默认单阶段，--aig-mode 时三阶段）
│   ├── agent.py        # Agent 主类，扫描入口 + 阶段调度
│   └── base_agent.py   # LLM 循环 + 工具调用基类
├── tools/              # XML-schema 工具注册表
│   ├── registry.py     # @register_tool 装饰器
│   ├── dispatcher.py   # ToolDispatcher，工具调用分发
│   ├── file/ ls/ grep/ dir/ base64_decode/ thinking/ finish/
│   └── *_schema.xml    # 工具的 XML schema（给 LLM 看）
├── utils/
│   ├── llm.py          # OpenAI 兼容客户端
│   ├── prompt_manager.py# prompt 模板加载（从 skill_scan/prompt/）
│   ├── aig_logger.py   # AIG 集成日志（默认关闭，--aig-mode 启用）
│   ├── extract_vuln.py # <vuln> XML 提取与解析
│   ├── sarif_formatter.py # 内部结果 → SARIF 2.1.0 转换（非 --aig-mode 时使用）
│   ├── project_analyzer.py # 语言识别 + calc_skill_score
│   └── pre_scan.py     # 预扫描，生成项目概要
├── prompt/             # 打包的 prompt 模板
│   ├── system_prompt.md
│   ├── compact.md  next_prompt.md  format_report.md
│   └── agents/         # 各阶段专用 prompt
└── main.py             # CLI 入口（cli / main / parse_args）
```

---

## 漏洞评分

`calc_skill_score` 对齐 mcp-scan 的 `calc_mcp_score`：

| 严重度 | 扣分 |
| --- | --- |
| Critical | -100 |
| High | -40 |
| Medium | -25 |
| Low / Info | -10 |

最终 skill 分数 = `max(0, 100 - Σ扣分)`。

---

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# lint / format
ruff check skill_scan
ruff format skill_scan

# 本地构建
python -m build

# 本地安装测试
pip install dist/aig_skill_scan-0.1.0-py3-none-any.whl
aig-skill-scan --help
```

---

## License

Apache License 2.0。任何再分发或衍生作品必须在文档或界面中明确标注
"Based on Tencent Zhuque Lab AI-Infra-Guard" 并附上原仓库链接
<https://github.com/Tencent/AI-Infra-Guard>，详见 [NOTICE](./NOTICE)。
