#!/usr/bin/env python3
from __future__ import print_function

import argparse
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from forgebench.io_utils import read_json, write_json
from forgebench.scenarios import build_cases, save_jsonl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canonical",
        default=os.path.join(ROOT, "scenarios", "canonical_families.json"),
    )
    parser.add_argument(
        "--output",
        default=os.path.join(ROOT, "scenarios", "generated_cases.jsonl"),
    )
    args = parser.parse_args()
    payload = read_json(args.canonical)
    cases = build_cases(payload)
    save_jsonl(args.output, cases)
    index = {
        "schema_version": payload.get("schema_version"),
        "family_count": len(payload.get("families") or []),
        "case_count": len(cases),
        "case_ids": [case["case_id"] for case in cases],
    }
    write_json(os.path.join(os.path.dirname(args.output), "generated_index.json"), index)
    print("built %d cases from %d families -> %s" % (
        len(cases), index["family_count"], args.output
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
