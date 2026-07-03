import os
import re
from typing import Any, Optional
from skill_scan.tools.registry import register_tool
from skill_scan.utils.loging import logger
from skill_scan.utils.tool_context import ToolContext


@register_tool
def grep(
        pattern: str,
        path: str,
        recursive: bool = True,
        ignore_case: bool = False,
        max_results: int = 200,
        context: ToolContext = None,
) -> dict[str, Any]:
    """Search files or directories for text lines matching the given regex pattern.

    Args:
        pattern: The regex pattern to search for
        path: The file or directory path to search
        recursive: Whether to recurse into subdirectories (default True)
        ignore_case: Whether to ignore case (default False)
        max_results: Maximum number of results to return (default 200)

    Returns:
        Dict containing the list of matching results
    """
    if isinstance(max_results, str):
        max_results = int(max_results)
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
        flags = re.IGNORECASE if ignore_case else 0
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            return {
                'success': False,
                'message': f'Invalid regular expression: {e}',
            }
        matches = []
        files_searched = 0

        def search_file(file_path: str):
            nonlocal files_searched
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_no, line in enumerate(f, start=1):
                        if compiled.search(line):
                            rel = os.path.relpath(file_path,
                                                  abs_path if os.path.isdir(abs_path) else os.path.dirname(abs_path))
                            matches.append(f'{rel}:{line_no}: {line.rstrip()}')
                            if len(matches) >= max_results:
                                return True
                files_searched += 1
            except (PermissionError, OSError):
                pass
            return False

        def walk(target: str):
            if os.path.isfile(target):
                search_file(target)
            elif os.path.isdir(target):
                if recursive:
                    for root, dirs, files in os.walk(target):
                        dirs[:] = [d for d in sorted(dirs) if not d.startswith('.')]
                        for fname in sorted(files):
                            if len(matches) >= max_results:
                                return
                            search_file(os.path.join(root, fname))
                else:
                    for fname in sorted(os.listdir(target)):
                        if len(matches) >= max_results:
                            return
                        full = os.path.join(target, fname)
                        if os.path.isfile(full):
                            search_file(full)

        walk(abs_path)
        truncated = len(matches) >= max_results
        logger.info(f'grep "{pattern}" in {abs_path}: {len(matches)} matches, {files_searched} files searched')
        return {
            'pattern': pattern,
            'path': abs_path,
            'matches': matches,
            'match_count': len(matches),
            'truncated': truncated,
        }
    except Exception as e:
        logger.error(f'grep error: {e}')
        return {
            'success': False,
            'message': f'Search failed: {str(e)}',
        }
