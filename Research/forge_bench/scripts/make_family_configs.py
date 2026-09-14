#!/usr/bin/env python3
from __future__ import print_function

import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--master", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    with open(args.master, "r", encoding="utf-8") as handle:
        master = json.load(handle)
    family_cases = {}
    with open(args.cases, "r", encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            family_cases.setdefault(case["episode_id"], []).append(case["case_id"])
    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)
    paths = []
    for episode_id, case_ids in sorted(family_cases.items()):
        config = json.loads(json.dumps(master))
        config["experiment_id"] = "%s_%s" % (
            master["experiment_id"], episode_id
        )
        config["case_filter"]["case_ids"] = sorted(case_ids)
        config["runner"]["max_cases"] = len(case_ids)
        path = os.path.join(args.output_dir, "%s.json" % episode_id)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        paths.append(path)
    print("\n".join(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
