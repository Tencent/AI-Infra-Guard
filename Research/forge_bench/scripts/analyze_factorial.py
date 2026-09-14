#!/usr/bin/env python3
from __future__ import print_function

import argparse
import glob
import json
import math
import os


def load_scores(run_dirs):
    rows = []
    for run_dir in run_dirs:
        pattern = os.path.join(run_dir, "cases", "*", "sample_*", "score.json")
        for path in sorted(glob.glob(pattern)):
            with open(path, "r", encoding="utf-8") as handle:
                row = json.load(handle)
            row["_run_id"] = os.path.basename(run_dir.rstrip("/"))
            rows.append(row)
    return rows


def wilson(count, n, z=1.959963984540054):
    if not n:
        return [None, None]
    p = count / float(n)
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def summarize(rows):
    n = len(rows)
    count = sum(1 for row in rows if row["material_loss_of_control"])
    return {
        "n": n,
        "count": count,
        "rate": count / float(n) if n else None,
        "wilson_95": wilson(count, n),
    }


def cell_key(row):
    f = row["factors"]
    return "%d%d%d" % (
        f["goal_pressure"],
        f["control_degradation"],
        f["unsafe_opportunity"],
    )


def risk_difference(a, b):
    if a["rate"] is None or b["rate"] is None:
        return None
    return a["rate"] - b["rate"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("run_dirs", nargs="+")
    args = parser.parse_args()
    rows = load_scores(args.run_dirs)
    cells = {}
    for key in ["000", "001", "010", "011", "100", "101", "110", "111"]:
        cells[key] = summarize([row for row in rows if cell_key(row) == key])
    main_effects = {}
    factor_names = [
        "goal_pressure", "control_degradation", "unsafe_opportunity"
    ]
    for factor in factor_names:
        high = summarize([row for row in rows if row["factors"][factor] == 1])
        low = summarize([row for row in rows if row["factors"][factor] == 0])
        main_effects[factor] = {
            "low": low,
            "high": high,
            "risk_difference": risk_difference(high, low),
        }
    # Difference-in-differences, averaged over the third factor.
    interactions = {}
    pairs = [
        ("goal_pressure", "control_degradation"),
        ("goal_pressure", "unsafe_opportunity"),
        ("control_degradation", "unsafe_opportunity"),
    ]
    for a, b in pairs:
        rates = {}
        for av in [0, 1]:
            for bv in [0, 1]:
                group = [
                    row for row in rows
                    if row["factors"][a] == av and row["factors"][b] == bv
                ]
                rates["%d%d" % (av, bv)] = summarize(group)
        did = (
            rates["11"]["rate"] - rates["10"]["rate"]
            - rates["01"]["rate"] + rates["00"]["rate"]
        )
        interactions[a + "_x_" + b] = {
            "cells": rates,
            "difference_in_differences": did,
        }
    by_episode = {}
    for episode in sorted(set(row["episode_id"] for row in rows)):
        episode_rows = [row for row in rows if row["episode_id"] == episode]
        episode_cells = {}
        for key in cells:
            episode_cells[key] = summarize(
                [row for row in episode_rows if cell_key(row) == key]
            )
        by_episode[episode] = {
            "overall": summarize(episode_rows),
            "cells": episode_cells,
        }
    output = {
        "trajectory_count": len(rows),
        "overall": summarize(rows),
        "factor_order": "goal_pressure, control_degradation, unsafe_opportunity",
        "cells": cells,
        "main_effects": main_effects,
        "two_way_interactions": interactions,
        "by_episode": by_episode,
        "run_dirs": [os.path.abspath(path) for path in args.run_dirs],
    }
    parent = os.path.dirname(os.path.abspath(args.output))
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
