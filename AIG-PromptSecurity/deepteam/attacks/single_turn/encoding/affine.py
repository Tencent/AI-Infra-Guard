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

class AffineCipher(BaseAttack):
    def __init__(self, weight: int = 1, a: int = 5, b: int = 8, m: int = 26):
        self.weight = weight
        self.a = a
        self.b = b
        self.m = m

    def enhance(self, attack: str) -> str:
        """Encrypt text using Affine Cipher"""
        result = []
        for c in attack:
            code = ord(c)
            if 65 <= code <= 90:  # Uppercase letters
                encrypted = (self.a * (code - 65) + self.b) % self.m
                result.append(chr(65 + encrypted))
            elif 97 <= code <= 122:  # Lowercase letters
                encrypted = (self.a * (code - 97) + self.b) % self.m
                result.append(chr(97 + encrypted))
            else:
                result.append(c)
        return ''.join(result)
