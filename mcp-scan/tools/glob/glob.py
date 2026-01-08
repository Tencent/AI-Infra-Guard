"""
Glob 工具 - 基于 glob / os.walk 匹配文件
限制 200 条结果，并提示截断，排序遵循修改时间
"""
import os
import fnmatch
from typing import Any, Optional, List, Tuple
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.path_utils import validate_path, should_ignore_path, IGNORE_DIRECTORIES


MAX_RESULTS = 200


def glob_files(
    pattern: str,
    root_path: str,
    ignore_patterns: Optional[set] = None
) -> List[Tuple[str, float]]:
    """
    使用 glob 模式匹配文件
    
    Args:
        pattern: glob 模式
        root_path: 搜索根目录
        ignore_patterns: 忽略的模式
        
    Returns:
        (文件路径, 修改时间) 元组列表
    """
    results = []
    ignore = IGNORE_DIRECTORIES.copy()
    if ignore_patterns:
        ignore.update(ignore_patterns)
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # 过滤忽略的目录
        dirnames[:] = [d for d in dirnames if d not in ignore and not d.startswith('.')]
        
        for filename in filenames:
            if filename.startswith('.'):
                continue
            
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root_path)
            
            # 检查是否匹配模式
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(filename, pattern):
                try:
                    mtime = os.path.getmtime(full_path)
                except OSError:
                    mtime = 0
                results.append((full_path, mtime))
                
                if len(results) >= MAX_RESULTS + 1:
                    return results
    
    return results


@register_tool
def glob(
    pattern: str,
    path: Optional[str] = None,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    使用 glob 模式匹配文件
    
    Args:
        pattern: glob 模式（如 "*.py", "**/*.ts"）
        path: 搜索目录（可选，默认为项目根目录）
        context: 工具上下文
        
    Returns:
        包含匹配文件列表的字典
    """
    try:
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
        
        if not os.path.isdir(search_path):
            return {
                "success": False,
                "error": f"Path is not a directory: {search_path}"
            }
        
        # 执行搜索
        results = glob_files(pattern, search_path)
        
        # 检查是否截断
        truncated = len(results) > MAX_RESULTS
        if truncated:
            results = results[:MAX_RESULTS]
        
        # 按修改时间排序（最新在前）
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 构建输出
        file_paths = [r[0] for r in results]
        
        if not file_paths:
            output = "No files found"
        else:
            output_lines = file_paths.copy()
            if truncated:
                output_lines.append("")
                output_lines.append(f"(Results truncated at {MAX_RESULTS} files. Consider using a more specific path or pattern.)")
            output = '\n'.join(output_lines)
        
        logger.info(f"Glob '{pattern}' found {len(file_paths)} files")
        
        return {
            "success": True,
            "title": os.path.relpath(search_path, root) if path else ".",
            "count": len(file_paths),
            "truncated": truncated,
            "files": file_paths,
            "output": output
        }
        
    except Exception as e:
        logger.error(f"Error in glob: {e}")
        return {
            "success": False,
            "error": f"Error searching files: {str(e)}"
        }

