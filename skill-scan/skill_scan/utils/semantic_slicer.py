# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

"""Semantic slicing for pure natural-language / documentation Skill files.

Splits pure semantic files (``SKILL.md``, ``.md``, ``.markdown``, ``.txt``,
``.rst``) into isolated semantic chunks along structural boundaries (YAML
frontmatter, headings, thematic breaks, fenced blocks, paragraphs, list items)
while intentionally excluding executable source code files.

Each chunk is meant to be audited independently without surrounding narrative
framing so multi-paragraph or cross-section gradual induction cannot hide
dangerous or policy-overriding directives inside benign prose.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from skill_scan.utils.loging import logger
from skill_scan.utils.text_decoder import TextDecodeError, read_text_file

SEMANTIC_FILENAMES = frozenset({"skill.md"})
SEMANTIC_EXTS = frozenset({".md", ".markdown", ".txt", ".rst"})

_SKIP_DIRS = frozenset({
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".nuxt",
})
_SKIP_FILES = frozenset({"_VERDICT.txt", "_GROUND_TRUTH.txt", "_EVAL.txt"})
_METADATA_FILENAMES = frozenset({
    ".DS_Store",
    "._DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "._.DS_Store",
})
_METADATA_PREFIXES = (".__", "._")

DEFAULT_MAX_FILE_SIZE = 512 * 1024  # 512 KB
DEFAULT_MAX_CHUNK_CHARS = 800
DEFAULT_MIN_PACK_CHARS = 80
DEFAULT_MAX_CHUNKS = 24

_ATX_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}(?:\s+\S|\s*$)")
_SETEXT_UNDERLINE_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")
_THEMATIC_BREAK_RE = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
_FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-*+]|\d{1,3}[.)])\s+")
_TABLE_SEP_RE = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)


@dataclass(frozen=True)
class SemanticChunk:
    """An isolated slice of a pure semantic file."""

    file_path: str
    chunk_index: int
    line_start: int
    line_end: int
    kind: str
    text: str
    heading: str = ""
    is_recovered_mojibake: bool = False


@dataclass(frozen=True)
class SkillBaseline:
    """Minimal declared capability baseline extracted from Skill metadata/intro.

    Used strictly as a semantic anchor to measure how far an isolated slice
    diverges from the Skill's stated core task (perplexity-like surprise),
    never as an authorization pass for unsafe or malicious directives.
    """

    name: str = ""
    description: str = ""
    source_file: str = ""

    @property
    def is_empty(self) -> bool:
        return not (self.name.strip() or self.description.strip())

    def format_prompt_block(self, language: str = "zh") -> str:
        """Render the baseline as untrusted metadata for slice auditing."""
        if self.is_empty:
            return ""
        parts = []
        if self.name:
            parts.append(f"name: {self.name}")
        if self.description:
            parts.append(f"declared_purpose: {self.description}")
        body = "\n".join(parts)
        src = self.source_file or "SKILL.md"
        if language == "en":
            return (
                f"<skill_baseline source=\"{src}\" untrusted=\"true\">\n"
                f"{body}\n"
                "</skill_baseline>"
            )
        return (
            f"<skill_baseline source=\"{src}\" untrusted=\"true\">\n"
            f"{body}\n"
            "</skill_baseline>"
        )


def _sanitize_baseline_field(value: str, max_chars: int) -> str:
    """Collapse whitespace, strip XML-like tags, and bound baseline text."""
    cleaned = re.sub(r"<[^>]+>", " ", value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 3].rstrip() + "..."
    return cleaned


def _parse_frontmatter_metadata(frontmatter_text: str) -> tuple[str, str]:
    """Extract (name, description) from YAML frontmatter without full YAML deps."""
    lines = frontmatter_text.splitlines()
    # Strip opening/closing --- or ...
    if lines and lines[0].strip() == "---":
        lines = lines[1:]
    if lines and lines[-1].strip() in {"---", "..."}:
        lines = lines[:-1]

    fields: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        if val in {"|", "|-", "|+", ">", ">-", ">+"}:
            i += 1
            block_lines: list[str] = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block_lines.append(lines[i].strip())
                i += 1
            val = " ".join(part for part in block_lines if part)
        else:
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                if len(val) >= 2:
                    val = val[1:-1]
            i += 1
        if key in {"name", "description"} and val:
            fields[key] = val

    return fields.get("name", ""), fields.get("description", "")


def extract_baseline_from_text(
    text: str,
    file_path: str = "SKILL.md",
) -> SkillBaseline:
    """Extract a minimal capability baseline from a semantic file's text."""
    if not text or not text.strip():
        return SkillBaseline()

    lines = text.splitlines()
    blocks = _parse_blocks(lines)
    if not blocks:
        return SkillBaseline()

    name = ""
    description = ""
    for block in blocks:
        if block.kind == "frontmatter":
            name, description = _parse_frontmatter_metadata(block.text)
            break

    if not name:
        for block in blocks:
            if block.kind == "heading":
                heading_line = block.text.splitlines()[0]
                name = re.sub(r"^\s{0,3}#{1,6}\s*", "", heading_line).strip()
                break

    if not description:
        for block in blocks:
            if block.kind == "paragraph":
                description = block.text
                break

    sanitized_name = _sanitize_baseline_field(name, 80)
    sanitized_desc = _sanitize_baseline_field(description, 300)
    if not sanitized_name and not sanitized_desc:
        return SkillBaseline()
    return SkillBaseline(
        name=sanitized_name,
        description=sanitized_desc,
        source_file=file_path,
    )


