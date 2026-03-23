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

class CaesarCipher(BaseAttack):
    def __init__(self, weight: int = 1, shift: int = 3):
        self.weight = weight
        self.shift = shift  # Traditional Caesar shift is 3

    def enhance(self, attack: str) -> str:
        result = []
        for c in attack:
            code = ord(c)
            # Only shift letters, leave other characters unchanged
            if 65 <= code <= 90:  # Uppercase letters
                shifted = ((code - 65 + self.shift) % 26) + 65
                result.append(chr(shifted))
            elif 97 <= code <= 122:  # Lowercase letters
                shifted = ((code - 97 + self.shift) % 26) + 97
                result.append(chr(shifted))
            else:
                result.append(c)
        return ''.join(result)