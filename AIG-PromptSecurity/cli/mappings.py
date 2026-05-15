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

# 支持的scenarios和techniques映射
TECHNIQUE_CLASS_MAP = {
    "A1Z26": "deepteam.attacks.single_turn.A1Z26",
    "ASCII85": "deepteam.attacks.single_turn.ASCII85",
    "AcrosticPoem": "deepteam.attacks.single_turn.AcrosticPoem",
    "AffineCipher": "deepteam.attacks.single_turn.AffineCipher",
    "AlternatingCase": "deepteam.attacks.single_turn.AlternatingCase",
    "AsciiDrawing": "deepteam.attacks.single_turn.AsciiDrawing",
    "AsciiSmuggling": "deepteam.attacks.single_turn.AsciiSmuggling",
    "AtbashCipher": "deepteam.attacks.single_turn.AtbashCipher",
    "Aurebesh": "deepteam.attacks.single_turn.Aurebesh",
    "BaconianCipher": "deepteam.attacks.single_turn.BaconianCipher",
    "BaseEncoding": "deepteam.attacks.single_turn.BaseEncoding",
    "Binary": "deepteam.attacks.single_turn.Binary",
    "Braille": "deepteam.attacks.single_turn.Braille",
    "Bubble": "deepteam.attacks.single_turn.Bubble",
    "CaesarCipher": "deepteam.attacks.single_turn.CaesarCipher",
    "CamelCase": "deepteam.attacks.single_turn.CamelCase",
    "CharacterSplit": "deepteam.attacks.single_turn.CharacterSplit",
    "ChemicalSymbols": "deepteam.attacks.single_turn.ChemicalSymbols",
    "CodeAttack": "deepteam.attacks.single_turn.CodeAttack",
    "ContextPoisoning": "deepteam.attacks.single_turn.ContextPoisoning",
    "Contradictory": "deepteam.attacks.single_turn.Contradictory",
    "Cursive": "deepteam.attacks.single_turn.Cursive",
    "CyrillicStylized": "deepteam.attacks.single_turn.CyrillicStylized",
    "DRAttack": "deepteam.attacks.single_turn.DRAttack",
    "Disemvowel": "deepteam.attacks.single_turn.Disemvowel",
    "DoubleStruck": "deepteam.attacks.single_turn.DoubleStruck",
    "Dovahzul": "deepteam.attacks.single_turn.Dovahzul",
    "Ecoji": "deepteam.attacks.single_turn.Ecoji",
    "ElderFuthark": "deepteam.attacks.single_turn.ElderFuthark",
    "Emoji": "deepteam.attacks.single_turn.Emoji",
    "EquaCode": "deepteam.attacks.single_turn.EquaCode",
    "Fraktur": "deepteam.attacks.single_turn.Fraktur",
    "FullWidth": "deepteam.attacks.single_turn.FullWidth",
    "GoalRedirection": "deepteam.attacks.single_turn.GoalRedirection",
    "GrayBox": "deepteam.attacks.single_turn.GrayBox",
    "GreekLetters": "deepteam.attacks.single_turn.GreekLetters",
    "HTMLEntities": "deepteam.attacks.single_turn.HTMLEntities",
    "Hex": "deepteam.attacks.single_turn.Hex",
    "Hieroglyphics": "deepteam.attacks.single_turn.Hieroglyphics",
    "Hiragana": "deepteam.attacks.single_turn.Hiragana",
    "Homomorphic": "deepteam.attacks.single_turn.Homomorphic",
    "ICRTJailbreak": "deepteam.attacks.single_turn.ICRTJailbreak",
    "InputBypass": "deepteam.attacks.single_turn.InputBypass",
    "InvisibleText": "deepteam.attacks.single_turn.InvisibleText",
    "Katakana": "deepteam.attacks.single_turn.Katakana",
    "KebabCase": "deepteam.attacks.single_turn.KebabCase",
    "Klingon": "deepteam.attacks.single_turn.Klingon",
    "LanternRiddle": "deepteam.attacks.single_turn.LanternRiddle",
    "Leetspeak": "deepteam.attacks.single_turn.Leetspeak",
    "LinguisticConfusion": "deepteam.attacks.single_turn.LinguisticConfusion",
    "LongText": "deepteam.attacks.single_turn.LongText",
    "MathProblem": "deepteam.attacks.single_turn.MathProblem",
    "MathematicalNotation": "deepteam.attacks.single_turn.MathematicalNotation",
    "Medieval": "deepteam.attacks.single_turn.Medieval",
    "MirrorText": "deepteam.attacks.single_turn.MirrorText",
    "Monospace": "deepteam.attacks.single_turn.Monospace",
    "Morse": "deepteam.attacks.single_turn.Morse",
    "Multilingual": "deepteam.attacks.single_turn.Multilingual",
    "Nato": "deepteam.attacks.single_turn.Nato",
    "Ogham": "deepteam.attacks.single_turn.Ogham",
    "Opposing": "deepteam.attacks.single_turn.Opposing",
    "PROMISQROUTE": "deepteam.attacks.single_turn.PROMISQROUTE",
    "PermissionEscalation": "deepteam.attacks.single_turn.PermissionEscalation",
    "PigLatin": "deepteam.attacks.single_turn.PigLatin",
    "PromptInjection": "deepteam.attacks.single_turn.PromptInjection",
    "PromptProbing": "deepteam.attacks.single_turn.PromptProbing",
    "Quenya": "deepteam.attacks.single_turn.Quenya",
    "QwertyShift": "deepteam.attacks.single_turn.QwertyShift",
    "ROTEncoding": "deepteam.attacks.single_turn.ROTEncoding",
    "RailFence": "deepteam.attacks.single_turn.RailFence",
    "RandomCase": "deepteam.attacks.single_turn.RandomCase",
    "Raw": "deepteam.attacks.single_turn.Raw",
    "RegionalIndicator": "deepteam.attacks.single_turn.RegionalIndicator",
    "ReverseWords": "deepteam.attacks.single_turn.ReverseWords",
    "Roleplay": "deepteam.attacks.single_turn.Roleplay",
    "RomanNumerals": "deepteam.attacks.single_turn.RomanNumerals",
    "Rovarspraket": "deepteam.attacks.single_turn.Rovarspraket",
    "ScriptTemplate": "deepteam.attacks.single_turn.ScriptTemplate",
    "SemaphoreFlags": "deepteam.attacks.single_turn.SemaphoreFlags",
    "SentenceCase": "deepteam.attacks.single_turn.SentenceCase",
    "Shuffle": "deepteam.attacks.single_turn.Shuffle",
    "SmallCaps": "deepteam.attacks.single_turn.SmallCaps",
    "SnakeCase": "deepteam.attacks.single_turn.SnakeCase",
    "Stego": "deepteam.attacks.single_turn.Stego",
    "Strikethrough": "deepteam.attacks.single_turn.Strikethrough",
    "Subscript": "deepteam.attacks.single_turn.Subscript",
    "SuperUser": "deepteam.attacks.single_turn.SuperUser",
    "Superscript": "deepteam.attacks.single_turn.Superscript",
    "SystemOverride": "deepteam.attacks.single_turn.SystemOverride",
    "TapCode": "deepteam.attacks.single_turn.TapCode",
    "TengwarScript": "deepteam.attacks.single_turn.TengwarScript",
    "TitleCase": "deepteam.attacks.single_turn.TitleCase",
    "URLEncode": "deepteam.attacks.single_turn.URLEncode",
    "UbbiDubbi": "deepteam.attacks.single_turn.UbbiDubbi",
    "Underline": "deepteam.attacks.single_turn.Underline",
    "UpsideDown": "deepteam.attacks.single_turn.UpsideDown",
    "Vaporwave": "deepteam.attacks.single_turn.Vaporwave",
    "VigenereCipher": "deepteam.attacks.single_turn.VigenereCipher",
    "Wingdings": "deepteam.attacks.single_turn.Wingdings",
    "Zalgo": "deepteam.attacks.single_turn.Zalgo",
    "Zerowidth": "deepteam.attacks.single_turn.Zerowidth",
    "BadLikertJudge": "deepteam.attacks.multi_turn.BadLikertJudge",
    "BestofN": "deepteam.attacks.multi_turn.BestofN",
    "CrescendoJailbreaking": "deepteam.attacks.multi_turn.CrescendoJailbreaking",
    "LinearJailbreaking": "deepteam.attacks.multi_turn.LinearJailbreaking",
    "SequentialJailbreak": "deepteam.attacks.multi_turn.SequentialJailbreak",
    "TreeJailbreaking": "deepteam.attacks.multi_turn.TreeJailbreaking"
}

