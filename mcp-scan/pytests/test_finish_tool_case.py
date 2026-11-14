"""Finish aliases must terminate the real Agent loop after the first response."""

import pytest
from mcp_scan.agent.base_agent import BaseAgent
from mcp_scan.tools.dispatcher import ToolDispatcher
from mcp_scan.tools.registry import get_tool_by_name


class ModelReplies:
    """Supply deterministic model text; no provider or scan target is contacted."""

    context_window = 128000

    def __init__(self, first_name: str):
        self.calls = 0
        self.first_name = first_name

    def chat(self, messages, p=False, ret_usage=False, language="en"):
        name = self.first_name if self.calls == 0 else "finish"
        self.calls += 1
        response = (
            "Report: completed synthetic task\n"
            f"<function={name}><parameter=content>done</parameter></function>"
        )
        return (response, {"prompt_tokens": 10}) if ret_usage else response

    async def chat_async(self, messages, language="en"):
        return self.chat(messages, language=language)


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["finish", "Finish", "FINISH", "fInIsH", "finish_later"])
async def test_finish_name_case_terminates_agent(tool_name: str):
    assert get_tool_by_name("FINISH") is get_tool_by_name("finish")
    assert get_tool_by_name("finish") is not None
    model = ModelReplies(tool_name)
    agent = BaseAgent(
        "fixture",
        "Return the supplied result.",
        model,
        log_step_id="fixture",
        language="en",
        dispatcher=ToolDispatcher(),
        output_check_fn=lambda s: s.startswith("Report:"),
    )
    agent.max_iter = 3

    result = await agent.run()

    expected_calls = 2 if tool_name == "finish_later" else 1
    assert model.calls == expected_calls
    assert agent.iter == expected_calls
    assert agent.is_finished
    assert result.startswith("Report: completed synthetic task")
