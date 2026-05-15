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

class QwertyShift(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.rows = [
            'qwertyuiop',
            'asdfghjkl',
            'zxcvbnm'
        ]
        self._map = None

    def _build_map(self):
        """Build the QWERTY right shift mapping"""
        if self._map is not None:
            return self._map

        self._map = {}
        for row in self.rows:
            for i in range(len(row)):
                from_char = row[i]
                to_char = row[(i + 1) % len(row)]
                self._map[from_char] = to_char
                self._map[from_char.upper()] = to_char.upper()
        return self._map

    def enhance(self, attack: str) -> str:
        """Shift each character one position to the right on QWERTY keyboard"""
        mapping = self._build_map()
        result = []
        for c in attack:
            result.append(mapping.get(c, c))
        return ''.join(result)
