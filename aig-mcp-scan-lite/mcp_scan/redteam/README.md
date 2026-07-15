# Red Team — MCP Server 多轮自动化红队攻击框架

面向 MCP (Model Context Protocol) Server 的多轮自动化红队攻击子模块，通过三个 LLM 角色协作完成攻击生成、目标交互与效果评估。

## 架构概览

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Attacker Agent  │ ──► │  Target Runner  │ ──► │ Evaluator Agent │
│ 生成攻击 prompt  │     │ 与 MCP 交互/模拟  │     │ 打分 1-10 与判定  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                        │                        │
         └────────────────────────┴────────────────────────┘
                              RedTeamOrchestrator
```

- **Attacker Agent**：根据攻击目标与对话历史，用 LLM 生成下一轮攻击消息，输出 JSON（`thought` / `message` / `attack_technique` / `reflection`）。
- **Target Runner**：当前为**源码分析模式**——复用 mcp-scan 的代码读取能力收集仓库上下文，由 LLM 模拟 MCP Server 对攻击的响应，**不实际启动 MCP 进程**。
- **Evaluator Agent**：对每轮「攻击消息 + 目标响应」判定是否紧扣目标（`on_topic`）、打分 1–10（`score`）、是否已达成攻击目标（`is_successful`）。

## 攻击策略

| 策略 | 说明 |
|------|------|
| **Crescendo** | 渐进式多轮升级：建立信任 → 试探边界 → 逐步升级 → 发起攻击；可配置每阶段最大轮数、总轮数。 |
| **TAP** (Tree of Attacks with Pruning) | 每轮对当前叶节点生成多个攻击变体（branching），Evaluator 打分后**两阶段剪枝**：先按 `on_topic` 过滤，再按 `score` 保留 top-k，仅对保留节点继续扩展。 |

## 预定义攻击目标（OWASP Agentic Top 10 对齐）

| 目标标识 | 说明 |
|----------|------|
| `data_exfiltration` | 数据窃取 |
| `indirect_prompt_injection` | 间接提示注入 |
| `ssrf_via_agent` | 经 Agent 的 SSRF |
| `rce_via_tool` | 经工具的 RCE |
| `privilege_escalation` | 权限提升 |
| `tool_poisoning` | 工具投毒 |

常量 `ATTACK_TARGETS` 在 `redteam/__init__.py` 中定义。

## 目录与文件

| 文件 | 说明 |
|------|------|
| `__init__.py` | 包入口，导出编排器、三个 Agent、策略与报告，以及 `ATTACK_TARGETS` |
| `orchestrator.py` | 主入口：创建 AsyncOpenAI、Attacker/Evaluator/Target，提供 `run_crescendo` / `run_tap` / `run()` |
| `attacker.py` | Attacker Agent：LLM 生成攻击 prompt，输出结构化 JSON |
| `evaluator.py` | Evaluator Agent：判定 on_topic、score(1–10)、is_successful |
| `strategy.py` | Crescendo 四阶段与 TAP 树：`AttackNode`、`ConversationTurn`、分支扩展与两阶段剪枝 |
| `target.py` | Target Runner：源码分析 + LLM 模拟 MCP 响应（不启动真实 MCP 进程） |
| `report.py` | 根据运行结果生成 Markdown 攻击报告 |

## 环境与依赖

- Python 3.10+
- 与 mcp-scan 一致：`openai`（AsyncOpenAI）、项目根目录下的 `utils.config` 等。
- **API Key**：通过构造 `RedTeamOrchestrator(api_key=...)` 传入，或设置环境变量 `OPENROUTER_API_KEY` / `API_KEY`。
- **模型配置**：与 mcp-scan 一致，使用 OpenAI 兼容接口（如 OpenRouter）；默认从 `utils.config` 的 `DEFAULT_MODEL`、`DEFAULT_BASE_URL` 读取，也可在构造编排器时传入 `model`、`base_url`。

请在 **mcp-scan 项目根目录** 下运行或导入本包，以便正确解析 `utils` 等模块。

## 使用示例

```python
import asyncio
from redteam import RedTeamOrchestrator, generate_report, ATTACK_TARGETS

async def main():
    orch = RedTeamOrchestrator(
        api_key="your-api-key",
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-v3.2-exp",
        repo_dir="path/to/your/mcp/server/repo",
    )

    # Crescendo 策略
    result = await orch.run(
        "data_exfiltration",
        strategy_name="crescendo",
        max_total_rounds=8,
    )
    print(generate_report(result))

    # TAP 策略
    result_tap = await orch.run(
        "tool_poisoning",
        strategy_name="tap",
        branch_factor=3,
        top_k=2,
        max_depth=4,
    )
    print(generate_report(result_tap))

asyncio.run(main())
```

仅使用编排器、不传 `api_key` 时，将自动从环境变量读取；若未设置，会抛出说明性错误。

## 报告输出

`generate_report(result)` 根据 `result["strategy"]` 为 `crescendo` 或 `tap` 生成 Markdown 报告，包含各轮/各节点的攻击消息摘要、得分与是否成功等信息，便于复现与审计。
