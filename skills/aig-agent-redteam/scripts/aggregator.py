#!/usr/bin/env python3
"""Phase 4: Aggregator.

Collects all module_findings.json under reports/<run_id>/ and produces:
- aggregated_findings.json (raw merged)
- summary.json (severity counts, module breakdown)

Final report.md is composed by the host agent following SKILL.md Rule 5 (报告生成与内容规范);
this script just prepares the structured input.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def collect_findings(run_dir: Path) -> dict:
    aggregated = {
        "schema": "aig-agent-redteam.aggregated.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "modules": {},
        "all_findings": [],
        "stats": {},
    }

    severity_counter = Counter()
    module_counter = Counter()
    total_duration = 0.0
    total_ops = 0

    for findings_file in sorted(run_dir.glob("*_findings.json")):
        try:
            data = json.loads(findings_file.read_text())
        except Exception as e:
            print(f"warning: cannot parse {findings_file}: {e}", file=sys.stderr)
            continue

        module_name = data.get("module") or findings_file.stem.replace("_findings", "")
        aggregated["modules"][module_name] = {
            "target": data.get("target"),
            "started_at": data.get("started_at"),
            "ended_at": data.get("ended_at"),
            "stats": data.get("stats", {}),
            "finding_count": len(data.get("findings", [])),
        }
        for f in data.get("findings", []):
            f = dict(f)
            f["__module"] = module_name
            aggregated["all_findings"].append(f)
            severity_counter[f.get("severity", "info").lower()] += 1
            module_counter[module_name] += 1

        stats = data.get("stats", {})
        total_duration += stats.get("duration_sec", 0)
        total_ops += stats.get("operators_run", 0)

    # Sort findings: critical first, then by module
    aggregated["all_findings"].sort(key=lambda x: (
        SEVERITY_ORDER.index(x.get("severity", "info").lower())
        if x.get("severity", "info").lower() in SEVERITY_ORDER else 99,
        x.get("__module", ""),
    ))

    aggregated["stats"] = {
        "total_findings": sum(severity_counter.values()),
        "by_severity": dict(severity_counter),
        "by_module": dict(module_counter),
        "total_duration_sec": round(total_duration, 1),
        "total_operators_run": total_ops,
    }

    return aggregated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="reports/<run_id>/")
    ap.add_argument("--out", help="aggregated.json path; default: <run-dir>/aggregated.json")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.exists():
        print(f"error: run dir not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    out = Path(args.out) if args.out else run_dir / "aggregated.json"
    aggregated = collect_findings(run_dir)
    out.write_text(json.dumps(aggregated, indent=2, ensure_ascii=False))
    print(json.dumps(aggregated["stats"], indent=2, ensure_ascii=False))
    print(f"\n→ aggregated written to {out}")


if __name__ == "__main__":
    main()
