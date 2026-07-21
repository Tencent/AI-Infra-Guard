"""aig-mcp-scan - MCP Server Security Scanning Tool.

A multi-stage security auditing tool for MCP (Model Context Protocol) server
projects, performing static and dynamic security analysis via an LLM-driven
code audit + vulnerability review pipeline.

Public API:
    from mcp_scan.agent.agent import Agent
    from mcp_scan.utils.llm import LLM
"""

from __future__ import annotations

__version__ = "0.2.0"
__all__ = ["__version__"]