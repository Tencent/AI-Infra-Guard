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

from .context_poisoning import ContextPoisoning
from .encoding import *
from .equa_code import EquaCode
from .goal_redirection import GoalRedirection
from .gray_box import GrayBox
from .icrt_jailbreak import ICRTJailbreak
from .input_bypass import InputBypass
from .math_problem import MathProblem
from .multilingual import Multilingual
from .permission_escalation import PermissionEscalation
from .promisqroute import PROMISQROUTE
from .prompt_injection import PromptInjection
from .prompt_probing import PromptProbing
from .raw import Raw
from .roleplay import Roleplay
from .semantic_manipulation import LinguisticConfusion
from .stego import Stego
from .stratasword import *
from .super_user import SuperUser
from .system_override import SystemOverride
