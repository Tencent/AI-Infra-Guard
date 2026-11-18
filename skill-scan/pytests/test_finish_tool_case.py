"""A finish call written in any letter case must end the agent loop."""

import pytest

from skill_scan.agent.base_agent import BaseAgent
from skill_scan.tools.dispatcher import ToolDispatcher

REPORT = "<report>no issues found</report>"


class ModelReplies:
    """Return a scripted finish call; no provider is contacted."""

    context_window = 128000

    def __init__(self, first_name: str):
        self.first_name = first_name
        self.calls = 0

    def chat(self, messages, p=False, ret_usage=False, language="zh"):
        name = self.first_name if self.calls == 0 else "finish"
        self.calls += 1
        response = (
            f"Audit complete.\n<function={name}><parameter=content>{REPORT}</parameter></function>"
        )
        return (response, {"prompt_tokens": 10}) if ret_usage else response


def _agent(model: ModelReplies) -> BaseAgent:
    agent = BaseAgent(
        "fixture",
        "Return the supplied result.",
        model,
        ToolDispatcher(),
        log_step_id="fixture",
        output_check_fn=lambda text: REPORT in text,
        language="en",
    )
    agent.max_iter = 5
    return agent


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", ["finish", "Finish", "FINISH", "fInIsH"])
async def test_finish_name_case_terminates_agent(tool_name: str):
    model = ModelReplies(tool_name)
    agent = _agent(model)

    result = await agent.run()

    assert model.calls == 1
    assert agent.iter == 1
    assert agent.is_finished
    assert result == REPORT


@pytest.mark.asyncio
async def test_mixed_case_finish_is_deferred_after_exploration_calls(tmp_path):
    (tmp_path / "SKILL.md").write_text("skill body", encoding="utf-8")
    agent = _agent(ModelReplies("finish"))
    agent.set_repo_dir(str(tmp_path))
    await agent.initialize()

    response = (
        f"<function=read_file><parameter=file_path>{tmp_path / 'SKILL.md'}</parameter></function>"
        f"<function=Finish><parameter=content>{REPORT}</parameter></function>"
    )
    agent.history.append({"role": "assistant", "content": response})

    assert await agent.handle_response(response) is None
    assert not agent.is_finished
    follow_up = agent.history[-1]["content"]
    assert "skill body" in follow_up
    assert "finish call was deferred" in follow_up
