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

"""0-Token progressive-disclosure map, hidden-cue scan, and audit read-coverage helpers."""

from __future__ import annotations

import os
import re

from skill_scan.utils.config import get_env
from skill_scan.utils.text_decoder import TextDecodeError, read_text_file

_SEMANTIC_FILENAMES = frozenset({"skill.md"})
_SEMANTIC_EXTS = frozenset({".md", ".markdown", ".txt", ".rst"})

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

_PROGRESSIVE_DIRS = frozenset({
    "references",
    "reference",
    "phases",
    "prompts",
    "prompt",
    "rules",
    "workflows",
    "workflow",
    "guides",
})
_BOILERPLATE_FILENAMES = frozenset({
    "readme.md",
    "readme_zh.md",
    "readme.zh-cn.md",
    "readme.txt",
    "readme.rst",
    "changelog.md",
    "history.md",
    "license.md",
    "license.txt",
    "contributing.md",
    "code_of_conduct.md",
})

_DEFAULT_MAX_FILE_SIZE = 512 * 1024
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s#]+)(?:#[^)]*)?\)")
_REL_SEMANTIC_PATH_RE = re.compile(
    r"(?:^|[\s`\"'(])(\.?/?(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:md|markdown|txt|rst))\b",
    re.IGNORECASE,
)
_PRESCAN_FILE_LINE_RE = re.compile(r"^- \*\*([^*]+)\*\* —", re.MULTILINE)
_HTML_COMMENT_OPEN_RE = re.compile(r"^\s{0,3}<!--")
_MALFORMED_COMMENT_CLOSE_RE = re.compile(r"^\s*-*>\s*$")

_BIDI_CONTROL_CHARS = frozenset({
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
})
_ZERO_WIDTH_CHARS = frozenset({
    "\u200b",
    "\u200c",
    "\u200d",
    "\u2060",
    "\ufeff",
})

_RISKY_COMMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:!\s*`[^`]+`|\|\s*(?:ba|z)?sh\b|\b(?:curl|wget|powershell|pwsh|iex|base64|chmod\s+\+x|crontab|launchctl|systemctl|schtasks)\b|\b(?:ba|z)?sh\s+-[a-z]*c\b|\b(?:eval|exec)\s*\()",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:~/\.|\b(?:\.ssh|\.aws|\.env|id_rsa|authorized_keys|credentials|OPENAI_API_KEY|AWS_SECRET|MEMORY\.md|SOUL\.md|/etc/passwd|169\.254\.169\.254|open\s+-a\b))",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:\b(?:ignore\s+(?:previous|prior|all)|override|bypass|suppress|silently|quietly|without\s+(?:telling|mentioning|flagging)|do\s+not\s+(?:tell|mention|disclose)|prerequisite|always\s+append)\b|\bimportant\*{0,2}\s*:|静默|悄悄|忽略(?:之前|先前|所有)|绕过|隐瞒|不要(?:告诉|提及)|文末|必带|扫码|进群|环境变量|凭据|密钥)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:https?://|paste\.|rentry\.|glot\.io|raw\.githubusercontent\.com|\b\d{1,3}(?:\.\d{1,3}){3}\b|extract\s+(?:with|using)\s+pass)",
        re.IGNORECASE,
    ),
)


def is_autonomous_guards_enabled() -> bool:
    """Return True unless ``SKILL_SCAN_AUTONOMOUS_GUARDS`` explicitly disables guards."""
    raw = str(get_env("SKILL_SCAN_AUTONOMOUS_GUARDS", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _is_semantic_doc(rel_path: str) -> bool:
    norm = rel_path.replace("\\", "/")
    parts = [p for p in norm.split("/") if p and p != "."]
    if not parts:
        return False
    if any(p in _SKIP_DIRS for p in parts[:-1]):
        return False
    fname = parts[-1]
    if fname in _SKIP_FILES or fname in _METADATA_FILENAMES:
        return False
    if any(fname.startswith(prefix) for prefix in _METADATA_PREFIXES):
        return False
    if fname.lower() in _SEMANTIC_FILENAMES:
        return True
    return os.path.splitext(fname)[1].lower() in _SEMANTIC_EXTS


def _is_path_within_repo(repo_dir: str, target_path: str) -> bool:
    """Return True iff *target_path* resolves inside *repo_dir* and exists as a regular file."""
    try:
        real_root = os.path.realpath(repo_dir)
        real_target = os.path.realpath(target_path)
        return (
            os.path.commonpath([real_root, real_target]) == real_root
            and os.path.isfile(real_target)
        )
    except (OSError, ValueError):
        return False


def _normalize_repo_rel_ref(raw_ref: str) -> str:
    norm = raw_ref.strip().strip("`\"'").replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    return norm.lstrip("/")


