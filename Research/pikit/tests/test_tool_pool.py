"""Tests for the expanded tool pool, pool management API, and dynamic prompts."""

from __future__ import annotations

import pytest

from pikit.agent import (
    all_tools,
    categories,
    data_source_tools,
    get_tool,
    get_tools,
    sink_tools,
    tool_names,
    tools_by_category,
    BROWSER_TOOLS,
    CODING_TOOLS,
    EMAIL_TOOLS,
    RAG_TOOLS,
    build_system_prompt,
)
from pikit.agent.tools import Tool
from pikit.targets.mock import MockTarget
from pikit.agent import get_agent


# ── Pool size and structure ────────────────────────────────────────────


class TestToolPool:
    """Verify the tool pool has the expected size and structure."""

    def test_pool_has_at_least_30_tools(self):
        tools = all_tools()
        assert len(tools) >= 30, f"Expected >=30 tools, got {len(tools)}"

    def test_all_tools_are_tool_instances(self):
        for t in all_tools():
            assert isinstance(t, Tool)

    def test_every_tool_has_category(self):
        for t in all_tools():
            assert t.category, f"Tool {t.name} has empty category"

    def test_categories_present(self):
        cats = categories()
        expected = {"web", "email", "file", "code", "knowledge", "communication"}
        assert expected.issubset(set(cats)), f"Missing categories: {expected - set(cats)}"

    def test_tool_names_unique(self):
        names = tool_names()
        assert len(names) == len(set(names)), "Duplicate tool names in pool"

    def test_sink_and_source_partition(self):
        """Every tool is either a sink or a data-source (not both, not neither)."""
        sinks = {t.name for t in sink_tools()}
        sources = {t.name for t in data_source_tools()}
        all_names = set(tool_names())
        assert sinks | sources == all_names, "Some tools are neither sink nor source"
        assert sinks & sources == set(), "Some tools are both sink and source"


# ── Pool query functions ───────────────────────────────────────────────


class TestPoolQueries:
    """Test the pool management API."""

    def test_get_tool_returns_tool_or_none(self):
        assert get_tool("fetch_url") is not None
        assert get_tool("send_email") is not None
        assert get_tool("nonexistent") is None

    def test_get_tools_by_name_list(self):
        result = get_tools(["fetch_url", "send_email", "nonexistent"])
        assert len(result) == 2
        assert all(isinstance(t, Tool) for t in result)

    def test_tools_by_category(self):
        web_tools = tools_by_category("web")
        assert len(web_tools) >= 5
        for t in web_tools:
            assert t.category == "web"

    def test_sink_count(self):
        sinks = sink_tools()
        assert len(sinks) >= 10, f"Expected >=10 sinks, got {len(sinks)}"

    def test_data_source_count(self):
        sources = data_source_tools()
        assert len(sources) >= 15, f"Expected >=15 sources, got {len(sources)}"


# ── Category bundles ───────────────────────────────────────────────────


class TestCategoryBundles:
    """Verify each scenario bundle resolves to real tools."""

    def test_browser_bundle(self):
        tools = get_tools(BROWSER_TOOLS)
        assert len(tools) == len(BROWSER_TOOLS)
        names = {t.name for t in tools}
        assert "fetch_url" in names
        assert "post_form" in names  # sink

    def test_email_bundle(self):
        tools = get_tools(EMAIL_TOOLS)
        assert len(tools) == len(EMAIL_TOOLS)
        names = {t.name for t in tools}
        assert "read_email" in names
        assert "send_email" in names  # sink
        assert "forward_email" in names  # sink
        assert "search_kb" in names  # cross-domain

    def test_coding_bundle(self):
        tools = get_tools(CODING_TOOLS)
        assert len(tools) == len(CODING_TOOLS)
        names = {t.name for t in tools}
        assert "read_code" in names
        assert "run_command" in names  # sink
        assert "write_file" in names  # sink
        assert "install_package" in names  # sink

    def test_rag_bundle(self):
        tools = get_tools(RAG_TOOLS)
        assert len(tools) == len(RAG_TOOLS)
        names = {t.name for t in tools}
        assert "search_kb" in names
        assert "get_document" in names
        assert "summarize_text" in names
        assert "translate_text" in names


# ── Dynamic system prompt ─────────────────────────────────────────────


class TestSystemPromptBuilder:
    """Test the dynamic system-prompt builder."""

    def test_prompt_contains_role(self):
        tools = get_tools(BROWSER_TOOLS)
        prompt = build_system_prompt("a test assistant", tools)
        assert "a test assistant" in prompt

    def test_prompt_lists_all_tools(self):
        tools = get_tools(BROWSER_TOOLS)
        prompt = build_system_prompt("a test assistant", tools)
        for t in tools:
            assert t.name in prompt, f"Tool {t.name} not in prompt"

    def test_prompt_includes_sink_warning(self):
        tools = get_tools(EMAIL_TOOLS)
        prompt = build_system_prompt("an email assistant", tools)
        # Should mention sink tools by name
        for t in tools:
            if t.is_sink:
                assert t.name in prompt

    def test_prompt_includes_safety_text(self):
        tools = get_tools(BROWSER_TOOLS)
        prompt = build_system_prompt("a browser", tools)
        assert "IMPORTANT" in prompt
        assert "untrusted" in prompt.lower() or "data, not commands" in prompt.lower()

    def test_custom_safety_text(self):
        tools = get_tools(BROWSER_TOOLS)
        prompt = build_system_prompt("a browser", tools, safety="BE SAFE")
        assert "BE SAFE" in prompt

    def test_custom_instructions(self):
        tools = get_tools(BROWSER_TOOLS)
        prompt = build_system_prompt("a browser", tools, instructions="Always check URLs.")
        assert "Always check URLs." in prompt


