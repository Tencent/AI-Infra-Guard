"""
Grep 工具 - 调用 ripgrep 或 re 模块搜索文件内容
支持 include 过滤、100 条上限与二进制跳过
"""
import os
import re
import subprocess
import shutil
from typing import Any, Optional, List, Tuple
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.path_utils import validate_path, should_ignore_path, IGNORE_DIRECTORIES
from utils.file_utils import is_binary_file


MAX_RESULTS = 100
MAX_LINE_LENGTH = 2000


def find_ripgrep() -> Optional[str]:
    """查找 ripgrep 可执行文件"""
    return shutil.which('rg')


def grep_with_ripgrep(
    pattern: str,
    search_path: str,
    include: Optional[str] = None
) -> Tuple[List[dict], Optional[str]]:
    """
    使用 ripgrep 搜索
    
    Returns:
        (matches, error)
    """
    rg_path = find_ripgrep()
    if not rg_path:
        return [], "ripgrep not found"
    
    args = [
        rg_path,
        '-nH',  # 显示行号和文件名
        '--field-match-separator=|',
        '--regexp', pattern
    ]
    
    if include:
        args.extend(['--glob', include])
    
    args.append(search_path)
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 1:
            # 没有匹配
            return [], None
        
        if result.returncode != 0:
            return [], f"ripgrep error: {result.stderr}"
        
        matches = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('|', 2)
            if len(parts) < 3:
                continue
            
            file_path, line_num_str, line_text = parts
            try:
                line_num = int(line_num_str)
            except ValueError:
                continue
            
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                mtime = 0
            
            matches.append({
                'path': file_path,
                'line_num': line_num,
                'line_text': line_text,
                'mtime': mtime
            })
            
            if len(matches) >= MAX_RESULTS + 1:
                break
        
        return matches, None
        
    except subprocess.TimeoutExpired:
        return [], "ripgrep timed out"
    except Exception as e:
        return [], str(e)


def grep_with_re(
    pattern: str,
    search_path: str,
    include: Optional[str] = None
) -> Tuple[List[dict], Optional[str]]:
    """
    使用 Python re 模块搜索
    
    Returns:
        (matches, error)
    """
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return [], f"Invalid regex pattern: {e}"
    
    matches = []
    ignore = IGNORE_DIRECTORIES
    
    for dirpath, dirnames, filenames in os.walk(search_path):
        # 过滤忽略的目录
        dirnames[:] = [d for d in dirnames if d not in ignore and not d.startswith('.')]
        
        for filename in filenames:
            if filename.startswith('.'):
                continue
            
            # 检查 include 模式
            if include:
                import fnmatch
                if not fnmatch.fnmatch(filename, include):
                    continue
            
            full_path = os.path.join(dirpath, filename)
            
            # 跳过二进制文件
            if is_binary_file(full_path):
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            try:
                                mtime = os.path.getmtime(full_path)
                            except OSError:
                                mtime = 0
                            
                            matches.append({
                                'path': full_path,
                                'line_num': line_num,
                                'line_text': line.rstrip('\n\r'),
                                'mtime': mtime
                            })
                            
                            if len(matches) >= MAX_RESULTS + 1:
                                return matches, None
            except (IOError, OSError):
                continue
    
    return matches, None


@register_tool
def grep(
    pattern: str,
    path: Optional[str] = None,
    include: Optional[str] = None,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    在文件中搜索匹配的内容
    
    Args:
        pattern: 正则表达式模式
        path: 搜索目录（可选，默认为项目根目录）
        include: 文件名模式过滤（如 "*.py", "*.{ts,tsx}"）
        context: 工具上下文
        
    Returns:
        包含匹配结果的字典
    """
    try:
        if not pattern:
            return {
                "success": False,
                "error": "pattern is required"
            }
        
        # 确定搜索根目录
        root = context.folder if context else os.getcwd()
        
        if path:
            is_valid, search_path, error = validate_path(path, root)
            if not is_valid:
                return {
                    "success": False,
                    "error": error
                }
        else:
            search_path = root
        
        # 尝试使用 ripgrep，失败则使用 re
        matches, error = grep_with_ripgrep(pattern, search_path, include)
        
        if error and "ripgrep not found" in error:
            logger.info("ripgrep not found, falling back to re module")
            matches, error = grep_with_re(pattern, search_path, include)
        
        if error:
            return {
                "success": False,
                "error": error
            }
        
        # 检查是否截断
        truncated = len(matches) > MAX_RESULTS
        if truncated:
            matches = matches[:MAX_RESULTS]
        
        # 按修改时间排序
        matches.sort(key=lambda x: x['mtime'], reverse=True)
        
        if not matches:
            return {
                "success": True,
                "title": pattern,
                "matches": 0,
                "truncated": False,
                "output": "No matches found"
            }
        
        # 构建输出
        output_lines = [f"Found {len(matches)} matches"]
        
        current_file = ""
        for match in matches:
            if current_file != match['path']:
                if current_file:
                    output_lines.append("")
                current_file = match['path']
                output_lines.append(f"{match['path']}:")
            
            line_text = match['line_text']
            if len(line_text) > MAX_LINE_LENGTH:
                line_text = line_text[:MAX_LINE_LENGTH] + "..."
            
            output_lines.append(f"  Line {match['line_num']}: {line_text}")
        
        if truncated:
            output_lines.append("")
            output_lines.append(f"(Results truncated at {MAX_RESULTS} matches. Consider using a more specific path or pattern.)")
        
        output = '\n'.join(output_lines)
        
        logger.info(f"Grep '{pattern}' found {len(matches)} matches")
        
        return {
            "success": True,
            "title": pattern,
            "matches": len(matches),
            "truncated": truncated,
            "output": output
        }
        
    except Exception as e:
        logger.error(f"Error in grep: {e}")
        return {
            "success": False,
            "error": f"Error searching: {str(e)}"
        }

