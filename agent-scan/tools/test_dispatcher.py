import pytest
from tools.dispatcher import ToolDispatcher


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
