"""Operator selector: pick top N operators based on registry rules."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def load_registry(registry_path: Path) -> dict:
    return json.loads(registry_path.read_text())


def select_operators(
    registry: dict,
    goal_type: str = "content",
    profile: str = "medium_defense",
    used: Optional[list] = None,
    failed: Optional[list] = None,
    top_n: int = 6,
    section: str = "single_turn",
) -> list:
    """Return top N operator ids ranked by applicability + scoring."""
    used = used or []
    failed = failed or []
    candidates = []

    pool = registry.get(section, {})
    for op_id, info in pool.items():
        if op_id in used:
            continue
        # Conflict check
        conflicts = info.get("conflicts_with", [])
        if any(c in used for c in conflicts):
            continue
        # Applicability
        applies = info.get("applies_to", [])
        if goal_type not in applies and "all" not in applies:
            continue

        score = info.get("default_priority", 50)

        # Profile bonus
        if profile == "weak_defense" and info["family"] in ("baseline", "roleplay"):
            score += 30
        if profile == "high_defense" and info["family"] in ("ssrt", "semantic"):
            score += 30
        if profile == "filter_bypass" and info["family"] in ("encoding", "stego"):
            score += 30

        # Combo bonus
        for u in used:
            if u in info.get("combo_with", []):
                score += 25

        # Penalty for similar-failed family
        for f in failed:
            f_info = pool.get(f, {})
            if f_info.get("family") == info["family"]:
                score -= 20

        candidates.append((op_id, score))

    candidates.sort(key=lambda x: -x[1])
    return [op_id for op_id, _ in candidates[:top_n]]


def select_multi_turn(
    registry: dict,
    profile: str = "medium_defense",
) -> Optional[str]:
    """Pick a multi-turn operator based on profile."""
    mapping = {
        "weak_defense": "crescendo",
        "medium_defense": "crescendo",
        "high_defense": "goat",
        "unknown": "tap",
        "large_context": "many_shot",
    }
    candidate = mapping.get(profile, "tap")
    if candidate in registry.get("multi_turn", {}):
        return candidate
    # Fallback to first available multi-turn op
    mt = registry.get("multi_turn", {})
    return next(iter(mt.keys()), None)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--goal-type", default="content")
    ap.add_argument("--profile", default="medium_defense")
    ap.add_argument("--top-n", type=int, default=6)
    args = ap.parse_args()
    reg = load_registry(Path(args.registry))
    ops = select_operators(reg, args.goal_type, args.profile, top_n=args.top_n)
    print(json.dumps({"selected": ops}, ensure_ascii=False, indent=2))
