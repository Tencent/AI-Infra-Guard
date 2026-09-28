#!/usr/bin/env python3
"""Parallel naive-attack test on full_channel_mode dataset.

Runs all 1120 cases with the naive attack method using 5 concurrent
threads. Reports overall and per-channel success rates.

Output: result/naive_full_test/

Environment variables:
    PIKIT_TARGET    Target spec (default: mock)
    PIKIT_AGENT     Agent key  (default: general_permissive)
    PIKIT_WORKERS   Concurrency (default: 5)
"""

from __future__ import annotations

import csv as csv_mod
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pikit.datasets import load_dataset
from pikit.matrix import MatrixRunner, ExperimentResult
from pikit.outcomes import Outcome
from pikit.targets import get_target

RESULT_DIR = Path(__file__).resolve().parent.parent / "result" / "naive_full_test"
TARGET_SPEC = os.environ.get("PIKIT_TARGET", "mock")
AGENT_KEY = os.environ.get("PIKIT_AGENT", "general_permissive")
ATTACK_KEY = "naive"
NUM_WORKERS = int(os.environ.get("PIKIT_WORKERS", "5"))


def _save_jsonl(results, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            obj = r.to_dict() if hasattr(r, "to_dict") else r
            f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def _save_csv(results, path):
    fieldnames = [
        "case_id", "attack", "defense", "channel", "agent", "target",
        "task", "success", "partial_success", "success_level",
        "confidence", "reason", "timestamp",
        "sink_fired", "final_text", "outcome", "signals",
        "case_description",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv_mod.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            obj = r.to_dict() if hasattr(r, "to_dict") else r
            row = {k: obj.get(k, "") for k in fieldnames}
            row["signals"] = ";".join(row.get("signals", []) or [])
            desc = obj.get("metadata", {}).get("case_description", "")
            row["case_description"] = desc if isinstance(desc, str) else str(desc)
            writer.writerow(row)


def _get_val(r, key, default=None):
    if hasattr(r, key):
        return getattr(r, key)
    if isinstance(r, dict):
        return r.get(key, default)
    return default


def run_one_case(case, attack_key):
    cfg = case.config
    cfg.target_spec = TARGET_SPEC
    cfg.agents = [AGENT_KEY]
    cfg.attacks = [attack_key]
    cfg.judge_type = "rule"

    try:
        runner = MatrixRunner(cfg, verbose=False)
        results = runner.run()
        for r in results:
            r.case_id = case.id
            r.metadata["case_description"] = case.description
            r.metadata["attack_method"] = attack_key
        return results
    except (Exception, SystemExit) as exc:
        err_result = ExperimentResult(
            attack=attack_key,
            defense="none",
            channel=cfg.channels[0] if cfg.channels else "",
            agent=AGENT_KEY,
            target=TARGET_SPEC,
            task=cfg.task,
            success=False,
            confidence="n/a",
            reason=f"error: {exc}",
            timestamp=datetime.now().isoformat(),
            case_id=case.id,
            outcome=Outcome.RUNTIME_ERROR,
            metadata={"case_description": case.description, "attack_method": attack_key, "error": str(exc)},
        )
        return [err_result]


def run_test():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("full_channel_mode")
    total_ds = len(ds.cases)
    cases = ds.cases
    n_cases = len(cases)

    agent_target = get_target(TARGET_SPEC)
    print(f"Dataset: {ds.name} - {total_ds} cases", file=sys.stderr, flush=True)
    print(f"Attack: {ATTACK_KEY} (raw payload, no wrapping)", file=sys.stderr, flush=True)
    print(f"Agent: {AGENT_KEY}", file=sys.stderr, flush=True)
    print(f"Target: {agent_target.name} ({TARGET_SPEC})", file=sys.stderr, flush=True)
    print(f"Workers: {NUM_WORKERS} concurrent threads", file=sys.stderr, flush=True)
    print(f"Total runs: {n_cases} cases x 1 attack = {n_cases}", file=sys.stderr, flush=True)
    print(f"{'='*60}", file=sys.stderr, flush=True)

    all_results = []
    start_time = time.time()
    error_count = 0
    completed = 0

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        future_to_case = {executor.submit(run_one_case, case, ATTACK_KEY): case for case in cases}

        for future in as_completed(future_to_case):
            completed += 1
            case = future_to_case[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as exc:
                error_count += 1
                print(f"  ERROR on {case.id}: {exc}", file=sys.stderr, flush=True)
                err_result = ExperimentResult(
                    attack=ATTACK_KEY,
                    defense="none",
                    channel="",
                    agent=AGENT_KEY,
                    target=TARGET_SPEC,
                    task="",
                    success=False,
                    confidence="n/a",
                    reason=f"error: {exc}",
                    timestamp=datetime.now().isoformat(),
                    case_id=case.id,
                    outcome=Outcome.RUNTIME_ERROR,
                    metadata={"error": str(exc)},
                )
                all_results.append(err_result)

            if completed % 20 == 0 or completed == n_cases:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = n_cases - completed
                eta = remaining / rate if rate > 0 else 0
                successes_so_far = sum(1 for r in all_results if _get_val(r, "success"))
                partials_so_far = sum(1 for r in all_results if _get_val(r, "partial_success") and not _get_val(r, "success"))
                print(
                    f"  [{completed}/{n_cases}] {elapsed:.0f}s elapsed, ~{eta:.0f}s remaining, "
                    f"errors: {error_count}, full: {successes_so_far}, partial: {partials_so_far}",
                    file=sys.stderr, flush=True,
                )

    elapsed = time.time() - start_time
    print(f"\nCompleted {n_cases} runs in {elapsed:.1f}s ({n_cases/elapsed:.1f} runs/sec)", file=sys.stderr, flush=True)

    all_results.sort(key=lambda r: r.case_id or "")

    all_jsonl = RESULT_DIR / "all_results.jsonl"
    all_csv = RESULT_DIR / "all_results.csv"
    _save_jsonl(all_results, all_jsonl)
    _save_csv(all_results, all_csv)
    print(f"Saved: {all_jsonl.name}, {all_csv.name}", file=sys.stderr, flush=True)

    summary = build_summary(all_results, n_cases, elapsed)
    summary_path = RESULT_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved: summary.json", file=sys.stderr, flush=True)

    print_report(summary)


def build_summary(results, n_cases, elapsed):
    total = len(results)
    full = sum(1 for r in results if _get_val(r, "success"))
    partial = sum(1 for r in results if _get_val(r, "partial_success") and not _get_val(r, "success"))
    none_count = total - full - partial
    sink_fires = sum(1 for r in results if _get_val(r, "sink_fired"))

    by_channel = {}
    for r in results:
        obj = r.to_dict() if hasattr(r, "to_dict") else r
        ch = obj.get("channel", "") or "(direct)"
        if ch not in by_channel:
            by_channel[ch] = {"total": 0, "full": 0, "partial": 0, "sink_fired": 0}
        by_channel[ch]["total"] += 1
        if _get_val(r, "success"):
            by_channel[ch]["full"] += 1
        if _get_val(r, "partial_success") and not _get_val(r, "success"):
            by_channel[ch]["partial"] += 1
        if _get_val(r, "sink_fired"):
            by_channel[ch]["sink_fired"] += 1

    for ch, d in by_channel.items():
        d["any_influence_rate"] = round((d["full"] + d["partial"]) / d["total"] * 100, 1) if d["total"] > 0 else 0
        d["full_rate"] = round(d["full"] / d["total"] * 100, 1) if d["total"] > 0 else 0

    outcome_counts = defaultdict(int)
    for r in results:
        obj = r.to_dict() if hasattr(r, "to_dict") else r
        outcome = obj.get("outcome", "unknown")
        if hasattr(outcome, "value"):
            outcome = outcome.value
        outcome_counts[outcome] += 1

    overall_rate = full / total * 100 if total > 0 else 0
    partial_rate = partial / total * 100 if total > 0 else 0
    any_rate = (full + partial) / total * 100 if total > 0 else 0

    return {
        "overall": {
            "total": total,
            "full_success": full,
            "partial_success": partial,
            "none": none_count,
            "full_rate": round(overall_rate, 1),
            "partial_rate": round(partial_rate, 1),
            "any_influence_rate": round(any_rate, 1),
            "sink_fired": sink_fires,
        },
        "by_channel": dict(sorted(by_channel.items())),
        "outcomes": dict(outcome_counts),
        "n_cases": n_cases,
        "elapsed_seconds": round(elapsed, 1),
        "throughput": round(n_cases / elapsed, 1) if elapsed > 0 else 0,
        "timestamp": datetime.now().isoformat(),
        "target": TARGET_SPEC,
        "agent": AGENT_KEY,
        "attack": ATTACK_KEY,
        "judge": "RuleJudge (three-level)",
        "workers": NUM_WORKERS,
    }


def print_report(summary):
    print("\n" + "=" * 80)
    print("NAIVE ATTACK - FULL CHANNEL MODE TEST")
    print(f"(Target: {summary['target']}, Agent: {summary['agent']}, Workers: {summary['workers']})")
    print("=" * 80)
    ov = summary["overall"]
    print(f"\nOverall ({ov['total']} runs):")
    print(f"  Full success:    {ov['full_success']:>4} ({ov['full_rate']:.1f}%)")
    print(f"  Partial success: {ov['partial_success']:>4} ({ov['partial_rate']:.1f}%)")
    print(f"  Any influence:   {ov['full_success'] + ov['partial_success']:>4} ({ov['any_influence_rate']:.1f}%)")
    print(f"  None:            {ov['none']:>4}")
    print(f"  Sink fired:      {ov['sink_fired']:>4}")

    print(f"\n{'Channel':<30} {'Total':>6} {'Full':>6} {'Partial':>8} {'Any%':>8} {'Sink':>6}")
    print("-" * 70)
    for ch, data in summary["by_channel"].items():
        print(
            f"{ch:<30} {data['total']:>6} {data['full']:>6} {data['partial']:>8} "
            f"{data['any_influence_rate']:>7.1f}% {data['sink_fired']:>6}"
        )

    print(f"\nOutcome distribution:")
    for outcome, count in summary["outcomes"].items():
        print(f"  {outcome}: {count}")

    print(f"\nElapsed: {summary['elapsed_seconds']}s ({summary['throughput']} runs/sec)")
    print(f"Results: {RESULT_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    run_test()
