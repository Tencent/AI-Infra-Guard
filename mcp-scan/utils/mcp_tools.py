import requests
from typing import Optional


class MCPToolsManager:
    """Helper to fetch and format MCP server tools descriptions.

    This class centralizes logic that was previously embedded in
    `agent/dynamic_base_agent.py`. It provides a stable API for
    other modules to obtain a human-readable (or machine-friendly)
    description of tools exposed by a remote MCP server.

    Usage:
        desc = MCPToolsManager().describe_mcp_tools(server_url)
    """

    def fetch_tools(self, server_url: str, timeout: float = 3.0) -> Optional[object]:
        """Try to fetch tools info from common MCP discovery endpoints.

        Returns parsed JSON when available, or None on failure.
        """
        if not server_url:
            return None
        urls = [
            server_url.rstrip('/') + '/.well-known/mcp/tools',
            server_url.rstrip('/') + '/tools',
        ]
        for url in urls:
            try:
                r = requests.get(url, timeout=timeout)
                if r.status_code == 200:
                    try:
                        return r.json()
                    except Exception:
                        # Not JSON - return raw text wrapped
                        return r.text
            except Exception:
                # try next URL
                continue
        return None

    def describe_mcp_tools(self, server_url: str) -> str:
        """Return a formatted description derived from the MCP server.

        Falls back to a helpful snippet when fetch fails.
        """
        try:
            data = self.fetch_tools(server_url)
            if data is None:
                raise RuntimeError("no data")

            desc_lines = [f"# MCP server tools from {server_url}"]
            if isinstance(data, dict):
                tools = data.get('tools') or data.get('items') or data
            else:
                # Could be list or raw text
                tools = data

            if isinstance(tools, list):
                for t in tools:
                    if isinstance(t, dict):
                        name = t.get('name') or t.get('id') or '[unknown]'
                        detail = t.get('description') or t.get('desc') or ''
                        desc_lines.append(f"- {name}: {detail}")
                    else:
                        desc_lines.append(f"- {t}")
            elif isinstance(tools, dict):
                for k, v in tools.items():
                    desc_lines.append(f"- {k}: {v}")
            else:
                # raw text
                desc_lines.append(str(tools)[:1000])

            # Produce an XML-like snippet string suitable to be embedded
            # into prompts. This mirrors the meeting note asking for an
            # XML-like format (a string, not necessarily a file).
            xml_lines = ["<mcp_tools>"]
            for line in desc_lines[1:]:
                xml_lines.append(f"  <tool>{line}</tool>")
            xml_lines.append("</mcp_tools>")

            return "\n".join(desc_lines) + "\n\n" + "\n".join(xml_lines)
        except Exception:
            # Fallback snippet when requests is not available or any error
            snippet = (
                f"# MCP server connection snippet for manual inspection:\n"
                f"# 请使用 MCP 客户端列出工具并填充此节: {server_url}\n"
                f"# Example client usage:\n"
                f"# from fastmcp import Client\n# client = Client('{server_url}')\n"
            )
            return snippet
