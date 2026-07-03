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
LLM Manager - manages multiple specialized LLM instances.
"""

from __future__ import annotations

from skill_scan.utils import config
from skill_scan.utils.llm import LLM
from skill_scan.utils.loging import logger


class LLMManager:
    """Manages multiple specialized LLM instances, supporting model configuration per purpose."""

    DEFAULT_CONFIGS = {
        "default": {
            "model": config.DEFAULT_MODEL,
            "base_url": config.DEFAULT_BASE_URL,
            "context_window": config.DEFAULT_MODEL_CONTEXT_WINDOW,
            "description": "Default model",
        },
        "thinking": {
            "model": config.THINKING_MODEL,
            "base_url": config.THINKING_BASE_URL,
            "api_key": config.THINKING_API_KEY,
            "context_window": config.THINKING_MODEL_CONTEXT_WINDOW,
            "description": "Model dedicated to deep thinking and reasoning",
        },
        "coding": {
            "model": config.CODING_MODEL,
            "base_url": config.CODING_BASE_URL,
            "api_key": config.CODING_API_KEY,
            "context_window": config.CODING_MODEL_CONTEXT_WINDOW,
            "description": "Model dedicated to code generation and analysis",
        },
        "fast": {
            "model": config.FAST_MODEL,
            "base_url": config.FAST_BASE_URL,
            "api_key": config.FAST_API_KEY,
            "context_window": config.FAST_MODEL_CONTEXT_WINDOW,
            "description": "Lightweight model for fast responses",
        },
    }

    def __init__(self, api_key: str, base_url: str = None):
        self.default_api_key = api_key
        self.default_base_url = base_url or config.DEFAULT_BASE_URL
        self._llm_instances: dict[str, LLM] = {}
        self._custom_configs: dict[str, dict] = {}

    def configure(
        self,
        purpose: str,
        model: str,
        temperature: float = 0.7,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._custom_configs[purpose] = {
            "model": model,
            "temperature": temperature,
            "base_url": base_url,
            "api_key": api_key,
        }
        if purpose in self._llm_instances:
            del self._llm_instances[purpose]
        logger.info(f"Configured LLM for purpose '{purpose}': {model}")

    def get_llm(self, purpose: str = "default") -> LLM | None:
        if purpose in self._llm_instances:
            return self._llm_instances[purpose]

        llm_config = None
        if purpose in self._custom_configs:
            llm_config = self._custom_configs[purpose].copy()
        elif purpose in self.DEFAULT_CONFIGS:
            llm_config = self.DEFAULT_CONFIGS[purpose].copy()
            if "temperature" not in llm_config:
                llm_config["temperature"] = 0.7

        if llm_config is None:
            logger.warning(f"No configuration found for purpose '{purpose}'")
            return None

        api_key = llm_config.get("api_key") or self.default_api_key
        base_url = llm_config.get("base_url") or self.default_base_url
        context_window = llm_config.get("context_window")

        try:
            llm = LLM(
                model=llm_config["model"],
                api_key=api_key,
                base_url=base_url,
                context_window=context_window,
            )
            llm.temperature = llm_config.get("temperature", 0.7)
            self._llm_instances[purpose] = llm
            logger.info(
                f"Created LLM instance for purpose '{purpose}': {llm_config['model']} @ {base_url}"
            )
            return llm
        except Exception as e:
            logger.error(f"Failed to create LLM for purpose '{purpose}': {e}")
            return None

    def get_specialized_llms(self, purposes: list[str] = None) -> dict[str, LLM]:
        if purposes is None:
            purposes = list(
                set(list(self._custom_configs.keys()) + list(self.DEFAULT_CONFIGS.keys()))
            )

        result = {}
        for purpose in purposes:
            llm = self.get_llm(purpose)
            if llm:
                result[purpose] = llm
        return result
