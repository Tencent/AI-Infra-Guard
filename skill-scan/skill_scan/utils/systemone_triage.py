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

"""System One Capability Primitives IR compiler for pure semantic Skill docs.

Compiles isolated semantic slices (with 4k coarse packing and tightened gray-zone
auto zoom-in) via a non-generative System One endpoint (``POST /v1/systemone``)
into a Two-Tier Rhetoric-Free Behavior Ledger. Failed/rate-limited slices are
never dropped silently; they are surfaced via ``unscanned_slices`` for mandatory
``read_file`` inspection by the downstream System 2 auditor (Option A fallback).
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from skill_scan.utils.config import get_env, get_env_int
from skill_scan.utils.progressive_audit import (
    _is_path_within_repo,
    _iter_semantic_files_with_tiers,
)
from skill_scan.utils.semantic_slicer import (
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_MIN_PACK_CHARS,
    SemanticChunk,
    SkillBaseline,
    extract_capability_baseline,
    slice_semantic_text,
)
from skill_scan.utils.text_decoder import TextDecodeError, read_text_file

_LOCALHOST_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_ISOLATED_KINDS = frozenset({"frontmatter", "html_comment"})
_RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})

SYSTEMONE_QUESTIONS: dict[str, dict[str, Any]] = {
    "modality": {
        "type": "choice",
        "instructions": "Operational modality of this slice.",
        "criteria": {
            "inert_prose": "Explanatory docs, schema, or boilerplate without execution directives.",
            "passive_reference": "Security rule table, threat catalog, or bad-example to detect/avoid.",
            "actionable_directive": "Steps, prerequisites, hooks, or commands directing actions (even if optional/diagnostic).",
        },
    },
    "trigger": {
        "type": "choice",
        "instructions": "When does the behavior trigger?",
        "criteria": {
            "none": "No runtime trigger.",
            "user_explicit": "Only when user explicitly asks for this task.",
            "auto_lifecycle": "Automatically on load, prerequisites, init, hook, or background.",
            "every_output": "Forced on every response or appended to unrelated output.",
        },
    },
    "ds_credentials": {
        "type": "noul",
        "instructions": "Directs reading secrets, credentials, .env, ~/.ssh, API keys, or tokens?",
        "criteria": {
            "true": "Reads secrets, credentials, .env, API/SSH keys, or tokens.",
            "false": "Does not read secrets or credentials.",
        },
    },
    "ds_env_host_context": {
        "type": "noul",
        "instructions": "Directs inspecting host/OS info, env vars, home/profile configs, or chat history?",
        "criteria": {
            "true": "Collects host fingerprint, env vars, home configs, workspace paths, or chat history.",
            "false": "No host, env, home-config, or chat-history inspection.",
        },
    },
    "act_external_network": {
        "type": "noul",
        "instructions": "Directs sending/relaying data or telemetry to an external URL, domain, or IP?",
        "criteria": {
            "true": "Sends/relays data or telemetry to an external URL, domain, or IP.",
            "false": "No external network send.",
        },
    },
    "act_untrusted_exec": {
        "type": "noul",
        "instructions": "Directs piped/obfuscated shell (curl|bash, base64|sh), external archive/binary run, hooks/command, or !`cmd`?",
        "criteria": {
            "true": "Piped/obfuscated shell, unknown download+run, frontmatter hooks/command, or inline !`cmd`.",
            "false": "Standard local build/test commands (npm run build, pytest) or no execution.",
        },
    },
    "act_persistence_memory": {
        "type": "noul",
        "instructions": "Directs writing to persistent memory (MEMORY.md/SOUL.md), startup hooks, cron, or cross-session state?",
        "criteria": {
            "true": "Writes persistent memory, startup hooks, cron, or cross-session persistence.",
            "false": "No cross-session persistence.",
        },
    },
    "act_state_staging": {
        "type": "noul",
        "instructions": "Directs capturing/embedding collected data into a variable, metadata field, header, temp file, or snapshot?",
        "criteria": {
            "true": "Stages/embeds collected data into an intermediate field, variable, header, or snapshot.",
            "false": "No intermediate staging.",
        },
    },
    "act_tool_output_hijack": {
        "type": "noul",
        "instructions": "Directs tool replacement/spoofing, forced output appendices/links, or agent goal override?",
        "criteria": {
            "true": "Spoofs tools, forces output text/links, or hijacks agent goals.",
            "false": "No tool/output hijacking.",
        },
    },
    "stealth_hide_from_user": {
        "type": "noul",
        "instructions": "Instructs acting silently or omitting/hiding steps from user responses, CLI, or logs?",
        "criteria": {
            "true": "Tells agent to act silently or hide/omit actions from user or logs.",
            "false": "No concealment instruction.",
        },
    },
    "stealth_override_safety": {
        "type": "noul",
        "instructions": "Contains instruction-override/jailbreak directives or hidden Unicode/HTML comment commands?",
        "criteria": {
            "true": "Overrides prior rules/evaluator or uses hidden Unicode/HTML comment directives.",
            "false": "No override or concealed channel.",
        },
    },
    "baseline_drift": {
        "type": "score",
        "instructions": "Divergence from skill_baseline_untrusted.",
        "criteria": [
            "Aligned: Core declared task",
            "Minor_Aux: Standard helper/setup",
            "Scope_Creep: Weakly related or broad access",
            "Severe_Drift: Unrelated or contrary",
        ],
    },
}

_URL_RE = re.compile(r"https?://[^\s`\"')<>]+", re.IGNORECASE)
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b")
_SENSITIVE_PATH_RE = re.compile(
    r"(?:~/\.[^\s`\"')]+|\b(?:\.env(?:\.[A-Za-z0-9_.-]+)?|\.ssh(?:/[^\s`\"')]+)?|\.aws(?:/[^\s`\"')]+)?|"
    r"id_rsa|id_ed25519|authorized_keys|MEMORY\.md|SOUL\.md|/etc/passwd|/tmp/[A-Za-z0-9_.-]+|"
    r"[A-Z][A-Z0-9_]{2,}_(?:API_KEY|SECRET|SECRET_KEY|TOKEN|PASSWORD))\b)"
)
_EXEC_TOKEN_RE = re.compile(
    r"(?:!\s*`[^`]{1,100}`|\|\s*(?:ba|z)?sh\b|\b(?:curl|wget|base64|powershell|pwsh|iex|crontab|launchctl|systemctl)\b|"
    r"^\s*(?:hooks|command|UserPromptSubmit|PreToolUse|PostToolUse)\s*:|extract\s+(?:with|using)\s+pass\b)",
    re.IGNORECASE | re.MULTILINE,
)
_BACKTICK_IDENT_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.-]{1,48})`")
_SUSPICIOUS_IDENT_HINT_RE = re.compile(
    r"(?:^_|ctx|diag|bundle|state|token|secret|key|env|telemetry|header|X-[A-Za-z0-9-]+)",
    re.IGNORECASE,
)


def get_systemone_base_url() -> str:
    """Return normalized System One endpoint URL, or empty string when disabled."""
    raw = (get_env("SYSTEMONE_BASE_URL") or "").strip()
    if not raw:
        return ""
    stripped = raw.rstrip("/")
    if stripped.endswith("/v1"):
        return f"{stripped}/systemone"
    return raw


def is_systemone_enabled() -> bool:
    """Return True iff ``SYSTEMONE_BASE_URL`` is configured."""
    return bool(get_systemone_base_url())


def get_systemone_model() -> str:
    return (get_env("SYSTEMONE_MODEL") or "").strip() or "typesafe/jev-1.13"


def get_systemone_api_key(fallback_key: str = "") -> str:
    for candidate in (
        get_env("SYSTEMONE_API_KEY"),
        get_env("LLM_API_KEY"),
        get_env("OPENAI_API_KEY"),
        fallback_key,
    ):
        if candidate and str(candidate).strip():
            return str(candidate).strip()
    return ""


def get_systemone_concurrency() -> int:
    return max(1, get_env_int("SYSTEMONE_CONCURRENCY", 3))


def get_systemone_min_interval_s() -> float:
    return max(0, get_env_int("SYSTEMONE_MIN_INTERVAL_MS", 150)) / 1000.0


def get_systemone_coarse_chars() -> int:
    return max(1200, get_env_int("SYSTEMONE_COARSE_CHARS", 4000))


def _is_localhost_url(url: str) -> bool:
    try:
        host = (urllib.parse.urlparse(url).hostname or "").strip().lower()
    except ValueError:
        return False
    return host in _LOCALHOST_HOSTS


def _post_systemone_sync(
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: float = 35.0,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    if _is_localhost_url(url):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class PacedSystemOneClient:
    """Async concurrency-bounded, interval-paced client for ``/v1/systemone``."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        concurrency: int = 3,
        min_interval_s: float = 0.15,
        max_retries: int = 5,
        timeout: float = 35.0,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.sem = asyncio.Semaphore(max(1, concurrency))
        self.min_interval_s = max(0.0, min_interval_s)
        self.max_retries = max_retries
        self.timeout = timeout
        self._pace_lock = asyncio.Lock()
        self._next_slot = 0.0

    async def _wait_slot(self) -> None:
        if self.min_interval_s <= 0:
            return
        async with self._pace_lock:
            now = time.monotonic()
            if now < self._next_slot:
                await asyncio.sleep(self._next_slot - now)
                now = time.monotonic()
            self._next_slot = now + self.min_interval_s

    async def evaluate(
        self,
        state: dict[str, Any],
        questions: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, float, int, int, float, int, str]:
        payload = {
            "model": self.model,
            "state": state,
            "questions": questions or SYSTEMONE_QUESTIONS,
        }
        backoff = (1.0, 2.0, 4.0, 8.0, 12.0)
        retries_used = 0
        t0 = time.monotonic()
        last_err = ""
        async with self.sem:
            for attempt in range(self.max_retries + 1):
                await self._wait_slot()
                try:
                    data = await asyncio.to_thread(
                        _post_systemone_sync,
                        self.base_url,
                        self.api_key,
                        payload,
                        self.timeout,
                    )
                    elapsed = time.monotonic() - t0
                    usage = data.get("usage") or {}
                    return (
                        data,
                        elapsed,
                        int(usage.get("input_tokens") or 0),
                        int(usage.get("output_tokens") or 0),
                        float(usage.get("cost") or 0.0),
                        retries_used,
                        "",
                    )
                except urllib.error.HTTPError as exc:
                    body = exc.read().decode("utf-8", errors="replace")[:300]
                    last_err = f"HTTP {exc.code}: {body}"
                    if exc.code in _RETRYABLE_HTTP_CODES and attempt < self.max_retries:
                        retries_used += 1
                        delay = backoff[min(attempt, len(backoff) - 1)]
                        await asyncio.sleep(delay + random.uniform(0.05, 0.35))
                        continue
                    return None, time.monotonic() - t0, 0, 0, 0.0, retries_used, last_err
                except Exception as exc:  # noqa: BLE001
                    last_err = f"{type(exc).__name__}: {exc}"
                    if attempt < self.max_retries:
                        retries_used += 1
                        delay = backoff[min(attempt, len(backoff) - 1)]
                        await asyncio.sleep(delay + random.uniform(0.05, 0.35))
                        continue
                    return None, time.monotonic() - t0, 0, 0, 0.0, retries_used, last_err
        return None, time.monotonic() - t0, 0, 0, 0.0, retries_used, last_err


