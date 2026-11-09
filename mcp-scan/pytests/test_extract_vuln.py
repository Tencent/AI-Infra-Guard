from mcp_scan.utils.extract_vuln import VulnerabilityExtractor, extract_result


def test_finding_without_optional_level_and_suggestion_is_kept():
    # title/desc/risk_type 是必填校验的全部字段；模型省略 level/suggestion 时，
    # 整条发现不应被丢弃。
    text = "<vuln><title>t</title><desc>d</desc><risk_type>r</risk_type></vuln>"
    results = VulnerabilityExtractor().extract_vulnerabilities(text)
    assert results == [
        {"title": "t", "description": "d", "risk_type": "r", "level": "", "suggestion": ""}
    ]


def test_finding_without_suggestion_is_kept():
    text = (
        "<vuln><title>t</title><desc>d</desc><risk_type>r</risk_type>"
        "<level>High</level></vuln>"
    )
    results = VulnerabilityExtractor().extract_vulnerabilities(text)
    assert len(results) == 1
    assert results[0]["level"] == "High"
    assert results[0]["suggestion"] == ""


def test_finding_missing_required_field_is_still_dropped():
    text = "<vuln><title>t</title><desc>d</desc></vuln>"
    assert VulnerabilityExtractor().extract_vulnerabilities(text) == []


def test_extract_result_returns_first_finding():
    text = (
        "<vuln><title>a</title><desc>d1</desc><risk_type>r</risk_type></vuln>"
        "<vuln><title>b</title><desc>d2</desc><risk_type>r</risk_type></vuln>"
    )
    assert extract_result(text)["title"] == "a"
