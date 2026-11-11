import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mcp_scan.redteam.attacker import AttackerAgent
from mcp_scan.redteam.evaluator import EvaluatorAgent
from mcp_scan.redteam.strategy import ConversationTurn
from mcp_scan.redteam.target import TargetRunner


def _client_with_response(content: str):
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    return client, create


async def _exercise_requests():
    attacker_client, attacker_create = _client_with_response(
        '{"thought":"","message":"test","attack_technique":"test","reflection":""}'
    )
    evaluator_client, evaluator_create = _client_with_response(
        '{"on_topic":true,"score":1,"is_successful":false,"reasoning":""}'
    )
    target_client, target_create = _client_with_response("target response")

    await AttackerAgent(attacker_client, "gpt-5.5").generate_attack("test", [])
    await EvaluatorAgent(evaluator_client, "gpt-5.5").evaluate(
        "test", ConversationTurn("attack", "response")
    )
    await TargetRunner(target_client, "gpt-5.5").respond_to_attack("test")
    return attacker_create, evaluator_create, target_create


def test_redteam_requests_omit_temperature():
    for create in asyncio.run(_exercise_requests()):
        assert create.call_count == 1
        assert "temperature" not in create.call_args.kwargs


@pytest.mark.parametrize(
    ("setting", "expected"),
    [("high", "high"), (" medium ", "medium"), (None, None), ("", None), (" \t ", None)],
)
def test_redteam_requests_use_optional_reasoning_effort(monkeypatch, setting, expected):
    if setting is None:
        monkeypatch.delenv("REASONING_EFFORT", raising=False)
    else:
        monkeypatch.setenv("REASONING_EFFORT", setting)

    for create in asyncio.run(_exercise_requests()):
        assert create.call_count == 1
        if expected is None:
            assert "reasoning_effort" not in create.call_args.kwargs
        else:
            assert create.call_args.kwargs["reasoning_effort"] == expected
