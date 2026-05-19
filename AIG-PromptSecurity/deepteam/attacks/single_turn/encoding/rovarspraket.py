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
import re

class Rovarspraket(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def _is_consonant(self, c: str) -> bool:
        """Check if a character is a consonant (case-insensitive)"""
        return bool(re.match(r'[bcdfghjklmnpqrstvwxyz]', c, re.IGNORECASE))

    def enhance(self, attack: str) -> str:
        """Convert text to Rövarspråket by doubling consonants with 'o' in between"""
        result = []
        for ch in attack:
            if self._is_consonant(ch):
                result.append(f"{ch}o{ch.lower()}")  # Second consonant in lowercase
            else:
                result.append(ch)
        return ''.join(result)
