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
skill-scan project analysis utility module

Analyzes the programming language distribution of a project and computes a
security score. The scoring algorithm mirrors mcp-scan's calc_mcp_score, but
is adapted to skill-scan's malicious/suspicious/normal three-tier verdict
system.
"""

from collections import defaultdict
from pathlib import Path

from .loging import logger


def classify_language(ext: str) -> str:
    """Map a file extension to a programming language."""
    ext_to_lang = {
        ".go": "Go",
        ".py": "Python",
        ".java": "Java",
        ".rs": "Rust",
        ".php": "PHP",
        ".rb": "Ruby",
        ".swift": "Swift",
        ".c": "C",
        ".h": "C",
        ".cpp": "C++",
        ".hpp": "C++",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".html": "HTML",
        ".css": "CSS",
        ".sql": "SQL",
        ".sh": "Shell",
        ".md": "Markdown",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".toml": "TOML",
    }
    return ext_to_lang.get(ext, "")


def analyze_language(directory: str) -> dict:
    """Walk the directory and count files per programming language."""
    stats = defaultdict(int)
    dir_path = Path(directory)

    try:
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                lang = classify_language(ext)
                if lang:
                    stats[lang] += 1
    except Exception as e:
        logger.warning(f"Error analyzing language: {e}")

    return dict(stats)


def get_top_language(stats: dict) -> str:
    """Return the programming language with the highest file count."""
    if not stats:
        return "Other"
    sorted_langs = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    return sorted_langs[0][0]


def calc_skill_score(issues: list) -> int:
    """Compute a security score (0-100) from the vulnerability list.

    The deduction rules mirror mcp-scan's calc_mcp_score:
    - Critical / "严重": -100
    - High / "高危": -40
    - Medium / "中危": -25
    - Other: -10

    Max score is 100, min is 0; an empty list returns 100.
    """
    if not issues:
        return 100

    score = 100
    for item in issues:
        # Support both dict and object formats
        level = (
            item.get("level", "").lower()
            if isinstance(item, dict)
            else getattr(item, "level", "").lower()
        )
        if level in ["critical", "严重"]:
            score -= 100
        elif level in ["high", "高危"]:
            score -= 40
        elif level in ["medium", "中危"]:
            score -= 25
        else:
            score -= 10

    return max(0, score)
