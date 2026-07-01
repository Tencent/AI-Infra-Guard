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
skill-scan 项目分析工具模块

分析项目的编程语言分布和计算安全评分。
评分算法参照 mcp-scan 的 calc_mcp_score，但适配 skill-scan 的
malicious/suspicious/normal 三级评定体系。
"""

from collections import defaultdict
from pathlib import Path

from .loging import logger


def classify_language(ext: str) -> str:
    """将文件扩展名映射到编程语言。"""
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
    """分析目录中的文件，统计各编程语言的文件数量。"""
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
        logger.warning(f"分析语言时出错: {e}")

    return dict(stats)


def get_top_language(stats: dict) -> str:
    """获取文件数量最多的编程语言。"""
    if not stats:
        return "Other"
    sorted_langs = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    return sorted_langs[0][0]


def calc_skill_score(issues: list) -> int:
    """根据漏洞列表计算安全分数（0-100）。

    扣分规则对齐 mcp-scan 的 calc_mcp_score：
    - Critical / "严重": 扣 100 分
    - High / "高危": 扣 40 分
    - Medium / "中危": 扣 25 分
    - 其他: 扣 10 分

    满分 100，最低 0，空列表返回 100。
    """
    if not issues:
        return 100

    score = 100
    for item in issues:
        # 兼容字典和对象两种格式
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
