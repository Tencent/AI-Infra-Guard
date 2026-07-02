import os
from typing import Any, Optional
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext

def _format_size(size: int) -> str:
    if size < 1024:
        return f'{size} B'
    if size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'
    if size < 1024 * 1024 * 1024:
        return f'{size / (1024 * 1024):.1f} MB'
    return f'{size / (1024 * 1024 * 1024):.1f} GB'

@register_tool
def ls(path: str, context: ToolContext = None) -> dict[str, Any]:
    """列出指定目录下的文件和子目录

    Args:
        path: 要列出内容的目录路径

    Returns:
        包含目录内容列表的字典
    """
    try:
        abs_path = os.path.realpath(path)
        if context and context.folder:
            folder = os.path.realpath(context.folder)
            if os.path.commonpath([abs_path, folder]) != folder:
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
        entries = []
        items = []
        for name in sorted(os.listdir(abs_path)):
            full = os.path.join(abs_path, name)
            entry_type = 'dir' if os.path.isdir(full) else 'file'
            try:
                size = os.path.getsize(full) if entry_type == 'file' else 0
            except OSError:
                size = 0
            size_text = _format_size(size)
            entries.append(f'[{entry_type}] {name}' + (f'  ({size_text})' if entry_type == 'file' else ''))
            items.append({
                'name': name,
                'type': entry_type,
                'size_text': size_text,
            })
        logger.info(f'ls: {abs_path} -> {len(entries)} entries')
        return {
            'path': abs_path,
            'entries': entries,
            'items': items,
            'count': len(entries),
        }
    except PermissionError:
        return {
            'success': False,
            'message': f'权限拒绝: {path}',
        }
    except Exception as e:
        logger.error(f'ls error: {e}')
        return {
            'success': False,
            'message': f'列出目录失败: {str(e)}',
        }
