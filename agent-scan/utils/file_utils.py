"""
文件工具模块 - 提供文本/二进制判定、Diff 生成、目录树渲染及文件读写包装器
"""
import os
import difflib
from pathlib import Path
from typing import Optional, List, Tuple, Generator
from utils.path_utils import should_ignore_path, IGNORE_DIRECTORIES


# 常见二进制文件扩展名
BINARY_EXTENSIONS = {
    '.zip', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.7z', '.rar',
    '.exe', '.dll', '.so', '.dylib', '.a', '.lib', '.o', '.obj',
    '.class', '.jar', '.war', '.ear',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.odt', '.ods', '.odp',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp', '.svg',
    '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
    '.wasm', '.pyc', '.pyo',
    '.bin', '.dat', '.db', '.sqlite', '.sqlite3',
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
}


def is_binary_by_extension(path: str) -> bool:
    """通过文件扩展名判断是否为二进制文件"""
    ext = os.path.splitext(path)[1].lower()
    return ext in BINARY_EXTENSIONS


def is_binary_by_content(path: str, check_bytes: int = 4096) -> bool:
    """
    通过文件内容判断是否为二进制文件
    
    Args:
        path: 文件路径
        check_bytes: 检查的字节数
        
    Returns:
        如果是二进制文件返回 True
    """
    try:
        with open(path, 'rb') as f:
            chunk = f.read(check_bytes)
        
        if not chunk:
            return False
        
        # 检查 NULL 字节
        if b'\x00' in chunk:
            return True
        
        # 检查不可打印字符比例
        non_printable = sum(1 for byte in chunk if byte < 9 or (13 < byte < 32))
        return non_printable / len(chunk) > 0.3
        
    except Exception:
        return True


def is_binary_file(path: str) -> bool:
    """判断文件是否为二进制文件"""
    if is_binary_by_extension(path):
        return True
    return is_binary_by_content(path)


def is_image_file(path: str) -> bool:
    """判断是否为图片文件"""
    ext = os.path.splitext(path)[1].lower()
    return ext in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico'}


def is_pdf_file(path: str) -> bool:
    """判断是否为 PDF 文件"""
    return os.path.splitext(path)[1].lower() == '.pdf'


def generate_unified_diff(
    old_content: str,
    new_content: str,
    filepath: str = "",
    context_lines: int = 3
) -> str:
    """
    生成统一格式的 Diff
    
    Args:
        old_content: 原始内容
        new_content: 新内容
        filepath: 文件路径
        context_lines: 上下文行数
        
    Returns:
        Diff 字符串
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filepath}" if filepath else "a/file",
        tofile=f"b/{filepath}" if filepath else "b/file",
        n=context_lines
    )
    
    return ''.join(diff)


def trim_diff_indentation(diff: str) -> str:
    """
    裁剪 Diff 的缩进，使输出更紧凑
    """
    lines = diff.split('\n')
    content_lines = [
        line for line in lines
        if (line.startswith('+') or line.startswith('-') or line.startswith(' '))
        and not line.startswith('---') and not line.startswith('+++')
    ]
    
    if not content_lines:
        return diff
    
    # 计算最小缩进
    min_indent = float('inf')
    for line in content_lines:
        content = line[1:]  # 跳过第一个字符 (+/-/空格)
        if content.strip():
            stripped = len(content) - len(content.lstrip())
            min_indent = min(min_indent, stripped)
    
    if min_indent == float('inf') or min_indent == 0:
        return diff
    
    # 裁剪缩进
    result_lines = []
    for line in lines:
        if (line.startswith('+') or line.startswith('-') or line.startswith(' ')) \
           and not line.startswith('---') and not line.startswith('+++'):
            prefix = line[0]
            content = line[1:]
            result_lines.append(prefix + content[min_indent:])
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def render_directory_tree(
    root_path: str,
    max_depth: int = -1,
    max_files: int = 100,
    ignore_patterns: Optional[set] = None
) -> Tuple[str, int, bool]:
    """
    渲染目录树
    
    Args:
        root_path: 根目录路径
        max_depth: 最大深度 (-1 表示无限)
        max_files: 最大文件数
        ignore_patterns: 额外忽略的模式
        
    Returns:
        (树形字符串, 文件计数, 是否被截断)
    """
    ignore = IGNORE_DIRECTORIES.copy()
    if ignore_patterns:
        ignore.update(ignore_patterns)
    
    file_count = 0
    truncated = False
    lines = [f"{os.path.basename(root_path) or root_path}/"]
    
    def walk(path: str, prefix: str = "", depth: int = 0):
        nonlocal file_count, truncated
        
        if max_depth >= 0 and depth > max_depth:
            return
        
        if file_count >= max_files:
            truncated = True
            return
        
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return
        
        # 分离目录和文件
        dirs = []
        files = []
        for entry in entries:
            if entry in ignore or entry.startswith('.'):
                continue
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                dirs.append(entry)
            else:
                files.append(entry)
        
        all_entries = dirs + files
        
        for i, entry in enumerate(all_entries):
            if file_count >= max_files:
                truncated = True
                break
            
            is_last = (i == len(all_entries) - 1)
            connector = "└── " if is_last else "├── "
            full_path = os.path.join(path, entry)
            
            if os.path.isdir(full_path):
                lines.append(f"{prefix}{connector}{entry}/")
                extension = "    " if is_last else "│   "
                walk(full_path, prefix + extension, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry}")
                file_count += 1
    
    walk(root_path)
    
    return '\n'.join(lines), file_count, truncated


def read_file_with_lines(
    path: str,
    offset: int = 0,
    limit: int = 2000,
    max_bytes: int = 50 * 1024,
    max_line_length: int = 2000
) -> Tuple[List[str], int, bool, bool]:
    """
    读取文件内容，带行号
    
    Args:
        path: 文件路径
        offset: 起始行 (0-based)
        limit: 读取行数
        max_bytes: 最大字节数
        max_line_length: 最大行长度
        
    Returns:
        (带行号的行列表, 总行数, 是否有更多行, 是否因字节限制截断)
    """
    with open(path, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    total_lines = len(all_lines)
    result = []
    bytes_count = 0
    truncated_by_bytes = False
    
    for i in range(offset, min(len(all_lines), offset + limit)):
        line = all_lines[i].rstrip('\n\r')
        
        # 截断过长的行
        if len(line) > max_line_length:
            line = line[:max_line_length] + "..."
        
        line_size = len(line.encode('utf-8')) + 1
        
        if bytes_count + line_size > max_bytes:
            truncated_by_bytes = True
            break
        
        # 格式化行号
        line_num = str(i + 1).zfill(5)
        result.append(f"{line_num}| {line}")
        bytes_count += line_size
    
    has_more = (offset + len(result)) < total_lines
    
    return result, total_lines, has_more, truncated_by_bytes


def safe_write_file(path: str, content: str, create_dirs: bool = True) -> None:
    """
    安全写入文件
    
    Args:
        path: 文件路径
        content: 文件内容
        create_dirs: 是否创建父目录
    """
    if create_dirs:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def safe_read_file(path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    安全读取文件
    
    Returns:
        (content, error_message)
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read(), None
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except PermissionError:
        return None, f"Permission denied: {path}"
    except UnicodeDecodeError:
        return None, f"Failed to decode file (binary?): {path}"
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