def extract_objective_literals(chunk: SemanticChunk) -> dict[str, list[str]]:
    """Deterministically extract concrete literal tokens (no prose/adjectives)."""
    hidden_txt = getattr(chunk, "hidden_decoded_text", "") or ""
    combined = f"{chunk.text}\n{hidden_txt}" if hidden_txt else chunk.text

    urls = list(dict.fromkeys(_URL_RE.findall(combined)))[:6]
    ips = [
        ip for ip in dict.fromkeys(_IP_RE.findall(combined)) if not ip.startswith("127.0.0.")
    ][:4]
    sens = list(dict.fromkeys(_SENSITIVE_PATH_RE.findall(combined)))[:8]
    execs = list(
        dict.fromkeys(m.strip() for m in _EXEC_TOKEN_RE.findall(combined) if m.strip())
    )[:6]

    idents: list[str] = []
    for raw_id in _BACKTICK_IDENT_RE.findall(combined):
        if _SUSPICIOUS_IDENT_HINT_RE.search(raw_id) and raw_id not in idents:
            idents.append(raw_id)
        if len(idents) >= 6:
            break

    concealed: list[str] = []
    if hidden_txt:
        concealed.append("hidden_unicode:" + re.sub(r"\s+", " ", hidden_txt).strip()[:160])
    if chunk.kind == "html_comment":
        concealed.append("html_comment:" + re.sub(r"\s+", " ", chunk.text).strip()[:160])
    if chunk.is_recovered_mojibake:
        concealed.append("recovered_mojibake:true")

    return {
        "urls": urls,
        "ips": ips,
        "sensitive_tokens": sens,
        "exec_tokens": execs,
        "state_idents": idents,
        "concealed": concealed,
    }


