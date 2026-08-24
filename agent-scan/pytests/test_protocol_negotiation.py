"""Unit tests for MCP protocol auto-negotiation logic.

Covers both the modern (server/discover success) and legacy (discover failure →
initialize fallback) branches of MCPTools._negotiate_protocol(), addressing
reviewer feedback on PR #579.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_scan.utils.mcp_tools import (
    _DEFAULT_LEGACY_VERSION,
    _DEFAULT_MODERN_VERSION,
    MCPTools,
)


def _make_discover_result(protocol_version=None):
    """Create a mock discover result with an optional protocolVersion attribute."""
    result = MagicMock()
    result.protocolVersion = protocol_version
    return result


def _make_init_result(protocol_version=None):
    """Create a mock initialize result with an optional protocolVersion attribute."""
    result = MagicMock()
    result.protocolVersion = protocol_version
    return result


@pytest.mark.asyncio
async def test_negotiate_modern_with_explicit_version():
    """discover() succeeds and returns a protocolVersion → modern path."""
    tools = MCPTools(url="http://localhost:9999/sse", transport="sse")
    session = MagicMock()
    session.discover = AsyncMock(return_value=_make_discover_result("2026-07-28"))

    await tools._negotiate_protocol(session)

    assert tools.negotiation_type == "modern"
    assert tools.negotiated_protocol_version == "2026-07-28"
    session.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_negotiate_modern_without_version_uses_default():
    """discover() succeeds but protocolVersion is None → fall back to default modern version."""
    tools = MCPTools(url="http://localhost:9999/sse", transport="sse")
    session = MagicMock()
    session.discover = AsyncMock(return_value=_make_discover_result(None))

    await tools._negotiate_protocol(session)

    assert tools.negotiation_type == "modern"
    assert tools.negotiated_protocol_version == _DEFAULT_MODERN_VERSION
    session.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_negotiate_legacy_on_discover_failure():
    """discover() raises → fall back to legacy initialize handshake."""
    tools = MCPTools(url="http://localhost:9999/sse", transport="sse")
    session = MagicMock()
    session.discover = AsyncMock(side_effect=AttributeError("no discover method"))
    session.initialize = AsyncMock(return_value=_make_init_result("2025-11-25"))

    await tools._negotiate_protocol(session)

    assert tools.negotiation_type == "legacy"
    assert tools.negotiated_protocol_version == "2025-11-25"
    session.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_negotiate_legacy_without_version_uses_default():
    """discover() fails and initialize returns no protocolVersion → default legacy version."""
    tools = MCPTools(url="http://localhost:9999/sse", transport="sse")
    session = MagicMock()
    session.discover = AsyncMock(side_effect=Exception("method not found"))
    session.initialize = AsyncMock(return_value=_make_init_result(None))

    await tools._negotiate_protocol(session)

    assert tools.negotiation_type == "legacy"
    assert tools.negotiated_protocol_version == _DEFAULT_LEGACY_VERSION


@pytest.mark.asyncio
async def test_negotiate_modern_discover_returns_none():
    """discover() returns None (server doesn't support) → legacy fallback."""
    tools = MCPTools(url="http://localhost:9999/sse", transport="sse")
    session = MagicMock()
    session.discover = AsyncMock(return_value=None)
    session.initialize = AsyncMock(return_value=_make_init_result("2025-11-25"))

    await tools._negotiate_protocol(session)

    assert tools.negotiation_type == "legacy"
    assert tools.negotiated_protocol_version == "2025-11-25"
    session.initialize.assert_called_once()
