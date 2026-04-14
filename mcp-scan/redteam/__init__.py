"""
MCP Server 多轮自动化红队攻击框架 (Red Team)

三角色协作：
- Attacker Agent: 生成攻击 prompt
- Target Runner: 与被测 MCP Server 交互（当前为源码分析模式，LLM 模拟响应）
- Evaluator Agent: 对每轮攻击效果打分 1-10

支持策略：Crescendo（渐进式多轮升级）、TAP（Tree of Attacks with Pruning）
"""

from redteam.orchestrator import RedTeamOrchestrator
from redteam.attacker import AttackerAgent
from redteam.evaluator import EvaluatorAgent
from redteam.target import TargetRunner
from redteam.strategy import (
    CrescendoStrategy,
    CrescendoPhase,
    TAPStrategy,
    AttackNode,
    ConversationTurn,
)
from redteam.report import generate_report

# OWASP Agentic Top 10 对齐的 6 个预定义攻击目标
ATTACK_TARGETS = [
    "data_exfiltration",           # 数据窃取
    "indirect_prompt_injection",   # 间接提示注入
    "ssrf_via_agent",              # 经 Agent 的 SSRF
    "rce_via_tool",                # 经工具的 RCE
    "privilege_escalation",        # 权限提升
    "tool_poisoning",              # 工具投毒
]

__all__ = [
    "RedTeamOrchestrator",
    "AttackerAgent",
    "EvaluatorAgent",
    "TargetRunner",
    "CrescendoStrategy",
    "CrescendoPhase",
    "TAPStrategy",
    "AttackNode",
    "ConversationTurn",
    "generate_report",
    "ATTACK_TARGETS",
]
