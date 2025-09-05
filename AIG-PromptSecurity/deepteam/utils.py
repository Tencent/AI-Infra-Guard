import re
from typing import Literal

def judge_language(text: str, chinese_threshold: int = 0.5, english_threshold: int = 0.5) -> Literal["default", "chinese", "english"]:
    if not text or not text.strip():
        return 'default'
    
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    english_pattern = re.compile(r'[A-Za-z]')
    
    chinese_chars = chinese_pattern.findall(text)
    english_chars = english_pattern.findall(text)
    
    total_chars = len([c for c in text if c.strip()])
    
    if total_chars == 0:
        return 'default'
    
    chinese_ratio = len(chinese_chars) / total_chars
    english_ratio = len(english_chars) / total_chars
    
    if chinese_ratio >= chinese_threshold:
        return 'chinese'
    elif english_ratio >= english_threshold:
        return 'english'
    else:
        return 'default'
