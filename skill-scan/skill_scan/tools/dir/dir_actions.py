import os
from typing import Any

from skill_scan.tools.registry import register_tool
from skill_scan.utils.loging import logger
from skill_scan.utils.tool_context import ToolContext

_IGNORED_DIRS = {'.git'}
# Dirs kept visible (but flagged) so referenced payloads stay auditable (issue #631)
_FLAGGED_DIRS = {'__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build', '.next', '.nuxt', '.idea', '.mypy_cache'}
# Bytecode files kept visible (but flagged) instead of hidden (issue #630)
_FLAGGED_EXTS = {'.pyc', '.pyo', '.pyd'}


def _build_tree(root: str, prefix: str, max_depth: int, current_depth: int, lines: list[str]):
    if current_depth > max_depth:
        return
    try:
        entries = sorted(os.listdir(root))
    except PermissionError:
        return
    dirs = [e for e in entries if os.path.isdir(os.path.join(root, e)) and e not in _IGNORED_DIRS]
    files = [e for e in entries if os.path.isfile(os.path.join(root, e))]
    all_entries = dirs + files
    for idx, name in enumerate(all_entries):
        is_last = idx == len(all_entries) - 1
        connector = '└── ' if is_last else '├── '
        full = os.path.join(root, name)
        if os.path.isdir(full):
            suffix = ' [!]' if name in _FLAGGED_DIRS else ''
            lines.append(f'{prefix}{connector}{name}{suffix}')
            extension = '    ' if is_last else '│   '
            _build_tree(
                full,
                prefix + extension,
                max_depth,
                current_depth + 1,
                lines,
            )
        else:
            suffix = ' [!]' if os.path.splitext(name)[1] in _FLAGGED_EXTS else ''
            lines.append(f'{prefix}{connector}{name}{suffix}')


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
            if os.path.commonpath([abs_path, folder]) != folder:
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
