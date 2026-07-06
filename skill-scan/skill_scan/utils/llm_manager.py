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

"""
LLM Manager - manages a single default LLM instance.
"""

from __future__ import annotations

from skill_scan.utils import config
from skill_scan.utils.llm import LLM
from skill_scan.utils.loging import logger


class LLMManager:
    """Manages a single default LLM instance."""

    DEFAULT_CONFIGS = {
        "default": {
            "model": config.DEFAULT_MODEL,
            "base_url": config.DEFAULT_BASE_URL,
            "context_window": config.DEFAULT_MODEL_CONTEXT_WINDOW,
            "description": "Default model",
        },
    }

    def __init__(self, api_key: str, base_url: str = None):
        self.default_api_key = api_key
        self.default_base_url = base_url or config.DEFAULT_BASE_URL
        self._llm_instances: dict[str, LLM] = {}

    def get_llm(self, purpose: str = "default") -> LLM | None:
        if purpose in self._llm_instances:
            return self._llm_instances[purpose]

        llm_config = self.DEFAULT_CONFIGS.get("default")
        if llm_config is None:
            logger.warning("No default configuration found")
            return None

        api_key = self.default_api_key
        base_url = self.default_base_url

        try:
            llm = LLM(
                model=llm_config["model"],
                api_key=api_key,
                base_url=base_url,
                context_window=llm_config.get("context_window"),
            )
            self._llm_instances["default"] = llm
            logger.info(
                f"Created LLM instance: {llm_config['model']} @ {base_url}"
            )
            return llm
        except Exception as e:
            logger.error(f"Failed to create LLM: {e}")
            return None
