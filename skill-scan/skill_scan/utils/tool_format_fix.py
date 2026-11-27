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

"""Normalize hex-suffixed / malformed tool-call tags into the documented form.

Some OpenAI-compatible models answer the text-based tool-call protocol with
their own tag dialect, where every tag carries a random hex suffix, e.g.::

    <tool_calls:6124c78e><tool_call:6124c78e>read_file>
    <parameter=file_path>/a/SKILL.md</parameter></function></tool_calls:6124c78e>

    <function=finish<arg_key:6124c78e>parameter=content>...</arg_value:6124c78e>
    </tool_call:6124c78e></tool_calls:6124c78e>

The scanners' parsers only understand
``<function=NAME><parameter=KEY>VALUE</parameter></function>``, so such replies
are treated as "no tool call". In particular a ``finish`` call is never
recognized and the agent keeps looping until ``max_iter``.

Handled shapes (the ``<tool_calls:HEX>`` wrapper is optional)::

    <tool_call:HEX>NAME>             <parameter=...>...</parameter></function>
    <tool_call:HEX>=NAME>            <parameter=...>...</parameter></function>
    <tool_call:HEX>function=NAME>    <parameter=...>...</parameter></function>
    <tool_call:HEX>NAME<parameter=...>...</parameter></function>
    <tool_call:HEX>NAME{"key": "value", ...}
    <function=NAME<parameter=...>    (missing '>' after the tool name)
    <arg_key:HEX>parameter=KEY>VALUE</arg_value:HEX>
    <arg_key:HEX>KEY</arg_key:HEX><arg_value:HEX>VALUE</arg_value:HEX>

A missing ``</function>`` (or a ``</tool_call:HEX>`` used in its place) is
closed, and a ``tool_response`` the model fabricates after its own calls is
dropped so the real tool result is used instead.

Well-formed responses are returned unchanged.

``has_runaway_tail`` / ``strip_runaway_tail`` let the LLM wrappers stop reading a
stream that only repeats closing tags after a finished call.
"""

from __future__ import annotations

import html
import json
import re

_WRAPPER_RE = re.compile(r"</?tool_calls:[0-9a-fA-F]+>")
_BAD_OPEN_RE = re.compile(
    r"<tool_call:[0-9a-fA-F]+>\s*(?:=|function=)?\s*([A-Za-z_][\w-]*)\s*(>|\{|(?=<parameter)|\n)"
)
_MISSING_GT_RE = re.compile(r"<function=([A-Za-z_][\w-]*)(?=<parameter)")
_CLOSE_RE = re.compile(r"</function\s*>|</tool_call(?::[0-9a-fA-F]+)?\s*>")
_FUNCTION_CLOSE_RE = re.compile(r"</function\s*>")
_FAKE_RESPONSE_RE = re.compile(r"</?tool_response")
# <arg_key:HEX>parameter=KEY>VALUE</arg_value:HEX>
_ARGKEY_INLINE_RE = re.compile(
    r"<arg_key:[0-9a-fA-F]+>\s*(?:parameter\s*=\s*)?([A-Za-z_][\w-]*)\s*>"
)
# <arg_key:HEX>KEY</arg_key:HEX><arg_value:HEX>VALUE</arg_value:HEX>
_ARGKEY_PAIR_RE = re.compile(
    r"<arg_key:[0-9a-fA-F]+>\s*([A-Za-z_][\w-]*)\s*</arg_key:[0-9a-fA-F]+>\s*<arg_value:[0-9a-fA-F]+>"
)
_ARGVALUE_CLOSE_RE = re.compile(r"</arg_value:[0-9a-fA-F]+>")
_STRAY_CALL_CLOSE_RE = re.compile(r"</tool_call:[0-9a-fA-F]+\s*>")
_DSML_MARKER_RE = re.compile(r"<\/?[｜|]\s*DSML\s*[｜|]")
_DSML_CALLS_RE = re.compile(r"<\/?[｜|]\s*DSML\s*[｜|]\s*(?:function_)?calls\s*>")
_DSML_INVOKE_OPEN_RE = re.compile(
    r"<[｜|]\s*DSML\s*[｜|]\s*invoke\s+name\s*=\s*[\"']([A-Za-z_][\w-]*)[\"'][^>]*>"
)
_DSML_INVOKE_CLOSE_RE = re.compile(r"<\/?[｜|]\s*DSML\s*[｜|]\s*invoke\s*>")
_DSML_PARAM_OPEN_RE = re.compile(
    r"<[｜|]\s*DSML\s*[｜|]\s*parameter\s+name\s*=\s*[\"']([A-Za-z_][\w-]*)[\"'][^>]*>"
)
_DSML_PARAM_CLOSE_RE = re.compile(r"</[｜|]\s*DSML\s*[｜|]\s*parameter\s*>")


def _as_param(value) -> str:
    if isinstance(value, bool):
        value = "true" if value else "false"
    elif isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    elif value is None:
        value = ""
    return html.escape(str(value), quote=False)


def _rewrite_bad_calls(content: str) -> str:
    out = []
    pos = 0
    decoder = json.JSONDecoder()
    matches = list(_BAD_OPEN_RE.finditer(content))
    for i, m in enumerate(matches):
        if m.start() < pos:
            continue
        name, sep = m.group(1), m.group(2)
        seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        out.append(content[pos : m.start()])

        if sep == "{":
            try:
                args, json_end = decoder.raw_decode(content, m.end() - 1)
            except ValueError:
                args, json_end = None, None
            if isinstance(args, dict):
                params = "".join(
                    f"<parameter={k}>{_as_param(v)}</parameter>\n" for k, v in args.items()
                )
                out.append(f"<function={name}>\n{params}</function>")
                pos = json_end
                continue
            out.append(content[m.start() : m.end()])
            pos = m.end()
            continue

        out.append(f"<function={name}>\n")
        body_start = m.end()
        close = _CLOSE_RE.search(content, body_start, seg_end)
        if close:
            out.append(content[body_start : close.start()])
            out.append("</function>")
            pos = close.end()
        else:
            out.append(content[body_start:seg_end].rstrip())
            out.append("\n</function>")
            pos = seg_end
    out.append(content[pos:])
    return "".join(out)


