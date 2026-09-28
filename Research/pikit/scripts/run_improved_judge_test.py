#!/usr/bin/env python3
"""Test improved judge with three-level success (full / partial / none).

Uses an OpenAI-compatible API with the general-purpose agent (full tool pool,
neutral system prompt). Tests a sample of indirect-injection cases from
the full_channel_mode dataset with multiple attack methods.

The key improvement: the judge now distinguishes:
  - full success    (canary terse / sink with matching args)
  - partial success (sink fired but args mismatch / canary in quoting context
                     / runtime policy blocked)
  - none            (refusal or no signals)

Output: result/improved_judge_test/

Environment variables:
    PIKIT_TARGET    Target spec (default: mock)
    PIKIT_AGENT     Agent key  (default: general_permissive)
"""

from __future__ import annotations

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

RESULT_DIR = Path(__file__).resolve().parent.parent / "result" / "improved_judge_test"
TARGET_SPEC = os.environ.get("PIKIT_TARGET", "mock")
AGENT_KEY = os.environ.get("PIKIT_AGENT", "general_permissive")

ALL_ATTACKS = [
    "naive",
    "escape",
    "context_ignoring",
    "fake_completion",
    "combined",
    "payload_splitting",
    "obfuscation",
    "prefix_injection",
    "format_confusion",
    "context_flooding",
    "cross_channel",
    "important_instructions",
    "stealth_instruction",
]


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


def sample_cases(ds, n=15):
    total = len(ds.cases)
    if total <= n:
        return ds.cases
    step = total / n
    indices = [int(i * step) for i in range(n)]
    return [ds.cases[i] for i in indices]


