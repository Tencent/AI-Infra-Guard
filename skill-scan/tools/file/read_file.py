import os
from typing import Any

from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext

_DEFAULT_MAX_LINES = 600
_DEFAULT_MAX_CHARS = 14000
_ALLOWED_MODES = {'preview', 'range', 'full'}


@register_tool
def read_file(
    file_path: str,
    start_line: int = 1,
    max_lines: int = _DEFAULT_MAX_LINES,
    max_chars: int = _DEFAULT_MAX_CHARS,
    mode: str = 'preview',
    context: ToolContext = None,
) -> dict[str, Any]:
    """读取文件内容

    Args:
        file_path: 文件路径
        start_line: 起始行号，默认为 1
        max_lines: 最大返回行数，默认 600
        max_chars: 最大返回字符数，默认 14000
        mode: 读取模式，支持 preview、range、full

    Returns:
        包含成功状态和文件内容的字典
    """
    try:
        if isinstance(start_line, str):
            start_line = int(start_line)
        if isinstance(max_lines, str):
            max_lines = int(max_lines)
        if isinstance(max_chars, str):
            max_chars = int(max_chars)
        mode = str(mode).strip().lower()
        if start_line < 1:
            return {
                'success': False,
                'message': 'start_line must be greater than or equal to 1',
            }
        if max_lines < 1 or max_chars < 1:
            return {
                'success': False,
                'message': 'max_lines and max_chars must be greater than 0',
            }
        if mode not in _ALLOWED_MODES:
            return {
                'success': False,
                'message': f'Unsupported read mode: {mode}',
            }
        abs_path = os.path.realpath(file_path)
        # 拦截评测标注文件，避免对模型判断产生锚定效应
        _BLOCKED_FILENAMES = {'_VERDICT.txt', '_GROUND_TRUTH.txt', '_EVAL.txt'}
        if os.path.basename(abs_path) in _BLOCKED_FILENAMES:
            return {
                'success': False,
                'message': f'This file is not part of the skill project and should not be read: {file_path}',
            }
        if context and context.folder:
            folder = os.path.realpath(context.folder)
            if os.path.commonpath([abs_path, folder]) != folder:
                return {
                    'success': False,
                    'message': f'Path is not allowed: {file_path}',
                }
        if not os.path.exists(abs_path):
            return {
                'success': False,
                'message': f'File not found: {file_path}',
            }
        if not os.path.isfile(abs_path):
            return {
                'success': False,
                'message': f'Path is not a file: {file_path}',
            }
        requested_mode = mode
        if requested_mode == 'full':
            start_line = 1
        lines = []
        total_lines = 0
        returned_chars = 0
        returned_lines = 0
        end_line = start_line - 1
        char_limited = False
        with open(abs_path, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, start=1):
                total_lines = line_no
                if line_no < start_line:
                    continue
                if returned_lines >= max_lines:
                    continue
                if returned_chars >= max_chars:
                    char_limited = True
                    continue
                remaining_chars = max_chars - returned_chars
                if len(line) > remaining_chars:
                    lines.append(line[:remaining_chars])
                    returned_chars += remaining_chars
                    returned_lines += 1
                    end_line = line_no
                    char_limited = True
                    continue
                lines.append(line)
                returned_chars += len(line)
                returned_lines += 1
                end_line = line_no
        if total_lines == 0:
            logger.info(f'Read file: {abs_path} (empty file)')
            return {
                'path': abs_path,
                'requested_mode': requested_mode,
                'mode': 'full',
                'start_line': 1,
                'end_line': 0,
                'total_lines': 0,
                'size_bytes': os.path.getsize(abs_path),
                'returned_chars': 0,
                'truncated': False,
                'summary_hint': '',
                'data': '',
            }
        if start_line > total_lines:
            return {
                'success': False,
                'message': f'start_line {start_line} exceeds total lines {total_lines}',
            }
        if requested_mode == 'range':
            requested_end_line = min(total_lines, start_line + max_lines - 1)
            truncated = char_limited or end_line < requested_end_line
        else:
            truncated = char_limited or end_line < total_lines
        effective_mode = requested_mode
        if requested_mode == 'full' and truncated:
            effective_mode = 'preview'
        summary_hint = ''
        if truncated:
            summary_hint = (
                'File content was truncated by the read budget. '
                'Use grep to locate relevant code, then call read_file again '
                'with a narrower start_line range.'
            )
        content = ''.join(lines)
        logger.info(
            f'Read file: {abs_path} '
            f'(mode={effective_mode}, lines={returned_lines}, chars={len(content)}, truncated={truncated})'
        )
        return {
            'path': abs_path,
            'requested_mode': requested_mode,
            'mode': effective_mode,
            'start_line': start_line,
            'end_line': end_line,
            'total_lines': total_lines,
            'size_bytes': os.path.getsize(abs_path),
            'returned_chars': len(content),
            'truncated': truncated,
            'summary_hint': summary_hint,
            'data': content,
        }
    except UnicodeDecodeError:
        return {
            'success': False,
            'message': f'Failed to decode file {file_path}. File may be binary.',
        }
    except PermissionError:
        return {
            'success': False,
            'message': f'Permission denied: {file_path}',
        }
    except Exception as e:
        logger.error(f'Error reading file {file_path}: {e}')
        return {
            'success': False,
            'message': f'Error reading file: {str(e)}',
        }