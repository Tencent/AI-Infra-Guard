"""
项目分析工具模块
用于分析项目的编程语言分布和计算安全评分
"""

import math
from pathlib import Path
from collections import defaultdict
from .loging import logger


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
    stats = defaultdict(int)
    dir_path = Path(directory)

    try:
        # 遍历目录下的所有文件
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
    
    Deprecated: Use tools.scan.report.calculate_security_score instead.
    
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
