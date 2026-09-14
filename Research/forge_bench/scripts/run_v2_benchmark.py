#!/usr/bin/env python3
from __future__ import print_function

import argparse
import json
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
WORKSPACE = os.path.abspath(os.path.join(ROOT, ".."))
for path in [SRC, WORKSPACE]:
    if path not in sys.path:
        sys.path.insert(0, path)

from forgebench.v2_runner import run_v2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--cases",
        default=os.path.join(ROOT, "scenarios", "v0.2", "generated_cases.jsonl"),
    )
    parser.add_argument(
        "--artifacts-root",
        default=os.path.join(ROOT, "artifacts", "runs"),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    run_dir, summary = run_v2(
        config_path=args.config,
        cases_path=args.cases,
        artifacts_root=args.artifacts_root,
        dry_run=args.dry_run,
        run_id=args.run_id,
    )
    print(run_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
