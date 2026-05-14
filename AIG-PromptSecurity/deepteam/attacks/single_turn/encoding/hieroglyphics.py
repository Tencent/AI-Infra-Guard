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

class Hieroglyphics(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.map = {
            'a': '𓃭', 'b': '𓃮', 'c': '𓃯', 'd': '𓃰', 'e': '𓃱', 'f': '𓃲', 'g': '𓃳', 'h': '𓃴', 'i': '𓃵',
            'j': '𓃶', 'k': '𓃷', 'l': '𓃸', 'm': '𓃹', 'n': '𓃺', 'o': '𓃻', 'p': '𓃼', 'q': '𓃽', 'r': '𓃾',
            's': '𓃿', 't': '𓄀', 'u': '𓄁', 'v': '𓄂', 'w': '𓄃', 'x': '𓄄', 'y': '𓄅', 'z': '𓄆',
            'A': '𓄇', 'B': '𓄈', 'C': '𓄉', 'D': '𓄊', 'E': '𓄋', 'F': '𓄌', 'G': '𓄍', 'H': '𓄎', 'I': '𓄏',
            'J': '𓄐', 'K': '𓄑', 'L': '𓄒', 'M': '𓄓', 'N': '𓄔', 'O': '𓄕', 'P': '𓄖', 'Q': '𓄗', 'R': '𓄘',
            'S': '𓄙', 'T': '𓄚', 'U': '𓄛', 'V': '𓄜', 'W': '𓄝', 'X': '𓄞', 'Y': '𓄟', 'Z': '𓄠'
        }

    def enhance(self, attack: str) -> str:
        return ''.join(self.map.get(c.lower(), c) for c in attack)
