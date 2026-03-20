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

import os
import re
from datetime import datetime
from utils.config import base_dir


class PromptManager:
    _instance = None
    _templates = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
        return cls._instance

    def load_template(self, name: str) -> str:
        if name not in self._templates:
            path = os.path.join(base_dir, "prompt", "system", f"{name}.md")

            if not os.path.exists(path):
                raise FileNotFoundError(f"Prompt template '{name}' not found.")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            content = self._strip_frontmatter(content)
            self._templates[name] = content

        return self._templates[name]

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter (---...---) from template content."""
        frontmatter_pattern = r'^---\s*\n.*?\n---\s*\n'
        content = re.sub(frontmatter_pattern, '', content, count=1, flags=re.DOTALL)
        return content.strip()

    def format_prompt(self, template_name: str, **kwargs) -> str:
        template = self.load_template(template_name)
        if "${NOWTIME}" in template:
            kwargs.setdefault("NOWTIME", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        formatted = template
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            if placeholder in formatted:
                formatted = formatted.replace(placeholder, str(value))
            alt_placeholder = "${" + key + "}"
            if alt_placeholder in formatted:
                formatted = formatted.replace(alt_placeholder, str(value))

        return formatted


prompt_manager = PromptManager()
