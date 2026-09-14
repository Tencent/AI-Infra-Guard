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

from forgebench.trajectory_judge import judge_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--model", default="hy4-preview-***")
    parser.add_argument("--judge-id", default=None)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    summary = judge_run(
        args.run_dir,
        args.model,
        judge_id=args.judge_id,
        max_workers=args.max_workers,
        retries=args.retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        resume=args.resume,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
