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

class Dovahzul(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.map = {
            'a': 'ah', 'b': 'b', 'c': 'k', 'd': 'd', 'e': 'eh', 'f': 'f', 'g': 'g', 'h': 'h', 'i': 'ii',
            'j': 'j', 'k': 'k', 'l': 'l', 'm': 'm', 'n': 'n', 'o': 'o', 'p': 'p', 'q': 'kw', 'r': 'r',
            's': 's', 't': 't', 'u': 'u', 'v': 'v', 'w': 'w', 'x': 'ks', 'y': 'y', 'z': 'z',
            'A': 'AH', 'B': 'B', 'C': 'K', 'D': 'D', 'E': 'EH', 'F': 'F', 'G': 'G', 'H': 'H', 'I': 'II',
            'J': 'J', 'K': 'K', 'L': 'L', 'M': 'M', 'N': 'N', 'O': 'O', 'P': 'P', 'Q': 'KW', 'R': 'R',
            'S': 'S', 'T': 'T', 'U': 'U', 'V': 'V', 'W': 'W', 'X': 'KS', 'Y': 'Y', 'Z': 'Z'
        }

    def enhance(self, attack: str) -> str:
        result = []
        for c in attack:
            if c.lower() in self.map:
                # Use the appropriate case mapping
                if c.isupper():
                    result.append(self.map.get(c, self.map[c.lower()].upper()))
                else:
                    result.append(self.map[c.lower()])
            else:
                result.append(c)
        return ''.join(result)
