import base64
import re
from typing import Any

from tools.registry import register_tool
from utils.loging import logger


@register_tool(sandbox_execution=False)
def base64_decode(text: str) -> dict[str, Any]:
    """对字符串进行 base64 解码，并自动提取文本中所有疑似 base64 编码的片段进行解码。

    Args:
        text: 需要解码的 base64 字符串，或包含 base64 片段的文本。
              可以是纯 base64 字符串，也可以是含有 base64 片段的混合文本。

    Returns:
        包含解码结果列表的字典，每个结果包含原始片段和解码内容。
    """
    results = []

    # 先尝试整体解码
    stripped = text.strip()
    direct = _try_decode(stripped)
    if direct is not None:
        results.append({
            'input': stripped,
            'decoded': direct,
        })

    # 再从文本中提取所有疑似 base64 片段（长度 >= 16，避免误报短词）
    # base64 字符集：A-Z a-z 0-9 + / = 以及 URL-safe 变体 - _
    pattern = re.compile(r'[A-Za-z0-9+/\-_]{16,}={0,2}')
    for match in pattern.finditer(text):
        fragment = match.group(0)
        # 跳过已整体解码成功的情况（避免重复）
        if fragment == stripped and direct is not None:
            continue
        decoded = _try_decode(fragment)
        if decoded is not None:
            results.append({
                'input': fragment,
                'decoded': decoded,
                'source': 'extracted',
            })

    if not results:
        logger.info(f'base64_decode: no valid base64 found in input (len={len(text)})')
        return {
            'success': False,
            'message': '未找到有效的 base64 编码内容',
        }

    logger.info(f'base64_decode: decoded {len(results)} fragment(s)')
    return {
        'success': True,
        'results': results,
        'count': len(results),
    }


def _try_decode(s: str) -> str | None:
    """尝试 base64 解码，成功且结果为可打印文本则返回，否则返回 None。"""
    # 补齐 padding
    padded = s + '=' * (-len(s) % 4)
    for decode_fn in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            raw = decode_fn(padded)
            text = raw.decode('utf-8')
            # 过滤掉乱码：要求可打印字符占比 > 80%
            printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
            if len(text) > 0 and printable / len(text) > 0.8:
                return text
        except Exception:
            continue
    return None
