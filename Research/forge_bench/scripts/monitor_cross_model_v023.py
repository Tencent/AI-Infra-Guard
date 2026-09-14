#!/usr/bin/env python3
from __future__ import print_function

import argparse
import glob
import json
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stamp", default="20260907")
    args = parser.parse_args()
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    pattern = os.path.join(
        root, "artifacts", "runs", "forge_v023_cross_*_" + args.stamp
    )
    rows = []
    for run_dir in sorted(glob.glob(pattern)):
        scores = glob.glob(
            os.path.join(run_dir, "cases", "*", "sample_*", "score.json")
        )
        errors = glob.glob(
            os.path.join(run_dir, "cases", "*", "sample_*", "error.json")
        )
        manifest_path = os.path.join(run_dir, "manifest.json")
        status = "missing"
        model = None
        if os.path.isfile(manifest_path):
            manifest = json.load(open(manifest_path, encoding="utf-8"))
            status = manifest.get("status")
            model = manifest.get("model")
        rows.append({
            "run_id": os.path.basename(run_dir),
            "model": model,
            "scored": len(scores),
            "errors": len(errors),
            "status": status,
        })
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