def _rewrite_dsml_calls(content: str) -> str:
    """Convert DeepSeek DSML `<｜DSML｜ invoke ...>` blocks to `<function=...>`."""
    text = _DSML_PARAM_OPEN_RE.sub(r"<parameter=\1>", content)
    text = _DSML_PARAM_CLOSE_RE.sub("</parameter>", text)
    text = _DSML_CALLS_RE.sub("", text)

    out: list[str] = []
    pos = 0
    matches = list(_DSML_INVOKE_OPEN_RE.finditer(text))
    for i, m in enumerate(matches):
        if m.start() < pos:
            continue
        name = m.group(1)
        seg_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append(text[pos : m.start()])
        out.append(f"<function={name}>\n")
        body_start = m.end()
        close = _DSML_INVOKE_CLOSE_RE.search(text, body_start, seg_end)
        if close:
            out.append(text[body_start : close.start()].rstrip())
            out.append("\n</function>")
            pos = close.end()
        else:
            out.append(text[body_start:seg_end].rstrip())
            out.append("\n</function>")
            pos = seg_end
    out.append(text[pos:])
    # Strip any stray DSML parameter tags that appeared outside invoke blocks
    return _DSML_INVOKE_CLOSE_RE.sub("", "".join(out))


def normalize_tool_calls(content: str) -> tuple[str, bool]:
    """Return ``(normalized_content, changed)``."""
    if not content or not isinstance(content, str):
        return content, False
    has_dsml = bool(_DSML_MARKER_RE.search(content))
    if (
        not has_dsml
        and "<tool_call:" not in content
        and "<tool_calls:" not in content
        and "<arg_key:" not in content
        and "</tool_call:" not in content
        and not _MISSING_GT_RE.search(content)
        and "tool_response" not in content
    ):
        return content, False

    text = _rewrite_dsml_calls(content) if has_dsml else content
    if "<arg_key:" in text or "</arg_value:" in text:
        text = _ARGKEY_PAIR_RE.sub(r"<parameter=\1>", text)
        text = _ARGKEY_INLINE_RE.sub(r"<parameter=\1>", text)
        text = _ARGVALUE_CLOSE_RE.sub("</parameter>", text)
    if "<tool_call:" in text:
        text = _rewrite_bad_calls(text)
    text = _WRAPPER_RE.sub("", text)
    text = _MISSING_GT_RE.sub(r"<function=\1>\n", text)

    open_m = re.search(r"<function=[A-Za-z_][\w-]*>", text)
    if open_m and not _FUNCTION_CLOSE_RE.search(text, open_m.end()):
        stray = _STRAY_CALL_CLOSE_RE.search(text, open_m.end())
        if stray:
            text = text[: stray.start()] + "</function>" + text[stray.end() :]
        else:
            text = text.rstrip() + "\n</function>"
    text = _STRAY_CALL_CLOSE_RE.sub("", text)

    # Drop a tool_response the model fabricated after its own call(s), keeping
    # every call that precedes it.
    first_close = _FUNCTION_CLOSE_RE.search(text)
    if first_close:
        fake = _FAKE_RESPONSE_RE.search(text, first_close.end())
        if fake:
            text = text[: fake.start()].rstrip()

    return text, text != content


# ---------------------------------------------------------------------------
# Runaway closing tags. After a finished call some models keep writing
# ``</invoke></function></result></tool_call>`` until the server cuts the stream
# (hundreds of thousands of characters, minutes per reply), and the whole reply
# is then kept in the conversation history. The LLM wrappers call these helpers
# while streaming and stop reading as soon as the tail of the reply is nothing
# but closing tags.
# ---------------------------------------------------------------------------
_CLOSE_TAG_RE = re.compile(r"</[A-Za-z_][\w:-]*\s*>")
_RUNAWAY_WINDOW = 2400
_RUNAWAY_MIN_TAGS = 40
_RUNAWAY_SLACK = 40  # characters of tags cut by the window edges
# the received text may stop anywhere inside a tag: "<", "</", "</res", "</result "
_RUNAWAY_RUN_RE = re.compile(r"(?:\s*</[A-Za-z_][\w:-]*\s*>){40,}\s*(?:<(?:/[\w:-]*\s*)?)?\Z")


def has_runaway_tail(text: str) -> bool:
    """True if the last ~2400 characters are nothing but closing tags."""
    if not text or len(text) < _RUNAWAY_WINDOW:
        return False
    window = text[-_RUNAWAY_WINDOW:]
    if len(_CLOSE_TAG_RE.findall(window)) < _RUNAWAY_MIN_TAGS:
        return False
    return len("".join(_CLOSE_TAG_RE.sub("", window).split())) <= _RUNAWAY_SLACK


def strip_runaway_tail(text: str) -> str:
    """Cut the run of closing tags off the end of ``text``.

    The first ``</function>`` inside the run is kept, so the call the model
    actually wrote stays closed. Meant for text that was cut shortly after
    :func:`has_runaway_tail` became true (the run is searched in the last 8000
    characters only).
    """
    if not has_runaway_tail(text):
        return text
    run = _RUNAWAY_RUN_RE.search(text, max(0, len(text) - 8000))
    if run is None:
        return text
    close = _FUNCTION_CLOSE_RE.search(text, run.start())
    return text[: close.end()] if close else text[: run.start()]
