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

class Hiragana(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.table = [
            ['kyo','きょ'],['kyu','きゅ'],['kya','きゃ'],
            ['sho','しょ'],['shu','しゅ'],['sha','しゃ'],['shi','し'],
            ['cho','ちょ'],['chu','ちゅ'],['cha','ちゃ'],['chi','ち'],
            ['tsu','つ'],['fu','ふ'],
            ['ryo','りょ'],['ryu','りゅ'],['rya','りゃ'],
            ['nyo','にょ'],['nyu','にゅ'],['nya','にゃ'],
            ['gya','ぎゃ'],['gyu','ぎゅ'],['gyo','ぎょ'],
            ['hya','ひゃ'],['hyu','ひゅ'],['hyo','ひょ'],
            ['mya','みゃ'],['myu','みゅ'],['myo','みょ'],
            ['pya','ぴゃ'],['pyu','ぴゅ'],['pyo','ぴょ'],
            ['bya','びゃ'],['byu','びゅ'],['byo','びょ'],
            ['ja','じゃ'],['ju','じゅ'],['jo','じょ'],
            ['ka','か'],['ki','き'],['ku','く'],['ke','け'],['ko','こ'],
            ['ga','が'],['gi','ぎ'],['gu','ぐ'],['ge','げ'],['go','ご'],
            ['sa','さ'],['su','す'],['se','せ'],['so','そ'],
            ['za','ざ'],['zu','ず'],['ze','ぜ'],['zo','ぞ'],
            ['ta','た'],['te','て'],['to','と'],
            ['da','だ'],['de','で'],['do','ど'],
            ['na','な'],['ni','に'],['nu','ぬ'],['ne','ね'],['no','の'],
            ['ha','は'],['hi','ひ'],['he','へ'],['ho','ほ'],
            ['ba','ば'],['bi','び'],['bu','ぶ'],['be','べ'],['bo','ぼ'],
            ['pa','ぱ'],['pi','ぴ'],['pu','ぷ'],['pe','ぺ'],['po','ぽ'],
            ['ma','ま'],['mi','み'],['mu','む'],['me','め'],['mo','も'],
            ['ra','ら'],['ri','り'],['ru','る'],['re','れ'],['ro','ろ'],
            ['wa','わ'],['wo','を'],['n','ん'],
            ['a','あ'],['i','い'],['u','う'],['e','え'],['o','お']
        ]
        # Sort table by length descending for proper matching
        self.sorted_table = sorted(self.table, key=lambda x: -len(x[0]))

    def enhance(self, attack: str) -> str:
        """Convert romaji to hiragana"""
        lower_text = attack.lower()
        i = 0
        result = []
        
        while i < len(lower_text):
            matched = False
            for rom, kana in self.sorted_table:
                if lower_text.startswith(rom, i):
                    result.append(kana)
                    i += len(rom)
                    matched = True
                    break
            if not matched:
                result.append(attack[i])  # Preserve original case
                i += 1
                
        return ''.join(result)
