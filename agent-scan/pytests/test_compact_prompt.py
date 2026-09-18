"""Regression tests for preserving findings during context compaction."""

from agent_scan.utils.prompt_manager import prompt_manager


def test_compact_template_requires_security_findings_section():
    template = prompt_manager.load_template("compact")

    assert "<security_findings>" in template
    assert "安全发现" in template
    assert "最高优先级" in template
    assert "不可丢弃" in template
