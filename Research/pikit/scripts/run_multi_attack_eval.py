#!/usr/bin/env python3
"""Run multi-attack indirect injection evaluation against an LLM target.

Unlike run_deepseek_eval.py (which only uses the weakest `naive` attack),
this script tests 8 different attack methods against a sampled subset of
the full_channel_mode dataset, then compares their success rates.

Usage:
    python scripts/run_multi_attack_eval.py                         # full run (50 cases x 8 attacks)
    python scripts/run_multi_attack_eval.py --limit 5               # smoke test (5 cases x 8 attacks)
    python scripts/run_multi_attack_eval.py --attacks important_instructions combined  # specific attacks
    python scripts/run_multi_attack_eval.py --limit 10 --verbose    # verbose smoke test

Output:
    result/multi_attack/
      per_attack/
        important_instructions_results.jsonl
        combined_results.jsonl
        ...
      all_results.jsonl          -- all results combined
      all_results.csv            -- flat CSV summary
      comparison_summary.json    -- success rate by attack method
      comparison_summary.txt     -- human-readable comparison table
      run_meta.json              -- run metadata

Environment variables:
    PIKIT_TARGET    Target spec (default: mock)
"""

from __future__ import annotations

import argparse
import csv as csv_mod
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pikit.datasets import load_dataset
from pikit.matrix import MatrixRunner, ExperimentResult
from pikit.outcomes import Outcome
from pikit.targets import get_target

RESULT_DIR = Path(__file__).resolve().parent.parent / "result" / "multi_attack"
TARGET_SPEC = os.environ.get("PIKIT_TARGET", "mock")

# Attack methods to test (excluding naive which was already tested at 0%).
ALL_ATTACKS = [
    "important_instructions",
    "combined",
    "fake_completion",
    "format_confusion",
    "context_ignoring",
    "escape",
    "obfuscation",
    "payload_splitting",
]


