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

"""Tests for the scan completeness check.

When the audit agent finishes with empty output (e.g. context compaction
loses analysis state on large projects), the empty result flows into
``calc_mcp_score([])`` which unconditionally returns 100 — publishing a
mechanically failed scan as a clean report. ``_warn_if_scan_incomplete``
marks that case so consumers can distinguish "no vulnerabilities found"
from "scan did not complete".
"""

from loguru import logger

from mcp_scan.agent.agent import _warn_if_scan_incomplete


def _capture_warnings():
    """loguru does not propagate to stdlib logging (caplog can't capture it);
    use a custom sink to collect warning messages."""
    messages = []
    handler_id = logger.add(messages.append, level="WARNING")
    return messages, handler_id


def test_marks_scan_incomplete_when_output_and_results_are_empty():
    """Both empty (no output, no findings) -> scanNote=possibly-incomplete + warning logged."""
    messages, handler_id = _capture_warnings()
    try:
        result_meta = {}
        _warn_if_scan_incomplete("", [], result_meta)
    finally:
        logger.remove(handler_id)
    assert result_meta["scanNote"] == "possibly-incomplete"
    assert any("Scan may be incomplete" in m for m in messages)


def test_marks_scan_incomplete_for_none_or_whitespace_output():
    """None and whitespace-only output are treated as empty."""
    result_meta = {}
    _warn_if_scan_incomplete(None, [], result_meta)
    assert result_meta["scanNote"] == "possibly-incomplete"

    result_meta = {}
    _warn_if_scan_incomplete("   \n\t  ", [], result_meta)
    assert result_meta["scanNote"] == "possibly-incomplete"


def test_sets_complete_when_output_is_present():
    """Text output present (normal clean audit) -> scanNote=complete, key always present."""
    result_meta = {}
    _warn_if_scan_incomplete("Audit finished, no vulnerabilities found.", [], result_meta)
    assert result_meta["scanNote"] == "complete"


def test_sets_complete_when_results_are_present():
    """Findings present -> scanNote=complete, key always present."""
    result_meta = {}
    vulns = [{"title": "Command Injection", "risk_type": "CommandInjection"}]
    _warn_if_scan_incomplete("", vulns, result_meta)
    assert result_meta["scanNote"] == "complete"


def test_setdefault_does_not_overwrite_existing_scan_note():
    """An existing scanNote value is not overwritten (setdefault semantics)."""
    result_meta = {"scanNote": "custom-note"}
    _warn_if_scan_incomplete("some output", [], result_meta)
    assert result_meta["scanNote"] == "custom-note"
