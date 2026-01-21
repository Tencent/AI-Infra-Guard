import pytest

from core.agent_adapter.adapter import AIProviderClient
from tools.dispatcher import ToolDispatcher
from utils.tool_context import ToolContext


@pytest.fixture
def dispatcher():
    return ToolDispatcher()


@pytest.mark.asyncio
async def test_get_all_tools_prompt(dispatcher):
    result = await dispatcher.get_all_tools_prompt()  # 异步函数需要 await
    print(result)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_call_tool_search_skill(dispatcher):
    result = await dispatcher.call_tool("search_skill", {"query": ""}, None)
    print(result)


@pytest.mark.asyncio
async def test_call_tool_load_skill(dispatcher):
    result = await dispatcher.call_tool("load_skill", {"name": "agent-security-review"}, None)
    print(result)


@pytest.mark.asyncio
async def test_call_tool_dialogue(dispatcher):
    client = AIProviderClient()
    agent_provider = client.load_config_from_file("demo_dify.yaml")[0]
    context = ToolContext(
        agent_provider=agent_provider,
    )
    result = await dispatcher.call_tool("dialogue", {
        "prompt": "你好你有什么技能"
    }, context)
    print(result)


@pytest.mark.asyncio
async def test_call_list_agents(dispatcher):
    result = await dispatcher.call_tool("list_agents", {}, None)
    print(result)


@pytest.mark.asyncio
async def test_call_run_task(dispatcher):
    client = AIProviderClient()
    agent_provider = client.load_config_from_file("demo_dify.yaml")[0]
    context = ToolContext(
        agent_provider=agent_provider,
    )

    result = await dispatcher.call_tool("task", {
        "prompt": "检测信息泄漏",
        "subagent_type": "data_leakage_detection",
        "description": "检测agent的敏感信息泄漏"
    }, None)
    print(result)
