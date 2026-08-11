#!/usr/bin/env python3
"""Phase 2: Attack dispatcher (optional helper).

Reads target_profile.json, emits attack_plan.json with ordered list of modules.

NOTE: Module scheduling is primarily prompt-driven — the host Agent should decide
which modules to run based on SKILL.md "目标分类与模块调度" rules.
This script is a lightweight convenience helper; its output can be overridden.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

# Default module priority order.
# mutation-attack is the unified variant-testing module: it covers bare LLM
# endpoints, tool/RAG/MCP-equipped Agents, and business products alike —
# the target's send/observe interface is what varies, not the module choice.
MODULE_PRIORITY = [
    "infra-attack",
    "code-attack",
    "mutation-attack",
]

# Default module mapping by target type prefix.
# The Agent may override these decisions based on context.
TYPE_MODULE_MAP: dict[str, list[str]] = {
    "self":           ["code-attack", "mutation-attack"],
    "http_service":   ["infra-attack"],
    "code_repository":["code-attack"],
    "mcp_server":     ["code-attack", "mutation-attack"],
    "skill_package":  ["code-attack", "mutation-attack"],
    "agent_definition": ["mutation-attack", "infra-attack"],
    "agent_endpoint":  ["mutation-attack", "infra-attack"],
    "llm_endpoint":    ["mutation-attack"],
}


def modules_for_target_type(t: str) -> list[str]:
    """Look up modules. Support prefix match: 'http_service:ollama' → 'http_service'."""
    if t in TYPE_MODULE_MAP:
        return list(TYPE_MODULE_MAP[t])
    if ":" in t:
        prefix = t.split(":")[0]
        if prefix in TYPE_MODULE_MAP:
            return list(TYPE_MODULE_MAP[prefix])
    return []


def build_plan(profile: dict) -> dict:
    plan = {
        "schema": "aig-agent-redteam.attack-plan.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_profile_summary": {
            "raw_input": profile.get("raw_input"),
            "target_types": profile.get("target_types", []),
        },
        "modules": [],
        "skipped": [],
    }

    seen: set[str] = set()
    target_types = profile.get("target_types", [])

    # Primary modules
    for t in target_types:
        for m in modules_for_target_type(t):
            if m not in seen:
                seen.add(m)
                plan["modules"].append({
                    "module": m,
                    "target_type": t,
                    "input": profile.get("extracted", {}),
                    "cascade_from": None,
                })

    # Cascade modules (e.g., infra found Ollama → add mutation-attack)
    for cascade in profile.get("cascade_targets", []):
        for ct in cascade.get("target_types", []):
            for m in modules_for_target_type(ct):
                if m not in seen:
                    seen.add(m)
                    plan["modules"].append({
                        "module": m,
                        "target_type": ct,
                        "input": cascade.get("extracted", {}),
                        "cascade_from": "primary",
                    })

    # Sort by priority
    priority = {m: i for i, m in enumerate(MODULE_PRIORITY)}
    plan["modules"].sort(key=lambda x: priority.get(x["module"], 999))

    if not plan["modules"]:
        plan["skipped"].append({
            "reason": "no_module_matches_target_types",
            "target_types": target_types,
            "hint": "参考 SKILL.md「目标分类与模块调度」Step 2 的类型→模块映射表",
        })

    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    profile = json.loads(Path(args.profile).read_text())
    plan = build_plan(profile)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
    print(json.dumps(plan, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
