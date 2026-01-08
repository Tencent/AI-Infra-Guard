"""
Edit 工具 - 文件编辑
严格替换（默认匹配唯一片段，replace_all 可多处修改），输出统一 Diff
"""
import os
from typing import Any, Optional, List, Generator
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.path_utils import validate_path, resolve_path
from utils.file_utils import generate_unified_diff, trim_diff_indentation, safe_read_file


def levenshtein_distance(a: str, b: str) -> int:
    """计算两个字符串的编辑距离"""
    if a == "" or b == "":
        return max(len(a), len(b))
    
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(
                dp[i-1][j] + 1,      # 删除
                dp[i][j-1] + 1,      # 插入
                dp[i-1][j-1] + cost  # 替换
            )
    
    return dp[m][n]


def simple_replacer(content: str, find: str) -> Generator[str, None, None]:
    """简单精确匹配"""
    if find in content:
        yield find


def line_trimmed_replacer(content: str, find: str) -> Generator[str, None, None]:
    """按行去除首尾空格后匹配"""
    original_lines = content.split('\n')
    search_lines = find.split('\n')
    
    if search_lines and search_lines[-1] == '':
        search_lines.pop()
    
    for i in range(len(original_lines) - len(search_lines) + 1):
        matches = True
        for j in range(len(search_lines)):
            if original_lines[i + j].strip() != search_lines[j].strip():
                matches = False
                break
        
        if matches:
            # 计算匹配的原始字符串
            start_idx = sum(len(original_lines[k]) + 1 for k in range(i))
            matched_lines = original_lines[i:i + len(search_lines)]
            yield '\n'.join(matched_lines)


def block_anchor_replacer(content: str, find: str) -> Generator[str, None, None]:
    """块锚点匹配 - 使用首尾行作为锚点"""
    original_lines = content.split('\n')
    search_lines = find.split('\n')
    
    if len(search_lines) < 3:
        return
    
    if search_lines and search_lines[-1] == '':
        search_lines.pop()
    
    first_line = search_lines[0].strip()
    last_line = search_lines[-1].strip()
    
    candidates = []
    for i in range(len(original_lines)):
        if original_lines[i].strip() != first_line:
            continue
        
        for j in range(i + 2, len(original_lines)):
            if original_lines[j].strip() == last_line:
                candidates.append((i, j))
                break
    
    if not candidates:
        return
    
    # 选择最佳匹配
    best_match = None
    best_similarity = -1
    
    for start, end in candidates:
        block_lines = original_lines[start:end + 1]
        
        # 计算相似度
        similarity = 0
        lines_to_check = min(len(search_lines) - 2, len(block_lines) - 2)
        
        if lines_to_check > 0:
            for k in range(1, lines_to_check + 1):
                orig_line = original_lines[start + k].strip()
                search_line = search_lines[k].strip()
                max_len = max(len(orig_line), len(search_line))
                if max_len == 0:
                    continue
                dist = levenshtein_distance(orig_line, search_line)
                similarity += 1 - dist / max_len
            similarity /= lines_to_check
        else:
            similarity = 1.0
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = (start, end)
    
    if best_match and best_similarity >= 0.3:
        start, end = best_match
        yield '\n'.join(original_lines[start:end + 1])


def whitespace_normalized_replacer(content: str, find: str) -> Generator[str, None, None]:
    """空白标准化匹配"""
    def normalize(text: str) -> str:
        import re
        return re.sub(r'\s+', ' ', text).strip()
    
    normalized_find = normalize(find)
    lines = content.split('\n')
    
    for line in lines:
        if normalize(line) == normalized_find:
            yield line


def multi_occurrence_replacer(content: str, find: str) -> Generator[str, None, None]:
    """多次出现匹配器"""
    start = 0
    while True:
        idx = content.find(find, start)
        if idx == -1:
            break
        yield find
        start = idx + len(find)


