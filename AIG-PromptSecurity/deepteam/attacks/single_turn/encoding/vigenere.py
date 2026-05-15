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

class VigenereCipher(BaseAttack):
    def __init__(self, weight: int = 1, key: str = 'KEY'):
        self.weight = weight
        self.key = key.upper()

    def enhance(self, attack: str) -> str:
        result = []
        key_index = 0
        
        for c in attack:
            code = ord(c)
            if 65 <= code <= 90:  # Uppercase letters
                k = ord(self.key[key_index % len(self.key)]) - 65
                shifted = 65 + ((code - 65 + k) % 26)
                result.append(chr(shifted))
                key_index += 1
            elif 97 <= code <= 122:  # Lowercase letters
                k = ord(self.key[key_index % len(self.key)]) - 65
                shifted = 97 + ((code - 97 + k) % 26)
                result.append(chr(shifted))
                key_index += 1
            else:
                result.append(c)
        
        return ''.join(result)
