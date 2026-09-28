"""Tests for JSON/JSONL experiment reporting."""

from pikit import report
from pikit.config import ExperimentConfig
from pikit.matrix import run


def test_report_summary_and_rendering(tmp_path):
    rows = [
        {
            "agent": "openclaw",
            "attack": "combined",
            "channel": "webpage",
            "defense": "none",
            "success": True,
            "signals": ["tainted_delivered", "sink_fired"],
            "trace": "trace",
        }
    ]
    assert report.summarize(rows)["success_rate"] == 1.0
    assert "openclaw" in report.markdown(rows)
    assert "<details>" in report.html_report(rows)


def test_report_accepts_experiment_result_objects():
    result = run(ExperimentConfig(target_spec="mock"))[0]
    assert "pikit experiment report" in report.markdown([result])
