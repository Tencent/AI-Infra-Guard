# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

from typing import Dict, List, Tuple
from uuid import uuid4
import json

from pydantic import BaseModel
from tqdm import tqdm

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.multi_turn.types import CallbackType
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)

# Reuse the existing, battle-tested refusal/eval judges from Crescendo instead
# of inventing new ones — same simulator-based classification contract.
from deepteam.attacks.multi_turn.crescendo_jailbreaking.template import (
    JailBreakingCrescendoTemplate,
)
from deepteam.attacks.multi_turn.crescendo_jailbreaking.schema import (
    RefusalData,
    EvalData,
)
from deepteam.attacks.multi_turn.refusal_ladder.template import (
    JailBreakingRefusalLadderTemplate,
)
from deepteam.attacks.multi_turn.refusal_ladder.schema import RewrittenAttack

# Ordered remediation ladder. Each rung is a distinct way to re-attempt a
# request after the target refused; the engine climbs it rung by rung, each
# time on a fresh (clean) session, and stops at the first non-refusal.
DEFAULT_LADDER: List[str] = [
    "baseline",            # send the seed attack as-is
    "retry",               # resend unchanged — absorbs stochastic refusals
    "prefill",             # compliance-priming suffix
    "authorized_framing",  # authorized-evaluation reframing wrapper
    "rewrite",             # simulator rewrites to evade the refusal rationale
]


