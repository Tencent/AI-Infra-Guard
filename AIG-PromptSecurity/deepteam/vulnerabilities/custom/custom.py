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

from typing import List, Optional

from deepteam.vulnerabilities import BaseVulnerability
from deepteam.vulnerabilities.custom.custom_types import CustomVulnerabilityType
from deepteam.metrics import BaseRedTeamingMetric


class CustomVulnerability(BaseVulnerability):
    """
    Custom vulnerability class that allows users to define their own vulnerability types.
    """

    def __init__(
        self,
        name: str,
        types: Optional[List[str]] = None,
        custom_prompt: Optional[str] = None,
        metric: Optional[BaseRedTeamingMetric] = None,
    ):
        self.name = name
        self.types = types
        self.raw_types = types or []
        self.custom_prompt = custom_prompt
        self.metric = metric
        super().__init__(self.types)

    def get_name(self) -> str:
        return self.name

    def get_custom_prompt(self) -> Optional[str]:
        return self.custom_prompt

    def get_metric(self) -> Optional[BaseRedTeamingMetric]:
        return self.metric

    def get_raw_types(self) -> List[str]:
        return self.raw_types
