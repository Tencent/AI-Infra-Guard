import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch

from agent_scan.utils.mcp_tools import MCPTools


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
                "agent_scan.utils.mcp_tools.create_mcp_http_client",
                fake_create_mcp_http_client,
            ),
            patch(
                "agent_scan.utils.mcp_tools.streamable_http_client",
                fake_streamable_http_client,
            ),
            patch("agent_scan.utils.mcp_tools.ClientSession", _Session),
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


if __name__ == "__main__":
    unittest.main()