def _save_jsonl(results: list, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            obj = r.to_dict() if hasattr(r, "to_dict") else r
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _save_csv(results: list, path: Path) -> None:
    fieldnames = [
        "case_id", "attack", "defense", "channel", "agent", "target",
        "task", "success", "confidence", "reason", "timestamp",
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


def sample_cases(ds, n: int = 50) -> list:
    total = len(ds.cases)
    if total <= n:
        return ds.cases
    step = total / n
    indices = [int(i * step) for i in range(n)]
    return [ds.cases[i] for i in indices]


def run_multi_attack(
    attacks: list[str],
    limit: int | None = None,
    verbose: bool = False,
    sample_size: int = 50,
) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    per_attack_dir = RESULT_DIR / "per_attack"
    per_attack_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("full_channel_mode")
    total_ds = len(ds.cases)
    print(f"Dataset: {ds.name} -- {total_ds} total cases", file=sys.stderr, flush=True)

    cases = sample_cases(ds, sample_size)
    if limit and limit > 0:
        cases = cases[:limit]
    n_cases = len(cases)
    print(f"Sampled {n_cases} cases for evaluation", file=sys.stderr, flush=True)

    agent_target = get_target(TARGET_SPEC)
    print(f"Agent target: {agent_target.name}", file=sys.stderr, flush=True)
    print(f"Judge: LLMJudge ({TARGET_SPEC})", file=sys.stderr, flush=True)
    print(f"Attacks: {', '.join(attacks)}", file=sys.stderr, flush=True)
    print(f"Total runs: {n_cases} cases x {len(attacks)} attacks = {n_cases * len(attacks)}", file=sys.stderr, flush=True)

    all_results: list = []
    per_attack_results: dict[str, list] = {a: [] for a in attacks}
    start_time = time.time()
    error_count = 0
    total_runs = n_cases * len(attacks)
    run_idx = 0

    for attack_key in attacks:
        print(f"\n{'='*60}", file=sys.stderr, flush=True)
        print(f"Starting attack: {attack_key}", file=sys.stderr, flush=True)
        print(f"{'='*60}", file=sys.stderr, flush=True)

        attack_start = time.time()
        for ci, case in enumerate(cases, 1):
            run_idx += 1
            cfg = case.config
            cfg.target_spec = TARGET_SPEC
            cfg.attacks = [attack_key]
            cfg.judge_type = "llm"

            if verbose:
                print(f"\n  [{run_idx}/{total_runs}] {attack_key} | {case.id}: {case.description}", file=sys.stderr, flush=True)
            elif ci % 10 == 0 or ci == 1 or ci == n_cases:
                elapsed = time.time() - start_time
                done = run_idx
                rate = done / elapsed if elapsed > 0 else 0
                remaining = total_runs - done
                eta = remaining / rate if rate > 0 else 0
                print(
                    f"  [{run_idx}/{total_runs}] {attack_key} case {ci}/{n_cases} -- "
                    f"{elapsed:.0f}s elapsed, ~{eta:.0f}s remaining, errors: {error_count}",
                    file=sys.stderr, flush=True,
                )

            try:
                runner = MatrixRunner(cfg, verbose=False)
                results = runner.run()
                for r in results:
                    r.case_id = case.id
                    r.metadata["case_description"] = case.description
                    r.metadata["attack_method"] = attack_key
                all_results.extend(results)
                per_attack_results[attack_key].extend(results)
            except (Exception, SystemExit) as exc:
                error_count += 1
                print(f"  Error on {attack_key}/{case.id}: {exc}", file=sys.stderr, flush=True)
                err_result = ExperimentResult(
                    attack=attack_key,
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
                    metadata={"case_description": case.description, "attack_method": attack_key, "error": str(exc)},
                )
                all_results.append(err_result)
                per_attack_results[attack_key].append(err_result)

            if ci % 10 == 0 or ci == n_cases:
                _save_jsonl(per_attack_results[attack_key], per_attack_dir / f"{attack_key}_results.jsonl")

        attack_elapsed = time.time() - attack_start
        attack_successes = sum(1 for r in per_attack_results[attack_key] if _get_success(r))
        attack_total = len(per_attack_results[attack_key])
        rate = (attack_successes / attack_total * 100) if attack_total > 0 else 0
        print(
            f"  {attack_key}: {attack_successes}/{attack_total} succeeded ({rate:.1f}%) "
            f"in {attack_elapsed:.0f}s",
            file=sys.stderr, flush=True,
        )

        _save_jsonl(per_attack_results[attack_key], per_attack_dir / f"{attack_key}_results.jsonl")
        _save_csv(per_attack_results[attack_key], per_attack_dir / f"{attack_key}_results.csv")

    elapsed = time.time() - start_time
    print(f"\nCompleted {total_runs} runs in {elapsed:.1f}s", file=sys.stderr)

    all_jsonl = RESULT_DIR / "all_results.jsonl"
    all_csv = RESULT_DIR / "all_results.csv"
    _save_jsonl(all_results, all_jsonl)
    _save_csv(all_results, all_csv)
    print(f"Saved: {all_jsonl.name}, {all_csv.name}", file=sys.stderr, flush=True)

    summary = build_comparison_summary(per_attack_results, attacks, n_cases, elapsed)
    summary_path = RESULT_DIR / "comparison_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved: {summary_path.name}", file=sys.stderr)

    txt_path = RESULT_DIR / "comparison_summary.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(format_comparison_text(summary))
    print(f"Saved: {txt_path.name}", file=sys.stderr)

    meta = {
        "dataset": "full_channel_mode",
        "target": TARGET_SPEC,
        "judge": f"llm ({TARGET_SPEC})",
        "attacks": attacks,
        "total_cases_sampled": n_cases,
        "total_runs": total_runs,
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now().isoformat(),
        "result_dir": str(RESULT_DIR),
    }
    meta_path = RESULT_DIR / "run_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Saved: {meta_path.name}", file=sys.stderr)

    print_comparison(summary)


def _get_success(r) -> bool:
    if hasattr(r, "success"):
        return r.success
    if isinstance(r, dict):
        return r.get("success", False)
    return False


