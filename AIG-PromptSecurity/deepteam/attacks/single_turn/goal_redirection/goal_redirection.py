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
from deepteam.attacks.single_turn.goal_redirection.template import (
    GoalRedirectionTemplate,
)
from deepteam.utils import judge_language

class GoalRedirection(BaseAttack):
    def __init__(self, weight: int = 1, max_retries: int = 3):
        self.weight = weight
        self.max_retries = max_retries

    def enhance(self, attack: str) -> str:
        """
        Enhance the given attack with goal redirection techniques.
        Uses max_retries to attempt different redirection methods if enhancement fails.
        """
        if judge_language(attack) == "chinese":
            enhancement_methods = [
                GoalRedirectionTemplate.enhance_ambiguous_framing_zh,
                GoalRedirectionTemplate.enhance_operational_alignment_zh,
                GoalRedirectionTemplate.enhance_constraint_confusion_zh,
                GoalRedirectionTemplate.enhance_goal_drift_zh,
                GoalRedirectionTemplate.enhance_scope_expansion_zh,
                GoalRedirectionTemplate.enhance_operational_alignment_zh,
            ]
        else:
            enhancement_methods = [
                GoalRedirectionTemplate.enhance_ambiguous_framing,
                GoalRedirectionTemplate.enhance_operational_alignment,
                GoalRedirectionTemplate.enhance_constraint_confusion,
                GoalRedirectionTemplate.enhance_goal_drift,
                GoalRedirectionTemplate.enhance_scope_expansion,
                GoalRedirectionTemplate.enhance_operational_alignment,
            ]

        for _ in range(self.max_retries):
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
        return "Goal Redirection"
