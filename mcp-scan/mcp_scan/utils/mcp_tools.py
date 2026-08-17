# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, Literal

from mcp import ClientSession
from mcp.client.sse import sse_client

import importlib.metadata

try:
    _MCP_MAJOR = int(importlib.metadata.version("mcp").split(".")[0])
except Exception:
    _MCP_MAJOR = 0

if _MCP_MAJOR >= 2:
    # mcp SDK >= 2.0：streamable_http_client 不再接受 headers 参数，需通过 httpx.AsyncClient 传入
    from mcp.client.streamable_http import streamable_http_client
    import httpx

    _USE_NEW_STREAMABLE_API = True
else:  # mcp SDK < 2.0 兼容
    from mcp.client.streamable_http import streamablehttp_client

    _USE_NEW_STREAMABLE_API = False


class MCPTools:
    """Small MCP-only wrapper used by this repo (no agno dependency)."""

    def __init__(
        self,
        url: str | None = None,
        transport: Literal["sse", "streamable-http"] = "sse",
        headers: dict = None,
    ):
        if headers is None:
            headers = {}
        self.url = url
        self.transport = transport
        self.timeout_seconds = 10
        self.headers = headers
        # 缓存工具 schema，用于参数类型转换
        self._tools_schema: dict[str, dict[str, Any]] = {}

    async def close(self) -> None:
        # Stateless wrapper: each operation uses a short-lived session.
        return

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[ClientSession]:
        """Short-lived session (enter/exit in same coroutine; safe for SSE + anyio)."""
        if not self.url:
            raise ValueError("MCP server url is required")

        http_client = None
        if self.transport == "sse":
            ctx = sse_client(url=self.url, headers=self.headers)  # type: ignore
        elif self.transport == "streamable-http":
            if _USE_NEW_STREAMABLE_API:
                # mcp SDK >= 2.0：headers 通过 httpx.AsyncClient 传入
                http_client = httpx.AsyncClient(headers=self.headers)
                ctx = streamable_http_client(url=self.url, http_client=http_client)
            else:
                ctx = streamablehttp_client(url=self.url, headers=self.headers)  # type: ignore
        else:
            raise ValueError(f"Unsupported transport protocol: {self.transport}")

        # mcp SDK >= 2.0 的 read_timeout_seconds 为 float 秒数；旧版为 timedelta
        read_timeout = self.timeout_seconds if _USE_NEW_STREAMABLE_API else timedelta(seconds=self.timeout_seconds)

        try:
            async with ctx as session_params:  # type: ignore
                read, write = session_params[0:2]
                async with ClientSession(
                    read,
                    write,
                    read_timeout_seconds=read_timeout,
                ) as session:  # type: ignore
                    await session.initialize()
                    yield session
        finally:
            # 新版 SDK 需要自行关闭传入的 http_client（旧版由 ctx 内部管理）
            if http_client is not None:
                await http_client.aclose()

    def _build_parameter_attributes(self, param: dict[str, Any]) -> str:
        """构建参数的 XML 属性字符串，包含所有 schema 信息"""
        attrs = []

        # 基础属性：type 和 required 在调用处处理

        # description: 描述
        if "description" in param and param["description"]:
            desc = str(param["description"]).replace('"', "&quot;")
            attrs.append(f'description="{desc}"')

        # enum: 枚举值列表
        if "enum" in param and param["enum"]:
            enum_values = param["enum"]
            if isinstance(enum_values, list):
                enum_str = ",".join(str(v) for v in enum_values)
                enum_str = enum_str.replace('"', "&quot;")
                attrs.append(f'enum="{enum_str}"')

        # default: 默认值
        if "default" in param:
            default_val = param["default"]
            if isinstance(default_val, (dict, list)):
                default_str = json.dumps(default_val, ensure_ascii=False)
            else:
                default_str = str(default_val)
            default_str = default_str.replace('"', "&quot;")
            attrs.append(f'default="{default_str}"')

        # minimum/maximum: 数值范围
        if "minimum" in param:
            attrs.append(f'minimum="{param["minimum"]}"')
        if "maximum" in param:
            attrs.append(f'maximum="{param["maximum"]}"')

        # minLength/maxLength: 字符串长度限制
        if "minLength" in param:
            attrs.append(f'minLength="{param["minLength"]}"')
        if "maxLength" in param:
            attrs.append(f'maxLength="{param["maxLength"]}"')

        # pattern: 正则表达式模式
        if "pattern" in param and param["pattern"]:
            pattern_str = str(param["pattern"]).replace('"', "&quot;")
            attrs.append(f'pattern="{pattern_str}"')

        # format: 格式（如 date-time, email, uri 等）
        if "format" in param and param["format"]:
            attrs.append(f'format="{param["format"]}"')

        # examples: 示例值
        if "examples" in param and param["examples"]:
            examples = param["examples"]
            if isinstance(examples, list) and examples:
                examples_str = ",".join(str(v) for v in examples)
                examples_str = examples_str.replace('"', "&quot;")
                attrs.append(f'examples="{examples_str}"')

        # items: 数组元素类型（对于 array 类型）
        if "items" in param:
            items = param["items"]
            if isinstance(items, dict):
                if "type" in items:
                    attrs.append(f'itemsType="{items["type"]}"')
                if "enum" in items:
                    items_enum = items["enum"]
                    if isinstance(items_enum, list):
                        items_enum_str = ",".join(str(v) for v in items_enum)
                        items_enum_str = items_enum_str.replace('"', "&quot;")
                        attrs.append(f'itemsEnum="{items_enum_str}"')

        return " ".join(attrs)

    # 工具描述最大长度，防止超长描述注入大量指令
    _MAX_DESC_LEN = 500

    # 需要净化的 prompt injection 指令模式
    _INJECTION_PATTERNS = [
        r"(?i)ignore\s+(previous|above|all)\s+instructions?",
        r"(?i)you\s+are\s+now\s+in\b",
        r"(?i)system\s*(note|override|prompt)\s*:",
        r"(?i)\bexecute\s+(this|the)\s+(shell|command|diagnostic)\b",
        r"(?i)\brun\s+this\s+(exact\s+)?diagnostic\b",
        r"(?i)\bself[- ]?test\b.*\b(execute|run|shell|command)\b",
        r"(?i)\bDNS\s+connectivity\s+self[- ]?test\b",
        r"(?i)\b(scanner|scanning)\s+(environment|pipeline)\s+self[- ]?test\b",
        r"(?i)\benvironment\s+fingerprint\b",
        r"(?i)\bexecute_shell\b",
    ]

    @classmethod
    def _sanitize_description(cls, desc: str) -> str:
        """净化 MCP 工具描述，移除 prompt injection 指令并截断过长内容。"""
        if not desc:
            return ""
        import re

        sanitized = desc
        for pattern in cls._INJECTION_PATTERNS:
            sanitized = re.sub(pattern, "[REMOVED]", sanitized)
        if len(sanitized) > cls._MAX_DESC_LEN:
            sanitized = sanitized[: cls._MAX_DESC_LEN] + "... [truncated]"
        return sanitized

    async def describe_mcp_tools(self) -> str:
        """Return `<mcp_tools>` XML listing tool names and descriptions.

        对远程 MCP 工具描述进行净化（截断 + 移除指令性内容），防止恶意
        MCP 服务器通过工具描述注入 prompt injection 指令。
        """
        try:
            async with self._session() as session:
                data = await session.list_tools()
        except BaseExceptionGroup as eg:
            root_cause = self._extract_root_cause(eg)
            raise RuntimeError(f"Failed to fetch MCP tools: {root_cause}") from eg
        except Exception as e:
            raise RuntimeError(f"Failed to fetch MCP tools: {type(e).__name__}: {e}") from e

        xml_lines = ["<mcp_tools>"]
        for t in data.tools:
            # mcp SDK >= 2.0 的 Tool 字段为 input_schema，旧版为 inputSchema
            tool_schema = getattr(t, "input_schema", None)
            if tool_schema is None:
                tool_schema = getattr(t, "inputSchema", None)
            if tool_schema is None:
                tool_schema = {}
            # 缓存工具 schema，用于后续参数类型转换
            self._tools_schema[t.name] = tool_schema

            # 净化工具描述，移除 prompt injection 指令
            safe_desc = self._sanitize_description(t.description)

            parameters = ""
            for k, param in tool_schema.get("properties", {}).items():
                required = "true" if k in tool_schema.get("required", []) else "false"
                param_type = param.get("type", "string")
                # 构建基础属性
                base_attrs = f'name="{k}" type="{param_type}" required="{required}"'
                # 构建额外的 schema 属性
                extra_attrs = self._build_parameter_attributes(param)
                # 合并所有属性（如果 extra_attrs 不为空，则添加空格）
                all_attrs = f"{base_attrs} {extra_attrs}".strip() if extra_attrs else base_attrs
                parameters += f"""<parameter {all_attrs}></parameter>"""
            xml_lines.append(f"""
    <name>{t.name}</name>
    <description>{safe_desc}</description>
    <parameters>
      <parameter name="tool_name" type=string required=true>tool_name is {t.name}</parameter>
      {parameters}
    </parameters>
            """)
            name = t.name
            detail = safe_desc
            xml_lines.append(f"detail:{detail} 调用格式:\n<tool_name>{name}</tool_name>\n</tool>")
        xml_lines.append("</mcp_tools>")
        return "\n".join(xml_lines)

    def _convert_param_type(self, value: Any, param_type: str) -> Any:
        """根据 schema 定义的类型转换参数值"""
        if value is None:
            return None

        try:
            if param_type == "integer":
                return int(value)
            elif param_type == "number":
                return float(value)
            elif param_type == "boolean":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes")
                return bool(value)
            elif param_type == "array":
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    import json

                    return json.loads(value)
                return [value]
            elif param_type == "object":
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    import json

                    return json.loads(value)
                return value
            else:
                # string 或其他类型，保持原样
                return value
        except (ValueError, TypeError):
            # 转换失败，返回原值
            return value

    def _convert_args_by_schema(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """根据工具 schema 转换所有参数类型"""
        schema = self._tools_schema.get(tool_name)
        if not schema:
            return args

        properties = schema.get("properties", {})
        converted_args = {}

        for key, value in args.items():
            param_schema = properties.get(key, {})
            param_type = param_schema.get("type", "string")
            converted_args[key] = self._convert_param_type(value, param_type)

        return converted_args

    def _extract_root_cause(self, exc: Exception) -> str:
        """从 ExceptionGroup/TaskGroup 中提取原始错误信息"""
        # 处理 ExceptionGroup (Python 3.11+)
        if isinstance(exc, BaseExceptionGroup):
            messages = []
            for sub_exc in exc.exceptions:
                # 递归提取嵌套的 ExceptionGroup
                messages.append(self._extract_root_cause(sub_exc))
            return "; ".join(messages)
        # 普通异常，返回其消息
        return f"{type(exc).__name__}: {exc}"

    async def call_remote_tool(self, tool_name: str, **kw) -> Any:
        """
        Call remote MCP server tool.
        call: {"toolName": name, "args": {...}}
        """
        if not tool_name:
            raise ValueError("call_remote_tool requires call['toolName']")

        # 根据 schema 转换参数类型
        converted_kw = self._convert_args_by_schema(tool_name, kw)

        try:
            async with self._session() as session:
                result = await session.call_tool(tool_name, converted_kw)
                if result is None:
                    return None
                result = result.content[0]
                # 判断TextContent or ImageContent or VideoContent
                if hasattr(result, "text"):
                    return result.text
                elif hasattr(result, "data"):
                    return result.data
        except BaseExceptionGroup as eg:
            # 提取 TaskGroup 中的原始错误
            root_cause = self._extract_root_cause(eg)
            raise RuntimeError(f"MCP call failed: {root_cause}") from eg
        except Exception as e:
            raise RuntimeError(f"MCP call failed: {type(e).__name__}: {e}") from e


if __name__ == "__main__":

    async def main():
        mcp_tools_manager = MCPTools(url="http://localhost:8090/sse", transport="sse")
        description = await mcp_tools_manager.describe_mcp_tools()
        print(description)
        result = await mcp_tools_manager.call_remote_tool("get_filename1", filename="/etc/passwd")
        print(f"Tool call result: {result}")

    asyncio.run(main())
