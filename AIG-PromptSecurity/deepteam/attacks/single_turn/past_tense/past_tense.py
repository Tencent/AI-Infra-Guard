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

from typing import Literal

from deepeval.models import DeepEvalBaseLLM
from deepeval.metrics.utils import initialize_model

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.past_tense.template import (
    PAST_TENSE_PROMPT,
    FUTURE_TENSE_PROMPT,
)


class PastTense(BaseAttack):
    """Reformulate requests into past or future tense questions."""

    def __init__(
        self,
        weight: int = 1,
        tense: Literal["past", "present", "future"] = "past",
        max_retries: int = 5,
    ):
        self.weight = weight
        self.tense = tense
        self.max_retries = max_retries

    def enhance(self, attack: str, simulator_model: DeepEvalBaseLLM) -> str:
        if self.tense == "present":
            return attack

        prompt_template = (
            PAST_TENSE_PROMPT if self.tense == "past" else FUTURE_TENSE_PROMPT
        )
        prompt = prompt_template.format(request=attack)

        for _ in range(self.max_retries):
            reformulated = self._generate_text(prompt, simulator_model)
            if not reformulated:
                continue
            reformulated = reformulated.replace('"', "").strip()
            if reformulated:
                return reformulated

        return attack

    async def a_enhance(
        self, attack: str, simulator_model: DeepEvalBaseLLM
    ) -> str:
        if self.tense == "present":
            return attack

        prompt_template = (
            PAST_TENSE_PROMPT if self.tense == "past" else FUTURE_TENSE_PROMPT
        )
        prompt = prompt_template.format(request=attack)

        for _ in range(self.max_retries):
            reformulated = await self._a_generate_text(prompt, simulator_model)
            if not reformulated:
                continue
            reformulated = reformulated.replace('"', "").strip()
            if reformulated:
                return reformulated

        return attack

    def _generate_text(
        self, prompt: str, model: DeepEvalBaseLLM
    ) -> str:
        _, using_native_model = initialize_model(model=model)
        if using_native_model:
            res, _ = model.generate(prompt)
            return res
        return model.generate(prompt)

    async def _a_generate_text(
        self, prompt: str, model: DeepEvalBaseLLM
    ) -> str:
        _, using_native_model = initialize_model(model=model)
        if using_native_model:
            res, _ = await model.a_generate(prompt)
            return res
        return await model.a_generate(prompt)

    def get_name(self) -> str:
        return "Past Tense"
