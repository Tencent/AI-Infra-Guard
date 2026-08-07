import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

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


def test_redteam_requests_omit_temperature():
    async def exercise_requests():
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

    for create in asyncio.run(exercise_requests()):
        assert create.call_count == 1
        assert "temperature" not in create.call_args.kwargs