def _noul(answers: dict[str, Any], key: str) -> float:
    return float((answers.get(key) or {}).get("noul") or 0.0)


def _choice(answers: dict[str, Any], key: str) -> tuple[str, dict[str, float]]:
    obj = answers.get(key) or {}
    return str(obj.get("choice") or ""), dict(obj.get("probabilities") or {})


def _score(answers: dict[str, Any], key: str) -> float:
    return float((answers.get(key) or {}).get("score") or 0.0)


def _extract_probs(answers: dict[str, Any]) -> dict[str, Any]:
    modality, mod_probs = _choice(answers, "modality")
    p_act = float(
        mod_probs.get("actionable_directive")
        or (1.0 if modality == "actionable_directive" else 0.0)
    )
    trigger, _ = _choice(answers, "trigger")
    return {
        "modality": modality,
        "p_actionable": round(p_act, 3),
        "trigger": trigger,
        "drift": round(_score(answers, "baseline_drift"), 2),
        "p_creds": round(_noul(answers, "ds_credentials"), 2),
        "p_env": round(_noul(answers, "ds_env_host_context"), 2),
        "p_net": round(_noul(answers, "act_external_network"), 2),
        "p_exec": round(_noul(answers, "act_untrusted_exec"), 2),
        "p_mem": round(_noul(answers, "act_persistence_memory"), 2),
        "p_stage": round(_noul(answers, "act_state_staging"), 2),
        "p_hijack": round(_noul(answers, "act_tool_output_hijack"), 2),
        "p_hide": round(_noul(answers, "stealth_hide_from_user"), 2),
        "p_override": round(_noul(answers, "stealth_override_safety"), 2),
    }


