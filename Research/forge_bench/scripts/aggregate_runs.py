#!/usr/bin/env python3
from __future__ import print_function

import argparse
import glob
import json
import os


def load_scores(run_dirs):
    rows = []
    for run_dir in run_dirs:
        pattern = os.path.join(run_dir, "cases", "*", "sample_*", "score.json")
        for path in sorted(glob.glob(pattern)):
            with open(path, "r", encoding="utf-8") as handle:
                row = json.load(handle)
            row["_run_id"] = os.path.basename(run_dir.rstrip("/"))
            row["_score_path"] = os.path.abspath(path)
            rows.append(row)
    return rows


def rate(rows, key):
    values = [bool(row[key]) for row in rows if row.get(key) is not None]
    count = sum(1 for value in values if value)
    return {
        "n": len(values),
        "count": count,
        "rate": count / float(len(values)) if values else None,
    }


def judge_summary(run_dir, judge_id):
    path = os.path.join(run_dir, "judges", judge_id, "summary.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--judge-id", default="hy4_blind_v1")
    parser.add_argument("run_dirs", nargs="+")
    args = parser.parse_args()
    run_dirs = [os.path.abspath(path) for path in args.run_dirs]
    rows = load_scores(run_dirs)
    by_control = {}
    for degradation in [0, 1]:
        group = [
            row for row in rows
            if row["factors"]["control_degradation"] == degradation
        ]
        by_control[str(degradation)] = {
            "n": len(group),
            "material_loss_of_control": rate(group, "material_loss_of_control"),
            "safe_terminal": rate(group, "safe_terminal"),
        }
    by_episode = {}
    for episode_id in sorted(set(row["episode_id"] for row in rows)):
        episode_rows = [row for row in rows if row["episode_id"] == episode_id]
        entry = {"n": len(episode_rows), "conditions": {}}
        for degradation in [0, 1]:
            group = [
                row for row in episode_rows
                if row["factors"]["control_degradation"] == degradation
            ]
            entry["conditions"][str(degradation)] = {
                "n": len(group),
                "material_loss_of_control": rate(
                    group, "material_loss_of_control"
                ),
                "safe_terminal": rate(group, "safe_terminal"),
                "selected_tools": [row["selected_tools"] for row in group],
                "violation_types": [row["violation_types"] for row in group],
            }
        by_episode[episode_id] = entry
    judge_summaries = [
        judge_summary(run_dir, args.judge_id) for run_dir in run_dirs
    ]
    judge_summaries = [item for item in judge_summaries if item is not None]
    judged = sum(item["n_judged"] for item in judge_summaries)
    mloc_agree_count = sum(
        item["material_loss_of_control_agreement_rate"] * item["n_judged"]
        for item in judge_summaries
    )
    control_agree_count = sum(
        item["control_failure_agreement_rate"] * item["n_judged"]
        for item in judge_summaries
    )
    output = {
        "run_dirs": run_dirs,
        "trajectory_count": len(rows),
        "overall": {
            "material_loss_of_control": rate(rows, "material_loss_of_control"),
            "control_failure": rate(rows, "control_failure"),
            "safe_terminal": rate(rows, "safe_terminal"),
            "report_state_divergence": rate(rows, "report_state_divergence"),
        },
        "by_control_degradation": by_control,
        "by_episode": by_episode,
        "judge": {
            "judge_id": args.judge_id,
            "n_judged": judged,
            "material_loss_of_control_agreement_rate": (
                mloc_agree_count / float(judged) if judged else None
            ),
            "control_failure_agreement_rate": (
                control_agree_count / float(judged) if judged else None
            ),
        },
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
