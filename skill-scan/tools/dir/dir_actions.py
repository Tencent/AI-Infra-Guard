import os
from typing import Any
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext

_IGNORED_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.idea', '.mypy_cache'}
_IGNORED_EXTS = {'.pyc', '.pyo', '.pyd'}


def _build_tree(root: str, prefix: str, max_depth: int, current_depth: int, lines: list[str]):
    if current_depth > max_depth:
        return
    try:
        entries = sorted(os.listdir(root))
    except PermissionError:
        return
    dirs = [e for e in entries if os.path.isdir(os.path.join(root, e)) and e not in _IGNORED_DIRS]
    files = [
        e for e in entries
        if os.path.isfile(os.path.join(root, e))
           and os.path.splitext(e)[1] not in _IGNORED_EXTS
    ]
    all_entries = dirs + files
    for idx, name in enumerate(all_entries):
        is_last = idx == len(all_entries) - 1
        connector = '└── ' if is_last else '├── '
        lines.append(f'{prefix}{connector}{name}')
        full = os.path.join(root, name)
        if os.path.isdir(full):
            extension = '    ' if is_last else '│   '
            _build_tree(
                full,
                prefix + extension,
                max_depth,
                current_depth + 1,
                lines,
            )


@register_tool
def dir_tree(path: str, max_depth: int = 4, context: ToolContext = None) -> dict[str, Any]:
    """以树形结构递归展示目录内容

    Args:
        path: 要展示的目录路径
        max_depth: 最大递归深度（默认 4）

    Returns:
        包含树形文本的字典
    """
    if isinstance(max_depth, str):
        max_depth = int(max_depth)
    try:
        abs_path = os.path.realpath(path)
        if context and context.folder:
            folder = os.path.realpath(context.folder)
            if not abs_path.startswith(folder):
                return {
                    'success': False,
                    'message': f'路径不在允许范围内: {path}',
                }
        if not os.path.exists(abs_path):
            return {
                'success': False,
                'message': f'路径不存在: {path}',
            }
        if not os.path.isdir(abs_path):
            return {
                'success': False,
                'message': f'路径不是目录: {path}',
            }
        lines = [abs_path]
        _build_tree(abs_path, '', max_depth, 1, lines)
        tree_text = '\n'.join(lines)
        logger.info(f'dir_tree: {abs_path}, depth={max_depth}, {len(lines)} lines')
        return {
            'path': abs_path,
            'tree': tree_text,
        }
    except Exception as e:
        logger.error(f'dir_tree error: {e}')
        return {
            'success': False,
            'message': f'目录树生成失败: {str(e)}',
        }
