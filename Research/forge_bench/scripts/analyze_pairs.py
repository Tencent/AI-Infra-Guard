#!/usr/bin/env python3
from __future__ import print_function

import argparse
import glob
import json
import os


def load_scores(run_dir):
    rows = []
    pattern = os.path.join(run_dir, "cases", "*", "sample_*", "score.json")
    for path in sorted(glob.glob(pattern)):
        with open(path, "r", encoding="utf-8") as handle:
            rows.append(json.load(handle))
    return rows


def key_without_degradation(row):
    factors = row["factors"]
    return (
        row["episode_id"],
        factors["goal_pressure"],
        factors["unsafe_opportunity"],
        row.get("sample_index", 1),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    args = parser.parse_args()
    rows = load_scores(args.run_dir)
    groups = {}
    for row in rows:
        groups.setdefault(key_without_degradation(row), {})[
            row["factors"]["control_degradation"]
        ] = row
    pairs = []
    for key, conditions in sorted(groups.items()):
        if 0 not in conditions or 1 not in conditions:
            continue
        intact = conditions[0]
        degraded = conditions[1]
        pairs.append({
            "episode_id": key[0],
            "goal_pressure": key[1],
            "unsafe_opportunity": key[2],
            "sample_index": key[3],
            "intact_mloc": intact["material_loss_of_control"],
            "degraded_mloc": degraded["material_loss_of_control"],
            "degradation_effect": (
                int(degraded["material_loss_of_control"])
                - int(intact["material_loss_of_control"])
            ),
            "intact_tools": intact["selected_tools"],
            "degraded_tools": degraded["selected_tools"],
            "intact_safe_terminal": intact["safe_terminal"],
            "degraded_safe_terminal": degraded["safe_terminal"],
        })
    output = {
        "run_dir": os.path.abspath(args.run_dir),
        "pair_count": len(pairs),
        "positive_degradation_effect_count": sum(
            1 for pair in pairs if pair["degradation_effect"] > 0
        ),
        "negative_degradation_effect_count": sum(
            1 for pair in pairs if pair["degradation_effect"] < 0
        ),
        "zero_degradation_effect_count": sum(
            1 for pair in pairs if pair["degradation_effect"] == 0
        ),
        "pairs": pairs,
    }
    path = os.path.join(args.run_dir, "paired_analysis.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
