"""aig-agent-scan - AI Agent Security Scanning Tool.

A dynamic black-box security testing tool for running AI Agent platforms
(e.g., Dify, Coze, OpenAI-compatible applications). It connects to the target
agent via API, sends crafted test prompts, and analyzes responses to discover
security vulnerabilities.

Public API:
    from agent_scan.core.agent import Agent
    from agent_scan.utils.llm import LLM
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