def find_replacement(content: str, old_string: str, replace_all: bool = False) -> tuple[str, Optional[str]]:
    """
    查找并替换内容
    
    Args:
        content: 原始内容
        old_string: 要替换的字符串
        replace_all: 是否替换所有匹配
        
    Returns:
        (找到的字符串, 错误信息)
    """
    replacers = [
        simple_replacer,
        line_trimmed_replacer,
        block_anchor_replacer,
        whitespace_normalized_replacer,
        multi_occurrence_replacer,
    ]
    
    not_found = True
    
    for replacer in replacers:
        for search in replacer(content, old_string):
            idx = content.find(search)
            if idx == -1:
                continue
            
            not_found = False
            
            if replace_all:
                return search, None
            
            # 检查是否有多个匹配
            last_idx = content.rfind(search)
            if idx != last_idx:
                continue
            
            return search, None
    
    if not_found:
        return "", "oldString not found in content"
    
    return "", "Found multiple matches for oldString. Provide more surrounding lines to identify the correct match."


@register_tool
def edit(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    编辑文件内容
    
    Args:
        file_path: 文件路径
        old_string: 要替换的内容
        new_string: 替换后的内容
        replace_all: 是否替换所有匹配（默认 False，只替换唯一匹配）
        context: 工具上下文
        
    Returns:
        包含执行结果的字典
    """
    try:
        # 验证参数
        if old_string == new_string:
            return {
                "success": False,
                "error": "old_string and new_string must be different"
            }
        
        # 解析和验证路径
        root = context.folder if context else os.getcwd()
        is_valid, resolved_path, error = validate_path(file_path, root)
        
        if not is_valid:
            return {
                "success": False,
                "error": error
            }
        
        # 处理创建新文件的情况
        if old_string == "":
            # 创建新文件或覆写
            parent_dir = os.path.dirname(resolved_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            
            content_old = ""
            if os.path.exists(resolved_path):
                content, err = safe_read_file(resolved_path)
                if err:
                    return {"success": False, "error": err}
                content_old = content or ""
            
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(new_string)
            
            diff = generate_unified_diff(content_old, new_string, file_path)
            diff = trim_diff_indentation(diff)
            
            return {
                "success": True,
                "title": os.path.basename(resolved_path),
                "diff": diff,
                "message": "File created/overwritten successfully"
            }
        
        # 读取现有文件
        if not os.path.exists(resolved_path):
            return {
                "success": False,
                "error": f"File not found: {resolved_path}"
            }
        
        if not os.path.isfile(resolved_path):
            return {
                "success": False,
                "error": f"Path is not a file: {resolved_path}"
            }
        
        content_old, err = safe_read_file(resolved_path)
        if err:
            return {"success": False, "error": err}
        
        # 规范化换行符
        content_old = content_old.replace('\r\n', '\n')
        old_string = old_string.replace('\r\n', '\n')
        new_string = new_string.replace('\r\n', '\n')
        
        # 查找要替换的内容
        search, error = find_replacement(content_old, old_string, replace_all)
        if error:
            return {
                "success": False,
                "error": error
            }
        
        # 执行替换
        if replace_all:
            content_new = content_old.replace(search, new_string)
        else:
            idx = content_old.find(search)
            content_new = content_old[:idx] + new_string + content_old[idx + len(search):]
        
        # 写入文件
        with open(resolved_path, 'w', encoding='utf-8') as f:
            f.write(content_new)
        
        # 生成 diff
        diff = generate_unified_diff(content_old, content_new, file_path)
        diff = trim_diff_indentation(diff)
        
        # 统计变更
        old_lines = content_old.split('\n')
        new_lines = content_new.split('\n')
        additions = sum(1 for line in new_lines if line not in old_lines)
        deletions = sum(1 for line in old_lines if line not in new_lines)
        
        logger.info(f"Edited file: {resolved_path} (+{additions}/-{deletions})")
        
        return {
            "success": True,
            "title": os.path.basename(resolved_path),
            "diff": diff,
            "additions": additions,
            "deletions": deletions,
        }
        
    except Exception as e:
        logger.error(f"Error editing file: {e}")
        return {
            "success": False,
            "error": f"Error editing file: {str(e)}"
        }