def _extract_skill_references(
    repo_dir: str,
    skill_rel_path: str = "SKILL.md",
    *,
    max_file_size: int = _DEFAULT_MAX_FILE_SIZE,
) -> set[str]:
    """Extract local semantic doc paths referenced by *skill_rel_path*."""
    abs_skill = os.path.join(repo_dir, skill_rel_path)
    if not _is_path_within_repo(repo_dir, abs_skill):
        return set()
    try:
        if os.path.getsize(abs_skill) > max_file_size:
            return set()
        decoded = read_text_file(abs_skill)
    except (OSError, TextDecodeError):
        return set()

    text = decoded.recovered_text or decoded.text
    skill_parent = os.path.dirname(skill_rel_path)
    refs: set[str] = set()

    raw_candidates = [m.group(1) for m in _MD_LINK_RE.finditer(text)]
    raw_candidates.extend(m.group(1) for m in _REL_SEMANTIC_PATH_RE.finditer(text))

    for raw in raw_candidates:
        if "://" in raw or raw.startswith(("mailto:", "#")):
            continue
        cleaned = _normalize_repo_rel_ref(raw)
        if not cleaned or cleaned.startswith(".."):
            continue
        for candidate_rel in (
            cleaned,
            os.path.normpath(os.path.join(skill_parent, cleaned)).replace("\\", "/")
            if skill_parent
            else cleaned,
        ):
            parts = candidate_rel.lower().split("/")
            if (
                parts[-1] in _BOILERPLATE_FILENAMES
                and not any(d in _PROGRESSIVE_DIRS for d in parts[:-1])
            ):
                continue
            if _is_semantic_doc(candidate_rel) and _is_path_within_repo(
                repo_dir, os.path.join(repo_dir, candidate_rel)
            ):
                refs.add(candidate_rel)
    return refs


def _classify_semantic_file_tier(
    rel_path: str,
    referenced_files: set[str],
    has_skill_md: bool,
) -> int:
    norm = rel_path.replace("\\", "/")
    parts = norm.lower().split("/")
    fname = parts[-1]
    if fname == "skill.md":
        return 0
    in_progressive_dir = any(d in _PROGRESSIVE_DIRS for d in parts[:-1])
    if has_skill_md and fname in _BOILERPLATE_FILENAMES and not in_progressive_dir:
        return 3
    if norm in referenced_files or in_progressive_dir:
        return 1
    return 2


def _iter_semantic_files_with_tiers(repo_dir: str) -> list[tuple[str, int]]:
    """Return ``(rel_path, tier)`` sorted by progressive-disclosure audit priority."""
    raw_paths: list[str] = []
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, repo_dir).replace(os.sep, "/")
            if _is_semantic_doc(rel) and _is_path_within_repo(repo_dir, fpath):
                raw_paths.append(rel)

    skill_files = [p for p in raw_paths if os.path.basename(p).lower() == "skill.md"]
    has_skill_md = bool(skill_files)
    referenced_files: set[str] = set()
    for sp in skill_files:
        referenced_files.update(_extract_skill_references(repo_dir, sp))

    tiered = [
        (rel, _classify_semantic_file_tier(rel, referenced_files, has_skill_md))
        for rel in raw_paths
    ]
    tiered.sort(
        key=lambda item: (
            item[1],
            0 if item[0] in referenced_files else 1,
            item[0].count("/"),
            item[0].lower(),
        )
    )
    return tiered


