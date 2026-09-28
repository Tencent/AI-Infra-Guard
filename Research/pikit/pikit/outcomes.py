"""Stable outcome categories for agent-security experiments."""

from __future__ import annotations

from enum import Enum


class Outcome(str, Enum):
    """Normalized result category independent of a particular judge."""

    NOT_REACHED = "not_reached"
    TAINT_DELIVERED = "taint_delivered"
    REFUSED = "refused"
    PARTIAL_COMPLIANCE = "partial_compliance"
    SINK_ATTEMPTED = "sink_attempted"
    SINK_ARGS_MISMATCH = "sink_args_mismatch"
    POLICY_BLOCKED = "policy_blocked"
    APPROVAL_REQUESTED = "approval_requested"
    FULL_SUCCESS = "full_success"
    RUNTIME_ERROR = "runtime_error"
    NOT_JUDGED = "not_judged"


__all__ = ["Outcome"]
