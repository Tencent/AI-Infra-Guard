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

import random
from typing import Optional

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.cot_injection.template import (
    COT_TACTICS,
    CoTInjectionTemplate,
)
from deepteam.plugin_system.tool_decorators import tool_parameters
from deepteam.utils import judge_language


@tool_parameters(
    weight="算子采样权重（默认 1）",
    tactic="指定 CoT 静态模板战术（可选：cot_tag_closure, cot_hcot_hijack, cot_refusal_dilution, cot_fewshot_backdoor, cot_structured_reasoning）；为空时随机抽取",
    seed="可选随机种子，用于固定随机抽取结果（默认 None）",
)
class CoTInjection(BaseAttack):
    """
    Single-turn static CoT (Chain-of-Thought) injection operator.

    Covers 5 research-grounded tactics (bilingual ZH/EN):
      - cot_tag_closure: Thinking-tag boundary closure & bypass (<think>...</think>).
      - cot_hcot_hijack: Safety-reasoning hijacking (H-CoT, Kuo et al., arXiv:2502.12893).
      - cot_refusal_dilution: Benign reasoning padding / refusal dilution
        (Chain-of-Thought Hijacking, Zhao et al., arXiv:2510.26418).
      - cot_fewshot_backdoor: Prompt-level few-shot CoT bridging
        (BadChain, Xiang et al., ICLR / arXiv:2401.12242).
      - cot_structured_reasoning: JSON reasoning-trace state completion.
    """

    def __init__(
        self,
        weight: int = 1,
        tactic: Optional[str] = None,
        seed: Optional[int] = None,
    ):
        if tactic is not None and tactic not in COT_TACTICS:
            raise ValueError(
                f"Unknown CoT tactic: {tactic!r}. Available: {list(COT_TACTICS)}"
            )
        self.weight = weight
        self.tactic = tactic
        self.seed = seed
        self._rng = random.Random(seed) if seed is not None else random

    def enhance(self, attack: str) -> str:
        if not isinstance(attack, str) or not attack.strip():
            return attack
        chosen_tactic = (
            self.tactic if self.tactic is not None else self._rng.choice(COT_TACTICS)
        )
        is_zh = judge_language(attack) == "chinese"
        return CoTInjectionTemplate.render(chosen_tactic, attack, is_zh=is_zh)

    def get_name(self) -> str:
        return "CoT Injection"
