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

import re

class CamelCase(BaseAttack):
    def __init__(self, weight: int = 1):
        self.weight = weight

    def enhance(self, attack: str) -> str:
        """Convert text to camelCase"""
        # Split into words (handling all non-alphanumeric characters as separators)
        parts = re.split(r'[^a-zA-Z0-9]+', attack)
        parts = [part for part in parts if part]  # Filter out empty strings
        
        if not parts:
            return ''
        
        # First word in lowercase
        first = parts[0].lower()
        
        # Subsequent words capitalized
        rest = ''.join(
            word[0].upper() + word[1:].lower() if word else ''
            for word in parts[1:]
        )
        
        return first + rest
