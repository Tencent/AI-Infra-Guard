"""Finding levels written as CVSS scores or in Chinese must keep their severity."""

import pytest

from agent_scan.core.report.report import (
    _extract_vuln_blocks,
    _normalize_level,
    generate_report_from_xml,
)


def vuln(level: str) -> str:
    return (
        "<vuln>\n"
        "  <title>Prompt injection leaks the system prompt</title>\n"
        "  <desc>The agent repeats its system prompt when asked to.</desc>\n"
        "  <risk_type>ASI01: Agent Goal Hijack</risk_type>\n"
        f"  <level>{level}</level>\n"
        "  <suggestion>Filter the reply.</suggestion>\n"
        "</vuln>\n"
    )


@pytest.mark.parametrize(
    "level,expected",
    [
        ("High", "High"),
        ("critical", "Critical"),
        ("MEDIUM", "Medium"),
        ("Low", "Low"),
        ("High (CVSS 8.1)", "High"),
        ("9.8", "Critical"),
        ("7.5", "High"),
        ("CVSS 6.1", "Medium"),
        (
            "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        ),
        ("CVSS v3.1: 9.1", "Critical"),
        ("3.7", "Low"),
        ("严重", "Critical"),
        ("高危", "High"),
        ("中危", "Medium"),
        ("低危", "Low"),
        ("Informational", "Informational"),
        ("42", "42"),
    ],
)
def test_normalize_level(level, expected):
    assert _normalize_level(level) == expected


def test_missing_level_still_defaults_to_medium():
    text = vuln("x").replace("  <level>x</level>\n", "")
    assert _extract_vuln_blocks(text)[0]["level"] == "Medium"


@pytest.mark.parametrize("level", ["High", "8.8", "CVSS 7.5", "高危"])
def test_high_findings_score_the_same_however_the_level_is_written(level):
    report = generate_report_from_xml(vuln(level))

    assert report.results[0].level == "High"
    assert report.risk_type == "high"
    assert report.score == 85
