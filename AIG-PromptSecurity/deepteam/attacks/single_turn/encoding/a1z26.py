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

class A1Z26(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        result = []
        for c in attack:
            if c.isalpha():
                # Convert character to its position in alphabet (A=1, B=2, etc.)
                num = ord(c.upper()) - 64
                result.append(f"{num}-")
            else:
                result.append(c)
        
        # Join and clean up hyphens
        encoded = ''.join(result)
        encoded = re.sub(r'-+(?!\d)', '-', encoded)  # Remove multiple hyphens not followed by digits
        encoded = re.sub(r'-+$', '', encoded)        # Remove trailing hyphens
        return encoded