def run_test(attacks, sample_size=15, verbose=False):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("full_channel_mode")
    total_ds = len(ds.cases)
    print(f"Dataset: {ds.name} - {total_ds} total cases", file=sys.stderr, flush=True)

    cases = sample_cases(ds, sample_size)
    n_cases = len(cases)
    print(f"Sampled {n_cases} cases for evaluation", file=sys.stderr, flush=True)

    agent_target = get_target(TARGET_SPEC)
    print(f"Agent: {AGENT_KEY} (full tool pool, neutral system prompt)", file=sys.stderr, flush=True)
    print(f"Target: {agent_target.name}", file=sys.stderr, flush=True)
    print(f"Judge: RuleJudge (three-level: full / partial / none)", file=sys.stderr, flush=True)
    print(f"Attacks: {', '.join(attacks)}", file=sys.stderr, flush=True)
    total_runs = n_cases * len(attacks)
    print(f"Total runs: {n_cases} cases x {len(attacks)} attacks = {total_runs}", file=sys.stderr, flush=True)

    all_results = []
    per_attack_results = {a: [] for a in attacks}
    start_time = time.time()
    error_count = 0
    run_idx = 0

    for attack_key in attacks:
        print(f"\n{'='*60}", file=sys.stderr, flush=True)
        print(f"Starting attack: {attack_key}", file=sys.stderr, flush=True)
        print(f"{'='*60}", file=sys.stderr, flush=True)

        for ci, case in enumerate(cases, 1):
            run_idx += 1
            cfg = case.config
            cfg.target_spec = TARGET_SPEC
            cfg.agents = [AGENT_KEY]
            cfg.attacks = [attack_key]
            cfg.judge_type = "rule"

            if verbose:
                print(f"\n  [{run_idx}/{total_runs}] {attack_key} | {case.id}: {case.description[:60]}", file=sys.stderr, flush=True)
            elif ci % 5 == 0 or ci == 1 or ci == n_cases:
                elapsed = time.time() - start_time
                done = run_idx
                rate = done / elapsed if elapsed > 0 else 0
                remaining = total_runs - done
                eta = remaining / rate if rate > 0 else 0
                print(
                    f"  [{run_idx}/{total_runs}] {attack_key} case {ci}/{n_cases} - "
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
                print(f"  ERROR on {attack_key}/{case.id}: {exc}", file=sys.stderr, flush=True)
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
                all_results.append(err_result)
                per_attack_results[attack_key].append(err_result)

    elapsed = time.time() - start_time
    print(f"\nCompleted {total_runs} runs in {elapsed:.1f}s", file=sys.stderr, flush=True)

    all_jsonl = RESULT_DIR / "all_results.jsonl"
    all_csv = RESULT_DIR / "all_results.csv"
    _save_jsonl(all_results, all_jsonl)
    _save_csv(all_results, all_csv)
    print(f"Saved: {all_jsonl.name}, {all_csv.name}", file=sys.stderr, flush=True)

    summary = build_summary(per_attack_results, attacks, n_cases, elapsed)
    summary_path = RESULT_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved: summary.json", file=sys.stderr, flush=True)

    print_report(summary)


def build_summary(per_attack, attacks, n_cases, elapsed):
    by_attack = {}
    overall = {"total": 0, "full": 0, "partial": 0, "none": 0, "sink_fired": 0}

    for attack in attacks:
        results = per_attack.get(attack, [])
        total = len(results)
        full = sum(1 for r in results if _get_val(r, "success"))
        partial = sum(1 for r in results if _get_val(r, "partial_success") and not _get_val(r, "success"))
        none_count = total - full - partial
        sink_fires = sum(1 for r in results if _get_val(r, "sink_fired"))

        outcome_counts = defaultdict(int)
        for r in results:
            obj = r.to_dict() if hasattr(r, "to_dict") else r
            outcome = obj.get("outcome", "unknown")
            if hasattr(outcome, "value"):
                outcome = outcome.value
            outcome_counts[outcome] += 1

        by_attack[attack] = {
            "total": total,
            "full_success": full,
            "partial_success": partial,
            "none": none_count,
            "full_rate": round(full / total * 100, 1) if total > 0 else 0,
            "partial_rate": round(partial / total * 100, 1) if total > 0 else 0,
            "any_influence_rate": round((full + partial) / total * 100, 1) if total > 0 else 0,
            "sink_fired": sink_fires,
            "outcomes": dict(outcome_counts),
        }
        overall["total"] += total
        overall["full"] += full
        overall["partial"] += partial
        overall["none"] += none_count
        overall["sink_fired"] += sink_fires

    overall_rate = overall["full"] / overall["total"] * 100 if overall["total"] > 0 else 0
    partial_rate = overall["partial"] / overall["total"] * 100 if overall["total"] > 0 else 0
    any_rate = (overall["full"] + overall["partial"]) / overall["total"] * 100 if overall["total"] > 0 else 0

    return {
        "overall": {
            "total": overall["total"],
            "full_success": overall["full"],
            "partial_success": overall["partial"],
            "none": overall["none"],
            "full_rate": round(overall_rate, 1),
            "partial_rate": round(partial_rate, 1),
            "any_influence_rate": round(any_rate, 1),
            "sink_fired": overall["sink_fired"],
        },
        "by_attack": by_attack,
        "n_cases_sampled": n_cases,
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now().isoformat(),
        "target": TARGET_SPEC,
        "agent": AGENT_KEY,
        "judge": "RuleJudge (three-level)",
        "improvement": "Partial success detection: sink fired with wrong args, canary in quoting context, runtime policy blocked",
    }


def print_report(summary):
    print("\n" + "=" * 80)
    print("IMPROVED JUDGE TEST - THREE-LEVEL SUCCESS")
    print("(OpenAI-compatible API, general agent, RuleJudge with partial success)")
    print("=" * 80)
    ov = summary["overall"]
    print(f"\nOverall ({ov['total']} runs):")
    print(f"  Full success:    {ov['full_success']:>4} ({ov['full_rate']:.1f}%)")
    print(f"  Partial success: {ov['partial_success']:>4} ({ov['partial_rate']:.1f}%)")
    print(f"  Any influence:   {ov['full_success'] + ov['partial_success']:>4} ({ov['any_influence_rate']:.1f}%)")
    print(f"  None:            {ov['none']:>4}")
    print(f"  Sink fired:      {ov['sink_fired']:>4}")

    print(f"\n{'Attack':<30} {'Full':>6} {'Partial':>8} {'None':>6} {'Any%':>8} {'Sink':>6}")
    print("-" * 70)
    for attack, data in summary["by_attack"].items():
        print(
            f"{attack:<30} {data['full_success']:>6} {data['partial_success']:>8} "
            f"{data['none']:>6} {data['any_influence_rate']:>7.1f}% {data['sink_fired']:>6}"
        )
    print("=" * 80)

    print("\nOutcome breakdown:")
    for attack, data in summary["by_attack"].items():
        print(f"  {attack}: {data['outcomes']}")

    print(f"\nElapsed: {summary['elapsed_seconds']}s")
    print(f"Results: {RESULT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test improved three-level judge.")
    parser.add_argument("--attacks", nargs="+", default=ALL_ATTACKS)
    parser.add_argument("--sample-size", type=int, default=15)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    run_test(attacks=args.attacks, sample_size=args.sample_size, verbose=args.verbose)
