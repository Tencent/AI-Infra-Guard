#!/usr/bin/env python3
from __future__ import print_function

import argparse
import os
import shutil
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from forgebench.io_utils import ensure_dir, hash_manifest, utc_now, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument(
        "--config",
        default=os.path.join(ROOT, "configs", "v0.2_expanded_dev.json"),
    )
    parser.add_argument(
        "--canonical",
        default=os.path.join(ROOT, "scenarios", "v0.2", "canonical_episodes.json"),
    )
    parser.add_argument(
        "--cases",
        default=os.path.join(ROOT, "scenarios", "v0.2", "generated_cases.jsonl"),
    )
    args = parser.parse_args()
    destination = os.path.join(ROOT, "artifacts", "dataset_snapshots", args.snapshot_id)
    if os.path.exists(destination):
        raise RuntimeError("snapshot already exists: %s" % destination)
    ensure_dir(destination)
    for source in [args.config, args.canonical, args.cases]:
        shutil.copy2(source, os.path.join(destination, os.path.basename(source)))
    write_json(os.path.join(destination, "snapshot_manifest.json"), {
        "snapshot_id": args.snapshot_id,
        "created_at": utc_now(),
        "source_files": [
            os.path.abspath(args.config),
            os.path.abspath(args.canonical),
            os.path.abspath(args.cases),
        ],
    })
    write_json(os.path.join(destination, "checksums.json"), {
        "created_at": utc_now(),
        "files": hash_manifest(destination),
    })
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
