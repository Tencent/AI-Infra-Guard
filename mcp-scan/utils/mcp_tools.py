import asyncio
from datetime import timedelta
from typing import Any, AsyncIterator, Literal, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client


class MCPTools:
    """Small MCP-only wrapper used by this repo (no agno dependency)."""

    def __init__(self, url: Optional[str] = None, transport: Literal["sse", "streamable-http"] = "sse",
                 headers: dict = None):
        if headers is None:
            headers = {}
        self.url = url
        self.transport = transport
        self.timeout_seconds = 10
        self.headers = headers

    async def close(self) -> None:
        # Stateless wrapper: each operation uses a short-lived session.
        return

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        """Short-lived session (enter/exit in same coroutine; safe for SSE + anyio)."""
        if not self.url:
            raise ValueError("MCP server url is required")

        if self.transport == "sse":
            ctx = sse_client(url=self.url, headers=self.headers)  # type: ignore
        elif self.transport == "streamable-http":
            ctx = streamablehttp_client(url=self.url, headers=self.headers)  # type: ignore
        else:
            raise ValueError(f"Unsupported transport protocol: {self.transport}")

        async with ctx as session_params:  # type: ignore
            read, write = session_params[0:2]
            async with ClientSession(
                    read,
                    write,
                    read_timeout_seconds=timedelta(seconds=self.timeout_seconds),
            ) as session:  # type: ignore
                await session.initialize()
                yield session

    async def describe_mcp_tools(self) -> str:
        """Return `<mcp_tools>` XML listing tool names and descriptions."""
        try:
            async with self._session() as session:
                data = await session.list_tools()
        except Exception as e:
            raise Exception(f"Failed to fetch MCP tools description from server: {e}")

        xml_lines = ["<mcp_tools>"]
        for t in data.tools:
            parameters = ''
            for k, param in t.inputSchema['properties'].items():
                required = 'true' if k in t.inputSchema["required"] else 'false'
                parameters += f'''<parameter name="{k}" type="{param['type']}" required="{required}"></parameter>'''
            xml_lines.append(f'''
    <name>{t.name}</name>
    <description>{t.description}</description>
    <parameters>
      <parameter name="tool_name" type=string required=true>tool_name is {t.name}</parameter>
      {parameters}
    </parameters>
            ''')
            name = t.name
            detail = t.description or ""
            xml_lines.append(f"detail:{detail} 调用格式:\n<tool_name>{name}</tool_name>\n</tool>")
        xml_lines.append("</mcp_tools>")
        return "\n".join(xml_lines)

    async def call_remote_tool(self, tool_name: str, **kw) -> Any:
        """
        Call remote MCP server tool.
        call: {"toolName": name, "args": {...}}
        """
        if not tool_name:
            raise ValueError("call_remote_tool requires call['toolName']")

        async with self._session() as session:
            result = await session.call_tool(tool_name, kw)
            if result is None:
                return None
            result = result.content[0]
            # 判断TextContent or ImageContent or VideoContent
            if hasattr(result, 'text'):
                return result.text
            elif hasattr(result, 'data'):
                return result.data


if __name__ == "__main__":
    async def main():
        mcp_tools_manager = MCPTools(url="http://localhost:8090/sse", transport="sse")
        description = await mcp_tools_manager.describe_mcp_tools()
        print(description)
        result = await mcp_tools_manager.call_remote_tool(
            "get_filename1",
            filename="/etc/passwd"
        )
        print(f"Tool call result: {result}")


    asyncio.run(main())
