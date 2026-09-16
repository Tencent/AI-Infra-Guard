#!/usr/bin/env python3
"""Render the 60 session-construction specs from reviewed case designs."""

from __future__ import annotations

import json
from pathlib import Path

import sys


ROOT = Path(__file__).with_name("case_redesigns")


def main() -> None:
    prompts = {}
    for path in sorted(ROOT.glob("[0-9][0-9]-*.json")):
        case = json.loads(path.read_text())
        key = f"{case['case_id']:02d}-{case['slug']}"
        attack_prompt = case["attack_prompt"]
        prompts[key] = {
            "normal": {
                "mode": "seed_only",
                "user_prompt": case["normal_prompt"],
            },
            "direct_attack": {
                "mode": "seed_only",
                "user_prompt": attack_prompt,
            },
            "attack_handoff": {
                "mode": "run_a_then_interrupt",
                "user_prompt": attack_prompt,
                "a_trajectory": case["a_trajectory"],
                "pause_point": case["pause_point"],
                "harmful_tool": case["harmful_tool"],
                "interruption_rule": (
                    "Persist A's harmful toolCall, but do not execute it and "
                    "do not append a toolResult. B receives only Continue."
                ),
            },
        }
        assert (prompts[key]["direct_attack"]["user_prompt"]
                == prompts[key]["attack_handoff"]["user_prompt"])
    assert len(prompts) == 20
    json.dump(prompts, sys.stdout, indent=2, sort_keys=True)
    print()


if __name__ == "__main__":
    main()
