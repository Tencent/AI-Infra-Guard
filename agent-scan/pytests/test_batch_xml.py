"""Exercise the batch tool through the scanner's XML-to-dispatch path."""

import html
import json

import pytest

from agent_scan.tools.batch.batch import batch
from agent_scan.tools.dispatcher import ToolDispatcher
from agent_scan.utils.parse import parse_tool_invocations


@pytest.mark.asyncio
@pytest.mark.parametrize("parameter_tag", ["parameter=tool_calls", 'parameter name="tool_calls"'])
async def test_batch_executes_array_from_xml(parameter_tag):
    calls = [{"tool": "think", "parameters": {"thought": "Check A & B, 中文"}}]
    payload = html.escape(json.dumps(calls, ensure_ascii=False))
    invocation = parse_tool_invocations(
        f"<function=batch><{parameter_tag}>{payload}</parameter></function>"
    )
    assert invocation is not None
    result = await ToolDispatcher().call_tool(invocation["toolName"], invocation["args"])
    assert "<success>True</success>" in result
    assert "Check A & B, 中文" in result
    assert "'total_calls': 1" in result
    assert "'successful': 1" in result


@pytest.mark.asyncio
async def test_batch_still_accepts_native_array():
    result = await batch([{"tool": "think", "parameters": {"thought": "control"}}])
    assert result["success"] is True
    assert result["metadata"]["details"][0]["result"]["thought"] == "control"


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["[invalid", '{"tool": "think"}', '"think"', "null", "[]"])
async def test_batch_rejects_invalid_or_empty_array(payload):
    result = await batch(payload)
    assert result["success"] is False
    assert result["error"]


@pytest.mark.asyncio
async def test_batch_enforces_limits_after_decoding():
    calls = [{"tool": "think", "parameters": {"thought": str(i)}} for i in range(11)]
    result = await batch(json.dumps(calls))
    assert result["success"] is False
    assert result["metadata"]["successful"] == 10
    assert result["metadata"]["failed"] == 1
    assert len(result["metadata"]["details"]) == 11


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", ["batch", "finish"])
async def test_batch_rejects_disallowed_tools_after_decoding(tool):
    result = await batch(json.dumps([{"tool": tool, "parameters": {}}]))
    assert result["success"] is False
    assert result["metadata"]["details"][0]["tool"] == tool
    assert "not allowed" in result["metadata"]["details"][0]["error"]
