"""
Ls 工具 - 构建目录树展示
默认忽略 node_modules、.git 等目录，并接受额外忽略模式
"""
import os
from typing import Any, Optional, List, Set
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.path_utils import validate_path, IGNORE_DIRECTORIES


MAX_FILES = 100


def build_directory_tree(
    root_path: str,
    ignore_patterns: Optional[Set[str]] = None,
    max_files: int = MAX_FILES
) -> tuple[str, int, bool]:
    """
    构建目录树字符串
    
    Args:
        root_path: 根目录路径
        ignore_patterns: 忽略的目录/文件名模式
        max_files: 最大文件数
        
    Returns:
        (树形字符串, 文件数, 是否截断)
    """
    ignore = IGNORE_DIRECTORIES.copy()
    if ignore_patterns:
        ignore.update(ignore_patterns)
    
    files_collected = []
    dirs_collected = set()
    files_by_dir = {}
    truncated = False
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # 过滤忽略的目录
        dirnames[:] = [d for d in dirnames if d not in ignore and not d.startswith('.')]
        
        rel_dir = os.path.relpath(dirpath, root_path)
        if rel_dir == '.':
            rel_dir = ''
        
        # 添加目录层级
        if rel_dir:
            parts = rel_dir.split(os.sep)
            for i in range(len(parts)):
                partial = os.sep.join(parts[:i+1])
                dirs_collected.add(partial)
        
        # 添加文件
        for filename in filenames:
            if filename.startswith('.'):
                continue
            
            if len(files_collected) >= max_files:
                truncated = True
                break
            
            rel_path = os.path.join(rel_dir, filename) if rel_dir else filename
            files_collected.append(rel_path)
            
            if rel_dir not in files_by_dir:
                files_by_dir[rel_dir] = []
            files_by_dir[rel_dir].append(filename)
        
        if truncated:
            break
    
    # 构建树形结构
    def render_tree(dir_path: str, prefix: str = "") -> List[str]:
        lines = []
        
        # 获取子目录和文件
        subdirs = sorted([
            d for d in dirs_collected
            if os.path.dirname(d) == dir_path and d != dir_path
        ])
        files = sorted(files_by_dir.get(dir_path, []))
        
        # 计算所有条目
        entries = [(d, True) for d in subdirs] + [(f, False) for f in files]
        
        for i, (entry, is_dir) in enumerate(entries):
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            
            if is_dir:
                dirname = os.path.basename(entry)
                lines.append(f"{prefix}{connector}{dirname}/")
                extension = "    " if is_last else "│   "
                lines.extend(render_tree(entry, prefix + extension))
            else:
                lines.append(f"{prefix}{connector}{entry}")
        
        return lines
    
    # 生成输出
    base_name = os.path.basename(root_path) or root_path
    output_lines = [f"{base_name}/"]
    output_lines.extend(render_tree(""))
    
    return '\n'.join(output_lines), len(files_collected), truncated


@register_tool
def ls(
    path: Optional[str] = None,
    ignore: Optional[List[str]] = None,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    列出目录内容（树形结构）
    
    Args:
        path: 目录路径（可选，默认为项目根目录）
        ignore: 额外忽略的模式列表
        context: 工具上下文
        
    Returns:
        包含目录树的字典
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
        
        # 构建忽略模式集合
        ignore_patterns = set(ignore) if ignore else None
        
        # 构建目录树
        tree_output, file_count, truncated = build_directory_tree(
            search_path,
            ignore_patterns,
            MAX_FILES
        )
        
        if truncated:
            tree_output += f"\n\n(Output truncated at {MAX_FILES} files. Use a more specific path to see more.)"
        
        logger.info(f"Listed directory: {search_path} ({file_count} files)")
        
        return {
            "success": True,
            "title": os.path.relpath(search_path, root) if path else ".",
            "count": file_count,
            "truncated": truncated,
            "output": tree_output
        }
        
    except Exception as e:
        logger.error(f"Error listing directory: {e}")
        return {
            "success": False,
            "error": f"Error listing directory: {str(e)}"
        }

