"""Tests for the 6 new agent scenarios: IM, calendar, finance, travel, social, file_manager."""

from __future__ import annotations

import pytest

from pikit.agent import (
    get_agent,
    list as agent_list,
    BROWSER_TOOLS, EMAIL_TOOLS, CODING_TOOLS, RAG_TOOLS,
    IM_TOOLS, CALENDAR_TOOLS, FINANCE_TOOLS, TRAVEL_TOOLS,
    SOCIAL_TOOLS, FILE_MANAGER_TOOLS,
    all_tools, get_tools, data_source_tools, sink_tools,
)
from pikit.agent.tools import Tool
from pikit.targets.mock import MockTarget


# ── Registration ───────────────────────────────────────────────────────


class TestNewAgentsRegistered:
    """Verify all 6 new agents are registered."""

    @pytest.mark.parametrize("key", ["im", "calendar", "finance", "travel", "social", "file_manager"])
    def test_agent_registered(self, key):
        assert key in agent_list()

    def test_total_agent_count(self):
        # chat, tool, email, rag, browser, coding + 6 new = 12
        assert len(agent_list()) >= 12


# ── Tool bundles ───────────────────────────────────────────────────────


class TestNewToolBundles:
    """Verify each new bundle resolves to real tools."""

    @pytest.mark.parametrize("bundle", [
        IM_TOOLS, CALENDAR_TOOLS, FINANCE_TOOLS, TRAVEL_TOOLS,
        SOCIAL_TOOLS, FILE_MANAGER_TOOLS,
    ])
    def test_bundle_resolves(self, bundle):
        tools = get_tools(bundle)
        assert len(tools) == len(bundle), f"Bundle has missing tools: {set(bundle) - {t.name for t in tools}}"

    def test_im_bundle_has_sink(self):
        tools = get_tools(IM_TOOLS)
        sinks = {t.name for t in tools if t.is_sink}
        assert "send_dm" in sinks
        assert "post_message" in sinks

    def test_calendar_bundle_has_sink(self):
        tools = get_tools(CALENDAR_TOOLS)
        sinks = {t.name for t in tools if t.is_sink}
        assert "create_event" in sinks
        assert "modify_event" in sinks

    def test_finance_bundle_has_sink(self):
        tools = get_tools(FINANCE_TOOLS)
        sinks = {t.name for t in tools if t.is_sink}
        assert "transfer_money" in sinks
        assert "pay_bill" in sinks

    def test_travel_bundle_has_sink(self):
        tools = get_tools(TRAVEL_TOOLS)
        sinks = {t.name for t in tools if t.is_sink}
        assert "book_flight" in sinks
        assert "book_hotel" in sinks

    def test_social_bundle_has_sink(self):
        tools = get_tools(SOCIAL_TOOLS)
        sinks = {t.name for t in tools if t.is_sink}
        assert "create_post" in sinks
        assert "share_post" in sinks

    def test_file_manager_bundle_has_sink(self):
        tools = get_tools(FILE_MANAGER_TOOLS)
        sinks = {t.name for t in tools if t.is_sink}
        assert "write_file" in sinks
        assert "delete_file" in sinks
        assert "move_file" in sinks


# ── Pool expansion ─────────────────────────────────────────────────────


class TestPoolExpansion:
    """Verify the tool pool grew with new categories and tools."""

    def test_pool_has_at_least_50_tools(self):
        assert len(all_tools()) >= 50, f"Expected >=50 tools, got {len(all_tools())}"

    def test_new_categories_present(self):
        from pikit.agent import categories
        cats = set(categories())
        assert "im" in cats
        assert "calendar" in cats
        assert "finance" in cats
        assert "travel" in cats
        assert "social" in cats

    def test_new_tools_in_pool(self):
        names = {t.name for t in all_tools()}
        for name in [
            "read_channel", "get_dm", "get_thread", "send_dm",
            "get_events", "get_event_details", "create_event", "modify_event",
            "get_balance", "get_transactions", "get_account_info",
            "transfer_money", "pay_bill",
            "search_flights", "search_hotels", "get_flight_details", "get_hotel_details",
            "book_flight", "book_hotel",
            "read_feed", "get_post", "get_notifications", "create_post", "share_post",
        ]:
            assert name in names, f"Tool {name} not in pool"

    def test_total_sinks_increased(self):
        sinks = sink_tools()
        assert len(sinks) >= 15, f"Expected >=15 sinks, got {len(sinks)}"

    def test_total_sources_increased(self):
        sources = data_source_tools()
        assert len(sources) >= 25, f"Expected >=25 sources, got {len(sources)}"


