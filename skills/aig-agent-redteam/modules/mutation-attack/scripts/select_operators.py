"""Operator selector: pick top N operators based on operators/*.md frontmatter.

Frontmatter schema (see any file in modules/mutation-attack/operators/*.md):
  name, description, kind, family, applies_to, combo_with, conflicts_with,
  default_priority, canary_only, updated

This replaces the old JSON-registry-based selector: metadata now lives next
to each operator's template/brief in a single file instead of two files that
had to be kept in sync by hand.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
MULTI_TURN_FAMILIES = {"multi_turn"}
SIDE_CHANNEL_FAMILIES = {"side_channel"}


def _parse_scalar(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []
    if raw in ("true", "false"):
        return raw == "true"
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    try:
        return int(raw)
    except ValueError:
        return raw


def _parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm_text = m.group(1)
    out: dict = {}
    lines = fm_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line.startswith("  ") or ":" not in line:
            i += 1
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "|":
            # multi-line block scalar (description); skip indented body
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i] == ""):
                i += 1
            continue
        out[key] = _parse_scalar(rest)
        i += 1
    return out


def load_registry(operators_dir: Path) -> dict:
    """Scan operators/*.md and build a registry dict grouped by section,
    matching the shape the old operator_registry.json used:
    {"single_turn": {id: meta}, "multi_turn": {...}, "side_channel": {...}}
    """
    registry: dict = {"single_turn": {}, "multi_turn": {}, "side_channel": {}}
    if not operators_dir.exists():
        return registry
    for md in sorted(operators_dir.glob("*.md")):
        if md.stem.startswith("_"):
            continue
        fm = _parse_frontmatter(md.read_text(encoding="utf-8"))
        if not fm:
            continue
        family = fm.get("family", "misc")
        meta = {
            "family": family,
            "kind": fm.get("kind", "program"),
            "applies_to": fm.get("applies_to", ["all"]),
            "combo_with": fm.get("combo_with", []),
            "conflicts_with": fm.get("conflicts_with", []),
            "default_priority": fm.get("default_priority", 50),
            "canary_only": fm.get("canary_only", False),
        }
        if family in MULTI_TURN_FAMILIES or fm.get("kind") == "multi_turn":
            registry["multi_turn"][md.stem] = meta
        elif family in SIDE_CHANNEL_FAMILIES:
            registry["side_channel"][md.stem] = meta
        else:
            registry["single_turn"][md.stem] = meta
    return registry


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
        conflicts = info.get("conflicts_with", [])
        if any(c in used for c in conflicts):
            continue
        applies = info.get("applies_to", [])
        if goal_type not in applies and "all" not in applies:
            continue

        score = info.get("default_priority", 50)

        if profile == "weak_defense" and info["family"] in ("baseline", "roleplay"):
            score += 30
        if profile == "high_defense" and info["family"] in ("ssrt", "semantic"):
            score += 30
        if profile == "filter_bypass" and info["family"] in ("encoding", "stego"):
            score += 30

        for u in used:
            if u in info.get("combo_with", []):
                score += 25

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
    mt = registry.get("multi_turn", {})
    return next(iter(mt.keys()), None)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--operators-dir",
        default=str(Path(__file__).resolve().parent.parent / "operators"),
        help="path to modules/mutation-attack/operators/",
    )
    ap.add_argument("--goal-type", default="content")
    ap.add_argument("--profile", default="medium_defense")
    ap.add_argument("--top-n", type=int, default=6)
    args = ap.parse_args()
    reg = load_registry(Path(args.operators_dir))
    ops = select_operators(reg, args.goal_type, args.profile, top_n=args.top_n)
    print(json.dumps({"selected": ops}, ensure_ascii=False, indent=2))
