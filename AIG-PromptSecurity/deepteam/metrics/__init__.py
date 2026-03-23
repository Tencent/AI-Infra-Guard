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

from .base_red_teaming_metric import BaseRedTeamingMetric

from .contracts.contracts import ContractsMetric
from .debug_access.debug_access import DebugAccessMetric
from .excessive_agency.excessive_agency import ExcessiveAgencyMetric
from .hallucination.hallucination import HallucinationMetric
from .harm.harm import HarmMetric
from .imitation.imitation import ImitationMetric
from .pii.pii import PIIMetric
from .rbac.rbac import RBACMetric
from .shell_injection.shell_injection import ShellInjectionMetric
from .sql_injection.sql_injection import SQLInjectionMetric
from .bias.bias import BiasMetric
from .bfla.bfla import BFLAMetric
from .bola.bola import BOLAMetric
from .competitors.competitors import CompetitorsMetric
from .overreliance.overreliance import OverrelianceMetric
from .prompt_extraction.prompt_extraction import PromptExtractionMetric
from .ssrf.ssrf import SSRFMetric
from .hijacking.hijacking import HijackingMetric
from .intellectual_property.intellectual_property import (
    IntellectualPropertyMetric,
)
from .toxicity.toxicity import ToxicityMetric
from .misinformation.misinformation import MisinformationMetric
from .illegal_activity.illegal_activity import IllegalMetric
from .graphic_content.graphic_content import GraphicMetric
from .personal_safety.personal_safety import SafetyMetric
from .random_metric.random_metric import RandomMetric
from .is_jailbreak import JailbreakMetric
