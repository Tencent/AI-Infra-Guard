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

class TapCode(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.letters = 'ABCDEFGHIKLMNOPQRSTUVWXYZ'  # No J
        self._map = None
        self.build_map()

    def build_map(self):
        """Build the tap code coordinate mappings"""
        if self._map is not None:
            return self._map

        self._map = {}
        
        for i, char in enumerate(self.letters):
            row = (i // 5) + 1
            col = (i % 5) + 1
            self._map[char] = (row, col)
            
        return self._map

    def enhance(self, attack: str) -> str:
        """Encode text into tap code"""
        self.build_map()
        out = []
        
        for ch in attack.upper():
            if ch == 'J':  # Common convention: J -> I
                row, col = self._map['I']
                out.append('.' * row + ' ' + '.' * col)
                continue
                
            if ch in self._map:
                row, col = self._map[ch]
                out.append('.' * row + ' ' + '.' * col)
            elif ch.isspace():
                out.append('/')
            else:
                out.append(ch)
                
        return ' '.join(out)
