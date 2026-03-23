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

import re
import random
from deepteam.attacks import BaseAttack

from deepteam.utils import judge_language

class Shuffle(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        parts = re.split(r'([,.!?;:，。！？；：])', attack)
        
        # 遍历每个部分，打乱非标点的内容
        for i in range(len(parts)):
            part = parts[i]
            if not re.match(r'^[,.!?;:，。！？；：]$', part):  # 如果不是标点
                if judge_language(part) == "chinese":
                    words = list(part)
                    random.shuffle(words)
                    parts[i] = "".join(words)
                else:
                    words = part.split()
                    random.shuffle(words)
                    parts[i] = " ".join(words)
        
        # 重新组合结果
        prompt = ''.join(parts)
        return prompt