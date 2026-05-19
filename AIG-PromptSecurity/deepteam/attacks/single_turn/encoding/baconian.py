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

class BaconianCipher(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.table = self._create_bacon_table()

    def _create_bacon_table(self):
        """Generate Baconian cipher lookup table"""
        bacon_table = {}
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for i in range(26):
            # Convert index to 5-bit binary, then replace 0 with A and 1 with B
            binary = format(i, '05b')
            code = binary.replace('0', 'A').replace('1', 'B')
            bacon_table[alphabet[i]] = code
        return bacon_table

    def enhance(self, attack: str) -> str:
        """Encode text into Baconian cipher"""
        result = []
        for ch in attack.upper():
            if ch in self.table:
                result.append(self.table[ch])
            elif ch.isspace():
                result.append('/')
            else:
                result.append(ch)
        return ' '.join(result)