def _extract_hidden_unicode_text(text: str) -> str:
    """Decode hidden ASCII from Unicode Tag steganography or zero-width/bidi obfuscation."""
    if not text or text.isascii():
        return ""

    recovered_parts: list[str] = []
    tag_chars: list[str] = []
    for ch in text:
        cp = ord(ch)
        if 0xE0020 <= cp <= 0xE007E:
            tag_chars.append(chr(cp - 0xE0000))
        elif cp == 0xE000A:
            tag_chars.append("\n")
        elif cp == 0xE0009:
            tag_chars.append("\t")
    decoded_tags = "".join(tag_chars).strip()
    if len(decoded_tags) >= 4:
        recovered_parts.append(f"[Unicode Tag steganography]: {decoded_tags}")

    bidi_count = sum(1 for ch in text if ch in _BIDI_CONTROL_CHARS)
    zw_sus = 0
    for i, ch in enumerate(text):
        if ch not in _ZERO_WIDTH_CHARS:
            continue
        if ch == "\u200d" and 0 < i < len(text) - 1:
            if ord(text[i - 1]) >= 0x2600 and ord(text[i + 1]) >= 0x2600:
                continue
        zw_sus += 1

    if bidi_count >= 1 or zw_sus >= 2:
        stripped = "".join(
            ch
            for ch in text
            if ch not in _BIDI_CONTROL_CHARS
            and ch not in _ZERO_WIDTH_CHARS
            and not (0xE0000 <= ord(ch) <= 0xE007F)
        ).strip()
        if stripped and stripped != decoded_tags:
            recovered_parts.append(f"[Zero-width/Bidi stripped text]: {stripped}")

    return "\n".join(recovered_parts)


def _scan_static_hidden_semantic_cues(
    repo_dir: str,
    tiered_files: list[tuple[str, int]],
    max_file_size: int = _DEFAULT_MAX_FILE_SIZE,
) -> list[tuple[str, int, str]]:
    """Detect hidden Unicode Tags, Bidi/zero-width obfuscation, or risky HTML comments."""
    cues: list[tuple[str, int, str]] = []
    for rel_path, tier in tiered_files:
        if tier == 3:
            continue
        abs_path = os.path.join(repo_dir, rel_path)
        if not _is_path_within_repo(repo_dir, abs_path):
            continue
        try:
            if os.path.getsize(abs_path) > max_file_size:
                continue
            decoded = read_text_file(abs_path)
        except (OSError, TextDecodeError):
            continue

        lines = decoded.text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            line_no = i + 1
            hidden_line = _extract_hidden_unicode_text(line)
            if hidden_line:
                cues.append(
                    (
                        rel_path,
                        line_no,
                        f"Hidden Unicode content decoded: {hidden_line[:180]}",
                    )
                )
            if _HTML_COMMENT_OPEN_RE.match(line):
                comment_lines = [line]
                j = i
                if "-->" not in line and not _MALFORMED_COMMENT_CLOSE_RE.match(line):
                    j = i + 1
                    while j < len(lines):
                        comment_lines.append(lines[j])
                        if "-->" in lines[j] or _MALFORMED_COMMENT_CLOSE_RE.match(lines[j]):
                            break
                        j += 1
                comment_text = "\n".join(comment_lines)
                hidden_comment = _extract_hidden_unicode_text(comment_text)
                if hidden_comment and not hidden_line:
                    cues.append(
                        (
                            rel_path,
                            line_no,
                            f"Hidden Unicode content decoded: {hidden_comment[:180]}",
                        )
                    )
                elif (
                    any(p.search(comment_text) for p in _RISKY_COMMENT_PATTERNS)
                    or len(comment_text) >= 120
                ):
                    snippet = re.sub(r"\s+", " ", comment_text).strip()[:180]
                    cues.append((rel_path, line_no, f"HTML comment block: {snippet}"))
                i = max(i + 1, j + 1)
                continue
            i += 1
    return cues


