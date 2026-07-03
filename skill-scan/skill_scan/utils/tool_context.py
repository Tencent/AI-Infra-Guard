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
Tool execution context - provides the environment information tools need to run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from skill_scan.tools.dispatcher import ToolDispatcher
from skill_scan.utils.llm import LLM


class ToolContext:
    """Tool execution context, including history, LLM instance, and other info."""

    def __init__(
        self,
        llm: LLM,
        history: list[dict[str, str]],
        agent_name: str = "Agent",
        iteration: int = 0,
        specialized_llms: dict[str, LLM] | None = None,
        folder: str | None = None,
        tool_dispatcher: Optional["ToolDispatcher"] = None,
    ):
        self.llm = llm
        self.history = history
        self.agent_name = agent_name
        self.iteration = iteration
        self.specialized_llms = specialized_llms or {}
        self.folder = folder
        self.tool_dispatcher = tool_dispatcher

    def get_llm(self, purpose: str = "default") -> LLM:
        if purpose in self.specialized_llms:
            return self.specialized_llms[purpose]
        return self.llm

    def get_recent_history(self, n: int = 5) -> list[dict[str, str]]:
        return self.history[-n:] if len(self.history) > n else self.history

    def call_llm(
        self,
        prompt: str,
        purpose: str = "default",
        system_prompt: str | None = None,
        use_history: bool = False,
    ) -> str:
        llm = self.get_llm(purpose)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if use_history:
            messages.extend(self.history[1:])
        messages.append({"role": "user", "content": prompt})
        return llm.chat(messages)

    def call_llm_messages(self, messages, purpose: str = "default") -> str:
        llm = self.get_llm(purpose)
        return llm.chat(messages)