# ── Scenario agents with new pool ─────────────────────────────────────


class TestScenarioAgentsWithPool:
    """Verify scenario agents use the tool pool correctly."""

    @pytest.mark.parametrize("scenario,bundle", [
        ("browser", BROWSER_TOOLS),
        ("email", EMAIL_TOOLS),
        ("coding", CODING_TOOLS),
        ("rag", RAG_TOOLS),
    ])
    def test_agent_has_expected_tools(self, scenario, bundle):
        cls = get_agent(scenario)
        agent = cls(MockTarget())
        agent_tool_names = {t.name for t in agent.tools}
        bundle_set = set(bundle)
        assert agent_tool_names == bundle_set, (
            f"{scenario} agent tools mismatch: "
            f"extra={agent_tool_names - bundle_set}, "
            f"missing={bundle_set - agent_tool_names}"
        )

    @pytest.mark.parametrize("scenario", ["browser", "email", "coding", "rag"])
    def test_agent_has_at_least_one_sink(self, scenario):
        cls = get_agent(scenario)
        agent = cls(MockTarget())
        sinks = [t for t in agent.tools if t.is_sink]
        assert len(sinks) >= 1, f"{scenario} agent has no sink tools"

    @pytest.mark.parametrize("scenario", ["browser", "email", "coding", "rag"])
    def test_agent_system_prompt_is_dynamic(self, scenario):
        cls = get_agent(scenario)
        agent = cls(MockTarget())
        # The dynamic prompt should mention all tool names
        for t in agent.tools:
            assert t.name in agent.system, (
                f"Tool {t.name} not mentioned in {scenario} agent's system prompt"
            )

    @pytest.mark.parametrize("scenario", ["browser", "email", "coding", "rag"])
    def test_agent_accepts_custom_tools(self, scenario):
        cls = get_agent(scenario)
        custom = get_tools(["fetch_url", "read_file"])
        agent = cls(MockTarget(), tools=custom)
        assert {t.name for t in agent.tools} == {"fetch_url", "read_file"}

    @pytest.mark.parametrize("scenario", ["browser", "email", "coding", "rag"])
    def test_agent_accepts_custom_system(self, scenario):
        cls = get_agent(scenario)
        agent = cls(MockTarget(), system="Custom prompt")
        assert agent.system == "Custom prompt"

    def test_email_agent_has_cross_domain_tools(self):
        """Email agent should have search_kb and post_message for richer testing."""
        cls = get_agent("email")
        agent = cls(MockTarget())
        names = {t.name for t in agent.tools}
        assert "search_kb" in names
        assert "post_message" in names

    def test_coding_agent_has_rich_toolset(self):
        """Coding agent should have >=10 tools."""
        cls = get_agent("coding")
        agent = cls(MockTarget())
        assert len(agent.tools) >= 10

    def test_all_scenarios_run_with_mock(self):
        """Each scenario agent should run without error on MockTarget.

        Uses the ``taint`` map so the mock's heuristic tool call (which
        passes empty args) doesn't hit a real function requiring arguments.
        """
        for name in ["browser", "email", "coding", "rag"]:
            cls = get_agent(name)
            # Find the first data-source tool name to taint it.
            tmp_agent = cls(MockTarget())
            first_source = next(
                (t.name for t in tmp_agent.tools if not t.is_sink),
                tmp_agent.tools[0].name if tmp_agent.tools else "fetch_url",
            )
            agent = cls(MockTarget(), taint={first_source: "tainted"})
            trace = agent.run("test message")
            assert trace is not None
            assert len(trace.steps) > 0


# ── Expanded attack surface ────────────────────────────────────────────


class TestExpandedAttackSurface:
    """Verify the expanded tool pool provides more taint points than before."""

    def test_total_taint_points_across_scenarios(self):
        """Count unique data-source tools across all scenarios."""
        all_taint = set()
        for bundle in [BROWSER_TOOLS, EMAIL_TOOLS, CODING_TOOLS, RAG_TOOLS]:
            tools = get_tools(bundle)
            for t in tools:
                if not t.is_sink:
                    all_taint.add(t.name)
        # Previously each scenario had 2-3 taint points (~8 total unique).
        # Now we expect significantly more.
        assert len(all_taint) >= 12, (
            f"Expected >=12 unique taint points, got {len(all_taint)}: {all_taint}"
        )

    def test_total_sinks_across_scenarios(self):
        """Count unique sink tools across all scenarios."""
        all_sinks = set()
        for bundle in [BROWSER_TOOLS, EMAIL_TOOLS, CODING_TOOLS, RAG_TOOLS]:
            tools = get_tools(bundle)
            for t in tools:
                if t.is_sink:
                    all_sinks.add(t.name)
        # Previously there were 4 sinks (send_email, post_form, run_command, write_file).
        # Now we expect more.
        assert len(all_sinks) >= 6, (
            f"Expected >=6 unique sinks, got {len(all_sinks)}: {all_sinks}"
        )