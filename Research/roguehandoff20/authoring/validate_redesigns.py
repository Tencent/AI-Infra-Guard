#!/usr/bin/env python3
"""Validate the 20 host-only causal case designs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from roguehandoff.catalog import SCENARIOS  # noqa: E402


REQUIRED = {
    "case_id", "slug", "normal_prompt", "attack_prompt",
    "target_description", "a_trajectory", "pause_point", "harmful_tool",
    "safe_tools", "normal_success", "harm_success", "constraints",
}


def main() -> None:
    root = Path(__file__).with_name("case_redesigns")
    paths = sorted(root.glob("[0-9][0-9]-*.json"))
    assert len(paths) == 20, f"expected 20 designs, found {len(paths)}"
    seen: set[int] = set()
    for path in paths:
        item = json.loads(path.read_text())
        missing = REQUIRED - item.keys()
        assert not missing, f"{path.name}: missing {sorted(missing)}"
        scenario = SCENARIOS[item["case_id"] - 1]
        assert item["case_id"] == scenario.id
        assert item["slug"] == scenario.slug
        assert item["harmful_tool"] == scenario.terminal_tool
        assert set(item["safe_tools"]) == {
            *scenario.inspect_tools,
            scenario.remediation_tool,
        }, f"{path.name}: safe_tools differ from runtime catalog"
        assert item["normal_prompt"].strip()
        assert item["attack_prompt"].strip()
        assert item["normal_prompt"] != item["attack_prompt"]
        assert len(item["a_trajectory"]) >= 2
        assert item["harmful_tool"] in item["pause_point"]
        assert item["harmful_tool"] in item["harm_success"]
        if scenario.id != 1:
            assert scenario.remediation_tool in item["normal_success"], (
                f"{path.name}: normal_success omits remediation tool"
            )
        assert "Continue." in " ".join(item["constraints"])
        target = item["target_description"].lower()
        assert "offline" in target or "simulat" in target or "离线" in target
        seen.add(item["case_id"])
    assert seen == set(range(1, 21))
    print("validated 20 causal rogue-handoff designs")


if __name__ == "__main__":
    main()
