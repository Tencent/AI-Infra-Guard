#!/usr/bin/env python3
"""Run full_channel_mode indirect injection evaluation with naive attack.

Usage:
    python scripts/run_deepseek_eval.py                    # full run (1120 cases)
    python scripts/run_deepseek_eval.py --limit 10         # smoke test (first 10 cases)
    python scripts/run_deepseek_eval.py --limit 5 --verbose  # verbose smoke test
    python scripts/run_deepseek_eval.py --resume           # resume from checkpoint

Output:
    result/
      results.jsonl    -- one structured result per line (full trace + verdict)
      results.json     -- pretty-printed full results
      results.csv      -- flat CSV summary
      summary.json     -- aggregate success rates by channel x mode
      run_meta.json    -- run metadata (model, timestamp, case count)

Environment variables:
    PIKIT_TARGET    Target spec (default: mock)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pikit.datasets import load_dataset
from pikit.matrix import MatrixRunner, save_json, save_csv, save_jsonl
from pikit.judges import LLMJudge
from pikit.targets import get_target

RESULT_DIR = Path(__file__).resolve().parent.parent / "result"
TARGET_SPEC = os.environ.get("PIKIT_TARGET", "mock")


def _incremental_save(results: list) -> None:
    """Incrementally save results to jsonl + csv so progress survives crashes."""
    jsonl_path = RESULT_DIR / "results.jsonl"
    csv_path = RESULT_DIR / "results.csv"
    try:
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in results:
                obj = r.to_dict() if hasattr(r, "to_dict") else r
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        import csv as csv_mod
        fieldnames = [
            "case_id", "attack", "defense", "channel", "agent", "target",
            "task", "success", "confidence", "reason", "timestamp",
            "sink_fired", "final_text", "outcome", "signals",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv_mod.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                obj = r.to_dict() if hasattr(r, "to_dict") else r
                row = {k: obj.get(k, "") for k in fieldnames}
                row["signals"] = ";".join(row.get("signals", []) or [])
                writer.writerow(row)
    except Exception as exc:
        print(f"  (incremental save error: {exc})", file=sys.stderr, flush=True)


def _load_checkpoint() -> tuple[list, int]:
    """Load previously saved results for crash recovery.

    Returns (loaded_results, next_case_index).
    """
    jsonl_path = RESULT_DIR / "results.jsonl"
    if not jsonl_path.exists():
        return [], 0
    results = []
    max_idx = 0
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                results.append(obj)
                cid = obj.get("case_id", "")
                if cid.startswith("fcm-"):
                    try:
                        num = int(cid[4:])
                        max_idx = max(max_idx, num)
                    except ValueError:
                        pass
    except (json.JSONDecodeError, IOError):
        return [], 0
    return results, max_idx


def run_eval(limit: int | None = None, verbose: bool = False, resume: bool = False) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("full_channel_mode")
    total = len(ds.cases)
    if limit and limit > 0:
        ds.cases = ds.cases[:limit]
        total = len(ds.cases)
    print(f"Dataset: {ds.name} -- {total} cases", file=sys.stderr, flush=True)

    all_results = []
    start_idx = 0
    if resume:
        loaded, last_done = _load_checkpoint()
        if loaded:
            all_results = loaded
            start_idx = last_done
            print(f"Resuming from checkpoint: {len(loaded)} results loaded, "
                  f"starting at case #{start_idx + 1}", file=sys.stderr, flush=True)

    agent_target = get_target(TARGET_SPEC)
    judge_target = get_target(TARGET_SPEC)
    print(f"Agent target: {agent_target.name}", file=sys.stderr, flush=True)
    print(f"Judge target: {judge_target.name} (LLMJudge)", file=sys.stderr, flush=True)

    start_time = time.time()
    error_count = 0

    for idx, case in enumerate(ds.cases, 1):
        if idx <= start_idx:
            continue
        i = idx
        cfg = case.config
        cfg.target_spec = TARGET_SPEC
        cfg.attacks = ["naive"]
        cfg.judge_type = "llm"

        if verbose:
            print(f"\n[{i}/{total}] {case.id}: {case.description}", file=sys.stderr, flush=True)
        elif i % 50 == 0 or i == 1:
            elapsed = time.time() - start_time
            done = i - start_idx
            rate = done / elapsed if elapsed > 0 else 0
            remaining_cases = total - i
            eta = remaining_cases / rate if rate > 0 else 0
            print(
                f"  [{i}/{total}] -- "
                f"{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining, "
                f"errors: {error_count}",
                file=sys.stderr, flush=True,
            )

        try:
            runner = MatrixRunner(cfg, verbose=False)
            results = runner.run()
            for r in results:
                r.case_id = case.id
                r.metadata["case_description"] = case.description
            all_results.extend(results)
        except (Exception, SystemExit) as exc:
            error_count += 1
            print(f"  Error on {case.id}: {exc}", file=sys.stderr, flush=True)
            from pikit.matrix import ExperimentResult
            from pikit.outcomes import Outcome
            all_results.append(ExperimentResult(
                attack="naive",
                defense="none",
                channel=cfg.channels[0] if cfg.channels else "",
                agent=cfg.agents[0] if cfg.agents else "",
                target=TARGET_SPEC,
                task=cfg.task,
                success=False,
                confidence="n/a",
                reason=f"error: {exc}",
                timestamp=datetime.now().isoformat(),
                case_id=case.id,
                outcome=Outcome.RUNTIME_ERROR,
                metadata={"case_description": case.description, "error": str(exc)},
            ))

        if i % 10 == 0 or i == total:
            _incremental_save(all_results)

    elapsed = time.time() - start_time
    print(f"\nCompleted {total} cases in {elapsed:.1f}s", file=sys.stderr)

    jsonl_path = RESULT_DIR / "results.jsonl"
    json_path = RESULT_DIR / "results.json"
    csv_path = RESULT_DIR / "results.csv"

    _incremental_save(all_results)

    json_data = [r.to_dict() if hasattr(r, "to_dict") else r for r in all_results]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"Saved: {jsonl_path.name}, {json_path.name}, {csv_path.name}", file=sys.stderr, flush=True)

    summary = build_summary(all_results)
    summary_path = RESULT_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved: {summary_path.name}", file=sys.stderr)

    meta = {
        "dataset": "full_channel_mode",
        "target": TARGET_SPEC,
        "judge": f"llm ({TARGET_SPEC})",
        "attack": "naive (direct task injection)",
        "total_cases": total,
        "total_results": len(all_results),
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now().isoformat(),
        "result_files": [
            "results.jsonl", "results.json", "results.csv",
            "summary.json", "run_meta.json",
        ],
    }
    meta_path = RESULT_DIR / "run_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Saved: {meta_path.name}", file=sys.stderr)

    print_summary(summary)


def build_summary(results: list) -> dict:
    """Aggregate success rates by channel x mode."""
    from collections import defaultdict

    stats = defaultdict(lambda: {"total": 0, "success": 0})
    overall = {"total": 0, "success": 0}

    for r in results:
        obj = r.to_dict() if hasattr(r, "to_dict") else r
        signals = obj.get("signals") or []
        if "repeat_summary" in signals:
            continue
        desc = obj.get("metadata", {}).get("case_description", "") if isinstance(obj.get("metadata"), dict) else ""
        parts = desc.split("x")
        channel = parts[0].strip() if parts else obj.get("channel", "unknown")
        mode = parts[1].strip().split()[0] if len(parts) > 1 else "unknown"

        bucket = f"{channel}/{mode}"
        stats[bucket]["total"] += 1
        stats[bucket]["success"] += 1 if obj.get("success") else 0
        overall["total"] += 1
        overall["success"] += 1 if obj.get("success") else 0

    breakdown = {}
    for bucket in sorted(stats.keys()):
        s = stats[bucket]
        rate = (s["success"] / s["total"] * 100) if s["total"] > 0 else 0
        breakdown[bucket] = {
            "total": s["total"],
            "success": s["success"],
            "success_rate": round(rate, 1),
        }

    overall_rate = (overall["success"] / overall["total"] * 100) if overall["total"] > 0 else 0

    return {
        "overall": {
            "total": overall["total"],
            "success": overall["success"],
            "success_rate": round(overall_rate, 1),
        },
        "by_channel_mode": breakdown,
    }


def print_summary(summary: dict) -> None:
    ov = summary["overall"]
    print("\n" + "=" * 70)
    print("INDIRECT INJECTION EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Overall: {ov['success']}/{ov['total']} succeeded "
          f"({ov['success_rate']}%)")
    print()
    print(f"{'Channel/Mode':<35} {'Success':>8} {'Total':>8} {'Rate':>8}")
    print("-" * 65)
    for bucket, stats in summary["by_channel_mode"].items():
        print(f"{bucket:<35} {stats['success']:>8} {stats['total']:>8} "
              f"{stats['success_rate']:>7.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run full_channel_mode indirect injection evaluation."
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit to first N cases (for smoke testing).",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print each case as it runs.",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from checkpoint (results.jsonl) if previous run was interrupted.",
    )
    args = parser.parse_args()
    run_eval(limit=args.limit, verbose=args.verbose, resume=args.resume)
