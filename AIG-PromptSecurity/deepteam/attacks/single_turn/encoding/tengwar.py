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

class TengwarScript(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.map = {
            'a': 'ᚪ', 'b': 'ᛒ', 'c': 'ᛣ', 'd': 'ᛞ', 'e': 'ᛖ', 'f': 'ᚠ', 'g': 'ᚷ', 'h': 'ᚺ', 'i': 'ᛁ',
            'j': 'ᛃ', 'k': 'ᛣ', 'l': 'ᛚ', 'm': 'ᛗ', 'n': 'ᚾ', 'o': 'ᚩ', 'p': 'ᛈ', 'q': 'ᛩ', 'r': 'ᚱ',
            's': 'ᛋ', 't': 'ᛏ', 'u': 'ᚢ', 'v': 'ᚡ', 'w': 'ᚹ', 'x': 'ᛉ', 'y': 'ᚣ', 'z': 'ᛉ',
            'A': 'ᚪ', 'B': 'ᛒ', 'C': 'ᛣ', 'D': 'ᛞ', 'E': 'ᛖ', 'F': 'ᚠ', 'G': 'ᚷ', 'H': 'ᚺ', 'I': 'ᛁ',
            'J': 'ᛃ', 'K': 'ᛣ', 'L': 'ᛚ', 'M': 'ᛗ', 'N': 'ᚾ', 'O': 'ᚩ', 'P': 'ᛈ', 'Q': 'ᛩ', 'R': 'ᚱ',
            'S': 'ᛋ', 'T': 'ᛏ', 'U': 'ᚢ', 'V': 'ᚡ', 'W': 'ᚹ', 'X': 'ᛉ', 'Y': 'ᚣ', 'Z': 'ᛉ'
        }

    def enhance(self, attack: str) -> str:
        return ''.join(self.map.get(c.lower(), c) for c in attack)
