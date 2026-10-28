import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch

from mcp.types import (
    AudioContent,
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    InputRequiredResult,
    ResourceLink,
    TextContent,
    TextResourceContents,
)

from mcp_scan.agent.base_agent import BaseAgent
from mcp_scan.tools.dispatcher import ToolDispatcher
from mcp_scan.utils.mcp_tools import MCPTools


class _Context:
    def __init__(self, value=None):
        self.value = value
        self.exited = False

    async def __aenter__(self):
        return self.value if self.value is not None else self

    async def __aexit__(self, *_args):
        self.exited = True


class _Session(_Context):
    instances = []

    def __init__(self, read, write, read_timeout_seconds=None):
        super().__init__()
        self.read = read
        self.write = write
        self.read_timeout_seconds = read_timeout_seconds
        self.initialized = False
        self.__class__.instances.append(self)

    async def initialize(self):
        self.initialized = True


class MCP20TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        _Session.instances.clear()

    async def test_streamable_http_uses_managed_mcp_client_and_float_timeout(self):
        captured = {}
        http_client = _Context()

        def fake_create_mcp_http_client(headers=None):
            captured["headers"] = headers
            return http_client

        @asynccontextmanager
        async def fake_streamable_http_client(url, *, http_client=None, terminate_on_close=True):
            captured.update(url=url, http_client=http_client)
            yield ("read", "write")

        with (
            patch(
                "mcp_scan.utils.mcp_tools.create_mcp_http_client",
                fake_create_mcp_http_client,
            ),
            patch(
                "mcp_scan.utils.mcp_tools.streamable_http_client",
                fake_streamable_http_client,
            ),
            patch("mcp_scan.utils.mcp_tools.ClientSession", _Session),
        ):
            manager = MCPTools(
                "https://example.test/mcp",
                "streamable-http",
                headers={"Authorization": "Bearer test"},
            )
            manager.timeout_seconds = 7
            async with manager._session():
                pass

        self.assertEqual(captured["headers"], {"Authorization": "Bearer test"})
        self.assertIs(captured["http_client"], http_client)
        self.assertTrue(http_client.exited)
        self.assertEqual(_Session.instances[0].read_timeout_seconds, 7.0)
        self.assertTrue(_Session.instances[0].initialized)

    async def test_sse_still_receives_headers(self):
        captured = {}

        @asynccontextmanager
        async def fake_sse_client(url, headers=None):
            captured.update(url=url, headers=headers)
            yield ("read", "write")

        with (
            patch("mcp_scan.utils.mcp_tools.sse_client", fake_sse_client),
            patch("mcp_scan.utils.mcp_tools.ClientSession", _Session),
        ):
            manager = MCPTools("https://example.test/sse", "sse", headers={"X-Key": "test"})
            async with manager._session():
                pass

        self.assertEqual(captured["headers"], {"X-Key": "test"})

    async def _call_remote_tool_with_result(self, result):
        class _ToolResultSession:
            async def call_tool(self, _tool_name, _arguments):
                return result

        manager = MCPTools("https://example.test/mcp", "streamable-http")

        @asynccontextmanager
        async def fake_session():
            yield _ToolResultSession()

        manager._session = fake_session
        return await manager.call_remote_tool("inspect", value="test")

    async def test_call_remote_tool_keeps_single_text_block_shape(self):
        result = CallToolResult(content=[TextContent(type="text", text="single result")])

        actual = await self._call_remote_tool_with_result(result)

        self.assertEqual(actual, "single result")

    async def test_call_remote_tool_keeps_single_image_data_shape(self):
        result = CallToolResult(
            content=[ImageContent(type="image", data="aGVsbG8=", mime_type="image/png")]
        )

        actual = await self._call_remote_tool_with_result(result)

        self.assertEqual(actual, "aGVsbG8=")

    async def test_call_remote_tool_preserves_multiple_text_blocks(self):
        result = CallToolResult(
            content=[
                TextContent(type="text", text="first: harmless status"),
                TextContent(type="text", text="second: security evidence"),
            ]
        )

        actual = await self._call_remote_tool_with_result(result)

        self.assertLess(
            actual.index("first: harmless status"), actual.index("second: security evidence")
        )
        self.assertIn("[content[0] text]", actual)
        self.assertIn("[content[1] text]", actual)

    async def test_call_remote_tool_keeps_text_after_image_block(self):
        result = CallToolResult(
            content=[
                ImageContent(type="image", data="aGVsbG8=", mime_type="image/png"),
                TextContent(type="text", text="text after image"),
            ]
        )

        actual = await self._call_remote_tool_with_result(result)

        self.assertIn("image/png", actual)
        self.assertIn("text after image", actual)

    async def test_call_remote_tool_preserves_structured_content_without_blocks(self):
        result = CallToolResult(content=[], structured_content={"finding": "structured evidence"})

        actual = await self._call_remote_tool_with_result(result)

        self.assertIn("structured evidence", actual)

    async def test_call_remote_tool_marks_errors_and_preserves_metadata(self):
        result = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="tool failure detail",
                    meta={"block_source": "remote"},
                    annotations={"priority": 0.7},
                )
            ],
            meta={"trace_id": "trace-123"},
            is_error=True,
        )

        actual = await self._call_remote_tool_with_result(result)

        self.assertIn("isError=true", actual)
        self.assertIn("tool failure detail", actual)
        self.assertIn("block_source", actual)
        self.assertIn("priority", actual)
        self.assertIn("trace_id", actual)

    async def test_call_remote_tool_preserves_explicit_null_structured_content(self):
        result = CallToolResult(content=[], structured_content=None)

        actual = await self._call_remote_tool_with_result(result)

        self.assertEqual(actual, "[structuredContent]\nnull")

    async def test_call_remote_tool_returns_empty_string_for_empty_success(self):
        result = CallToolResult(content=[])

        actual = await self._call_remote_tool_with_result(result)

        self.assertEqual(actual, "")

    async def test_call_remote_tool_rejects_input_required_result_explicitly(self):
        result = InputRequiredResult(request_state="pending")

        with self.assertRaisesRegex(
            RuntimeError, "Unsupported MCP tool result type: InputRequiredResult"
        ):
            await self._call_remote_tool_with_result(result)

    async def test_call_remote_tool_serializes_audio_and_resource_blocks(self):
        result = CallToolResult(
            content=[
                AudioContent(type="audio", data="YXVkaW8=", mime_type="audio/wav"),
                ResourceLink(
                    type="resource_link",
                    name="risk report",
                    uri="mcp://server/report",
                    description="resource metadata evidence",
                ),
                EmbeddedResource(
                    type="resource",
                    resource=TextResourceContents(
                        uri="mcp://server/evidence",
                        mime_type="text/plain",
                        text="embedded evidence",
                    ),
                ),
            ]
        )

        actual = await self._call_remote_tool_with_result(result)

        self.assertIn("audio/wav", actual)
        self.assertIn("resource metadata evidence", actual)
        self.assertIn("embedded evidence", actual)

    async def test_call_remote_tool_keeps_late_text_in_large_result_history(self):
        result = CallToolResult(
            content=[
                ImageContent(type="image", data="A" * 50_000, mime_type="image/png"),
                TextContent(type="text", text="LATE SECURITY EVIDENCE"),
            ]
        )
        tool_result = await self._call_remote_tool_with_result(result)
        dispatcher = ToolDispatcher(mcp_server_url="https://example.test/mcp")
        formatted_result = dispatcher._format_result(
            {"tool_name": "inspect", "tool_result": tool_result}
        )
        agent = BaseAgent(
            name="test",
            instruction="",
            llm=SimpleNamespace(context_window=8192),
            dispatcher=dispatcher,
        )

        history_result = agent._build_history_tool_result("call_mcp_tool", {}, formatted_result)

        self.assertTrue(history_result.startswith("[tool_result_summary]"))
        self.assertLess(tool_result.index("LATE SECURITY EVIDENCE"), tool_result.index('"data":'))
        preview = history_result.split("preview=\n", maxsplit=1)[1]
        self.assertIn("LATE SECURITY EVIDENCE", preview)


class _Tool:
    """Mimics mcp 2.0 Tool: exposes input_schema (snake_case), no inputSchema."""

    def __init__(self, name, description, input_schema):
        self.name = name
        self.description = description
        self.input_schema = input_schema


class _ListToolsResult:
    def __init__(self, tools):
        self.tools = tools


class _FakeSession:
    async def list_tools(self):
        return _ListToolsResult([
            _Tool(
                "echo",
                "Echo a message",
                {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                },
            )
        ])


class MCP20ToolSchemaTests(unittest.IsolatedAsyncioTestCase):
    async def test_describe_mcp_tools_reads_input_schema(self):
        manager = MCPTools("https://example.test/mcp", "streamable-http")

        @asynccontextmanager
        async def fake_session(_self):
            yield _FakeSession()

        with patch.object(MCPTools, "_session", fake_session):
            description = await manager.describe_mcp_tools()

        self.assertIn("echo", description)
        self.assertIn('name="message" type="string" required="true"', description)
        self.assertEqual(
            manager._tools_schema["echo"]["properties"]["message"]["type"],
            "string",
        )


if __name__ == "__main__":
    unittest.main()
