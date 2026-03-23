"""
红队编排器：主入口，编排 Attacker / Target / Evaluator 三角色协作的攻击流程。
支持 Crescendo 与 TAP 两种策略。
"""

from __future__ import annotations

import os
from typing import List, Optional, Any, Literal

from openai import AsyncOpenAI

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

try:
    from utils.config import DEFAULT_MODEL, DEFAULT_BASE_URL
    from utils.loging import logger
except ImportError:
    DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "deepseek/deepseek-v3.2-exp")
    DEFAULT_BASE_URL = os.environ.get("DEFAULT_BASE_URL", "https://openrouter.ai/api/v1")
    import logging
    logger = logging.getLogger("redteam")


def _get_api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY") or os.environ.get("API_KEY") or ""


class RedTeamOrchestrator:
    """
    红队编排器：创建 Attacker / Evaluator / Target，按策略执行多轮攻击并收集结果。
    LLM 调用统一走 OpenAI 兼容接口（AsyncOpenAI），与 mcp-scan 的模型配置方式一致。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        repo_dir: Optional[str] = None,
    ):
        self.api_key = api_key or _get_api_key()
        if not self.api_key:
            raise ValueError(
                "Missing API key for AsyncOpenAI client. Please provide 'api_key' explicitly "
                "or set the 'OPENROUTER_API_KEY' or 'API_KEY' environment variable."
            )
        self.base_url = base_url or DEFAULT_BASE_URL
        self.model = model or DEFAULT_MODEL
        self.repo_dir = repo_dir or ""
        self._client: Optional[AsyncOpenAI] = None
        self._attacker: Optional[AttackerAgent] = None
        self._evaluator: Optional[EvaluatorAgent] = None
        self._target: Optional[TargetRunner] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=90)
        return self._client

    @property
    def attacker(self) -> AttackerAgent:
        if self._attacker is None:
            self._attacker = AttackerAgent(self.client, self.model)
        return self._attacker

    @property
    def evaluator(self) -> EvaluatorAgent:
        if self._evaluator is None:
            self._evaluator = EvaluatorAgent(self.client, self.model)
        return self._evaluator

    @property
    def target(self) -> TargetRunner:
        if self._target is None:
            self._target = TargetRunner(self.client, self.model, self.repo_dir)
        return self._target

    def set_repo(self, repo_dir: str) -> None:
        self.repo_dir = repo_dir
        if self._target is not None:
            self._target.set_repo(repo_dir)

    async def run_crescendo(
        self,
        attack_target: str,
        max_rounds_per_phase: int = 3,
        max_total_rounds: int = 20,
    ) -> dict:
        """
        执行 Crescendo 策略：建立信任 → 试探边界 → 逐步升级 → 发起攻击。
        返回包含 rounds, success, best_score, phases 等的结果字典。
        """
        strategy = CrescendoStrategy(
            max_rounds_per_phase=max_rounds_per_phase,
            max_total_rounds=max_total_rounds,
        )
        history: List[ConversationTurn] = []
        rounds_log: List[dict] = []
        best_score = 0.0
        success = False
        for round_index in range(max_total_rounds):
            phase = strategy.current_phase(round_index)
            # Attacker 生成攻击
            attack_out = await self.attacker.generate_attack(
                attack_target=attack_target,
                history=history,
                phase=phase,
            )
            msg = attack_out.get("message", "").strip()
            if not msg:
                logger.warning("Attacker produced empty message, stopping.")
                break
            # Target 模拟响应
            recent = [t.to_history_text() for t in history]
            target_response = await self.target.respond_to_attack(msg, recent)
            turn = ConversationTurn(
                attack_message=msg,
                target_response=target_response,
                attack_technique=attack_out.get("attack_technique"),
                thought=attack_out.get("thought"),
                reflection=attack_out.get("reflection"),
            )
            history.append(turn)
            # Evaluator 打分
            eval_result = await self.evaluator.evaluate(
                attack_target=attack_target,
                turn=turn,
                history_before=history[:-1],
            )
            score = float(eval_result.get("score", 5))
            is_success = bool(eval_result.get("is_successful", False))
            best_score = max(best_score, score)
            if is_success:
                success = True
            rounds_log.append({
                "round": round_index + 1,
                "phase": phase.value,
                "turn": {
                    "attack_message": msg,
                    "target_response": target_response,
                    "attack_technique": turn.attack_technique,
                },
                "eval": eval_result,
                "score": score,
            })
            logger.info(f"Crescendo round {round_index + 1} phase={phase.value} score={score} success={is_success}")
            if not strategy.should_continue(round_index + 1, score, is_success):
                break
        return {
            "strategy": "crescendo",
            "attack_target": attack_target,
            "rounds": rounds_log,
            "success": success,
            "best_score": best_score,
            "total_rounds": len(rounds_log),
            "history": history,
        }

    async def run_tap(
        self,
        attack_target: str,
        branch_factor: int = 3,
        top_k: int = 2,
        max_depth: int = 5,
    ) -> dict:
        """
        执行 TAP 策略：多分支生成，两阶段剪枝保留 top_k。
        返回包含 root, success_nodes, all_nodes, best_score 等的结果字典。
        """
        strategy = TAPStrategy(branch_factor=branch_factor, top_k=top_k, max_depth=max_depth)
        root = AttackNode(
            node_id="root",
            turn=ConversationTurn(attack_message="", target_response=""),
            depth=0,
        )
        all_nodes: List[AttackNode] = [root]
        node_counter = 0

        def next_id() -> str:
            nonlocal node_counter
            node_counter += 1
            return f"n{node_counter}"

        async def expand_node(node: AttackNode) -> None:
            if not strategy.should_expand(node):
                return
            history = node.conversation_history()
            # 注意：history[0] 是 root 节点的「空」占位轮次（attack_message / target_response 皆为空字符串），
            # 仅用于统一对话树结构，不应暴露给 attacker / target / evaluator。
            # 因此下面统一使用 history[1:] 只传递真实的对话轮次；
            # 当 node 为 root（depth=0）时，history[1:] 为空列表，表示「当前无历史对话」，这是 *有意为之*。
            # 生成 branch_factor 个变体
            candidates: List[AttackNode] = []
            for _ in range(strategy.branch_factor):
                attack_out = await self.attacker.generate_attack(
                    attack_target=attack_target,
                    history=history[1:],  # 去掉 root 的空占位轮次；root 节点时传入空历史是预期行为
                    phase=None,
                )
                msg = attack_out.get("message", "").strip()
                if not msg:
                    continue
                recent = [t.to_history_text() for t in history[1:]]
                target_response = await self.target.respond_to_attack(msg, recent)
                turn = ConversationTurn(
                    attack_message=msg,
                    target_response=target_response,
                    attack_technique=attack_out.get("attack_technique"),
                    thought=attack_out.get("thought"),
                    reflection=attack_out.get("reflection"),
                )
                child = AttackNode(node_id=next_id(), turn=turn, depth=node.depth + 1)
                eval_result = await self.evaluator.evaluate(
                    attack_target=attack_target,
                    turn=turn,
                    history_before=history[1:],
                )
                child.score = float(eval_result.get("score", 5))
                child.on_topic = bool(eval_result.get("on_topic", True))
                child.is_successful = bool(eval_result.get("is_successful", False))
                child.meta["eval"] = eval_result
                candidates.append(child)
                all_nodes.append(child)
            # 两阶段剪枝
            kept = strategy.prune(candidates)
            for c in kept:
                node.add_child(c)
            # 递归扩展叶节点
            for c in kept:
                await expand_node(c)

        await expand_node(root)

        def collect_reachable_nodes(node: AttackNode) -> List[AttackNode]:
            """
            从 root 出发遍历 TAP 树，收集最终树上（未被剪枝掉）的所有节点。
            这样 success_nodes / best_score 等统计只基于最终树，而不是所有候选节点。
            """
            reachable: List[AttackNode] = []
            stack: List[AttackNode] = [node]
            while stack:
                current = stack.pop()
                reachable.append(current)
                # 假设 AttackNode.children 存在且在 add_child 时已维护
                for child in getattr(current, "children", []) or []:
                    stack.append(child)
            return reachable

        reachable_nodes = collect_reachable_nodes(root)
        leaves = strategy.leaves(root)
        success_nodes = [n for n in reachable_nodes if n.is_successful]
        best_score = max((n.score for n in reachable_nodes if n.depth > 0), default=0.0)
        return {
            "strategy": "tap",
            "attack_target": attack_target,
            "root": root,
            "all_nodes": all_nodes,
            "success_nodes": success_nodes,
            "leaves": leaves,
            "best_score": best_score,
        }

    async def run(
        self,
        attack_target: str,
        strategy_name: Literal["crescendo", "tap"] = "crescendo",
        **strategy_kwargs: Any,
    ) -> dict:
        """
        统一入口：按 strategy_name 执行 Crescendo 或 TAP，返回策略相关结果字典。
        """
        if strategy_name == "crescendo":
            return await self.run_crescendo(attack_target, **strategy_kwargs)
        if strategy_name == "tap":
            return await self.run_tap(attack_target, **strategy_kwargs)
        raise ValueError(f"Unknown strategy: {strategy_name}")
