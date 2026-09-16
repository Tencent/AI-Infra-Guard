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

"""
aig-skill-scan vulnerability information extractor

Extracts vulnerability results from the <vuln> XML emitted by the LLM and
converts them into a results list. Mirrors mcp-scan's VulnerabilityExtractor
implementation.
"""

from __future__ import annotations

import json
import re
from typing import Any

VALID_VERDICTS = frozenset({"normal", "suspicious", "malicious"})

# Some models wrap XML tag content in a CDATA section on their own
# initiative even though the schema only asks for raw Markdown text — a
# habit picked up from general "produce valid XML" training rather than an
# instruction we give. Strip it so the wrapper markers never leak into a
# finding's description/suggestion text.
_CDATA_PATTERN = re.compile(r"^\s*<!\[CDATA\[\s*(.*?)\s*\]\]>\s*$", re.DOTALL)

# A model occasionally renames a required tag to a close synonym (e.g.
# ``<description>`` instead of the documented ``<desc>``). Accept the most
# common synonyms instead of silently discarding the whole finding.
_TAG_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("title", "name"),
    "desc": ("desc", "description"),
    "suggestion": ("suggestion", "remediation", "recommendation"),
}


def _strip_cdata(value: str) -> str:
    """Unwrap a ``<![CDATA[ ... ]]>`` section if the whole value is one."""
    match = _CDATA_PATTERN.match(value)
    return match.group(1) if match else value


def _json_objects(text: str):
    """Yield JSON objects from a whole response or fenced JSON blocks."""
    candidates = [text.strip()]
    candidates.extend(
        re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    )
    for candidate in candidates:
        try:
            payload = json.loads(candidate.strip())
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict):
            yield payload


def extract_explicit_verdict(text: str) -> str | None:
    """Extract an explicit XML or whole-response JSON project verdict."""
    match = re.search(r"<verdict>\s*([^<]+?)\s*</verdict>", text, re.IGNORECASE)
    if match:
        verdict = match.group(1).strip().lower()
        return verdict if verdict in VALID_VERDICTS else None

    for payload in _json_objects(text):
        verdict = payload.get("verdict", payload.get("project_verdict"))
        if not isinstance(verdict, str):
            continue
        verdict = verdict.strip().lower()
        if verdict in VALID_VERDICTS:
            return verdict
    return None


def extract_verdict(
    text: str, vulnerabilities: list[dict[str, Any]] | None = None
) -> str | None:
    """Extract the project-level verdict without conflating severity and intent.

    The fallback keeps legacy responses usable: an empty response is normal
    and a response with findings is suspicious. A High severity issue alone
    is not evidence that the Skill itself is malicious.
    """
    verdict = extract_explicit_verdict(text)
    if verdict:
        return verdict
    if re.search(r"<empty\s*/?>", text, re.IGNORECASE):
        return "normal"
    if vulnerabilities:
        return "suspicious"
    return None


