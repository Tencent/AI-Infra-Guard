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

class Katakana(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight
        self.table = [
            ['kyo','キョ'],['kyu','キュ'],['kya','キャ'],
            ['sho','ショ'],['shu','シュ'],['sha','シャ'],['shi','シ'],
            ['cho','チョ'],['chu','チュ'],['cha','チャ'],['chi','チ'],
            ['tsu','ツ'],['fu','フ'],
            ['ryo','リョ'],['ryu','リュ'],['rya','リャ'],
            ['nyo','ニョ'],['nyu','ニュ'],['nya','ニャ'],
            ['gya','ギャ'],['gyu','ギュ'],['gyo','ギョ'],
            ['hya','ヒャ'],['hyu','ヒュ'],['hyo','ヒョ'],
            ['mya','ミャ'],['myu','ミュ'],['myo','ミョ'],
            ['pya','ピャ'],['pyu','ピュ'],['pyo','ピョ'],
            ['bya','ビャ'],['byu','ビュ'],['byo','ビョ'],
            ['ja','ジャ'],['ju','ジュ'],['jo','ジョ'],
            ['ka','カ'],['ki','キ'],['ku','ク'],['ke','ケ'],['ko','コ'],
            ['ga','ガ'],['gi','ギ'],['gu','グ'],['ge','ゲ'],['go','ゴ'],
            ['sa','サ'],['su','ス'],['se','セ'],['so','ソ'],
            ['za','ザ'],['zu','ズ'],['ze','ゼ'],['zo','ゾ'],
            ['ta','タ'],['te','テ'],['to','ト'],
            ['da','ダ'],['de','デ'],['do','ド'],
            ['na','ナ'],['ni','ニ'],['nu','ヌ'],['ne','ネ'],['no','ノ'],
            ['ha','ハ'],['hi','ヒ'],['he','ヘ'],['ho','ホ'],
            ['ba','バ'],['bi','ビ'],['bu','ブ'],['be','ベ'],['bo','ボ'],
            ['pa','パ'],['pi','ピ'],['pu','プ'],['pe','ペ'],['po','ポ'],
            ['ma','マ'],['mi','ミ'],['mu','ム'],['me','メ'],['mo','モ'],
            ['ra','ラ'],['ri','リ'],['ru','ル'],['re','レ'],['ro','ロ'],
            ['wa','ワ'],['wo','ヲ'],['n','ン'],
            ['a','ア'],['i','イ'],['u','ウ'],['e','エ'],['o','オ']
        ]
        # Sort table by length descending for proper matching
        self.sorted_table = sorted(self.table, key=lambda x: -len(x[0]))

    def enhance(self, attack: str) -> str:
        """Convert romaji to katakana"""
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
