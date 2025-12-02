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
    
    评分规则：
    - 无漏洞时得分为100
    - 高危/严重漏洞权重为0.7
    - 中危漏洞权重为0.5
    - 低危漏洞权重为0.3
    - 最终得分 = 100 - 加权风险比例 * 100
    
    Args:
        issues: 漏洞列表，每个漏洞应包含 risk_type 字段
        
    Returns:
        安全评分（0-100的整数）
    """
    total = len(issues)
    if total == 0:
        return 100

    high = 0
    middle = 0
    low = 0

    for item in issues:
        # 兼容字典和对象两种格式
        risk_type = item.get("risk_type", "").lower() if isinstance(item, dict) else getattr(item, "risk_type",
                                                                                             "").lower()

        if risk_type in ["high", "critical", "高危", "严重"]:
            high += 1
        elif risk_type in ["medium", "中危"]:
            middle += 1
        else:
            low += 1

    # 计算加权风险比例
    weighted_risk = (
            (high / total) * 0.7 +
            (middle / total) * 0.5 +
            (low / total) * 0.3
    )

    # 计算安全评分（百分制）
    safety_score = int(100 - weighted_risk * 100)

    # 确保评分在0-100范围内
    safety_score = max(0, min(100, safety_score))

    return int(round(safety_score))
