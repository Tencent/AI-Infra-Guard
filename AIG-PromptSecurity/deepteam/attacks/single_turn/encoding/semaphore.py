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

class SemaphoreFlags(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.arrows = ['','⬆️','↗️','➡️','↘️','⬇️','↙️','⬅️','↖️']
        self.table = {
            'A':[1,2],'B':[1,3],'C':[1,4],'D':[1,5],'E':[1,6],'F':[1,7],'G':[1,8],
            'H':[2,3],'I':[2,4],'J':[2,1],
            'K':[2,5],'L':[2,6],'M':[2,7],'N':[2,8],
            'O':[3,4],'P':[3,5],'Q':[3,6],'R':[3,7],'S':[3,8],
            'T':[4,5],'U':[4,6],'V':[4,7],'W':[4,8],
            'X':[5,6],'Y':[5,7],'Z':[5,8]
        }

    def encode_pair(self, pair):
        return self.arrows[pair[0]] + self.arrows[pair[1]]

    def enhance(self, attack: str) -> str:
        result = []
        for ch in attack:
            if ch.isspace():
                result.append('/')
                continue
            
            up = ch.upper()
            pair = self.table.get(up)
            if pair:
                result.append(self.encode_pair(pair))
            else:
                result.append(ch)
        return ' '.join(result)
