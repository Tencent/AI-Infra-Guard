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
    "AcrosticPoem": "deepteam.attacks.single_turn.AcrosticPoem",
    "AffineCipher": "deepteam.attacks.single_turn.AffineCipher",
    "AsciiSmuggling": "deepteam.attacks.single_turn.AsciiSmuggling",
    "Aurebesh": "deepteam.attacks.single_turn.Aurebesh",
    "CaesarCipher": "deepteam.attacks.single_turn.CaesarCipher",
    "DRAttack": "deepteam.attacks.single_turn.DRAttack",
    "Leetspeak": "deepteam.attacks.single_turn.Leetspeak",
    "MirrorText": "deepteam.attacks.single_turn.MirrorText",
    "Ogham": "deepteam.attacks.single_turn.Ogham",
    "Raw": "deepteam.attacks.single_turn.Raw",
    "Stego": "deepteam.attacks.single_turn.Stego",
    "Vaporwave": "deepteam.attacks.single_turn.Vaporwave",
    "Zalgo": "deepteam.attacks.single_turn.Zalgo",
}

SCENARIO_CLASS_MAP = {
    "Bias": "deepteam.vulnerabilities.Bias",
    "Toxicity": "deepteam.vulnerabilities.Toxicity",
    "Misinformation": "deepteam.vulnerabilities.Misinformation",
    "IllegalActivity": "deepteam.vulnerabilities.IllegalActivity",
    "PromptLeakage": "deepteam.vulnerabilities.PromptLeakage",
    "PIILeakage": "deepteam.vulnerabilities.PIILeakage",
    "UnauthorizedAccess": "deepteam.vulnerabilities.UnauthorizedAccess",
    "ExcessiveAgency": "deepteam.vulnerabilities.ExcessiveAgency",
    "Robustness": "deepteam.vulnerabilities.Robustness",
    "IntellectualProperty": "deepteam.vulnerabilities.IntellectualProperty",
    "Competition": "deepteam.vulnerabilities.Competition",
    "GraphicContent": "deepteam.vulnerabilities.GraphicContent",
    "PersonalSafety": "deepteam.vulnerabilities.PersonalSafety",
    "Custom": "deepteam.vulnerabilities.CustomVulnerability",
    "CustomPrompt": "deepteam.vulnerabilities.CustomPrompt",
    "MultiDataset": "deepteam.vulnerabilities.MultiDatasetVulnerability",
}

# 支持的自定义metric映射
METRIC_CLASS_MAP = {
    'RandomMetric': 'deepteam.metrics.RandomMetric',
    'JailbreakMetric': 'deepteam.metrics.JailbreakMetric'
} 
