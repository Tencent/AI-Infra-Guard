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

import ahocorasick
import random
import json
from pathlib import Path
from deepteam.attacks import BaseAttack

class Homomorphic(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Homomorphic transformation."""
        # Load homomorphic mapping
        json_path = Path(__file__).resolve().parent / "homomorphic.json"
        with open(json_path, "r", encoding="utf-8") as f:
            homomorphic_map = json.load(f)
        
        # Build AC automaton
        automaton = ahocorasick.Automaton()
        for word, homomorphs in homomorphic_map.items():
            # Store (original word, homomorph list)
            automaton.add_word(word, (word, homomorphs))
        automaton.make_automaton()
        
        # Perform replacement
        last_end = 0
        result = []
        for end_index, (word, homomorphs) in automaton.iter(attack):
            start_index = end_index - len(word) + 1
            # Add unmatched part
            result.append(attack[last_end:start_index])
            # Add random homomorphic character
            result.append(random.choice(homomorphs))
            last_end = end_index + 1
        
        result.append(attack[last_end:])
        return "".join(result)

    def get_name(self) -> str:
        return "Homomorphic"
