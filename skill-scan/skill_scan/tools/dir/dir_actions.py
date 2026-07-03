import os
from typing import Any
from skill_scan.tools.registry import register_tool
from skill_scan.utils.loging import logger
from skill_scan.utils.tool_context import ToolContext

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
    """Recursively render directory contents as a tree structure.

    Args:
        path: The directory path to render
        max_depth: Maximum recursion depth (default 4)

    Returns:
        Dict containing the tree-formatted text
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
                    'message': f'Path is not allowed: {path}',
                }
        if not os.path.exists(abs_path):
            return {
                'success': False,
                'message': f'Path does not exist: {path}',
            }
        if not os.path.isdir(abs_path):
            return {
                'success': False,
                'message': f'Path is not a directory: {path}',
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
            'message': f'Failed to generate directory tree: {str(e)}',
        }
