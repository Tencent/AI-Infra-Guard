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
项目分析工具模块
用于分析项目的编程语言分布和计算安全评分
"""

import os
from collections import defaultdict

from .logging import logger
from .path_utils import is_path_within, should_ignore_path


def classify_language(ext: str) -> str:
    """
    将文件扩展名映射到编程语言
    
    Args:
        ext: 文件扩展名（如 .py, .java）
        
    Returns:
        编程语言名称，如果无法识别则返回空字符串
    """
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
    }
    return ext_to_lang.get(ext, "")


def analyze_language(directory: str) -> dict:
    """
    分析目录中的文件，统计各编程语言的文件数量
    
    Args:
        directory: 要分析的目录路径
        
    Returns:
        字典，键为编程语言名称，值为该语言的文件数量
    """
    if not directory or not os.path.isdir(directory):
        return {}

    stats = defaultdict(int)
    real_root = os.path.realpath(directory)
    visited_dirs: set[str] = set()

    try:
        for dirpath, dirnames, filenames in os.walk(real_root, followlinks=False):
            real_dir = os.path.realpath(dirpath)
            if not is_path_within(real_dir, real_root) or real_dir in visited_dirs:
                dirnames[:] = []
                continue
            visited_dirs.add(real_dir)
            dirnames[:] = [
                d
                for d in dirnames
                if not should_ignore_path(d)
                and is_path_within(os.path.join(dirpath, d), real_root)
            ]
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                if not is_path_within(full_path, real_root) or not os.path.isfile(full_path):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                lang = classify_language(ext)
                if lang:
                    stats[lang] += 1
    except Exception as e:
        logger.warning(f"分析语言时出错: {e}")

    return dict(stats)


def get_top_language(stats: dict) -> str:
    """
    获取文件数量最多的编程语言
    
    Args:
        stats: 语言统计字典（由 analyze_language 返回）
        
    Returns:
        文件数量最多的编程语言名称，如果没有则返回 "Other"
    """
    if not stats:
        return "Other"

    # 按文件数量降序排序
    sorted_langs = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    return sorted_langs[0][0]


def calculate_security_score(issues: list) -> int:
    """
    Calculate security score (0-100) based on vulnerability list.
    
    Deprecated: Use core.report.calculate_security_score instead.
    
    Args:
        issues: List of vulnerabilities, each should contain 'level' field
        
    Returns:
        Security score (0-100 integer)
    """
    if not issues:
        return 100

    score = 100
    for item in issues:
        level = item.get("level", "").lower() if isinstance(item, dict) else getattr(item, "level", "").lower()
        if level in ['critical']:
            score -= 100
        elif level in ["high"]:
            score -= 40
        elif level in ["medium"]:
            score -= 25
        else:
            score -= 10

    return max(0, score)


# Backward compatibility alias (deprecated)
calc_mcp_score = calculate_security_score
