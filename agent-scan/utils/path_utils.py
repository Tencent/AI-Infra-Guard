"""
路径工具模块 - 提供路径解析、越界校验等逻辑
所有工具都应以 context.folder 为根目录进行路径校验
"""
import os
from pathlib import Path
from typing import Optional, Tuple


def normalize_path(path: str) -> str:
    """规范化路径，处理符号链接和相对路径"""
    return os.path.normpath(os.path.realpath(path))


def resolve_path(path: str, root: str) -> str:
    """
    解析路径，如果是相对路径则相对于 root 解析
    
    Args:
        path: 待解析的路径
        root: 根目录
        
    Returns:
        解析后的绝对路径
    """
    if os.path.isabs(path):
        return normalize_path(path)
    return normalize_path(os.path.join(root, path))


def is_path_within(path: str, root: str) -> bool:
    """
    检查路径是否在根目录内
    
    Args:
        path: 待检查的路径
        root: 根目录
        
    Returns:
        如果路径在根目录内返回 True
    """
    try:
        normalized_path = normalize_path(path)
        normalized_root = normalize_path(root)
        
        # 使用 commonpath 检查是否有公共路径前缀
        common = os.path.commonpath([normalized_path, normalized_root])
        return common == normalized_root
    except (ValueError, OSError):
        return False


def validate_path(path: str, root: str, must_exist: bool = False) -> Tuple[bool, str, Optional[str]]:
    """
    验证路径合法性
    
    Args:
        path: 待验证的路径
        root: 根目录
        must_exist: 是否必须存在
        
    Returns:
        (is_valid, resolved_path, error_message)
    """
    try:
        resolved = resolve_path(path, root)
        
        if not is_path_within(resolved, root):
            return False, resolved, f"Path '{path}' is outside the allowed directory '{root}'"
        
        if must_exist and not os.path.exists(resolved):
            return False, resolved, f"Path does not exist: {resolved}"
        
        return True, resolved, None
        
    except Exception as e:
        return False, path, f"Path validation error: {str(e)}"


def ensure_parent_dir(path: str) -> None:
    """确保路径的父目录存在"""
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def relative_path(path: str, root: str) -> str:
    """获取相对于根目录的相对路径"""
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def get_file_extension(path: str) -> str:
    """获取文件扩展名（小写）"""
    return os.path.splitext(path)[1].lower()


def is_hidden_path(path: str) -> bool:
    """检查路径是否为隐藏文件/目录"""
    parts = Path(path).parts
    return any(part.startswith('.') and part not in ('.', '..') for part in parts)


# 常见的应忽略的目录
IGNORE_DIRECTORIES = {
    'node_modules',
    '__pycache__',
    '.git',
    '.svn',
    '.hg',
    'dist',
    'build',
    'target',
    'vendor',
    'bin',
    'obj',
    '.idea',
    '.vscode',
    '.zig-cache',
    'zig-out',
    '.coverage',
    'coverage',
    'tmp',
    'temp',
    '.cache',
    'cache',
    'logs',
    '.venv',
    'venv',
    'env',
    '.env',
    '.eggs',
    '*.egg-info',
}


def should_ignore_path(path: str, extra_ignores: Optional[set] = None) -> bool:
    """
    检查路径是否应该被忽略
    
    Args:
        path: 待检查的路径
        extra_ignores: 额外的忽略模式集合
        
    Returns:
        如果应该忽略返回 True
    """
    ignores = IGNORE_DIRECTORIES.copy()
    if extra_ignores:
        ignores.update(extra_ignores)
    
    parts = Path(path).parts
    return any(part in ignores for part in parts)