def needs_zoom_in(chunk: SemanticChunk, meta: dict[str, Any]) -> bool:
    """Return True if a coarse chunk (>1200 chars) warrants fine-grained zoom-in."""
    if len(chunk.text) <= 1200 or chunk.kind in _ISOLATED_KINDS:
        return False
    if max(
        meta["p_hide"],
        meta["p_override"],
        meta["p_exec"],
        meta["p_mem"],
        meta["p_hijack"],
    ) >= 0.25:
        return True
    trig = meta["trigger"]
    drift = meta["drift"]
    if (
        max(meta["p_creds"], meta["p_net"], meta["p_stage"]) >= 0.30
        and (trig in {"auto_lifecycle", "every_output"} or drift >= 1.2)
    ):
        return True
    if meta["p_env"] >= 0.45 and drift >= 1.5:
        return True
    return drift >= 1.8


def classify_tier(chunk: SemanticChunk, meta: dict[str, Any]) -> tuple[str, float]:
    """Classify a slice into ``tier_a``, ``tier_b_cap``, ``tier_b_ref``, or ``none``."""
    has_concealed = bool(getattr(chunk, "hidden_decoded_text", "")) or bool(
        chunk.is_recovered_mojibake
    )
    is_actionable = meta["modality"] == "actionable_directive" or meta["p_actionable"] >= 0.45
    trig = meta["trigger"]
    drift = meta["drift"]

    tier_a = False
    if has_concealed:
        tier_a = True
    elif meta["p_hide"] >= 0.50 or meta["p_override"] >= 0.50:
        tier_a = True
    elif is_actionable and (
        meta["p_exec"] >= 0.50
        or meta["p_mem"] >= 0.50
        or meta["p_hijack"] >= 0.50
        or (
            (meta["p_creds"] >= 0.50 or meta["p_net"] >= 0.50 or meta["p_stage"] >= 0.50)
            and (trig in {"auto_lifecycle", "every_output"} or drift >= 1.5)
        )
        or (
            meta["p_env"] >= 0.55
            and (
                meta["p_stage"] >= 0.50
                or (trig in {"auto_lifecycle", "every_output"} and drift >= 1.5)
                or drift >= 2.0
            )
        )
    ):
        tier_a = True

    severity = (
        2.5 * max(meta["p_hide"], meta["p_override"])
        + 2.0 * max(meta["p_net"], meta["p_exec"], meta["p_mem"], meta["p_hijack"])
        + 1.5 * meta["p_creds"]
        + 0.8 * meta["p_stage"]
        + 0.5 * meta["p_env"]
        + 0.5 * drift
        + (2.0 if has_concealed else 0.0)
    )
    if tier_a:
        return "tier_a", round(severity, 3)

    if (
        is_actionable
        and meta["p_hide"] < 0.50
        and meta["p_override"] < 0.50
        and trig == "user_explicit"
        and drift < 1.5
        and (meta["p_creds"] >= 0.50 or meta["p_net"] >= 0.50 or meta["p_stage"] >= 0.50)
    ):
        return "tier_b_cap", round(severity, 3)

    if meta["modality"] == "passive_reference":
        return "tier_b_ref", round(severity, 3)

    return "none", round(severity, 3)


