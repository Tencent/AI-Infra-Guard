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

from enum import Enum
from typing import Dict

from deepteam.vulnerabilities.types import *


class LLMRiskCategories(Enum):
    RESPONSIBLE_AI = "Responsible AI"
    ILLEGAL = "Illegal"
    BRAND_IMAGE = "Brand Image"
    DATA_PRIVACY = "Data Privacy"
    UNAUTHORIZED_ACCESS = "Unauthorized Access"


def getRiskCategory(
    vulnerability_type: VulnerabilityType,
) -> LLMRiskCategories:
    risk_category_map: Dict[VulnerabilityType, LLMRiskCategories] = {
        # Responsible AI
        **{bias: LLMRiskCategories.RESPONSIBLE_AI for bias in BiasType},
        **{
            toxicity: LLMRiskCategories.RESPONSIBLE_AI
            for toxicity in ToxicityType
        },
        # Illegal
        **{
            illegal: LLMRiskCategories.ILLEGAL
            for illegal in IllegalActivityType
        },
        **{
            graphic: LLMRiskCategories.ILLEGAL for graphic in GraphicContentType
        },
        **{safety: LLMRiskCategories.ILLEGAL for safety in PersonalSafetyType},
        # Brand Image
        **{
            misinfo: LLMRiskCategories.BRAND_IMAGE
            for misinfo in MisinformationType
        },
        **{
            agency: LLMRiskCategories.BRAND_IMAGE
            for agency in ExcessiveAgencyType
        },
        **{robust: LLMRiskCategories.BRAND_IMAGE for robust in RobustnessType},
        **{
            ip: LLMRiskCategories.BRAND_IMAGE for ip in IntellectualPropertyType
        },
        **{comp: LLMRiskCategories.BRAND_IMAGE for comp in CompetitionType},
        # Data Privacy
        **{
            prompt: LLMRiskCategories.DATA_PRIVACY
            for prompt in PromptLeakageType
        },
        **{pii: LLMRiskCategories.DATA_PRIVACY for pii in PIILeakageType},
        # Unauthorized Access
        **{
            unauth: LLMRiskCategories.UNAUTHORIZED_ACCESS
            for unauth in UnauthorizedAccessType
        },
    }

    return risk_category_map.get(
        vulnerability_type, "Others"
    )  # Returns None if not found