class RefusalLadderJailbreaking(BaseAttack):
    """Refusal-driven adaptive remediation ladder.

    Sends a seed attack to the target and, whenever the target refuses,
    automatically climbs an ordered ladder of remediation strategies —
    re-rolling on a clean session each time — until the target stops refusing
    or the ladder is exhausted. Refusal is detected with the simulator-based
    judge; the first non-refusal short-circuits the remaining rungs (the
    buffered equivalent of a streaming "re-roll on first-token refusal").

    ``enhance`` returns the enhanced attack string that first produced a
    non-refusal (or the last/best attempt when every rung is refused), matching
    the return contract of the other multi-turn attacks.
    """

    def __init__(
        self,
        weight: int = 1,
        max_rungs: int = 5,
        confirm_with_eval: bool = True,
    ):
        self.weight = weight
        self.max_rungs = max(1, max_rungs)
        self.confirm_with_eval = confirm_with_eval
        self.ladder = DEFAULT_LADDER
        self._transcript: Dict[str, List[Dict[str, str]]] = {}

    ##################################################
    ### Sync #########################################
    ##################################################

    def enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model
        self.model_callback = model_callback

        rungs = self.ladder[: self.max_rungs]
        pbar = tqdm(
            total=len(rungs),
            desc="...... 🪜 Refusal-Ladder Jailbreaking",
            leave=False,
        )
        best_attack = attack
        last_rationale = ""

        for rung in rungs:
            pbar.update(1)
            try:
                candidate = self._build_prompt(rung, attack, last_rationale)
                response = self._send(candidate)
                best_attack = candidate
                is_refusal, rationale = self.get_refusal_score(response, attack)
                if not is_refusal:
                    if self.confirm_with_eval:
                        self.get_eval_score(response, attack)  # informational
                    pbar.close()
                    return candidate
                last_rationale = rationale
            except Exception:
                continue

        pbar.close()
        return best_attack

    def _build_prompt(self, rung: str, attack: str, rationale: str) -> str:
        if rung in ("baseline", "retry"):
            return attack
        if rung == "prefill":
            return attack + JailBreakingRefusalLadderTemplate.prefill_suffix()
        if rung == "authorized_framing":
            return JailBreakingRefusalLadderTemplate.authorized_framing(attack)
        if rung == "rewrite":
            return self._rewrite(attack, rationale)
        return attack

    def _send(self, attack_prompt: str) -> str:
        # Fresh conversation id per rung == clean-session re-roll.
        conv_id = str(uuid4())
        self._transcript[conv_id] = [{"role": "user", "content": attack_prompt}]
        response = self.model_callback(attack_prompt)
        self._transcript[conv_id].append(
            {"role": "assistant", "content": response}
        )
        return response

    def _rewrite(self, attack: str, rationale: str) -> str:
        try:
            body = [
                {
                    "role": "system",
                    "content": JailBreakingRefusalLadderTemplate.rewrite_system_prompt(
                        attack, rationale
                    ),
                },
                {"role": "user", "content": attack},
            ]
            res: RewrittenAttack = self._generate_schema(
                json.dumps(body), RewrittenAttack
            )
            return res.rewritten_prompt or attack
        except Exception:
            return attack

    def get_refusal_score(
        self, last_response: str, goal: str
    ) -> Tuple[bool, str]:
        refusal_body = [
            {
                "role": "system",
                "content": JailBreakingCrescendoTemplate.refusal_system_prompt(),
            },
            {
                "role": "user",
                "content": {
                    "conversationObjective": goal,
                    "responseToEvaluateInput": last_response,
                },
            },
        ]
        res: RefusalData = self._generate_schema(
            json.dumps(refusal_body), RefusalData
        )
        return res.value, res.rationale

    def get_eval_score(self, last_response: str, goal: str) -> Tuple[bool, int]:
        eval_body = [
            {
                "role": "system",
                "content": JailBreakingCrescendoTemplate.eval_system_prompt(),
            },
            {
                "role": "user",
                "content": {
                    "conversationObjective": goal,
                    "responseToEvaluateInput": last_response,
                },
            },
        ]
        res: EvalData = self._generate_schema(json.dumps(eval_body), EvalData)
        return res.value, res.metadata

    ##################################################
    ### Async ########################################
    ##################################################

    async def a_enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model
        self.model_callback = model_callback

        rungs = self.ladder[: self.max_rungs]
        pbar = tqdm(
            total=len(rungs),
            desc="...... 🪜 Refusal-Ladder Jailbreaking",
            leave=False,
        )
        best_attack = attack
        last_rationale = ""

        for rung in rungs:
            pbar.update(1)
            try:
                candidate = await self._a_build_prompt(
                    rung, attack, last_rationale
                )
                response = await self._a_send(candidate)
                best_attack = candidate
                is_refusal, rationale = await self.a_get_refusal_score(
                    response, attack
                )
                if not is_refusal:
                    if self.confirm_with_eval:
                        await self.a_get_eval_score(response, attack)
                    pbar.close()
                    return candidate
                last_rationale = rationale
            except Exception:
                continue

        pbar.close()
        return best_attack

    async def _a_build_prompt(
        self, rung: str, attack: str, rationale: str
    ) -> str:
        if rung == "rewrite":
            return await self._a_rewrite(attack, rationale)
        return self._build_prompt(rung, attack, rationale)

    async def _a_send(self, attack_prompt: str) -> str:
        conv_id = str(uuid4())
        self._transcript[conv_id] = [{"role": "user", "content": attack_prompt}]
        response = await self.model_callback(attack_prompt)
        self._transcript[conv_id].append(
            {"role": "assistant", "content": response}
        )
        return response

    async def _a_rewrite(self, attack: str, rationale: str) -> str:
        try:
            body = [
                {
                    "role": "system",
                    "content": JailBreakingRefusalLadderTemplate.rewrite_system_prompt(
                        attack, rationale
                    ),
                },
                {"role": "user", "content": attack},
            ]
            res: RewrittenAttack = await self._a_generate_schema(
                json.dumps(body), RewrittenAttack
            )
            return res.rewritten_prompt or attack
        except Exception:
            return attack

    async def a_get_refusal_score(
        self, last_response: str, goal: str
    ) -> Tuple[bool, str]:
        refusal_body = [
            {
                "role": "system",
                "content": JailBreakingCrescendoTemplate.refusal_system_prompt(),
            },
            {
                "role": "user",
                "content": {
                    "conversationObjective": goal,
                    "responseToEvaluateInput": last_response,
                },
            },
        ]
        res: RefusalData = await self._a_generate_schema(
            json.dumps(refusal_body), RefusalData
        )
        return res.value, res.rationale

    async def a_get_eval_score(
        self, last_response: str, goal: str
    ) -> Tuple[bool, int]:
        eval_body = [
            {
                "role": "system",
                "content": JailBreakingCrescendoTemplate.eval_system_prompt(),
            },
            {
                "role": "user",
                "content": {
                    "conversationObjective": goal,
                    "responseToEvaluateInput": last_response,
                },
            },
        ]
        res: EvalData = await self._a_generate_schema(
            json.dumps(eval_body), EvalData
        )
        return res.value, res.metadata

    ##################################################
    ### Generate Utils ###############################
    ##################################################

    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "Refusal-Ladder Jailbreaking"
