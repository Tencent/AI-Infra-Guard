from types import SimpleNamespace
from unittest.mock import Mock

from agent_scan.utils.llm import LLM


def test_chat_request_omits_temperature():
    create = Mock(return_value=[])
    llm = object.__new__(LLM)
    llm.model = "gpt-5.5"
    llm.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    assert list(llm.chat_stream([{"role": "user", "content": "test"}])) == []
    assert create.call_count == 1
    assert "temperature" not in create.call_args.kwargs
