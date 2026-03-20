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

from typing import List, Literal, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.personal_safety import PersonalSafetyType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

PersonalSafetyLiteral = Literal[
    "bullying",
    "self-harm",
    "unsafe practices",
    "dangerous challenges",
    "stalking",
]


class PersonalSafety(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[PersonalSafetyLiteral]] = [
            type.value for type in PersonalSafetyType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=PersonalSafetyType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Personal Safety"
