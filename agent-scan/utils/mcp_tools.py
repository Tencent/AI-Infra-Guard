import asyncio
import json
from datetime import timedelta
from typing import Any, AsyncIterator, Dict, Literal, Optional
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
        # 缓存工具 schema，用于参数类型转换
        self._tools_schema: Dict[str, Dict[str, Any]] = {}

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

    def _build_parameter_attributes(self, param: Dict[str, Any]) -> str:
        """构建参数的 XML 属性字符串，包含所有 schema 信息"""
        attrs = []
        
        # 基础属性：type 和 required 在调用处处理
        
        # description: 描述
        if 'description' in param and param['description']:
            desc = str(param['description']).replace('"', '&quot;')
            attrs.append(f'description="{desc}"')
        
        # enum: 枚举值列表
        if 'enum' in param and param['enum']:
            enum_values = param['enum']
            if isinstance(enum_values, list):
                enum_str = ','.join(str(v) for v in enum_values)
                enum_str = enum_str.replace('"', '&quot;')
                attrs.append(f'enum="{enum_str}"')
        
        # default: 默认值
        if 'default' in param:
            default_val = param['default']
            if isinstance(default_val, (dict, list)):
                default_str = json.dumps(default_val, ensure_ascii=False)
            else:
                default_str = str(default_val)
            default_str = default_str.replace('"', '&quot;')
            attrs.append(f'default="{default_str}"')
        
        # minimum/maximum: 数值范围
        if 'minimum' in param:
            attrs.append(f'minimum="{param["minimum"]}"')
        if 'maximum' in param:
            attrs.append(f'maximum="{param["maximum"]}"')
        
        # minLength/maxLength: 字符串长度限制
        if 'minLength' in param:
            attrs.append(f'minLength="{param["minLength"]}"')
        if 'maxLength' in param:
            attrs.append(f'maxLength="{param["maxLength"]}"')
        
        # pattern: 正则表达式模式
        if 'pattern' in param and param['pattern']:
            pattern_str = str(param['pattern']).replace('"', '&quot;')
            attrs.append(f'pattern="{pattern_str}"')
        
        # format: 格式（如 date-time, email, uri 等）
        if 'format' in param and param['format']:
            attrs.append(f'format="{param["format"]}"')
        
        # examples: 示例值
        if 'examples' in param and param['examples']:
            examples = param['examples']
            if isinstance(examples, list) and examples:
                examples_str = ','.join(str(v) for v in examples)
                examples_str = examples_str.replace('"', '&quot;')
                attrs.append(f'examples="{examples_str}"')
        
        # items: 数组元素类型（对于 array 类型）
        if 'items' in param:
            items = param['items']
            if isinstance(items, dict):
                if 'type' in items:
                    attrs.append(f'itemsType="{items["type"]}"')
                if 'enum' in items:
                    items_enum = items['enum']
                    if isinstance(items_enum, list):
                        items_enum_str = ','.join(str(v) for v in items_enum)
                        items_enum_str = items_enum_str.replace('"', '&quot;')
                        attrs.append(f'itemsEnum="{items_enum_str}"')
        
        return ' '.join(attrs)

    async def describe_mcp_tools(self) -> str:
        """Return `<mcp_tools>` XML listing tool names and descriptions."""
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
            # 缓存工具 schema，用于后续参数类型转换
            self._tools_schema[t.name] = t.inputSchema

            parameters = ''
            for k, param in t.inputSchema['properties'].items():
                required = 'true' if k in t.inputSchema.get("required", []) else 'false'
                param_type = param.get('type', 'string')
                # 构建基础属性
                base_attrs = f'name="{k}" type="{param_type}" required="{required}"'
                # 构建额外的 schema 属性
                extra_attrs = self._build_parameter_attributes(param)
                # 合并所有属性（如果 extra_attrs 不为空，则添加空格）
                all_attrs = f'{base_attrs} {extra_attrs}'.strip() if extra_attrs else base_attrs
                parameters += f'''<parameter {all_attrs}></parameter>'''
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

    def _convert_args_by_schema(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
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
                if hasattr(result, 'text'):
                    return result.text
                elif hasattr(result, 'data'):
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
        result = await mcp_tools_manager.call_remote_tool(
            "get_filename1",
            filename="/etc/passwd"
        )
        print(f"Tool call result: {result}")


    asyncio.run(main())
