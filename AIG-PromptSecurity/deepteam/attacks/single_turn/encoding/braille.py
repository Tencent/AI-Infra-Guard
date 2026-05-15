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

class Braille(BaseAttack):

    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Enhance the attack using Braille encoding."""
        characterUnicodes = {
            "a": "\u2801",
            "b": "\u2803",
            "k": "\u2805",
            "l": "\u2807",
            "c": "\u2809",
            "i": "\u280A",
            "f": "\u280B",
            "m": "\u280D",
            "s": "\u280E",
            "p": "\u280F",
            "e": "\u2811",
            "h": "\u2813",
            "o": "\u2815",
            "r": "\u2817",
            "d": "\u2819",
            "j": "\u281A",
            "g": "\u281B",
            "n": "\u281D",
            "t": "\u281E",
            "q": "\u281F",
            "u": "\u2825",
            "v": "\u2827",
            "x": "\u282D",
            "z": "\u2835",
            "w": "\u283A",
            "y": "\u283D",
            "num": "\u283C",
            "caps": "\u2820",
            ".": "\u2832",
            "'": "\u2804",
            ",": "\u2802",
            "-": "\u2824",
            "/": "\u280C",
            "!": "\u2816",
            "?": "\u2826",
            "$": "\u2832",
            ":": "\u2812",
            ";": "\u2830",
            "(": "\u2836",
            ")": "\u2836",
            "1": "\u2801",
            "2": "\u2803",
            "3": "\u2809",
            "4": "\u2819",
            "5": "\u2811",
            "6": "\u280B",
            "7": "\u281B",
            "8": "\u2813",
            "9": "\u280A",
            "0": "\u281A",
            " ": " ",
        }
        numberPunctuations = [".", ",", "-", "/", "$"]
        escapeCharacters = ["\n", "\r", "\t"]

        output = ""

        for char in attack:
            is_number = False
            if char in escapeCharacters:
                output += char
            elif char.isupper():
                if char.lower() in characterUnicodes:
                    output += characterUnicodes["caps"]
                    output += characterUnicodes[char.lower()]
            elif char in characterUnicodes:
                if char.isdigit():
                    if not is_number:
                        is_number = True
                        output += characterUnicodes["num"]
                output += characterUnicodes[char]
            if is_number and char not in numberPunctuations:
                is_number = False

        return output

    def get_name(self) -> str:
        return "Braille"
