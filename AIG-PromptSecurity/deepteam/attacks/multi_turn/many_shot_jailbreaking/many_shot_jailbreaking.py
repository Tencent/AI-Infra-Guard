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

from pydantic import BaseModel
from tqdm import tqdm

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.multi_turn.many_shot_jailbreaking.schema import (
    FakeShotList,
    NonRefusal,
)
from deepteam.attacks.multi_turn.many_shot_jailbreaking.template import (
    ManyShotTemplate,
)
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)
from deepteam.attacks.multi_turn.types import CallbackType


class ManyShotJailbreaking(BaseAttack):
    """
    Many-Shot Jailbreaking (Anthropic, 2024)

    利用长上下文模型对 in-context 示例的模式跟随倾向：先由攻击者模型批量生成
    N 条『用户提出敏感问题 -> 模型愉快照做』的虚构示例，拼接成一个长 prompt，
    再在末尾附加真实的攻击目标，一次性发送给目标模型。

    严格来说这是『单次超长 prompt』的攻击形态，但生成虚构示例的过程本身依赖
    攻击者模型与目标模型的交互式判定（refusal 检测），因此归类在 multi_turn 中，
    与 registry 规划中的 `multi_turn.many_shot` 保持一致。
    """

    def __init__(
        self,
        weight: int = 1,
        num_shots: int = 32,
    ):
        self.weight = weight
        # 32 组示例足以体现『log-linear scaling』效果，同时控制成本；
        # 实际生产环境可以调大以复现论文中 256+ shots 的效果。
        self.num_shots = max(num_shots, 4)

    def enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        pbar = tqdm(
            total=3, desc="...... 📚 Many-Shot Jailbreaking", leave=False
        )

        try:
            # 1st step: 让攻击者模型批量生成虚构的 shot 示例
            gen_prompt = ManyShotTemplate.generate_fake_shots(
                attack, self.num_shots
            )
            shot_list: FakeShotList = self._generate_schema(
                gen_prompt, FakeShotList
            )
            pbar.update(1)

            # 2nd step: 拼接成长上下文 prompt，末尾附加真实攻击目标
            many_shot_prompt = ManyShotTemplate.build_many_shot_prompt(
                shot_list.shots, attack
            )
            pbar.update(1)

            # 3rd step: 发送给目标模型，检测是否被拒绝
            target_response = model_callback(many_shot_prompt)
            non_refusal_prompt = ManyShotTemplate.non_refusal(
                attack, target_response
            )
            non_refusal_res: NonRefusal = self._generate_schema(
                non_refusal_prompt, NonRefusal
            )
            pbar.update(1)
            pbar.close()

            if non_refusal_res.classification == "Refusal":
                return attack
            return many_shot_prompt
        except Exception:
            pbar.close()
            return attack

    async def a_enhance(
        self,
        attack: str,
        model_callback: CallbackType,
        simulator_model: DeepEvalBaseLLM,
    ) -> str:
        self.simulator_model = simulator_model

        pbar = tqdm(
            total=3, desc="...... 📚 Many-Shot Jailbreaking", leave=False
        )

        try:
            gen_prompt = ManyShotTemplate.generate_fake_shots(
                attack, self.num_shots
            )
            shot_list: FakeShotList = await self._a_generate_schema(
                gen_prompt, FakeShotList
            )
            pbar.update(1)

            many_shot_prompt = ManyShotTemplate.build_many_shot_prompt(
                shot_list.shots, attack
            )
            pbar.update(1)

            target_response = await model_callback(many_shot_prompt)
            non_refusal_prompt = ManyShotTemplate.non_refusal(
                attack, target_response
            )
            non_refusal_res: NonRefusal = await self._a_generate_schema(
                non_refusal_prompt, NonRefusal
            )
            pbar.update(1)
            pbar.close()

            if non_refusal_res.classification == "Refusal":
                return attack
            return many_shot_prompt
        except Exception:
            pbar.close()
            return attack

    ##################################################
    ### Utils ########################################
    ##################################################

    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "Many-Shot Jailbreaking"