class VulnerabilityExtractor:
    """Vulnerability information extractor"""

    def __init__(self):
        self.pattern = re.compile(
            r"<vuln>\s*(.*?)\s*</vuln>",
            re.DOTALL,  # Make . match all characters, including newlines
        )

    def extract_vulnerabilities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract all vulnerability information from the text.

        Args:
            text: Text containing vulnerability information

        Returns:
            A list of vulnerability information dicts. Each dict has the
            required keys ``title``/``description``/``risk_type``/``level``/
            ``suggestion``, plus optional ``file``/``line_start``/``line_end``
            (int) when the LLM provided structured location tags.
        """
        vulnerabilities = []

        # Find all vuln blocks
        vuln_blocks = self.pattern.findall(text)

        for i, block in enumerate(vuln_blocks, 1):
            try:
                vuln_info = self._parse_vuln_block(block, i)
                if vuln_info:
                    vulnerabilities.append(vuln_info)
            except Exception as e:
                print(f"Error parsing vulnerability block #{i}: {e}")
                continue

        if vulnerabilities:
            return vulnerabilities

        for payload in _json_objects(text):
            findings = payload.get("findings")
            if not isinstance(findings, list):
                continue
            for index, finding in enumerate(findings, 1):
                parsed = self._parse_json_finding(finding, index)
                if parsed:
                    vulnerabilities.append(parsed)
            if vulnerabilities:
                break

        return vulnerabilities

    @staticmethod
    def _parse_json_finding(finding: Any, index: int) -> dict[str, Any] | None:
        """Normalize common model-emitted JSON finding fields to legacy results."""
        if not isinstance(finding, dict):
            return None

        def first(*keys: str) -> str:
            for key in keys:
                value = finding.get(key)
                if value is not None and str(value).strip():
                    return str(value).strip()
            return ""

        file_path = first("file", "file_path", "filePath")
        risk_type = first("risk_type", "riskType", "category")
        title = first("title", "name")
        if not title:
            title = risk_type or f"Security finding #{index}"
            if file_path:
                title += f" in {file_path}"

        description = first("description", "desc")
        if not description:
            sections = []
            for label, keys in (
                ("Evidence", ("raw_snippet", "rawSnippet", "originalSnippet")),
                ("Trigger condition", ("trigger_condition", "triggerCondition")),
                ("Attacker control point", ("attacker_control_point", "attackerControlPoint")),
                ("Trust boundary", ("trust_boundary_cross", "trustBoundary")),
                ("Impact", ("impact",)),
            ):
                value = first(*keys)
                if value:
                    sections.append(f"### {label}\n\n{value}")
            description = "\n\n".join(sections)

        if not risk_type or not description:
            return None

        result: dict[str, Any] = {
            "title": title,
            "description": description,
            "risk_type": risk_type,
            "level": first("level", "risk_level", "riskLevel"),
            "suggestion": first("suggestion", "suggested_fix", "suggestedFix"),
        }
        if file_path:
            result["file"] = file_path

        line_text = first("line_start", "lineStart", "line_number", "lineNumber", "line")
        line_numbers = [int(value) for value in re.findall(r"\d+", line_text)]
        if line_numbers:
            result["line_start"] = line_numbers[0]
            result["line_end"] = line_numbers[-1]
        return result

    def _parse_vuln_block(self, block: str, index: int) -> dict[str, Any] | None:
        """Parse a single vuln block"""

        # Extract each field (tolerating a handful of tag-name synonyms)
        title = self._extract_field(block, "title")
        desc = self._extract_field(block, "desc")
        risk_type = self._extract_tag_content(block, "risk_type")
        level = self._extract_tag_content(block, "level")
        suggestion = self._extract_field(block, "suggestion")
        # Optional structured location fields (used to populate SARIF
        # physicalLocation when not running in --aig-mode)
        file_path = self._extract_tag_content(block, "file")
        line_start = self._extract_tag_content(block, "line_start")
        line_end = self._extract_tag_content(block, "line_end")

        # Validate required fields
        if not all([title, desc, risk_type]):
            print(f"Vulnerability block #{index} is missing required fields, skipping")
            return None

        result: dict[str, Any] = {
            "title": title.strip(),
            "description": desc.strip(),
            "risk_type": risk_type.strip(),
            "level": (level or "").strip(),
            "suggestion": (suggestion or "").strip(),
        }

        if file_path and file_path.strip():
            result["file"] = file_path.strip()
        if line_start and line_start.strip().lstrip("-").isdigit():
            result["line_start"] = int(line_start.strip())
        if line_end and line_end.strip().lstrip("-").isdigit():
            result["line_end"] = int(line_end.strip())

        return result

    def _extract_tag_content(self, text: str, tag: str) -> str | None:
        """Extract the content of the given tag, with any CDATA wrapper stripped."""
        pattern = re.compile(rf"<{tag}>\s*(.*?)\s*</{tag}>", re.DOTALL)
        match = pattern.search(text)
        if not match:
            return None
        return _strip_cdata(match.group(1))

    def _extract_field(self, block: str, canonical_tag: str) -> str | None:
        """Extract a field trying its documented tag name first, then aliases."""
        for tag in _TAG_ALIASES.get(canonical_tag, (canonical_tag,)):
            value = self._extract_tag_content(block, tag)
            if value is not None:
                return value
        return None


def extract_result(text: str) -> dict | None:
    """Extract the first vulnerability result from LLM output (fallback function).

    Parses the <vuln> XML structure and returns the first vulnerability's
    {title, description, risk_type, level, suggestion} dict, or None if
    parsing fails.
    """
    extractor = VulnerabilityExtractor()
    results = extractor.extract_vulnerabilities(text)
    return results[0] if results else None