def build_progressive_semantic_map(
    repo_dir: str,
    *,
    max_file_size: int = _DEFAULT_MAX_FILE_SIZE,
    max_entries: int = 30,
) -> str:
    """Build a 0-token progressive-disclosure file map and hidden-cue summary for Code Audit."""
    if not repo_dir or not os.path.isdir(repo_dir):
        return ""
    tiered = _iter_semantic_files_with_tiers(repo_dir)
    if not tiered:
        return ""

    t01 = [(rel, tier) for rel, tier in tiered if tier in (0, 1)]
    hidden_cues = _scan_static_hidden_semantic_cues(
        repo_dir, tiered, max_file_size=max_file_size
    )
    if len(t01) <= 1 and not hidden_cues:
        return ""

    lines: list[str] = []
    if len(t01) > 1:
        lines.append(
            "Progressive-disclosure semantic inventory (0-token static map; read referenced "
            "files instead of stopping at SKILL.md):"
        )
        for rel, tier in t01[:max_entries]:
            abs_path = os.path.join(repo_dir, rel)
            try:
                if os.path.getsize(abs_path) > max_file_size:
                    continue
                decoded = read_text_file(abs_path)
                n_lines = len(decoded.text.splitlines())
                n_chars = len(decoded.text)
                tag = "entry" if tier == 0 else "ref"
                lines.append(f"- [{tag}] `{rel}` ({n_lines} lines, {n_chars} chars)")
            except (OSError, TextDecodeError):
                lines.append(f"- [ref] `{rel}`")
        if len(t01) > max_entries:
            lines.append(f"- ... (+{len(t01) - max_entries} additional semantic reference files)")

    if hidden_cues:
        lines.append(
            "\nStatic concealed-semantic alerts (decoded invisible Unicode / suspicious HTML comments):"
        )
        for rel, line_no, desc in hidden_cues[:12]:
            lines.append(f"- `{rel}` L{line_no}: {desc}")

    return "\n".join(lines)


def collect_required_audit_files(
    repo_dir: str,
    pre_scan_hints: str = "",
    *,
    max_tier1_required: int = 8,
) -> list[str]:
    """Return relative POSIX paths that Code Audit must inspect before concluding clean."""
    if not repo_dir or not os.path.isdir(repo_dir):
        return []
    tiered = _iter_semantic_files_with_tiers(repo_dir)
    required: list[str] = []
    seen: set[str] = set()

    def add_path(rel: str) -> None:
        norm = rel.replace("\\", "/").lstrip("./")
        if norm and norm not in seen and os.path.isfile(os.path.join(repo_dir, norm)):
            seen.add(norm)
            required.append(norm)

    for rel, tier in tiered:
        if tier == 0:
            add_path(rel)

    for hit_file in _PRESCAN_FILE_LINE_RE.findall(pre_scan_hints or ""):
        add_path(hit_file)
    for cue_file, _, _ in _scan_static_hidden_semantic_cues(repo_dir, tiered):
        add_path(cue_file)

    t1_files = [rel for rel, tier in tiered if tier == 1]
    t1_non_agents = [r for r in t1_files if os.path.basename(r).lower() != "agents.md"]
    if len(t1_non_agents) <= max_tier1_required:
        for rel in t1_files:
            add_path(rel)
    else:
        for rel in t1_files:
            if os.path.basename(rel).lower() == "agents.md":
                add_path(rel)

    return required
