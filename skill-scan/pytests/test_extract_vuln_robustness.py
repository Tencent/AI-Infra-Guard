"""Tests for VulnerabilityExtractor tolerance of common model quirks.

Two failure modes were observed in production traffic against the same
target Skill:

1. A model wraps ``<desc>``/``<suggestion>`` content in a ``<![CDATA[ ... ]]>``
   section on its own initiative (not requested by the prompt). The
   unstripped markers used to leak all the way into the SARIF
   ``properties.description`` field and were displayed verbatim by
   downstream consumers (e.g. ClawHub's security-audit page).
2. A model renames a required tag to a close synonym (``<description>``
   instead of the documented ``<desc>``), causing ``_parse_vuln_block`` to
   silently drop an otherwise valid finding.

Both are regression-tested here using the exact shapes seen in the wild.
"""

from skill_scan.utils.extract_vuln import VulnerabilityExtractor


def test_cdata_wrapper_is_stripped_from_desc_and_suggestion():
    text = """
<vuln>
  <title>Bearer token transmission to an unrestricted and non-TLS endpoint</title>
  <desc><![CDATA[
## Vulnerability Details
**Risk Level**: High

### Technical Analysis

The token is sent over plain HTTP.
  ]]></desc>
  <risk_type>T09: Insecure Skill Coding Practices</risk_type>
  <level>High</level>
  <suggestion><![CDATA[
## Remediation Suggestions

- Require HTTPS for all connections.
  ]]></suggestion>
</vuln>
"""
    findings = VulnerabilityExtractor().extract_vulnerabilities(text)
    assert len(findings) == 1
    finding = findings[0]
    assert "<![CDATA[" not in finding["description"]
    assert "]]>" not in finding["description"]
    assert finding["description"].startswith("## Vulnerability Details")
    assert "<![CDATA[" not in finding["suggestion"]
    assert finding["suggestion"].startswith("## Remediation Suggestions")


def test_description_tag_is_accepted_as_desc_alias():
    text = """
<vuln>
  <title>Hardcoded alarm code example</title>
  <description>Alarm disarm example hardcodes a 4-digit PIN.</description>
  <risk_type>T09: Insecure Skill Coding Practices</risk_type>
  <level>Medium</level>
  <remediation>Replace the example PIN with a non-secret placeholder.</remediation>
</vuln>
"""
    findings = VulnerabilityExtractor().extract_vulnerabilities(text)
    assert len(findings) == 1
    finding = findings[0]
    assert finding["description"] == "Alarm disarm example hardcodes a 4-digit PIN."
    assert finding["suggestion"] == "Replace the example PIN with a non-secret placeholder."


def test_documented_tag_names_still_take_priority_over_aliases():
    text = """
<vuln>
  <title>t</title>
  <desc>documented tag wins</desc>
  <description>alias should be ignored</description>
  <risk_type>T09</risk_type>
  <level>Low</level>
  <suggestion>use suggestion</suggestion>
</vuln>
"""
    findings = VulnerabilityExtractor().extract_vulnerabilities(text)
    assert findings[0]["description"] == "documented tag wins"
    assert findings[0]["suggestion"] == "use suggestion"


def test_non_cdata_content_is_left_untouched():
    text = """
<vuln>
  <title>plain text finding</title>
  <desc>Some plain Markdown, no CDATA here.</desc>
  <risk_type>T09</risk_type>
  <level>Low</level>
  <suggestion>Do the obvious thing.</suggestion>
</vuln>
"""
    findings = VulnerabilityExtractor().extract_vulnerabilities(text)
    assert findings[0]["description"] == "Some plain Markdown, no CDATA here."
    assert findings[0]["suggestion"] == "Do the obvious thing."


def test_missing_title_still_fails_closed():
    """Aliases must not paper over a genuinely missing required field."""
    text = """
<vuln>
  <description>only a description, no title/risk_type at all</description>
</vuln>
"""
    findings = VulnerabilityExtractor().extract_vulnerabilities(text)
    assert findings == []
