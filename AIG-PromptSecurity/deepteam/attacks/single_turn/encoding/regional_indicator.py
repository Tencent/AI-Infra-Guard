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

class RegionalIndicator(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.base = 0x1F1E6  # Unicode base for regional indicator symbols

    def enhance(self, attack: str) -> str:
        """Convert letters to regional indicator symbols"""
        result = []
        for c in attack:
            upper_c = c.upper()
            if 'A' <= upper_c <= 'Z':
                # Calculate regional indicator code point
                code_point = self.base + (ord(upper_c) - ord('A'))
                result.append(chr(code_point))
            else:
                result.append(c)
        return ''.join(result)
