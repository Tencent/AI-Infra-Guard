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

class RailFence(BaseAttack):
    def __init__(self, weight: int = 1, rails: int = 3):
        self.weight = weight
        self.rails = rails

    def enhance(self, attack: str) -> str:
        rails = [[] for _ in range(self.rails)]
        rail = 0
        direction = 1  # 1 for down, -1 for up
        
        for char in attack:
            rails[rail].append(char)
            rail += direction
            if rail == 0 or rail == self.rails - 1:
                direction *= -1
        
        # Flatten the rails
        return ''.join([char for rail in rails for char in rail])
