import os
import re
from typing import Any, Optional
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext


@register_tool
def grep(
        pattern: str,
        path: str,
        recursive: bool = True,
        ignore_case: bool = False,
        max_results: int = 200,
        context: ToolContext = None,
) -> dict[str, Any]:
    """在文件或目录中搜索匹配指定正则模式的文本行

    Args:
        pattern: 要搜索的正则表达式模式
        path: 要搜索的文件或目录路径
        recursive: 是否递归搜索子目录（默认 True）
        ignore_case: 是否忽略大小写（默认 False）
        max_results: 最大返回结果数（默认 200）

    Returns:
        包含匹配结果列表的字典
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
                    'message': f'路径不在允许范围内: {path}',
                }
        if not os.path.exists(abs_path):
            return {
                'success': False,
                'message': f'路径不存在: {path}',
            }
        flags = re.IGNORECASE if ignore_case else 0
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            return {
                'success': False,
                'message': f'无效的正则表达式: {e}',
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
            'message': f'搜索失败: {str(e)}',
        }
