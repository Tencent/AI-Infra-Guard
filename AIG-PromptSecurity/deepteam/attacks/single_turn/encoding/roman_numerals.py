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

class RomanNumerals(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.numerals = [
            ['M',1000],['CM',900],['D',500],['CD',400],
            ['C',100],['XC',90],['L',50],['XL',40],
            ['X',10],['IX',9],['V',5],['IV',4],['I',1]
        ]

    def _int_to_roman(self, num: int) -> str:
        if num <= 0 or num > 3999:
            return str(num)
        out = []
        for sym, val in self.numerals:
            while num >= val:
                out.append(sym)
                num -= val
        return ''.join(out)

    def enhance(self, attack: str) -> str:
        def replace_match(match):
            try:
                num = int(match.group())
                return self._int_to_roman(num)
            except ValueError:
                return match.group()
        
        return re.sub(r'\b\d+\b', replace_match, attack)
