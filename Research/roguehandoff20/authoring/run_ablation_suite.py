#!/usr/bin/env python3
"""Run the complete 2^3 O/R/A RogueHandoff ablation suite."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
CELLS = tuple(f"{value:03b}" for value in range(8))


def _route(value: str) -> tuple[str, str]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("route must be PROVIDER:MODEL")
    provider, model = value.split(":", 1)
    if not provider or not model:
        raise argparse.ArgumentTypeError("route must be PROVIDER:MODEL")
    return provider, model


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=PROJECT / "pi-fixtures")
    parser.add_argument(
        "--route", action="append", type=_route, required=True,
        metavar="PROVIDER:MODEL",
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--cases", nargs="+", type=int, choices=range(1, 21))
    parser.add_argument("--cells", nargs="+", choices=CELLS, default=list(CELLS))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.repetitions < 1 or args.jobs < 1 or args.timeout < 1:
        raise SystemExit("repetitions, jobs, and timeout must be positive")

    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "ablation-manifest.json"
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "design": {
            "bits": "Observations/Reasoning/pending Action",
            "attack_request_retained": True,
            "runtime_prompt": "Continue.",
            "cells": list(args.cells),
            "cases": args.cases or list(range(1, 21)),
            "repetitions": args.repetitions,
        },
        "fixtures": str(args.fixtures.resolve()),
        "jobs": args.jobs,
        "timeout_seconds": args.timeout,
        "routes": [
            {"provider": provider, "model": model}
            for provider, model in args.route
        ],
        "runs": {},
    }
    if manifest_path.is_file() and args.resume:
        previous = json.loads(manifest_path.read_text())
        manifest["created_at"] = previous.get("created_at", manifest["created_at"])
        manifest["runs"] = previous.get("runs", {})
    _write_json(manifest_path, manifest)

    failures = 0
    for provider, model in args.route:
        route_key = f"{_slug(provider)}--{_slug(model)}"
        for cell in args.cells:
            cell_name = f"o{cell[0]}-r{cell[1]}-a{cell[2]}"
            run_key = f"{route_key}/{cell_name}"
            run_dir = args.output / route_key / cell_name
            run_dir.mkdir(parents=True, exist_ok=True)
            command = [
                sys.executable, "-m", "roguehandoff.cli", "pi-matrix",
                "--fixtures", str(args.fixtures),
                "--provider", provider,
                "--model", model,
                "--conditions", "attack_handoff",
                "--handoff-ablation", cell,
                "--repetitions", str(args.repetitions),
                "--jobs", str(args.jobs),
                "--timeout", str(args.timeout),
                "--output", str(run_dir),
            ]
            if args.cases:
                command.extend(["--cases", *(str(case) for case in args.cases)])
            if args.resume:
                command.append("--resume")
            print(f"[{run_key}] {' '.join(command)}", flush=True)
            manifest["runs"][run_key] = {
                "status": "dry_run" if args.dry_run else "running",
                "directory": str(run_dir.resolve()),
                "provider": provider,
                "model": model,
                "bits": cell,
            }
            _write_json(manifest_path, manifest)
            if args.dry_run:
                continue
            with (run_dir / "runner.stdout.log").open("a") as stdout_log, (
                run_dir / "runner.stderr.log"
            ).open("a") as stderr_log:
                completed = subprocess.run(
                    command,
                    cwd=PROJECT,
                    stdout=stdout_log,
                    stderr=stderr_log,
                    check=False,
                )
            manifest["runs"][run_key]["returncode"] = completed.returncode
            manifest["runs"][run_key]["status"] = (
                "complete" if completed.returncode == 0 else "failed"
            )
            _write_json(manifest_path, manifest)
            if completed.returncode:
                failures += 1
                if not args.keep_going:
                    raise SystemExit(completed.returncode)
    if failures:
        raise SystemExit(f"{failures} ablation cells failed")


if __name__ == "__main__":
    main()
