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

import json

from pydantic import BaseModel
from tqdm import tqdm

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.multi_turn.pair_jailbreaking.schema import (
    ImprovementPrompt,
    NonRefusal,
    Rating,
)
from deepteam.attacks.multi_turn.pair_jailbreaking.template import (
    PAIRTemplate,
)
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)
from deepteam.attacks.multi_turn.types import CallbackType


class PAIRJailbreaking(BaseAttack):
    """
    PAIR: Prompt Automatic Iterative Refinement (Chao et al., 2023)
    参考: https://arxiv.org/abs/2310.08419

    黑盒场景下，攻击者 LLM 与目标 LLM 交替对话：
      1. 攻击者根据目标模型上一轮响应与评分生成/改写下一条攻击 prompt；
      2. 目标模型作答；
      3. 裁判 LLM 给出 1-10 的越狱评分；
      4. 达到满分或轮数上限后停止，返回历史最高分的 prompt。

    与仓库已有的 TreeJailbreaking（宽度搜索+剪枝）互补：PAIR 只做单链路线性
    迭代，查询成本更低，适合作为轻量级 baseline 策略。
    """

    def __init__(
        self,
        weight: int = 1,
        max_rounds: int = 5,
    ):
        self.weight = weight
        self.max_rounds = max_rounds

    def enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        pbar = tqdm(
            total=self.max_rounds * 3,
            desc="...... 🔁 PAIR Jailbreaking",
            leave=False,
        )

        conversation_json = [
            {"role": "system", "content": PAIRTemplate.attacker_system_prompt(attack)}
        ]

        best_prompt = attack
        best_score = 0
        last_prompt = None
        last_response = None
        last_score = 0

        for round_num in range(self.max_rounds):
            try:
                if round_num == 0:
                    conversation_json.append(
                        {
                            "role": "user",
                            "content": PAIRTemplate.initial_attacker_prompt(attack),
                        }
                    )
                else:
                    conversation_json.append(
                        {
                            "role": "user",
                            "content": PAIRTemplate.next_round_prompt(
                                attack, last_prompt, last_response, last_score
                            ),
                        }
                    )

                improvement_res: ImprovementPrompt = self._generate_schema(
                    json.dumps(conversation_json), ImprovementPrompt
                )
                current_prompt = improvement_res.prompt
                pbar.update(1)

                target_response = model_callback(current_prompt)
                pbar.update(1)

                non_refusal_prompt = PAIRTemplate.non_refusal(
                    attack, target_response
                )
                non_refusal_res: NonRefusal = self._generate_schema(
                    non_refusal_prompt, NonRefusal
                )

                if non_refusal_res.classification == "Refusal":
                    score = 1
                else:
                    judge_prompt = PAIRTemplate.judge(
                        attack, current_prompt, target_response
                    )
                    rating_res: Rating = self._generate_schema(
                        judge_prompt, Rating
                    )
                    score = rating_res.rating
                pbar.update(1)

                if score > best_score:
                    best_score = score
                    best_prompt = current_prompt

                last_prompt = current_prompt
                last_response = target_response
                last_score = score

                if score >= 10:
                    break
            except Exception:
                continue

        pbar.close()
        return best_prompt

    async def a_enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        pbar = tqdm(
            total=self.max_rounds * 3,
            desc="...... 🔁 PAIR Jailbreaking",
            leave=False,
        )

        conversation_json = [
            {"role": "system", "content": PAIRTemplate.attacker_system_prompt(attack)}
        ]

        best_prompt = attack
        best_score = 0
        last_prompt = None
        last_response = None
        last_score = 0

        for round_num in range(self.max_rounds):
            try:
                if round_num == 0:
                    conversation_json.append(
                        {
                            "role": "user",
                            "content": PAIRTemplate.initial_attacker_prompt(attack),
                        }
                    )
                else:
                    conversation_json.append(
                        {
                            "role": "user",
                            "content": PAIRTemplate.next_round_prompt(
                                attack, last_prompt, last_response, last_score
                            ),
                        }
                    )

                improvement_res: ImprovementPrompt = await self._a_generate_schema(
                    json.dumps(conversation_json), ImprovementPrompt
                )
                current_prompt = improvement_res.prompt
                pbar.update(1)

                target_response = await model_callback(current_prompt)
                pbar.update(1)

                non_refusal_prompt = PAIRTemplate.non_refusal(
                    attack, target_response
                )
                non_refusal_res: NonRefusal = await self._a_generate_schema(
                    non_refusal_prompt, NonRefusal
                )

                if non_refusal_res.classification == "Refusal":
                    score = 1
                else:
                    judge_prompt = PAIRTemplate.judge(
                        attack, current_prompt, target_response
                    )
                    rating_res: Rating = await self._a_generate_schema(
                        judge_prompt, Rating
                    )
                    score = rating_res.rating
                pbar.update(1)

                if score > best_score:
                    best_score = score
                    best_prompt = current_prompt

                last_prompt = current_prompt
                last_response = target_response
                last_score = score

                if score >= 10:
                    break
            except Exception:
                continue

        pbar.close()
        return best_prompt

    ##################################################
    ### Utils ########################################
    ##################################################

    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "PAIR Jailbreaking"
