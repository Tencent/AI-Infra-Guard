import weakref
from datetime import timedelta
from typing import Any, Literal, Optional
import asyncio

from agno.tools import Toolkit
from agno.tools.function import Function
from agno.utils.log import log_debug, log_error, log_info
from agno.utils.mcp import get_entrypoint_for_tool

try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client
except (ImportError, ModuleNotFoundError):
    raise ImportError("`mcp` not installed. Please install using `pip install mcp`")

class MCPTools(Toolkit):
    """
    A toolkit for integrating Model Context Protocol (MCP) servers.
    This allows agents to access tools, resources, and prompts exposed by MCP servers.

    Can be used in two ways:
    1. Direct initialization with a ClientSession
    2. As an async context manager with SSE or Streamable HTTP client parameters
    """

    def __init__(
        self,
        url: Optional[str] = None,
        transport: Literal["sse", "streamable-http"] = "sse",
    ):
        """
        Initialize the MCP toolkit.

        Args:
            session: An initialized MCP ClientSession connected to an MCP server
            server_params: Parameters for creating a new session
            url: The URL endpoint for SSE or Streamable HTTP connection when transport is "sse" or "streamable-http".
            client: The underlying MCP client (optional, used to prevent garbage collection)
            timeout_seconds: Read timeout in seconds for the MCP client
            include_tools: Optional list of tool names to include (if None, includes all)
            exclude_tools: Optional list of tool names to exclude (if None, excludes none)
            transport: The transport protocol to use, either "sse" or "streamable-http"
            refresh_connection: If True, the connection and tools will be refreshed on each run
        """
        super().__init__(name="MCPTools")

        if transport == "sse":
            log_info("SSE as a standalone transport is deprecated. Please use Streamable HTTP instead.")

        # Set these after `__init__` to bypass the `_check_tools_filters`
        # because tools are not available until `initialize()` is called.
        self.refresh_connection = False
        self.tool_name_prefix = None

        self.timeout_seconds = 10
        self.session: Optional[ClientSession] = None
        self.transport = transport
        self.url = url

        self._client = None

        self._initialized = False
        self._connection_task = None
        self._active_contexts: list[Any] = []
        self._context = None
        self._session_context = None

        def cleanup():
            """Cancel active connections"""
            if self._connection_task and not self._connection_task.done():
                self._connection_task.cancel()

        # Setup cleanup logic before the instance is garbage collected
        self._cleanup_finalizer = weakref.finalize(self, cleanup)

    @property
    def initialized(self) -> bool:
        return self._initialized

    async def is_alive(self) -> bool:
        if self.session is None:
            return False
        try:
            await self.session.send_ping()
            return True
        except (RuntimeError, BaseException):
            return False

    async def connect(self, force: bool = False):
        """Initialize a MCPTools instance and connect to the contextual MCP server"""

        if force:
            # Clean up the session and context so we force a new connection
            self.session = None
            self._context = None
            self._session_context = None
            self._initialized = False
            self._connection_task = None
            self._active_contexts = []

        if self._initialized:
            return

        try:
            await self._connect()
        except (RuntimeError, BaseException) as e:
            log_error(f"Failed to connect to {str(self)}: {e}")

    async def _connect(self) -> None:
        """Connects to the MCP server and initializes the tools"""

        if self._initialized:
            return

        if self.session is not None:
            await self.initialize()
            return

        # Create a new studio session
        if self.transport == "sse":
            sse_params = {}  # type: ignore
            sse_params["url"] = self.url
            self._context = sse_client(**sse_params)  # type: ignore
            client_timeout = min(self.timeout_seconds, sse_params.get("timeout", self.timeout_seconds))

        # Create a new streamable HTTP session
        elif self.transport == "streamable-http":
            streamable_http_params = {}  # type: ignore
            streamable_http_params["url"] = self.url
            self._context = streamablehttp_client(**streamable_http_params)  # type: ignore
            params_timeout = streamable_http_params.get("timeout", self.timeout_seconds)
            if isinstance(params_timeout, timedelta):
                params_timeout = int(params_timeout.total_seconds())
            client_timeout = min(self.timeout_seconds, params_timeout)

        else:
            raise ValueError(f"Unsupported transport protocol: {self.transport}")

        session_params = await self._context.__aenter__()  # type: ignore
        self._active_contexts.append(self._context)
        read, write = session_params[0:2]

        self._session_context = ClientSession(read, write, read_timeout_seconds=timedelta(seconds=client_timeout))  # type: ignore
        self.session = await self._session_context.__aenter__()  # type: ignore
        self._active_contexts.append(self._session_context)

        # Initialize with the new session
        await self.initialize()

    async def close(self) -> None:
        """Close the MCP connection and clean up resources"""
        if not self._initialized:
            return

        try:
            if self._session_context is not None:
                await self._session_context.__aexit__(None, None, None)
                self.session = None
                self._session_context = None

            if self._context is not None:
                await self._context.__aexit__(None, None, None)
                self._context = None
        except (RuntimeError, BaseException) as e:
            log_error(f"Failed to close MCP connection: {e}")

        self._initialized = False

    async def __aenter__(self) -> "MCPTools":
        await self._connect()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """Exit the async context manager."""
        if self._session_context is not None:
            await self._session_context.__aexit__(_exc_type, _exc_val, _exc_tb)
            self.session = None
            self._session_context = None

        if self._context is not None:
            await self._context.__aexit__(_exc_type, _exc_val, _exc_tb)
            self._context = None

        self._initialized = False

    async def build_tools(self) -> None:
        """Build the tools for the MCP toolkit"""
        if self.session is None:
            raise ValueError("Session is not initialized")

        try:
            # Get the list of tools from the MCP server
            available_tools = await self.session.list_tools()  # type: ignore

            self._check_tools_filters(
                available_tools=[tool.name for tool in available_tools.tools],
                include_tools=self.include_tools,
                exclude_tools=self.exclude_tools,
            )

            # Filter tools based on include/exclude lists
            filtered_tools = []
            for tool in available_tools.tools:
                if self.exclude_tools and tool.name in self.exclude_tools:
                    continue
                if self.include_tools is None or tool.name in self.include_tools:
                    filtered_tools.append(tool)

            # Get tool name prefix if available
            tool_name_prefix = ""
            if self.tool_name_prefix is not None:
                tool_name_prefix = self.tool_name_prefix + "_"

            # Register the tools with the toolkit
            for tool in filtered_tools:
                try:
                    # Get an entrypoint for the tool
                    entrypoint = get_entrypoint_for_tool(tool, self.session)  # type: ignore
                    # Create a Function for the tool
                    f = Function(
                        name=tool_name_prefix + tool.name,
                        description=tool.description,
                        parameters=tool.inputSchema,
                        entrypoint=entrypoint,
                        # Set skip_entrypoint_processing to True to avoid processing the entrypoint
                        skip_entrypoint_processing=True,
                    )

                    # Register the Function with the toolkit
                    self.functions[f.name] = f
                    log_debug(f"Function: {f.name} registered with {self.name}")
                except Exception as e:
                    log_error(f"Failed to register tool {tool.name}: {e}")

        except (RuntimeError, BaseException) as e:
            log_error(f"Failed to get tools for {str(self)}: {e}")
            raise

    async def initialize(self) -> None:
        """Initialize the MCP toolkit by getting available tools from the MCP server"""
        if self._initialized:
            return

        try:
            if self.session is None:
                raise ValueError("Session is not initialized")

            # Initialize the session if not already initialized
            await self.session.initialize()

            await self.build_tools()

            self._initialized = True

        except (RuntimeError, BaseException) as e:
            log_error(f"Failed to initialize MCP toolkit: {e}")


    async def describe_mcp_tools(self) -> str:
        xml_lines = ["<mcp_tools>"]
        await self.connect()

        try:
            # Get the list of tools from the MCP server
            data = await self.session.list_tools()
            if data is None:
                raise RuntimeError("no data")
            desc_lines = [f"# MCP server tools from {self.url}"]

            for t in data.tools:
                name = t.name
                detail = t.description or ""
                desc_lines.append(f"- {name}: {detail}")

            for line in desc_lines[1:]:
                xml_lines.append(f"  <tool>{line}</tool>")
            xml_lines.append("</mcp_tools>")

        except Exception as e:
            log_error(e)
            raise Exception("Failed to fetch MCP tools description from server.")
        return "\n".join(xml_lines)
        
    async def call_remote_tool(self, call: dict) -> tuple:
        """
        调用远程 MCP server 上的工具并返回结果。
        参数:
            call: {"toolName": name, "args": {...}}
        """
        await self.connect()

        try:
            # Get the list of tools from the MCP server
            tool_info_list = await self.session.list_tools()
            tool_info = {}
            for t in tool_info_list.tools:
                if t.name == call["toolName"]:
                    tool_info["description"] = t.description
                    tool_info["inputSchema"] = t.inputSchema
                    tool_info["outputSchema"] = t.outputSchema
                    break
            result = await self.session.call_tool(call["toolName"], call.get("args", {}))
            return tool_info, result
        except Exception as e:
            log_error(e)
            raise Exception(f"Failed to call remote tool {call.get('toolName')}: {str(e)}")


if __name__ == "__main__":
    async def main():
        mcp_tools_manager = MCPTools(url="http://localhost:9008/sse", transport="sse")
        description = await mcp_tools_manager.describe_mcp_tools()
        print(description)
        result = await mcp_tools_manager.call_remote_tool({
            "toolName": "get_user_role",
            "args": {"username": "alice"}
        })
        print(f"Tool call result: {result}")
    asyncio.run(main())
