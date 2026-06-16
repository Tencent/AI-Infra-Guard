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

from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.flip_attack.template import SYSTEM_PROMPT, MODE_PROMPT


class FlipAttack(BaseAttack):
    """Flip-character prompt wrapper with system-style instruction block."""

    def __init__(self, weight: int = 1, cot: bool = False):
        self.weight = weight
        self.cot = cot

    def enhance(self, attack: str) -> str:
        cot_prompt = "by providing the solution step by step " if self.cot else ""
        system_prompt = SYSTEM_PROMPT.format(
            mode_prompt=MODE_PROMPT,
            cot_prompt=cot_prompt,
        )
        disguised_prompt = attack[::-1]
        user_prompt = "TASK is '{}'".format(disguised_prompt)
        return "\n".join(
            [
                "system:\n" + system_prompt,
                "user:\n" + user_prompt,
            ]
        )

    def get_name(self) -> str:
        return "Flip Attack"