def extract_capability_baseline(
    repo_dir: str,
    *,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> SkillBaseline:
    """Extract the Skill's capability baseline from SKILL.md (or fallback doc)."""
    if not repo_dir or not os.path.isdir(repo_dir):
        return SkillBaseline()

    for rel_path in _iter_semantic_files(repo_dir):
        abs_path = os.path.join(repo_dir, rel_path)
        try:
            if os.path.getsize(abs_path) > max_file_size:
                continue
            decoded = read_text_file(abs_path)
        except (OSError, TextDecodeError):
            continue
        source_text = decoded.recovered_text or decoded.text
        baseline = extract_baseline_from_text(source_text, rel_path)
        if not baseline.is_empty:
            return baseline

    return SkillBaseline()


@dataclass(frozen=True)
class _Block:
    kind: str
    text: str
    line_start: int
    line_end: int


def is_semantic_file(rel_path: str) -> bool:
    """Return True iff *rel_path* is a pure semantic/documentation file in scope."""
    norm = rel_path.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    norm = norm.lstrip("/")
    if not norm:
        return False
    parts = norm.split("/")
    if any(part in _SKIP_DIRS for part in parts[:-1]):
        return False
    fname = parts[-1]
    if fname in _SKIP_FILES or fname in _METADATA_FILENAMES:
        return False
    if any(fname.startswith(prefix) for prefix in _METADATA_PREFIXES):
        return False
    if fname.lower() in SEMANTIC_FILENAMES:
        return True
    ext = os.path.splitext(fname)[1].lower()
    return ext in SEMANTIC_EXTS


def _find_frontmatter_end(lines: list[str]) -> int | None:
    """If lines start with YAML frontmatter, return 0-based inclusive end index."""
    if not lines or lines[0].strip() != "---":
        return None
    for idx in range(1, len(lines)):
        if lines[idx].strip() in {"---", "..."}:
            return idx
    return None


def _parse_blocks(lines: list[str]) -> list[_Block]:
    """Parse text lines into structural semantic blocks with 1-based line ranges."""
    blocks: list[_Block] = []
    total = len(lines)
    idx = 0

    fm_end = _find_frontmatter_end(lines)
    if fm_end is not None:
        blocks.append(
            _Block(
                kind="frontmatter",
                text="\n".join(lines[: fm_end + 1]),
                line_start=1,
                line_end=fm_end + 1,
            )
        )
        idx = fm_end + 1

    while idx < total:
        line = lines[idx]
        stripped = line.strip()

        if not stripped:
            idx += 1
            continue

        # Fenced code block (kept intact; never split mid-fence)
        fence_match = _FENCE_OPEN_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            fence_char = fence[0]
            fence_len = len(fence)
            close_re = re.compile(rf"^\s{{0,3}}{re.escape(fence_char)}{{{fence_len},}}\s*$")
            start = idx
            idx += 1
            while idx < total and not close_re.match(lines[idx]):
                idx += 1
            if idx < total:
                idx += 1  # include closing fence
            blocks.append(
                _Block(
                    kind="fenced_block",
                    text="\n".join(lines[start:idx]),
                    line_start=start + 1,
                    line_end=idx,
                )
            )
            continue

        # ATX heading
        if _ATX_HEADING_RE.match(line):
            blocks.append(
                _Block(
                    kind="heading",
                    text=line,
                    line_start=idx + 1,
                    line_end=idx + 1,
                )
            )
            idx += 1
            continue

        # Setext heading (single line followed immediately by === or ---)
        if idx + 1 < total and _SETEXT_UNDERLINE_RE.match(lines[idx + 1]):
            blocks.append(
                _Block(
                    kind="heading",
                    text="\n".join(lines[idx : idx + 2]),
                    line_start=idx + 1,
                    line_end=idx + 2,
                )
            )
            idx += 2
            continue

        # Thematic break (section separator)
        if _THEMATIC_BREAK_RE.match(line):
            blocks.append(
                _Block(
                    kind="thematic_break",
                    text=line,
                    line_start=idx + 1,
                    line_end=idx + 1,
                )
            )
            idx += 1
            continue

        # Blockquote
        if re.match(r"^\s{0,3}>", line):
            start = idx
            idx += 1
            while idx < total:
                cur = lines[idx]
                if not cur.strip():
                    break
                if (
                    _FENCE_OPEN_RE.match(cur)
                    or _ATX_HEADING_RE.match(cur)
                    or _THEMATIC_BREAK_RE.match(cur)
                ):
                    break
                if re.match(r"^\s{0,3}>", cur) or not _LIST_ITEM_RE.match(cur):
                    idx += 1
                else:
                    break
            blocks.append(
                _Block(
                    kind="blockquote",
                    text="\n".join(lines[start:idx]),
                    line_start=start + 1,
                    line_end=idx,
                )
            )
            continue

        # Markdown pipe table
        if (
            line.lstrip().startswith("|")
            or (idx + 1 < total and "|" in line and _TABLE_SEP_RE.match(lines[idx + 1]))
        ):
            start = idx
            idx += 1
            while idx < total and lines[idx].strip() and "|" in lines[idx]:
                idx += 1
            blocks.append(
                _Block(
                    kind="table",
                    text="\n".join(lines[start:idx]),
                    line_start=start + 1,
                    line_end=idx,
                )
            )
            continue

        # List item (top-level item + indented/nested continuation lines)
        list_match = _LIST_ITEM_RE.match(line)
        if list_match:
            base_indent = len(list_match.group(1))
            start = idx
            idx += 1
            while idx < total:
                cur = lines[idx]
                if not cur.strip():
                    break
                if (
                    _FENCE_OPEN_RE.match(cur)
                    or _ATX_HEADING_RE.match(cur)
                    or _THEMATIC_BREAK_RE.match(cur)
                ):
                    break
                next_list = _LIST_ITEM_RE.match(cur)
                if next_list and len(next_list.group(1)) <= base_indent:
                    break
                idx += 1
            blocks.append(
                _Block(
                    kind="list_item",
                    text="\n".join(lines[start:idx]),
                    line_start=start + 1,
                    line_end=idx,
                )
            )
            continue

        # Standard prose paragraph
        start = idx
        idx += 1
        while idx < total:
            cur = lines[idx]
            if not cur.strip():
                break
            if (
                _FENCE_OPEN_RE.match(cur)
                or _ATX_HEADING_RE.match(cur)
                or _THEMATIC_BREAK_RE.match(cur)
                or _LIST_ITEM_RE.match(cur)
                or re.match(r"^\s{0,3}>", cur)
            ):
                break
            if idx + 1 < total and _SETEXT_UNDERLINE_RE.match(lines[idx + 1]):
                break
            idx += 1
        blocks.append(
            _Block(
                kind="paragraph",
                text="\n".join(lines[start:idx]),
                line_start=start + 1,
                line_end=idx,
            )
        )

    return blocks


def _split_oversized_block(
    block: _Block,
    max_chunk_chars: int,
) -> list[_Block]:
    """Split a block exceeding *max_chunk_chars* cleanly along line boundaries."""
    if len(block.text) <= max_chunk_chars:
        return [block]

    raw_lines = block.text.splitlines()
    if len(raw_lines) <= 1:
        return [block]

    sub_blocks: list[_Block] = []
    cur_lines: list[str] = []
    cur_start = block.line_start
    cur_len = 0

    for offset, line in enumerate(raw_lines):
        line_no = block.line_start + offset
        added = len(line) + (1 if cur_lines else 0)
        if cur_lines and cur_len + added > max_chunk_chars:
            sub_blocks.append(
                _Block(
                    kind=block.kind,
                    text="\n".join(cur_lines),
                    line_start=cur_start,
                    line_end=line_no - 1,
                )
            )
            cur_lines = [line]
            cur_start = line_no
            cur_len = len(line)
        else:
            cur_lines.append(line)
            cur_len += added

    if cur_lines:
        sub_blocks.append(
            _Block(
                kind=block.kind,
                text="\n".join(cur_lines),
                line_start=cur_start,
                line_end=block.line_end,
            )
        )
    return sub_blocks


def slice_semantic_text(
    text: str,
    file_path: str,
    *,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    min_pack_chars: int = DEFAULT_MIN_PACK_CHARS,
    is_recovered_mojibake: bool = False,
) -> list[SemanticChunk]:
    """Slice semantic text into context-isolated chunks with exact line ranges.

    Design goals:
    - Never merge across YAML frontmatter, headings, or thematic breaks.
    - Keep each substantial block (>= *min_pack_chars*, fenced blocks, tables,
      blockquotes, frontmatter) isolated in its own chunk so surrounding
      narrative framing cannot hide dangerous directives.
    - Only pack consecutive small fragments (< *min_pack_chars*) within the same
      section up to *max_chunk_chars*.
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    blocks = _parse_blocks(lines)
    if not blocks:
        return []

    chunks: list[SemanticChunk] = []
    current_heading = ""
    pending_heading: _Block | None = None
    small_buffer: list[_Block] = []
    small_heading = ""

    def emit_chunk(
        chunk_blocks: list[_Block],
        kind: str,
        heading: str,
    ) -> None:
        joined = "\n\n".join(b.text for b in chunk_blocks if b.text.strip())
        if not joined.strip():
            return
        chunks.append(
            SemanticChunk(
                file_path=file_path,
                chunk_index=len(chunks) + 1,
                line_start=chunk_blocks[0].line_start,
                line_end=chunk_blocks[-1].line_end,
                kind=kind,
                text=joined,
                heading=heading,
                is_recovered_mojibake=is_recovered_mojibake,
            )
        )

    def flush_small_buffer() -> None:
        nonlocal small_buffer, small_heading
        if small_buffer:
            kind = small_buffer[0].kind if len(small_buffer) == 1 else "section_group"
            emit_chunk(small_buffer, kind, small_heading)
            small_buffer = []
            small_heading = ""

    def flush_pending_heading() -> None:
        nonlocal pending_heading
        if pending_heading is not None:
            emit_chunk([pending_heading], "heading", current_heading)
            pending_heading = None

    for block in blocks:
        if block.kind == "thematic_break":
            flush_small_buffer()
            flush_pending_heading()
            continue

        if block.kind == "frontmatter":
            flush_small_buffer()
            flush_pending_heading()
            for sub in _split_oversized_block(block, max_chunk_chars):
                emit_chunk([sub], "frontmatter", "")
            continue

        if block.kind == "heading":
            flush_small_buffer()
            flush_pending_heading()
            current_heading = block.text.strip()
            pending_heading = block
            continue

        is_isolated_kind = block.kind in {"fenced_block", "blockquote", "table"}
        is_substantial = is_isolated_kind or len(block.text.strip()) >= min_pack_chars

        if is_substantial:
            flush_small_buffer()
            parts = _split_oversized_block(block, max_chunk_chars)
            first, rest = parts[0], parts[1:]
            if pending_heading is not None:
                if len(pending_heading.text) + 2 + len(first.text) <= max_chunk_chars:
                    emit_chunk([pending_heading, first], first.kind, current_heading)
                    pending_heading = None
                else:
                    flush_pending_heading()
                    emit_chunk([first], first.kind, current_heading)
            else:
                emit_chunk([first], first.kind, current_heading)

            for sub in rest:
                emit_chunk([sub], sub.kind, current_heading)
            continue

        # Small fragment (< min_pack_chars)
        if pending_heading is not None:
            if len(pending_heading.text) + 2 + len(block.text) <= max_chunk_chars:
                small_buffer = [pending_heading, block]
                small_heading = current_heading
                pending_heading = None
            else:
                flush_pending_heading()
                small_buffer = [block]
                small_heading = current_heading
            continue

        if not small_buffer:
            small_buffer = [block]
            small_heading = current_heading
            continue

        projected = sum(len(b.text) for b in small_buffer) + 2 * len(small_buffer) + len(block.text)
        if projected <= max_chunk_chars:
            small_buffer.append(block)
        else:
            flush_small_buffer()
            small_buffer = [block]
            small_heading = current_heading

    flush_small_buffer()
    flush_pending_heading()
    return chunks


def _iter_semantic_files(repo_dir: str) -> list[str]:
    """Return relative POSIX paths of pure semantic files sorted by audit priority."""
    candidates: list[str] = []
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, repo_dir).replace(os.sep, "/")
            if is_semantic_file(rel):
                candidates.append(rel)

    def sort_key(rel: str) -> tuple[int, int, str]:
        is_skill_md = 0 if os.path.basename(rel).lower() == "skill.md" else 1
        depth = rel.count("/")
        return (is_skill_md, depth, rel.lower())

    candidates.sort(key=sort_key)
    return candidates


def collect_semantic_chunks(
    repo_dir: str,
    *,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    min_pack_chars: int = DEFAULT_MIN_PACK_CHARS,
) -> list[SemanticChunk]:
    """Discover pure semantic files in *repo_dir* and slice them into chunks."""
    if not repo_dir or not os.path.isdir(repo_dir) or max_chunks <= 0:
        return []

    collected: list[SemanticChunk] = []
    for rel_path in _iter_semantic_files(repo_dir):
        if len(collected) >= max_chunks:
            break
        abs_path = os.path.join(repo_dir, rel_path)
        try:
            if os.path.getsize(abs_path) > max_file_size:
                logger.info(
                    f"Skipping oversized semantic file (> {max_file_size} bytes): {rel_path}"
                )
                continue
            decoded = read_text_file(abs_path)
        except (OSError, TextDecodeError) as exc:
            logger.debug(f"Skipping unreadable semantic file {rel_path}: {exc}")
            continue

        file_chunks = slice_semantic_text(
            decoded.text,
            rel_path,
            max_chunk_chars=max_chunk_chars,
            min_pack_chars=min_pack_chars,
        )
        if decoded.recovered_text:
            file_chunks.extend(
                slice_semantic_text(
                    decoded.recovered_text,
                    rel_path,
                    max_chunk_chars=max_chunk_chars,
                    min_pack_chars=min_pack_chars,
                    is_recovered_mojibake=True,
                )
            )

        remaining = max_chunks - len(collected)
        if len(file_chunks) > remaining:
            collected.extend(file_chunks[:remaining])
            logger.info(
                f"Semantic chunk budget reached ({max_chunks}); "
                f"truncated remaining slices starting at {rel_path}"
            )
            break
        collected.extend(file_chunks)

    return collected
