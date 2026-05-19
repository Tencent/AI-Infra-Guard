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

class Fraktur(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.cap_map = {
            'A': 0x1D504, 'B': 0x1D505, 'C': 0x212D, 'D': 0x1D507, 'E': 0x1D508, 'F': 0x1D509, 'G': 0x1D50A,
            'H': 0x210C, 'I': 0x2111, 'J': 0x1D50D, 'K': 0x1D50E, 'L': 0x1D50F, 'M': 0x1D510, 'N': 0x1D511,
            'O': 0x1D512, 'P': 0x1D513, 'Q': 0x1D514, 'R': 0x211C, 'S': 0x1D516, 'T': 0x1D517, 'U': 0x1D518,
            'V': 0x1D519, 'W': 0x1D51A, 'X': 0x1D51B, 'Y': 0x1D51C, 'Z': 0x2128
        }
        self.lower_base = 0x1D51E  # 'a' in Fraktur

    def enhance(self, attack: str) -> str:
        """Convert text to Fraktur characters"""
        result = []
        for c in attack:
            code = ord(c)
            if 'A' <= c <= 'Z':
                fraktur_code = self.cap_map.get(c, code)
                result.append(chr(fraktur_code))
            elif 'a' <= c <= 'z':
                fraktur_char = chr(self.lower_base + (code - ord('a')))
                result.append(fraktur_char)
            else:
                result.append(c)
        return ''.join(result)
