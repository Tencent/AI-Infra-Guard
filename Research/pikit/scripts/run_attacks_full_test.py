#!/usr/bin/env python3
"""Run each attack method sequentially on full_channel_mode dataset.

For each attack (excluding naive), runs all 1120 cases with 5 concurrent
threads. Results saved per-attack under result/attacks/{attack_name}/.

Usage:
    python scripts/run_attacks_full_test.py                  # run all attacks
    python scripts/run_attacks_full_test.py --only combined  # run a single attack

Environment variables:
    PIKIT_TARGET    Target spec (default: mock)
    PIKIT_AGENT     Agent key  (default: general_permissive)
    PIKIT_WORKERS   Concurrency (default: 5)
"""

from __future__ import annotations

import argparse
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

from pikit import attacks as attacks_mod
from pikit.datasets import load_dataset
from pikit.matrix import MatrixRunner, ExperimentResult
from pikit.outcomes import Outcome
from pikit.targets import get_target

RESULT_BASE = Path(__file__).resolve().parent.parent / "result" / "attacks"
TARGET_SPEC = os.environ.get("PIKIT_TARGET", "mock")
AGENT_KEY = os.environ.get("PIKIT_AGENT", "general_permissive")
NUM_WORKERS = int(os.environ.get("PIKIT_WORKERS", "5"))

# All attacks except naive
ALL_ATTACKS = [a for a in attacks_mod.list() if a != "naive"]


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


def run_attack(attack_key, cases, n_cases):
    result_dir = RESULT_BASE / attack_key
    result_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}", file=sys.stderr, flush=True)
    print(f"  ATTACK: {attack_key}  ({n_cases} cases, {NUM_WORKERS} workers)", file=sys.stderr, flush=True)
    print(f"{'='*70}", file=sys.stderr, flush=True)

    all_results = []
    start_time = time.time()
    error_count = 0
    completed = 0

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        future_to_case = {executor.submit(run_one_case, case, attack_key): case for case in cases}

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
                    attack=attack_key,
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
    print(f"\n  {attack_key} done: {n_cases} runs in {elapsed:.1f}s ({n_cases/elapsed:.1f} runs/sec)", file=sys.stderr, flush=True)

    all_results.sort(key=lambda r: r.case_id or "")

    _save_jsonl(all_results, result_dir / "all_results.jsonl")
    _save_csv(all_results, result_dir / "all_results.csv")
    print(f"  Saved: all_results.jsonl, all_results.csv", file=sys.stderr, flush=True)

    summary = build_summary(all_results, n_cases, elapsed, attack_key)
    with open(result_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  Saved: summary.json", file=sys.stderr, flush=True)

    print_attack_report(summary)
    return summary


def build_summary(results, n_cases, elapsed, attack_key):
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
        "attack": attack_key,
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
        "workers": NUM_WORKERS,
    }


def print_attack_report(summary):
    print(f"\n  --- {summary['attack'].upper()} SUMMARY ---", file=sys.stderr, flush=True)
    ov = summary["overall"]
    print(f"  Total: {ov['total']}, Full: {ov['full_success']} ({ov['full_rate']:.1f}%), "
          f"Partial: {ov['partial_success']} ({ov['partial_rate']:.1f}%), "
          f"Any: {ov['any_influence_rate']:.1f}%, Sink: {ov['sink_fired']}", file=sys.stderr, flush=True)


def run_all(attack_list):
    ds = load_dataset("full_channel_mode")
    cases = ds.cases
    n_cases = len(cases)
    agent_target = get_target(TARGET_SPEC)

    print(f"Dataset: {ds.name} - {n_cases} cases", file=sys.stderr, flush=True)
    print(f"Agent: {AGENT_KEY}", file=sys.stderr, flush=True)
    print(f"Target: {agent_target.name} ({TARGET_SPEC})", file=sys.stderr, flush=True)
    print(f"Workers: {NUM_WORKERS} concurrent threads", file=sys.stderr, flush=True)
    print(f"Attacks to run ({len(attack_list)}): {', '.join(attack_list)}", file=sys.stderr, flush=True)
    print(f"Total runs: {len(attack_list)} x {n_cases} = {len(attack_list) * n_cases}", file=sys.stderr, flush=True)
    print(f"{'='*70}", file=sys.stderr, flush=True)

    all_summaries = []
    total_start = time.time()

    for i, attack_key in enumerate(attack_list, 1):
        print(f"\n[{i}/{len(attack_list)}] Starting attack: {attack_key}", file=sys.stderr, flush=True)
        summary = run_attack(attack_key, cases, n_cases)
        all_summaries.append(summary)

        comparison = build_comparison(all_summaries)
        comp_path = RESULT_BASE / "comparison.json"
        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)

    total_elapsed = time.time() - total_start
    print(f"\n{'='*70}", file=sys.stderr, flush=True)
    print(f"ALL ATTACKS COMPLETE", file=sys.stderr, flush=True)
    print(f"  {len(attack_list)} attacks x {n_cases} cases = {len(attack_list) * n_cases} total runs", file=sys.stderr, flush=True)
    print(f"  Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)", file=sys.stderr, flush=True)
    print(f"{'='*70}", file=sys.stderr, flush=True)

    comparison = build_comparison(all_summaries)
    comp_path = RESULT_BASE / "comparison.json"
    with open(comp_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    print_final_report(comparison)


def build_comparison(summaries):
    return {
        "attacks": [
            {
                "attack": s["attack"],
                "total": s["overall"]["total"],
                "full_success": s["overall"]["full_success"],
                "partial_success": s["overall"]["partial_success"],
                "full_rate": s["overall"]["full_rate"],
                "partial_rate": s["overall"]["partial_rate"],
                "any_influence_rate": s["overall"]["any_influence_rate"],
                "sink_fired": s["overall"]["sink_fired"],
                "elapsed_seconds": s["elapsed_seconds"],
            }
            for s in summaries
        ],
        "timestamp": datetime.now().isoformat(),
    }


def print_final_report(comparison):
    print(f"\n{'='*80}", file=sys.stderr, flush=True)
    print("FINAL COMPARISON ACROSS ALL ATTACKS", file=sys.stderr, flush=True)
    print(f"{'='*80}", file=sys.stderr, flush=True)
    print(f"\n{'Attack':<25} {'Total':>6} {'Full':>6} {'Partial':>8} {'Any%':>8} {'Sink':>6} {'Time':>8}", file=sys.stderr, flush=True)
    print("-" * 75, file=sys.stderr, flush=True)
    for a in comparison["attacks"]:
        print(
            f"{a['attack']:<25} {a['total']:>6} {a['full_success']:>6} {a['partial_success']:>8} "
            f"{a['any_influence_rate']:>7.1f}% {a['sink_fired']:>6} {a['elapsed_seconds']:>7.0f}s",
            file=sys.stderr, flush=True,
        )
    print(f"\nComparison saved: {RESULT_BASE / 'comparison.json'}", file=sys.stderr, flush=True)
    print(f"{'='*80}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default=None, help="Run only this attack")
    args = parser.parse_args()

    if args.only:
        attack_list = [args.only]
    else:
        attack_list = ALL_ATTACKS

    run_all(attack_list)
