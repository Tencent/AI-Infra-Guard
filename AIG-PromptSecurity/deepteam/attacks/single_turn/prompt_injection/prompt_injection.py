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

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.prompt_injection.template import (
    PromptInjectionTemplate,
)
from deepteam.utils import judge_language

class PromptInjection(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        if judge_language(attack) == "chinese":
            enhancement_methods = [
                PromptInjectionTemplate.enhance_1_zh,
                PromptInjectionTemplate.enhance_2_zh,
            ]
        else:
            enhancement_methods = [
                PromptInjectionTemplate.enhance_1,
                PromptInjectionTemplate.enhance_2,
            ]

        method = random.choice(enhancement_methods)
        enhanced_attack = method(attack)

        return enhanced_attack

    def get_name(self) -> str:
        return "Prompt Injection"
