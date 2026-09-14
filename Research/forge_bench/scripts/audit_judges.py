#!/usr/bin/env python3
from __future__ import print_function

import argparse
import glob
import json
import os


def select_judge(sample_dir, primary_id):
    primary = os.path.join(sample_dir, "judges", primary_id, "parsed_response.json")
    if os.path.isfile(primary):
        return primary_id, primary
    candidates = sorted(
        glob.glob(
            os.path.join(
                sample_dir,
                "judges",
                primary_id + "_retry_*",
                "parsed_response.json",
            )
        )
        + glob.glob(
            os.path.join(
                sample_dir,
                "judges",
                "hy4_blind_retry_v*",
                "parsed_response.json",
            )
        )
    )
    if candidates:
        path = candidates[-1]
        return path.split(os.sep)[-2], path
    return None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--primary-id", default="hy4_blind_full_v1")
    parser.add_argument("run_specs", nargs="+", help="RUN_DIR or RUN_DIR::JUDGE_ID")
    args = parser.parse_args()
    rows = []
    missing = []
    for spec in args.run_specs:
        if "::" in spec:
            run_dir, primary_id = spec.split("::", 1)
        else:
            run_dir, primary_id = spec, args.primary_id
        pattern = os.path.join(run_dir, "cases", "*", "sample_*", "score.json")
        for score_path in sorted(glob.glob(pattern)):
            sample_dir = os.path.dirname(score_path)
            score = json.load(open(score_path, encoding="utf-8"))
            judge_id, judge_path = select_judge(sample_dir, primary_id)
            if not judge_path:
                missing.append(sample_dir)
                continue
            judge = json.load(open(judge_path, encoding="utf-8"))
            rows.append({
                "sample_dir": os.path.abspath(sample_dir),
                "case_id": score["case_id"],
                "sample_index": score["sample_index"],
                "judge_id": judge_id,
                "deterministic_mloc": score["material_loss_of_control"],
                "judge_mloc": judge["material_loss_of_control"],
                "mloc_agreement": (
                    score["material_loss_of_control"]
                    == judge["material_loss_of_control"]
                ),
                "deterministic_control_failure": score["control_failure"],
                "judge_control_failure": judge["control_failure"],
                "control_failure_agreement": (
                    score["control_failure"] == judge["control_failure"]
                ),
                "judge_risk_types": judge.get("risk_types") or [],
                "judge_intentionality": judge.get("intentionality"),
            })
    n = len(rows)
    output = {
        "n_scored": n + len(missing),
        "n_judged": n,
        "missing_judges": missing,
        "mloc_agreement_count": sum(row["mloc_agreement"] for row in rows),
        "mloc_agreement_rate": (
            sum(row["mloc_agreement"] for row in rows) / float(n) if n else None
        ),
        "control_failure_agreement_count": sum(
            row["control_failure_agreement"] for row in rows
        ),
        "control_failure_agreement_rate": (
            sum(row["control_failure_agreement"] for row in rows) / float(n)
            if n else None
        ),
        "mloc_disagreements": [
            row for row in rows if not row["mloc_agreement"]
        ],
        "control_failure_disagreements": [
            row for row in rows if not row["control_failure_agreement"]
        ],
        "rows": rows,
    }
    parent = os.path.dirname(os.path.abspath(args.output))
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({
        "n_scored": output["n_scored"],
        "n_judged": output["n_judged"],
        "missing_judges": len(missing),
        "mloc_agreement_rate": output["mloc_agreement_rate"],
        "control_failure_agreement_rate": output["control_failure_agreement_rate"],
        "mloc_disagreements": len(output["mloc_disagreements"]),
        "control_failure_disagreements": len(
            output["control_failure_disagreements"]
        ),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
