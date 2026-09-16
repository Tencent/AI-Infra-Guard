#!/usr/bin/env python3
"""Freeze Qwen A runs into three causal Pi fixtures per case."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from roguehandoff.catalog import get_scenario  # noqa: E402
from roguehandoff.runner import (  # noqa: E402
    _pending_call_error,
    validate_pi_fixtures,
)


FIXED_LOCAL_URL = re.compile(
    r"https?://(?:127\.0\.0\.1|localhost|0\.0\.0\.0|\[::1\]):\d+",
    re.IGNORECASE,
)


def messages(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def user_seed(items: list[dict], prompt: str) -> list[dict]:
    # Session items contain nested message/content objects. A shallow copy makes
    # the normal and attack fixtures alias the same prompt and silently turns
    # both conditions into whichever one was written last.
    first_user_index = next(
        index for index, item in enumerate(items)
        if item.get("type") == "message"
        and item.get("message", {}).get("role") == "user"
    )
    copied = copy.deepcopy(items[:first_user_index + 1])
    message = copied[-1]["message"]
    content = message.get("content", [])
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                part["text"] = prompt
                break
    else:
        message["content"] = prompt
    return copied


def freeze(raw_root: Path, design_root: Path, output: Path, case_ids: list[int]) -> None:
    for case_id in case_ids:
        design_path = next(design_root.glob(f"{case_id:02d}-*.json"))
        design = json.loads(design_path.read_text())
        scenario = get_scenario(case_id)
        raw_path = next((raw_root / f"case{case_id:02d}").glob("*.jsonl"))
        items = messages(raw_path)
        output_case = output / f"{case_id:02d}-{design['slug']}"
        output_case.mkdir(parents=True, exist_ok=True)

        direct = user_seed(items, design["attack_prompt"])
        normal = user_seed(items, design["normal_prompt"])
        for condition, selected in (("normal", normal), ("direct_attack", direct)):
            (output_case / f"{condition}.jsonl").write_text(
                "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
                        for item in selected)
            )

        # Raw authoring sessions necessarily contain their ephemeral server
        # port.  Freeze the conversation against the runtime-provided base URL
        # before validating or publishing it.
        items = [
            json.loads(FIXED_LOCAL_URL.sub(
                "$ROGUEHANDOFF_BASE_URL", json.dumps(item, ensure_ascii=False)
            ))
            for item in items
        ]

        terminal = design["harmful_tool"]
        cut = None
        for index, item in enumerate(items):
            message = item.get("message", {})
            if message.get("role") != "assistant":
                continue
            content = message.get("content", [])
            if not isinstance(content, list):
                continue
            calls = [
                part for part in content
                if isinstance(part, dict)
                and part.get("type") in {"toolCall", "tool_use"}
            ]
            if len(calls) == 1 and _pending_call_error(calls[0], scenario) is None:
                cut = index + 1
                break
        if cut is None:
            raise ValueError(f"{raw_path}: Qwen did not emit harmful toolCall {terminal}")
        handoff = items[:cut]
        first_user = next(
            item["message"] for item in handoff
            if item.get("type") == "message"
            and item.get("message", {}).get("role") == "user"
        )
        content = first_user.get("content", [])
        first_text = content if isinstance(content, str) else "".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
        if first_text != design["attack_prompt"]:
            raise ValueError(f"{raw_path}: raw A session does not use attack_prompt")
        if handoff[-1].get("message", {}).get("role") != "assistant":
            raise ValueError(f"{raw_path}: harmful toolCall has a returned result")
        (output_case / "attack_handoff.jsonl").write_text(
            "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
                    for item in handoff)
        )

    validate_pi_fixtures(output)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: freeze_qwen_sessions.py RAW_ROOT DESIGN_ROOT OUTPUT")
    freeze(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), list(range(1, 21)))
    print("frozen and strictly validated Qwen sessions for 20 cases")
