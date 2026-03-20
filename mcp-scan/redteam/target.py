"""
Target Runner：当前为源码分析模式，复用项目代码读取能力，通过 LLM 模拟 MCP Server 对攻击的响应。
不实际启动 MCP 进程。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from openai import AsyncOpenAI

# 源码分析：可读扩展名与单文件最大字符数（与 mcp-scan 能力对齐）
READABLE_EXT = {".py", ".go", ".js", ".ts", ".md", ".json", ".yaml", ".yml", ".toml", ".sh", ".rs", ".java"}
MAX_FILE_CHARS = 50000
MAX_FILES = 100


def gather_code_context(repo_dir: str) -> str:
    """
    从仓库目录收集代码上下文：列出文件并读取部分文件内容，供 LLM 模拟 MCP 行为。
    复用与 mcp-scan 一致的“可读文件”能力，不依赖 ToolDispatcher。
    """
    repo = Path(repo_dir).resolve()
    if not repo.is_dir():
        return f"Invalid repo path: {repo_dir}"
    lines: List[str] = []
    total_chars = 0
    file_count = 0
    try:
        for path in sorted(repo.rglob("*")):
            # Enforce maximum number of files to process
            if file_count >= MAX_FILES:
                break
            # Skip symbolic links to avoid traversing outside the repo or special targets
            if path.is_symlink():
                continue
            # Resolve the real path and ensure it stays within the repository boundary
            try:
                resolved = path.resolve()
            except Exception:
                continue
            try:
                resolved.relative_to(repo)
            except ValueError:
                # Resolved path is outside the repository; skip it
                continue
            if not resolved.is_file():
                continue
            if path.suffix.lower() not in READABLE_EXT:
                continue
            try:
                text = resolved.read_text(encoding="utf-8", errors="replace")
            except (OSError, UnicodeError):
                continue
            if len(text) > MAX_FILE_CHARS:
                text = text[:MAX_FILE_CHARS] + "\n... (truncated)"
            rel = path.relative_to(repo)
            prospective_total = total_chars + len(text)
            if prospective_total > 300000:
                break
            lines.append(f"--- FILE: {rel} ---")
            lines.append(text)
            lines.append("")
            total_chars = prospective_total
            file_count += 1
    except Exception as e:
        lines.append(f"Error reading repo: {e}")
    if not lines:
        return "No readable files found in repo."
    return "\n".join(lines)


TARGET_SYSTEM = """你正在模拟一个 MCP (Model Context Protocol) Server 的对外行为。
你已获得该 MCP 项目的一部分源码/文档作为上下文。当收到来自“用户/客户端”的消息时，你需要以该 MCP Server 的身份回复：
- 回复应贴合项目能力（例如暴露的 tools、resources 等）
- 若消息明显为恶意或越权请求，可以拒绝、简短报错或给出安全响应，但不要脱离“MCP Server”人设
- 回复尽量简短（几行到一段），不要暴露内部实现细节
仅输出模拟的 MCP Server 回复内容，不要输出解释或 meta 说明。"""


class TargetRunner:
    """
    目标运行器：源码分析模式。
    - 初始化时从 repo_dir 收集代码上下文
    - respond_to_attack(message) 使用 LLM 根据上下文模拟 MCP Server 的响应
    """

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        repo_dir: Optional[str] = None,
        temperature: float = 0.3,
    ):
        self.client = client
        self.model = model
        self.repo_dir = repo_dir or ""
        self.temperature = temperature
        self._context: Optional[str] = None

    def set_repo(self, repo_dir: str) -> None:
        self.repo_dir = repo_dir
        self._context = None

    def _get_context(self) -> str:
        if self._context is not None:
            return self._context
        if not self.repo_dir or not os.path.isdir(self.repo_dir):
            self._context = "No repository path provided or path is not a directory."
            return self._context
        self._context = gather_code_context(self.repo_dir)
        return self._context

    def _build_messages(self, attack_message: str, recent_history: Optional[List[str]] = None) -> List[dict]:
        context = self._get_context()
        user_parts = ["当前项目（MCP Server）源码/文档上下文：", "", context, "", "---", ""]
        if recent_history:
            user_parts.append("最近几轮交互（仅作参考）：")
            for h in recent_history[-3:]:
                user_parts.append(h)
            user_parts.append("")
        user_parts.append("本轮收到的用户/客户端消息：")
        user_parts.append(attack_message)
        user_parts.append("")
        user_parts.append("请以 MCP Server 身份回复上述消息（仅输出回复内容）。")
        return [
            {"role": "system", "content": TARGET_SYSTEM},
            {"role": "user", "content": "\n".join(user_parts)},
        ]

    async def respond_to_attack(
        self,
        attack_message: str,
        recent_history: Optional[List[str]] = None,
    ) -> str:
        """
        根据当前攻击消息与已有上下文，模拟 MCP Server 的响应并返回字符串。
        """
        messages = self._build_messages(attack_message, recent_history)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return (response.choices[0].message.content or "").strip()
