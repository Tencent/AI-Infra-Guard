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

class ChemicalSymbols(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.map = {
            'a': 'Ac', 'b': 'B', 'c': 'C', 'd': 'D', 'e': 'Es', 'f': 'F', 'g': 'Ge', 'h': 'H', 'i': 'I',
            'j': 'J', 'k': 'K', 'l': 'L', 'm': 'Mn', 'n': 'N', 'o': 'O', 'p': 'P', 'q': 'Q', 'r': 'R',
            's': 'S', 't': 'Ti', 'u': 'U', 'v': 'V', 'w': 'W', 'x': 'Xe', 'y': 'Y', 'z': 'Zn',
            'A': 'AC', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'ES', 'F': 'F', 'G': 'GE', 'H': 'H', 'I': 'I',
            'J': 'J', 'K': 'K', 'L': 'L', 'M': 'MN', 'N': 'N', 'O': 'O', 'P': 'P', 'Q': 'Q', 'R': 'R',
            'S': 'S', 'T': 'TI', 'U': 'U', 'V': 'V', 'W': 'W', 'X': 'XE', 'Y': 'Y', 'Z': 'ZN'
        }

    def enhance(self, attack: str) -> str:
        result = []
        for c in attack:
            if c.lower() in self.map:
                # Use appropriate case mapping
                if c.isupper():
                    result.append(self.map.get(c, self.map[c.lower()].upper()))
                else:
                    result.append(self.map[c.lower()])
            else:
                result.append(c)
        return ''.join(result)