SCENARIO_CLASS_MAP = {
    "Bias": "deepteam.vulnerabilities.Bias",
    "Competition": "deepteam.vulnerabilities.Competition",
    "ExcessiveAgency": "deepteam.vulnerabilities.ExcessiveAgency",
    "GraphicContent": "deepteam.vulnerabilities.GraphicContent",
    "IllegalActivity": "deepteam.vulnerabilities.IllegalActivity",
    "IntellectualProperty": "deepteam.vulnerabilities.IntellectualProperty",
    "Misinformation": "deepteam.vulnerabilities.Misinformation",
    "PIILeakage": "deepteam.vulnerabilities.PIILeakage",
    "PersonalSafety": "deepteam.vulnerabilities.PersonalSafety",
    "PromptLeakage": "deepteam.vulnerabilities.PromptLeakage",
    "Robustness": "deepteam.vulnerabilities.Robustness",
    "Toxicity": "deepteam.vulnerabilities.Toxicity",
    "UnauthorizedAccess": "deepteam.vulnerabilities.UnauthorizedAccess"
}

# 支持的自定义metric映射
METRIC_CLASS_MAP = {
    'RandomMetric': 'deepteam.metrics.RandomMetric',
    'JailbreakMetric': 'deepteam.metrics.JailbreakMetric'
} 