def format_ledger_entry(
    chunk: SemanticChunk,
    meta: dict[str, Any],
    literals: dict[str, list[str]],
) -> str:
    """Format one active slice as a compact, rhetoric-free Capability Primitive entry."""
    ds_parts: list[str] = []
    if meta["p_creds"] >= 0.50:
        ds_parts.append(f"read_credentials(p={meta['p_creds']:.2f})")
    if meta["p_env"] >= 0.50:
        ds_parts.append(f"read_env_host_context(p={meta['p_env']:.2f})")
    if literals["sensitive_tokens"]:
        ds_parts.append("tokens=" + ",".join(literals["sensitive_tokens"]))

    act_parts: list[str] = []
    if meta["p_net"] >= 0.50:
        act_parts.append(f"external_network_send(p={meta['p_net']:.2f})")
    if meta["p_exec"] >= 0.50:
        act_parts.append(f"untrusted_exec_or_hook(p={meta['p_exec']:.2f})")
    if meta["p_mem"] >= 0.50:
        act_parts.append(f"persistence_or_memory_write(p={meta['p_mem']:.2f})")
    if meta["p_stage"] >= 0.50:
        act_parts.append(f"intermediate_state_staging(p={meta['p_stage']:.2f})")
    if meta["p_hijack"] >= 0.50:
        act_parts.append(f"tool_or_output_hijack(p={meta['p_hijack']:.2f})")
    if literals["urls"]:
        act_parts.append("urls=" + ",".join(literals["urls"]))
    if literals["ips"]:
        act_parts.append("ips=" + ",".join(literals["ips"]))
    if literals["exec_tokens"]:
        act_parts.append("exec=" + ",".join(literals["exec_tokens"]))
    if literals["state_idents"]:
        act_parts.append("carriers=" + ",".join(literals["state_idents"]))

    stealth_parts: list[str] = []
    if meta["p_hide"] >= 0.50:
        stealth_parts.append(f"hide_from_user_or_logs(p={meta['p_hide']:.2f})")
    if meta["p_override"] >= 0.50:
        stealth_parts.append(f"override_safety_or_concealed(p={meta['p_override']:.2f})")
    if literals["concealed"]:
        stealth_parts.append("concealed=[" + " | ".join(literals["concealed"]) + "]")

    return "\n".join(
        [
            f"- [{chunk.file_path}:L{chunk.line_start}-L{chunk.line_end}] "
            f"(kind={chunk.kind}, modality={meta['modality']}[p_act={meta['p_actionable']:.2f}], "
            f"trigger={meta['trigger']}, drift={meta['drift']:.2f}/3.0)",
            f"  DataSource: {'; '.join(ds_parts) if ds_parts else 'none_explicit'}",
            f"  ActionSink: {'; '.join(act_parts) if act_parts else 'none_explicit'}",
            f"  StealthOverride: {'; '.join(stealth_parts) if stealth_parts else 'none'}",
        ]
    )


def pack_coarse_chunks(
    fine_chunks: list[SemanticChunk],
    coarse_max_chars: int = 4000,
) -> tuple[list[SemanticChunk], dict[tuple[str, int, int, bool], list[SemanticChunk]]]:
    """Merge consecutive non-isolated slices within one file up to *coarse_max_chars*.

    ``frontmatter``, ``html_comment``, ``hidden_decoded_text``, and recovered
    mojibake slices remain isolated so concealed payloads are never diluted.
    """
    coarse: list[SemanticChunk] = []
    children_map: dict[tuple[str, int, int, bool], list[SemanticChunk]] = {}
    buf: list[SemanticChunk] = []
    buf_chars = 0

    def flush_buf() -> None:
        nonlocal buf, buf_chars
        if not buf:
            return
        if len(buf) == 1:
            c = buf[0]
            coarse.append(c)
            children_map[(c.file_path, c.line_start, c.line_end, c.is_recovered_mojibake)] = [c]
        else:
            joined = "\n\n".join(x.text for x in buf)
            merged = SemanticChunk(
                file_path=buf[0].file_path,
                chunk_index=len(coarse) + 1,
                line_start=buf[0].line_start,
                line_end=buf[-1].line_end,
                kind="coarse_section",
                text=joined,
                heading=buf[0].heading,
                is_recovered_mojibake=False,
                hidden_decoded_text="",
            )
            coarse.append(merged)
            children_map[(merged.file_path, merged.line_start, merged.line_end, False)] = list(buf)
        buf = []
        buf_chars = 0

    for c in fine_chunks:
        is_isolated = (
            c.kind in _ISOLATED_KINDS
            or bool(getattr(c, "hidden_decoded_text", ""))
            or bool(c.is_recovered_mojibake)
            or len(c.text) > coarse_max_chars
        )
        if is_isolated:
            flush_buf()
            coarse.append(c)
            children_map[(c.file_path, c.line_start, c.line_end, c.is_recovered_mojibake)] = [c]
            continue

        added = len(c.text) + (2 if buf else 0)
        if buf and buf_chars + added > coarse_max_chars:
            flush_buf()
        buf.append(c)
        buf_chars += len(c.text) + (2 if len(buf) > 1 else 0)

    flush_buf()
    return coarse, children_map


