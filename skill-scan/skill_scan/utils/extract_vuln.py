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

import re
from typing import Any, Optional


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

        return vulnerabilities

    def _parse_vuln_block(self, block: str, index: int) -> dict[str, Any] | None:
        """Parse a single vuln block"""

        # Extract each field
        title = self._extract_tag_content(block, "title")
        desc = self._extract_tag_content(block, "desc")
        risk_type = self._extract_tag_content(block, "risk_type")
        level = self._extract_tag_content(block, "level")
        suggestion = self._extract_tag_content(block, "suggestion")
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
        """Extract the content of the given tag"""
        pattern = re.compile(rf"<{tag}>\s*(.*?)\s*</{tag}>", re.DOTALL)
        match = pattern.search(text)
        return match.group(1) if match else None


def extract_result(text: str) -> Optional[dict]:
    """Extract the first vulnerability result from LLM output (fallback function).

    Parses the <vuln> XML structure and returns the first vulnerability's
    {title, description, risk_type, level, suggestion} dict, or None if
    parsing fails.
    """
    extractor = VulnerabilityExtractor()
    results = extractor.extract_vulnerabilities(text)
    return results[0] if results else None