# ── Scenario agent behavior ────────────────────────────────────────────


class TestNewScenarioAgents:
    """Verify scenario agents use the tool pool correctly."""

    @pytest.mark.parametrize("scenario,bundle", [
        ("im", IM_TOOLS),
        ("calendar", CALENDAR_TOOLS),
        ("finance", FINANCE_TOOLS),
        ("travel", TRAVEL_TOOLS),
        ("social", SOCIAL_TOOLS),
        ("file_manager", FILE_MANAGER_TOOLS),
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

    @pytest.mark.parametrize("scenario", ["im", "calendar", "finance", "travel", "social", "file_manager"])
    def test_agent_has_at_least_one_sink(self, scenario):
        cls = get_agent(scenario)
        agent = cls(MockTarget())
        sinks = [t for t in agent.tools if t.is_sink]
        assert len(sinks) >= 1, f"{scenario} agent has no sink tools"

    @pytest.mark.parametrize("scenario", ["im", "calendar", "finance", "travel", "social", "file_manager"])
    def test_agent_system_prompt_lists_all_tools(self, scenario):
        cls = get_agent(scenario)
        agent = cls(MockTarget())
        for t in agent.tools:
            assert t.name in agent.system, f"Tool {t.name} not in {scenario} prompt"

    @pytest.mark.parametrize("scenario", ["im", "calendar", "finance", "travel", "social", "file_manager"])
    def test_agent_has_default_task(self, scenario):
        cls = get_agent(scenario)
        agent = cls(MockTarget())
        assert agent.default_task
        assert len(agent.default_task) > 10

    @pytest.mark.parametrize("scenario", ["im", "calendar", "finance", "travel", "social", "file_manager"])
    def test_agent_runs_with_mock(self, scenario):
        cls = get_agent(scenario)
        tmp_agent = cls(MockTarget())
        first_source = next(
            (t.name for t in tmp_agent.tools if not t.is_sink),
            tmp_agent.tools[0].name if tmp_agent.tools else "read_channel",
        )
        agent = cls(MockTarget(), taint={first_source: "tainted content"})
        trace = agent.run("test message")
        assert trace is not None
        assert len(trace.steps) > 0


# ── Expanded attack surface ────────────────────────────────────────────


class TestExpandedAttackSurfaceAll:
    """Verify the expanded tool pool provides more taint points across all scenarios."""

    def test_total_taint_points_across_all_scenarios(self):
        all_taint = set()
        for bundle in [BROWSER_TOOLS, EMAIL_TOOLS, CODING_TOOLS, RAG_TOOLS,
                       IM_TOOLS, CALENDAR_TOOLS, FINANCE_TOOLS, TRAVEL_TOOLS,
                       SOCIAL_TOOLS, FILE_MANAGER_TOOLS]:
            tools = get_tools(bundle)
            for t in tools:
                if not t.is_sink:
                    all_taint.add(t.name)
        assert len(all_taint) >= 20, (
            f"Expected >=20 unique taint points, got {len(all_taint)}: {all_taint}"
        )

    def test_total_sinks_across_all_scenarios(self):
        all_sinks = set()
        for bundle in [BROWSER_TOOLS, EMAIL_TOOLS, CODING_TOOLS, RAG_TOOLS,
                       IM_TOOLS, CALENDAR_TOOLS, FINANCE_TOOLS, TRAVEL_TOOLS,
                       SOCIAL_TOOLS, FILE_MANAGER_TOOLS]:
            tools = get_tools(bundle)
            for t in tools:
                if t.is_sink:
                    all_sinks.add(t.name)
        assert len(all_sinks) >= 12, (
            f"Expected >=12 unique sinks, got {len(all_sinks)}: {all_sinks}"
        )
