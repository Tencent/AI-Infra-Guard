#!/usr/bin/env python3
from __future__ import print_function

import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    args = parser.parse_args()
    path = os.path.join(args.run_dir, "summary.json")
    with open(path, "r", encoding="utf-8") as handle:
        summary = json.load(handle)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
