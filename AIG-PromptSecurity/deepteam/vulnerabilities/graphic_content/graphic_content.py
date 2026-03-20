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
from deepteam.vulnerabilities.graphic_content import GraphicContentType
from deepteam.vulnerabilities.utils import validate_vulnerability_types

GraphicContentLiteral = Literal[
    "sexual content", "graphic content", "pornographic content"
]


class GraphicContent(BaseVulnerability):
    def __init__(
        self,
        types: Optional[List[GraphicContentLiteral]] = [
            type.value for type in GraphicContentType
        ],
    ):
        enum_types = validate_vulnerability_types(
            self.get_name(), types=types, allowed_type=GraphicContentType
        )
        super().__init__(types=enum_types)

    def get_name(self) -> str:
        return "Graphic Content"
