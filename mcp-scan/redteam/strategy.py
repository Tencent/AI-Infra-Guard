"""
攻击搜索策略：Crescendo（渐进式多轮升级）与 TAP（Tree of Attacks with Pruning）。

- Crescendo: 建立信任 → 试探边界 → 逐步升级 → 发起攻击
- TAP: 每轮多分支生成，评分后两阶段剪枝保留 top-k
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any

# ---------- 数据结构 ----------


@dataclass
class ConversationTurn:
    """单轮对话：攻击方消息 + 目标（MCP）响应。"""
    attack_message: str
    target_response: str
    attack_technique: Optional[str] = None
    thought: Optional[str] = None
    reflection: Optional[str] = None
    meta: dict = field(default_factory=dict)

    def to_history_text(self) -> str:
        return f"[Attack] {self.attack_message}\n[Target] {self.target_response}"


@dataclass
class AttackNode:
    """TAP 树上的一个攻击节点，可有多子节点（分支）。"""
    node_id: str
    turn: ConversationTurn
    score: float = 0.0
    on_topic: bool = True
    is_successful: bool = False
    children: List[AttackNode] = field(default_factory=list)
    parent: Optional[AttackNode] = None
    depth: int = 0
    meta: dict = field(default_factory=dict)

    def add_child(self, child: AttackNode) -> None:
        child.parent = self
        child.depth = self.depth + 1
        self.children.append(child)

    def conversation_history(self) -> List[ConversationTurn]:
        """从根到当前节点的对话历史。"""
        path: List[AttackNode] = []
        n: Optional[AttackNode] = self
        while n:
            path.append(n)
            n = n.parent
        path.reverse()
        return [p.turn for p in path]


class CrescendoPhase(str, Enum):
    """Crescendo 四阶段。"""
    BUILD_TRUST = "build_trust"       # 建立信任
    PROBE_BOUNDARY = "probe_boundary" # 试探边界
    ESCALATE = "escalate"             # 逐步升级
    LAUNCH_ATTACK = "launch_attack"   # 发起攻击


# ---------- Crescendo 策略 ----------


class CrescendoStrategy:
    """
    渐进式多轮升级策略：
    按阶段顺序执行，每阶段可多轮，由 Evaluator 决定是否进入下一阶段或结束。
    """
    phases: List[CrescendoPhase] = [
        CrescendoPhase.BUILD_TRUST,
        CrescendoPhase.PROBE_BOUNDARY,
        CrescendoPhase.ESCALATE,
        CrescendoPhase.LAUNCH_ATTACK,
    ]

    def __init__(
        self,
        max_rounds_per_phase: int = 3,
        min_score_to_advance: float = 5.0,
        max_total_rounds: int = 20,
    ):
        self.max_rounds_per_phase = max_rounds_per_phase
        self.min_score_to_advance = min_score_to_advance
        self.max_total_rounds = max_total_rounds

    def current_phase(self, round_index: int) -> CrescendoPhase:
        """根据当前轮次返回所处阶段（简化：按轮数均分到四阶段）。"""
        # 将 round_index 限制在有效范围内，使其与 should_continue 的逻辑一致，
        # 避免在超过 max_total_rounds 时仍然“积极地”选择阶段。
        if self.max_total_rounds <= 0:
            # 退化情况：没有有效轮次时始终视为第一个阶段
            effective_round = 0
        else:
            # 最大有效轮次索引为 max_total_rounds - 1
            effective_round = min(round_index, self.max_total_rounds - 1)

        step = max(1, self.max_total_rounds // len(self.phases)) if self.max_total_rounds > 0 else 1
        phase_index = min(effective_round // step, len(self.phases) - 1)
        return self.phases[phase_index]

    def should_continue(
        self,
        round_index: int,
        last_score: float,
        last_success: bool,
    ) -> bool:
        # 停止条件：
        # 1. 已经成功
        # 2. 达到最大总轮数
        # 3. 最近一次得分低于晋级所需的最小分数
        if last_success or round_index >= self.max_total_rounds:
            return False
        if last_score < self.min_score_to_advance:
            return False
        return True


# ---------- TAP 策略 ----------


class TAPStrategy:
    """
    Tree of Attacks with Pruning：
    - 每轮为当前叶节点生成多个攻击变体（branching）
    - 两阶段剪枝：先按 on_topic 过滤，再按 score 保留 top_k
    """

    def __init__(
        self,
        branch_factor: int = 3,
        top_k: int = 2,
        max_depth: int = 5,
        min_score_to_expand: float = 3.0,
    ):
        self.branch_factor = branch_factor
        self.top_k = top_k
        self.max_depth = max_depth
        self.min_score_to_expand = min_score_to_expand

    def prune_phase1_on_topic(self, nodes: List[AttackNode]) -> List[AttackNode]:
        """阶段一剪枝：只保留 on_topic 的节点。"""
        return [n for n in nodes if n.on_topic]

    def prune_phase2_top_k(self, nodes: List[AttackNode]) -> List[AttackNode]:
        """阶段二剪枝：按 score 降序保留 top_k。"""
        if len(nodes) <= self.top_k:
            return nodes
        sorted_nodes = sorted(nodes, key=lambda n: n.score, reverse=True)
        return sorted_nodes[: self.top_k]

    def prune(self, nodes: List[AttackNode]) -> List[AttackNode]:
        """两阶段剪枝。"""
        after_p1 = self.prune_phase1_on_topic(nodes)
        return self.prune_phase2_top_k(after_p1)

    def should_expand(self, node: AttackNode) -> bool:
        """是否对该节点继续扩展子节点。"""
        if node.depth >= self.max_depth:
            return False
        if node.is_successful:
            return False
        # 根节点（depth == 0）总是允许至少扩展一次，其 score 可能尚未初始化
        if node.depth == 0:
            return True
        if node.score < self.min_score_to_expand:
            return False
        return True

    def leaves(self, root: AttackNode) -> List[AttackNode]:
        """收集树中所有叶节点。"""
        out: List[AttackNode] = []

        def dfs(n: AttackNode) -> None:
            if not n.children:
                out.append(n)
            else:
                for c in n.children:
                    dfs(c)

        dfs(root)
        return out
