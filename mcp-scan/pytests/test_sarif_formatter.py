import pytest

from mcp_scan.utils.sarif_formatter import to_sarif


def finding(**overrides):
    return {
        "title": "Unsafe command construction",
        "description": "The tool interpolates an argument into a shell command.",
        "risk_type": "MCP05",
        "level": "high",
        "file": "server.py",
        "line_start": 12,
        **overrides,
    }


@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize(
    "suggestion", ["Pass an argument array.", "使用参数数组。\n保留输入校验。"]
)
def test_text_remediation_is_visible_without_claiming_an_applicable_fix(language, suggestion):
    report = to_sarif({"results": [finding(suggestion=suggestion)]}, language=language)
    result = report["runs"][0]["results"][0]

    # SARIF 2.1.0 section 3.55.3 requires at least one artifactChange in a fix.
    # A model's prose recommendation does not identify any replacement edits.
    assert "fixes" not in result
    assert "Unsafe command construction" in result["message"]["text"]
    assert suggestion in result["message"]["text"]
    assert result["properties"]["suggestion"] == suggestion


@pytest.mark.parametrize("suggestion", [None, ""])
def test_missing_remediation_keeps_the_original_message(suggestion):
    report = to_sarif({"results": [finding(suggestion=suggestion)]})
    result = report["runs"][0]["results"][0]

    assert result["message"]["text"] == "Unsafe command construction"
    assert "fixes" not in result
    assert "suggestion" not in result["properties"]


def test_remediation_does_not_change_alert_identity_or_location():
    original = to_sarif({"results": [finding()]})["runs"][0]["results"][0]
    with_remediation = to_sarif({"results": [finding(suggestion="Use execFile.")]})["runs"][0][
        "results"
    ][0]

    for key in ("ruleId", "level", "locations", "partialFingerprints"):
        assert with_remediation[key] == original[key]
