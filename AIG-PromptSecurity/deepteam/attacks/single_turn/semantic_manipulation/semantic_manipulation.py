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
from deepteam.attacks.single_turn.semantic_manipulation.template import (
    LinguisticConfusionTemplate,
)
from deepteam.utils import judge_language

class LinguisticConfusion(BaseAttack):
    def __init__(self, weight: int = 1, max_retries: int = 3):
        self.weight = weight
        self.max_retries = max_retries

    def enhance(self, attack: str) -> str:
        """
        Enhance the given attack with linguistic confusion techniques.
        Uses max_retries to attempt different confusion methods if enhancement fails.
        """
        if judge_language(attack) == "chinese":
            enhancement_methods = [
                LinguisticConfusionTemplate.enhance_semantic_ambiguity_zh,
                LinguisticConfusionTemplate.enhance_syntactic_variation_zh,
                LinguisticConfusionTemplate.enhance_contextual_reframing_zh,
                LinguisticConfusionTemplate.enhance_obfuscation_decoding_zh,
                LinguisticConfusionTemplate.enhance_pragmatic_inference_zh,
                LinguisticConfusionTemplate.enhance_universal_translation_zh,
            ]
        else:
            enhancement_methods = [
                LinguisticConfusionTemplate.enhance_semantic_ambiguity,
                LinguisticConfusionTemplate.enhance_syntactic_variation,
                LinguisticConfusionTemplate.enhance_contextual_reframing,
                LinguisticConfusionTemplate.enhance_obfuscation_decoding,
                LinguisticConfusionTemplate.enhance_pragmatic_inference,
                LinguisticConfusionTemplate.enhance_universal_translation,
            ]

        for attempt in range(self.max_retries):
            try:
                method = random.choice(enhancement_methods)
                enhanced_attack = method(attack)
                if enhanced_attack and len(enhanced_attack.strip()) > len(
                    attack.strip()
                ):
                    return enhanced_attack

            except Exception:
                continue

        return attack

    def get_name(self) -> str:
        return "Linguistic Confusion"
