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

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core.base_agent as base_agent_module
import utils.llm as llm_module
from core.base_agent import BaseAgent
from utils.llm import LLM, LLM_ERROR_PREFIX


class DummyConnectionError(Exception):
    pass


class DummyTimeoutError(Exception):
    pass


class DummyAPIError(Exception):
    pass


class DummyBadRequestError(Exception):
    pass


@pytest.fixture
def llm(monkeypatch):
    monkeypatch.setattr(llm_module.openai, "OpenAI", lambda **kwargs: object())
    monkeypatch.setattr(llm_module.openai, "APIConnectionError", DummyConnectionError)
    monkeypatch.setattr(llm_module.openai, "APITimeoutError", DummyTimeoutError)
    monkeypatch.setattr(llm_module.openai, "APIError", DummyAPIError)
    monkeypatch.setattr(llm_module.openai, "BadRequestError", DummyBadRequestError)
    return LLM(model="test-model", api_key="test-key", base_url="https://example.com")


def test_chat_resets_buffer_before_retry(monkeypatch, llm):
    attempts = {"count": 0}

    def fake_chat_stream(_message):
        attempts["count"] += 1
        if attempts["count"] == 1:
            yield "partial"
            raise DummyConnectionError("connection dropped")
        yield "full"

    monkeypatch.setattr(llm, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(llm_module.time, "sleep", lambda _seconds: None)

    assert llm.chat([]) == "full"


def test_chat_returns_prefixed_error_for_empty_responses(monkeypatch, llm):
    monkeypatch.setattr(llm, "chat_stream", lambda _message: iter(()))
    monkeypatch.setattr(llm_module.time, "sleep", lambda _seconds: None)

    response = llm.chat([], language="en")

    assert response.startswith(LLM_ERROR_PREFIX)


@pytest.mark.asyncio
async def test_compact_history_skips_on_llm_error(monkeypatch):
    class DummyLLM:
        async def chat_async(self, _history, language="zh"):
            return f"{LLM_ERROR_PREFIX} compact failed]"

    agent = BaseAgent.__new__(BaseAgent)
    agent.llm = DummyLLM()
    agent.language = "en"
    agent.history = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "original task"},
        {"role": "assistant", "content": "intermediate context"},
    ]

    original_history = list(agent.history)
    monkeypatch.setattr(base_agent_module.prompt_manager, "load_template", lambda _name: "compact prompt")

    assert await BaseAgent.compact_history(agent) is False
    assert agent.history == original_history


@pytest.mark.asyncio
async def test_format_final_output_falls_back_to_last_assistant(monkeypatch):
    class DummyLLM:
        async def chat_async(self, _history, language="zh"):
            return f"{LLM_ERROR_PREFIX} format failed]"

    agent = BaseAgent.__new__(BaseAgent)
    agent.llm = DummyLLM()
    agent.language = "en"
    agent.instruction = "format output"
    agent.history = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "original task"},
        {"role": "assistant", "content": "final report content"},
    ]

    monkeypatch.setattr(base_agent_module.prompt_manager, "format_prompt", lambda *_args, **_kwargs: "format prompt")

    assert await BaseAgent._format_final_output(agent) == "final report content"