def _resolve_target_files(
    repo_dir: str, target: str
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Resolve sandboxed *target* (``"."``, subdir, or file) inside *repo_dir*."""
    repo_abs = os.path.realpath(repo_dir)
    raw_target = (target or ".").strip()
    if os.path.isabs(raw_target):
        cand_abs = os.path.realpath(raw_target)
        if os.path.commonpath([repo_abs, cand_abs]) != repo_abs:
            raise ValueError(f"Target escapes repository sandbox: {target}")
        norm_target = (
            "." if cand_abs == repo_abs else os.path.relpath(cand_abs, repo_abs).replace("\\", "/")
        )
    else:
        norm_target = raw_target.replace("\\", "/")

    if norm_target in {"", ".", "./"}:
        tiered = _iter_semantic_files_with_tiers(repo_abs)
        selected = [rel for rel, tier in tiered if tier != 3]
        if not selected:
            selected = [rel for rel, _ in tiered]
    else:
        while norm_target.startswith("./"):
            norm_target = norm_target[2:]
        norm_target = norm_target.strip("/") or "."
        cand_abs = (
            repo_abs
            if norm_target == "."
            else os.path.realpath(os.path.join(repo_abs, norm_target))
        )
        if os.path.commonpath([repo_abs, cand_abs]) != repo_abs:
            raise ValueError(f"Target escapes repository sandbox: {target}")
        if os.path.isfile(cand_abs):
            selected = [os.path.relpath(cand_abs, repo_abs).replace("\\", "/")]
        elif os.path.isdir(cand_abs):
            tiered = _iter_semantic_files_with_tiers(repo_abs)
            if norm_target == ".":
                selected = [rel for rel, tier in tiered if tier != 3]
            else:
                prefix = norm_target + "/"
                selected = [
                    rel
                    for rel, tier in tiered
                    if (rel == norm_target or rel.startswith(prefix)) and tier != 3
                ]
                if not selected:
                    selected = [
                        rel
                        for rel, _ in tiered
                        if rel == norm_target or rel.startswith(prefix)
                    ]
        else:
            raise FileNotFoundError(f"Target path not found: {target}")

    loaded: list[tuple[str, str, str]] = []
    skipped: list[str] = []
    for rel_path in selected:
        abs_path = os.path.join(repo_abs, rel_path)
        if not _is_path_within_repo(repo_abs, abs_path):
            skipped.append(rel_path)
            continue
        try:
            if os.path.getsize(abs_path) > DEFAULT_MAX_FILE_SIZE:
                skipped.append(rel_path)
                continue
            decoded = read_text_file(abs_path)
            loaded.append((rel_path, decoded.text, decoded.recovered_text or ""))
        except (OSError, TextDecodeError):
            skipped.append(rel_path)
    return loaded, skipped


@dataclass
class TriageResult:
    """Output of a single ``compile_target_ledger`` invocation."""

    target: str
    granularity: str
    baseline: SkillBaseline
    files_covered: list[str]
    coarse_chunks_count: int
    zoom_in_chunks_count: int
    evaluated_slices_count: int
    tier_a_entries: list[dict[str, Any]]
    tier_b_caps: list[dict[str, Any]]
    tier_b_refs_count: int
    tier_b_ref_dirs: list[str]
    unscanned_slices: list[str]
    tier_a_files: list[str]
    stats: dict[str, Any]
    ledger_markdown: str


async def compile_target_ledger(
    repo_dir: str,
    *,
    target: str = ".",
    granularity: str = "coarse",
    line_start: int = 0,
    line_end: int = 0,
    language: str = "zh",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    concurrency: int | None = None,
    min_interval_s: float | None = None,
    coarse_chunk_chars: int | None = None,
    client: Any = None,
) -> TriageResult:
    """Compile target semantic files into a Two-Tier Rhetoric-Free Behavior Ledger."""
    resolved_url = (base_url or get_systemone_base_url()).strip()
    if client is None and not resolved_url:
        raise RuntimeError("SYSTEMONE_BASE_URL is not configured.")
    resolved_model = (model or get_systemone_model()).strip()
    resolved_key = get_systemone_api_key(api_key)

    caller = client or PacedSystemOneClient(
        resolved_url,
        resolved_key,
        resolved_model,
        concurrency=concurrency if concurrency is not None else get_systemone_concurrency(),
        min_interval_s=min_interval_s if min_interval_s is not None else get_systemone_min_interval_s(),
    )
    coarse_chars = coarse_chunk_chars if coarse_chunk_chars is not None else get_systemone_coarse_chars()

    baseline = extract_capability_baseline(repo_dir)
    baseline_str = (
        f"{baseline.name}: {baseline.description}"
        if not baseline.is_empty
        else "(no declared baseline)"
    )
    loaded, _skipped = _resolve_target_files(repo_dir, target)
    files_covered = [rel for rel, _, _ in loaded]

    gran = granularity if granularity in {"coarse", "standard", "fine"} else "coarse"
    fine_limit = 600 if gran == "fine" else 1200

    initial_chunks: list[SemanticChunk] = []
    parent_to_children: dict[tuple[str, int, int, bool], list[SemanticChunk]] = {}

    for rel_path, raw_text, rec_text in loaded:
        base_chunks = slice_semantic_text(
            raw_text,
            rel_path,
            max_chunk_chars=fine_limit,
            min_pack_chars=DEFAULT_MIN_PACK_CHARS,
        )
        if rec_text:
            base_chunks.extend(
                slice_semantic_text(
                    rec_text,
                    rel_path,
                    max_chunk_chars=fine_limit,
                    min_pack_chars=DEFAULT_MIN_PACK_CHARS,
                    is_recovered_mojibake=True,
                )
            )
        if line_start > 0 or line_end > 0:
            lo = max(1, line_start)
            hi = line_end if line_end > 0 else 10**9
            base_chunks = [c for c in base_chunks if c.line_end >= lo and c.line_start <= hi]

        if gran == "coarse":
            packed, cmap = pack_coarse_chunks(base_chunks, coarse_max_chars=coarse_chars)
            initial_chunks.extend(packed)
            parent_to_children.update(cmap)
        else:
            initial_chunks.extend(base_chunks)

    stats: dict[str, Any] = {
        "calls": 0,
        "coarse_calls": 0,
        "zoom_calls": 0,
        "errors": 0,
        "retries": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "wall_elapsed_s": 0.0,
    }

    async def eval_chunk(chunk: SemanticChunk, is_zoom: bool = False) -> dict[str, Any]:
        state: dict[str, Any] = {
            "skill_baseline_untrusted": baseline_str,
            "slice_file": chunk.file_path,
            "slice_lines": f"L{chunk.line_start}-L{chunk.line_end}",
            "block_kind": chunk.kind,
            "slice_text": chunk.text,
        }
        hidden_txt = getattr(chunk, "hidden_decoded_text", "") or ""
        if hidden_txt:
            state["hidden_decoded_content"] = hidden_txt
        if chunk.is_recovered_mojibake:
            state["is_recovered_mojibake"] = True

        literals = extract_objective_literals(chunk)
        data, _dt, in_t, out_t, cost, retries, err = await caller.evaluate(state)
        stats["calls"] += 1
        stats["zoom_calls" if is_zoom else "coarse_calls"] += 1
        stats["retries"] += retries
        stats["input_tokens"] += in_t
        stats["output_tokens"] += out_t
        stats["cost_usd"] += cost
        if data is None or "answers" not in data:
            stats["errors"] += 1
            return {
                "chunk": chunk,
                "literals": literals,
                "error": err or "missing_answers",
                "meta": None,
                "tier": "error",
                "severity": 0.0,
            }
        meta = _extract_probs(data["answers"])
        tier, sev = classify_tier(chunk, meta)
        return {
            "chunk": chunk,
            "literals": literals,
            "error": "",
            "meta": meta,
            "tier": tier,
            "severity": sev,
        }

    t0 = time.monotonic()
    first_pass = list(await asyncio.gather(*(eval_chunk(c, False) for c in initial_chunks)))

    final_results: list[dict[str, Any]] = []
    zoom_subchunks: list[SemanticChunk] = []
    if gran == "coarse":
        for item in first_pass:
            c: SemanticChunk = item["chunk"]
            meta = item["meta"]
            if item["error"]:
                final_results.append(item)
                continue
            children = parent_to_children.get(
                (c.file_path, c.line_start, c.line_end, c.is_recovered_mojibake), [c]
            )
            if len(children) > 1 and needs_zoom_in(c, meta):
                zoom_subchunks.extend(children)
                continue
            final_results.append(item)
        if zoom_subchunks:
            zoom_results = list(
                await asyncio.gather(*(eval_chunk(sc, True) for sc in zoom_subchunks))
            )
            final_results.extend(zoom_results)
    else:
        final_results = first_pass

    stats["wall_elapsed_s"] = round(time.monotonic() - t0, 3)

    unscanned: list[str] = []
    tier_a_items: list[dict[str, Any]] = []
    tier_b_caps: list[dict[str, Any]] = []
    tier_b_ref_dirs: set[str] = set()
    tier_b_refs_count = 0

    for item in final_results:
        c = item["chunk"]
        if item["error"]:
            unscanned.append(
                f"{c.file_path}:L{c.line_start}-L{c.line_end} ({item['error'][:60]})"
            )
            continue
        if item["tier"] == "tier_a":
            tier_a_items.append(item)
        elif item["tier"] == "tier_b_cap":
            tier_b_caps.append(item)
        elif item["tier"] == "tier_b_ref":
            tier_b_refs_count += 1
            tier_b_ref_dirs.add(os.path.dirname(c.file_path) or ".")

    tier_a_items.sort(
        key=lambda it: (-it["severity"], it["chunk"].file_path, it["chunk"].line_start)
    )
    tier_a_files = list(dict.fromkeys(it["chunk"].file_path for it in tier_a_items))

    tier_a_entries_out: list[dict[str, Any]] = []
    formatted_tier_a: list[str] = []
    for it in tier_a_items:
        c = it["chunk"]
        formatted_tier_a.append(format_ledger_entry(c, it["meta"], it["literals"]))
        tier_a_entries_out.append(
            {
                "file": c.file_path,
                "line_start": c.line_start,
                "line_end": c.line_end,
                "severity": it["severity"],
                "meta": it["meta"],
                "literals": it["literals"],
            }
        )

    lines: list[str] = []
    if language == "en":
        lines.append("## Rhetoric-Free Capability Primitives Behavior Ledger (System One IR)")
        lines.append(
            f"Target: `{target}` (granularity={gran}) | Baseline (untrusted): {baseline_str}"
        )
        lines.append(
            f"Coverage: {len(files_covered)} files | {len(initial_chunks)} init chunks + "
            f"{len(zoom_subchunks)} zoomed slices | Tier A={len(tier_a_items)} | "
            f"Tier B aligned={len(tier_b_caps)} | passive_refs={tier_b_refs_count} | "
            f"unscanned={len(unscanned)}"
        )
    else:
        lines.append("## 去修辞能力原语行为清单（System One 编译 IR）")
        lines.append(f"扫描范围：`{target}`（粒度={gran}）| 声明基线（不可信）：{baseline_str}")
        lines.append(
            f"覆盖统计：共 {len(files_covered)} 个语义文件 | 初扫 {len(initial_chunks)} 块 + "
            f"灰区下钻 {len(zoom_subchunks)} 细片 | Tier A 异常={len(tier_a_items)} 条 | "
            f"Tier B 基线一致={len(tier_b_caps)} 条 | 被动规则引用={tier_b_refs_count} 条 | "
            f"未完成切片={len(unscanned)} 条"
        )

    if formatted_tier_a:
        lines.append("\n### Tier A — Anomalous / High-Risk Primitives (MUST inspect via read_file)")
        lines.extend(formatted_tier_a)
    else:
        lines.append("\n### Tier A — Anomalous / High-Risk Primitives: NONE")

    if tier_b_caps or tier_b_refs_count:
        lines.append("\n### Tier B — Baseline-Aligned & Passive References (Summary)")
        if tier_b_caps:
            b_files = list(dict.fromkeys(it["chunk"].file_path for it in tier_b_caps))[:6]
            b_urls = list(dict.fromkeys(u for it in tier_b_caps for u in it["literals"]["urls"]))[:5]
            b_toks = list(
                dict.fromkeys(t for it in tier_b_caps for t in it["literals"]["sensitive_tokens"])
            )[:5]
            lines.append(
                f"- Baseline-aligned explicit capabilities ({len(tier_b_caps)} slices across "
                f"{', '.join(b_files)}): tokens={b_toks or 'none'}, urls={b_urls or 'none'}"
            )
        if tier_b_refs_count:
            dirs_str = ", ".join(sorted(tier_b_ref_dirs)[:6])
            lines.append(
                f"- Passive threat-catalog / documentation references: {tier_b_refs_count} slices "
                f"(dirs: {dirs_str})"
            )

    if unscanned:
        lines.append(
            "\n### Unscanned Slices (Failed / Rate-Limited — MUST inspect via read_file)"
        )
        for u in unscanned[:15]:
            lines.append(f"- {u}")

    return TriageResult(
        target=target,
        granularity=gran,
        baseline=baseline,
        files_covered=files_covered,
        coarse_chunks_count=len(initial_chunks),
        zoom_in_chunks_count=len(zoom_subchunks),
        evaluated_slices_count=len(final_results),
        tier_a_entries=tier_a_entries_out,
        tier_b_caps=[
            {"file": it["chunk"].file_path, "L": f"{it['chunk'].line_start}-{it['chunk'].line_end}"}
            for it in tier_b_caps
        ],
        tier_b_refs_count=tier_b_refs_count,
        tier_b_ref_dirs=sorted(tier_b_ref_dirs),
        unscanned_slices=unscanned,
        tier_a_files=tier_a_files,
        stats=stats,
        ledger_markdown="\n".join(lines),
    )
