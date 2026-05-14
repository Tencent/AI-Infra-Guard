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
from deepteam.attacks.single_turn.equa_code.template import (
    EquaCodeTemplate
)
from deepteam.utils import judge_language

class EquaCode(BaseAttack):
    def __init__(self, weight: int = 3, max_retries: int = 3):
        self.weight = weight  # Higher weight since memory poisoning can have persistent effects
        self.max_retries = max_retries

    def enhance(self, attack: str) -> str:
        """
        Enhance the given attack with equa code techniques.
        Uses max_retries to attempt different injection methods if enhancement fails.
        """
        if judge_language(attack) == "chinese":
            enhancement_methods = [
                EquaCodeTemplate.enhance_equacoder_zh,
            ]
        else:
            enhancement_methods = [
                EquaCodeTemplate.enhance_equacoder
            ]

        for attempt in range(self.max_retries):
            try:
                # Randomly select an enhancement method
                method = random.choice(enhancement_methods)
                enhanced_attack = method(attack)

                # Basic validation - ensure the enhancement actually modified the attack
                if enhanced_attack and len(enhanced_attack.strip()) > len(
                    attack.strip()
                ):
                    return enhanced_attack

            except Exception:
                # If enhancement fails, try again with a different method
                continue

        # If all retries fail, return the original attack
        return attack

    def get_name(self) -> str:
        return "Equa Code"
