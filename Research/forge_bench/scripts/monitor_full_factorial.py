#!/usr/bin/env python3
from __future__ import print_function

import glob
import json
import os


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUN_ROOT = os.path.join(ROOT, "artifacts", "runs")
PREFIX = "forge_v022_full_"


def count_events(path):
    completed = 0
    errors = 0
    if not os.path.isfile(path):
        return completed, errors
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line).get("event")
            except Exception:
                continue
            if event == "sample_completed":
                completed += 1
            elif event == "sample_error":
                errors += 1
    return completed, errors


def main():
    total_completed = 0
    total_errors = 0
    rows = []
    for run_dir in sorted(glob.glob(os.path.join(RUN_ROOT, PREFIX + "*_20260904"))):
        completed, errors = count_events(os.path.join(run_dir, "events.jsonl"))
        manifest_path = os.path.join(run_dir, "manifest.json")
        status = "not_started"
        expected = 40
        if os.path.isfile(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
            status = manifest.get("status")
            expected = int(manifest.get("expected_samples") or 0)
            if not expected:
                expected = len(manifest.get("selected_case_ids") or []) * int(
                    manifest.get("samples_per_case") or 5
                )
        rows.append({
            "run_id": os.path.basename(run_dir),
            "status": status,
            "completed": completed,
            "errors": errors,
            "expected": expected,
        })
        total_completed += completed
        total_errors += errors
    output = {
        "runs": rows,
        "total_completed": total_completed,
        "total_errors": total_errors,
        "total_expected": 240,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
