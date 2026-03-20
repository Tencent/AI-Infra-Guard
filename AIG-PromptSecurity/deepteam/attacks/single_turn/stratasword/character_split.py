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
from pathlib import Path
from deepteam.attacks import BaseAttack
from deepteam.attacks.single_turn.stratasword.template import (
    StrataSwordTemplate,
)

class CharacterSplit(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        json_path = Path(__file__).resolve().parent / "chaizi.json"
        with open(json_path, "r", encoding="utf-8") as f:
            rad_map = json.load(f)
        chunks = []
        for char in attack:
            rad = rad_map.get(char, None)
            chunk = char
            if rad:
                chunk += f"({rad[0]})"
            chunks.append(chunk)
        
        prompt = StrataSwordTemplate.generate_character_split(chunks)
        return prompt