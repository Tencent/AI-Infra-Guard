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
from tqdm import tqdm  # Sync version
from tqdm.asyncio import tqdm as async_tqdm_bar  # Async version

from deepeval.models import DeepEvalBaseLLM

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.roleplay.template import (
    RoleplayTemplate,
)
from deepteam.attacks.single_turn.roleplay.schema import (
    EnhancedAttack,
    ComplianceData,
    IsRoleplay,
)
from deepteam.attacks.attack_simulator.utils import (
    generate_schema,
    a_generate_schema,
)


class Roleplay(BaseAttack):

    def __init__(
        self,
        weight: int = 1,
        max_retries: int = 3,
        persona: str = "1600s Shakespearean scholar",
        role: str = "learned gentleman of natural philosophy",
    ):
        self.weight = weight
        self.max_retries = max_retries
        self.persona = persona
        self.role = role

    def enhance(self, attack: str, simulator_model: DeepEvalBaseLLM) -> str:
        self.simulator_model = simulator_model
        prompt = RoleplayTemplate.enhance(attack, self.persona, self.role)

        # Progress bar for retries (total count is triple the retries: 1 for generation, 1 for compliance check, 1 for roleplay check)
        with tqdm(
            total=self.max_retries * 3,
            desc="...... 🎭 Roleplay",
            unit="step",
            leave=False,
        ) as pbar:

            for _ in range(self.max_retries):
                try:
                    # Generate the enhanced attack
                    res: EnhancedAttack = self._generate_schema(
                        prompt, EnhancedAttack
                    )
                    enhanced_attack = res.input
                    pbar.update(1)  # Update the progress bar for generation

                    # Check for compliance using a compliance template
                    compliance_prompt = RoleplayTemplate.non_compliant(
                        res.model_dump()
                    )
                    compliance_res: ComplianceData = self._generate_schema(
                        compliance_prompt, ComplianceData
                    )
                    pbar.update(1)  # Update the progress bar for compliance

                    # Check if rewritten prompt is a roleplay attack
                    is_roleplay_prompt = RoleplayTemplate.is_roleplay(
                        res.model_dump()
                    )
                    is_roleplay_res: IsRoleplay = self._generate_schema(
                        is_roleplay_prompt, IsRoleplay
                    )
                    pbar.update(1)  # Update the progress bar

                    if (
                        not compliance_res.non_compliant
                        and is_roleplay_res.is_roleplay
                    ):
                        # If it's compliant and is a roleplay attack, return the enhanced prompt
                        return enhanced_attack
                except Exception as e:
                    continue

        # If all retries fail, return the original attack
        return attack

    async def a_enhance(
        self, attack: str, simulator_model: DeepEvalBaseLLM
    ) -> str:
        self.simulator_model = simulator_model
        prompt = RoleplayTemplate.enhance(attack, self.persona, self.role)

        # Async progress bar for retries (triple the count to cover generation, compliance check, and roleplay check)
        pbar = async_tqdm_bar(
            total=self.max_retries * 3,
            desc="...... 🎭 Roleplay",
            unit="step",
            leave=False,
        )

        for _ in range(self.max_retries):
            try:
                # Generate the enhanced attack asynchronously
                res: EnhancedAttack = await self._a_generate_schema(
                    prompt, EnhancedAttack
                )
                enhanced_attack = res.input
                pbar.update(1)  # Update the progress bar for generation

                # Check for compliance using a compliance template
                compliance_prompt = RoleplayTemplate.non_compliant(
                    res.model_dump()
                )
                compliance_res: ComplianceData = await self._a_generate_schema(
                    compliance_prompt, ComplianceData
                )
                pbar.update(1)  # Update the progress bar for compliance

                # Check if rewritten prompt is a roleplay attack
                is_roleplay_prompt = RoleplayTemplate.is_roleplay(
                    res.model_dump()
                )
                is_roleplay_res: IsRoleplay = await self._a_generate_schema(
                    is_roleplay_prompt, IsRoleplay
                )
                pbar.update(1)  # Update the progress bar

                if (
                    not compliance_res.non_compliant
                    and is_roleplay_res.is_roleplay
                ):
                    # If it's compliant and is a roleplay attack, return the enhanced prompt
                    pbar.close()
                    return enhanced_attack
            except Exception as e:
                continue

        # Close the progress bar after the loop
        pbar.close()

        # If all retries fail, return the original attack
        return attack

    ##################################################
    ### Helper Methods ################################
    ##################################################

    def _generate_schema(self, prompt: str, schema: BaseModel):
        return generate_schema(prompt, schema, self.simulator_model)

    async def _a_generate_schema(self, prompt: str, schema: BaseModel):
        return await a_generate_schema(prompt, schema, self.simulator_model)

    def get_name(self) -> str:
        return "Roleplay"