def build_comparison_summary(
    per_attack: dict[str, list],
    attacks: list[str],
    n_cases: int,
    elapsed: float,
) -> dict:
    by_attack = {}
    overall = {"total": 0, "success": 0}

    for attack in attacks:
        results = per_attack.get(attack, [])
        total = len(results)
        successes = sum(1 for r in results if _get_success(r))
        rate = (successes / total * 100) if total > 0 else 0

        outcome_counts = defaultdict(int)
        for r in results:
            obj = r.to_dict() if hasattr(r, "to_dict") else r
            outcome = obj.get("outcome", "unknown")
            outcome_counts[outcome] += 1

        channel_stats = defaultdict(lambda: {"total": 0, "success": 0})
        for r in results:
            obj = r.to_dict() if hasattr(r, "to_dict") else r
            channel = obj.get("channel", "unknown")
            channel_stats[channel]["total"] += 1
            if _get_success(r):
                channel_stats[channel]["success"] += 1

        channel_breakdown = {}
        for ch in sorted(channel_stats.keys()):
            s = channel_stats[ch]
            ch_rate = (s["success"] / s["total"] * 100) if s["total"] > 0 else 0
            channel_breakdown[ch] = {
                "total": s["total"],
                "success": s["success"],
                "success_rate": round(ch_rate, 1),
            }

        by_attack[attack] = {
            "total": total,
            "success": successes,
            "success_rate": round(rate, 1),
            "outcomes": dict(outcome_counts),
            "by_channel": channel_breakdown,
        }
        overall["total"] += total
        overall["success"] += successes

    overall_rate = (overall["success"] / overall["total"] * 100) if overall["total"] > 0 else 0

    ranking = sorted(by_attack.items(), key=lambda x: x[1]["success_rate"], reverse=True)

    return {
        "overall": {
            "total": overall["total"],
            "success": overall["success"],
            "success_rate": round(overall_rate, 1),
        },
        "by_attack": by_attack,
        "ranking": [{"attack": a, "success_rate": s["success_rate"], "success": s["success"], "total": s["total"]} for a, s in ranking],
        "n_cases_sampled": n_cases,
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now().isoformat(),
    }


def format_comparison_text(summary: dict) -> str:
    lines = []
    lines.append("=" * 75)
    lines.append("MULTI-ATTACK INDIRECT INJECTION EVALUATION -- COMPARISON SUMMARY")
    lines.append("=" * 75)
    ov = summary["overall"]
    lines.append(f"Overall: {ov['success']}/{ov['total']} succeeded ({ov['success_rate']}%)")
    lines.append(f"Cases sampled: {summary['n_cases_sampled']}")
    lines.append(f"Elapsed: {summary['elapsed_seconds']}s")
    lines.append("")
    lines.append(f"{'Attack':<30} {'Success':>8} {'Total':>8} {'Rate':>8}")
    lines.append("-" * 60)
    for item in summary["ranking"]:
        lines.append(
            f"{item['attack']:<30} {item['success']:>8} {item['total']:>8} "
            f"{item['success_rate']:>7.1f}%"
        )
    lines.append("=" * 75)
    lines.append("")

    for item in summary["ranking"]:
        attack = item["attack"]
        attack_data = summary["by_attack"][attack]
        lines.append(f"\n--- {attack} ({attack_data['success_rate']}%) ---")
        lines.append(f"  Outcomes: {attack_data['outcomes']}")
        if attack_data["by_channel"]:
            lines.append(f"  {'Channel':<25} {'Success':>8} {'Total':>8} {'Rate':>8}")
            lines.append("  " + "-" * 55)
            for ch, stats in sorted(attack_data["by_channel"].items()):
                lines.append(f"  {ch:<25} {stats['success']:>8} {stats['total']:>8} {stats['success_rate']:>7.1f}%")

    return "\n".join(lines)


def print_comparison(summary: dict) -> None:
    print("\n" + "=" * 75)
    print("MULTI-ATTACK INDIRECT INJECTION EVALUATION -- COMPARISON")
    print("=" * 75)
    ov = summary["overall"]
    print(f"Overall: {ov['success']}/{ov['total']} succeeded ({ov['success_rate']}%)")
    print(f"Cases sampled: {summary['n_cases_sampled']}")
    print()
    print(f"{'Attack':<30} {'Success':>8} {'Total':>8} {'Rate':>8}")
    print("-" * 60)
    for item in summary["ranking"]:
        print(
            f"{item['attack']:<30} {item['success']:>8} {item['total']:>8} "
            f"{item['success_rate']:>7.1f}%"
        )
    print("=" * 75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run multi-attack indirect injection evaluation."
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit to first N sampled cases (for smoke testing).",
    )
    parser.add_argument(
        "--attacks", nargs="+", default=ALL_ATTACKS,
        help=f"Attack methods to test. Default: {ALL_ATTACKS}",
    )
    parser.add_argument(
        "--sample-size", type=int, default=50,
        help="Number of cases to sample from dataset (default 50).",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print each case as it runs.",
    )
    args = parser.parse_args()
    run_multi_attack(
        attacks=args.attacks,
        limit=args.limit,
        verbose=args.verbose,
        sample_size=args.sample_size,
    )
