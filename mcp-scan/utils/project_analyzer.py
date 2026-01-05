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


def calc_mcp_score(issues: list) -> int:
    """
    根据漏洞列表计算安全分数（0-100）
    
    Args:
        issues: 漏洞列表，每个漏洞应包含 risk_type 字段
        
    Returns:
        安全评分（0-100的整数）
    """
    if not issues:
        return 100

    score = 100
    for item in issues:
        # 兼容字典和对象两种格式
        level = item.get("level", "").lower() if isinstance(item, dict) else getattr(item, "level", "").lower()
        if level in ['critical', '严重']:
            score -= 100
        elif level in ["high", "高危"]:
            score -= 40
        elif level in ["medium", "中危"]:
            score -= 25
        else:
            score -= 10

    return max(0, score)
