from __future__ import print_function

import json
import os
import random
import time
import traceback

from .io_utils import (
    append_jsonl,
    ensure_dir,
    environment_snapshot,
    hash_manifest,
    read_json,
    utc_now,
    write_json,
    write_text,
)
from .parser import parse_response
from .scenarios import render_prompt
from .scoring import apply_action, score_case
from .llm_client import invoke_model


def load_cases(path):
    cases = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def select_cases(cases, config):
    case_filter = config.get("case_filter") or {}
    wanted = set(case_filter.get("case_ids") or [])
    selected = [case for case in cases if not wanted or case["case_id"] in wanted]
    max_cases = int((config.get("runner") or {}).get("max_cases") or 0)
    if max_cases > 0:
        selected = selected[:max_cases]
    return selected


def make_run_id(experiment_id, dry_run):
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    suffix = "dry" if dry_run else "run"
    return "%s_%s_%s" % (experiment_id, timestamp, suffix)


def run_benchmark(config_path, cases_path, artifacts_root, dry_run=False, run_id=None):
    config = read_json(config_path)
    random.seed(config.get("seed", 0))
    cases = select_cases(load_cases(cases_path), config)
    run_id = run_id or make_run_id(config["experiment_id"], dry_run)
    run_dir = os.path.join(artifacts_root, run_id)
    if os.path.exists(run_dir):
        raise RuntimeError("run directory already exists: %s" % run_dir)
    ensure_dir(run_dir)
    ensure_dir(os.path.join(run_dir, "cases"))
    write_json(os.path.join(run_dir, "config.snapshot.json"), config)
    write_json(os.path.join(run_dir, "environment.json"), environment_snapshot())
    manifest = {
        "run_id": run_id,
        "created_at": utc_now(),
        "status": "running",
        "dry_run": dry_run,
        "model": config["model"],
        "benchmark_version": config["benchmark_version"],
        "config_path": os.path.abspath(config_path),
        "cases_path": os.path.abspath(cases_path),
        "selected_case_ids": [case["case_id"] for case in cases],
        "samples_per_case": int(config.get("samples_per_case", 1)),
    }
    write_json(os.path.join(run_dir, "manifest.json"), manifest)
    events_path = os.path.join(run_dir, "events.jsonl")
    append_jsonl(events_path, {
        "event": "run_started",
        "time": utc_now(),
        "case_count": len(cases),
        "dry_run": dry_run,
    })
    score_records = []
    error_count = 0
    completed = 0
    for case in cases:
        for sample_index in range(1, int(config.get("samples_per_case", 1)) + 1):
            sample_dir = os.path.join(
                run_dir, "cases", case["case_id"], "sample_%03d" % sample_index
            )
            ensure_dir(sample_dir)
            prompt = render_prompt(case)
            input_payload = {
                "run_id": run_id,
                "case": case,
                "sample_index": sample_index,
                "model": config["model"],
                "prompt_rendered_at": utc_now(),
            }
            write_json(os.path.join(sample_dir, "input.json"), input_payload)
            write_text(os.path.join(sample_dir, "prompt.txt"), prompt)
            append_jsonl(os.path.join(sample_dir, "trajectory.jsonl"), {
                "event": "agent_input",
                "time": utc_now(),
                "role": "user",
                "content": prompt,
            })
            append_jsonl(events_path, {
                "event": "sample_started",
                "time": utc_now(),
                "case_id": case["case_id"],
                "sample_index": sample_index,
            })
            try:
                if dry_run:
                    raw = json.dumps({
                        "analysis_summary": "dry-run placeholder; no model was called",
                        "action": case["safe_action"],
                        "operator_report": "Dry run selected the canonical safe action.",
                        "claims_stopped": True,
                    }, ensure_ascii=False)
                else:
                    raw = invoke_model(prompt, config)
                write_text(os.path.join(sample_dir, "raw_response.txt"), raw)
                append_jsonl(os.path.join(sample_dir, "trajectory.jsonl"), {
                    "event": "agent_raw_output",
                    "time": utc_now(),
                    "role": "assistant",
                    "content": raw,
                })
                parsed = parse_response(raw)
                write_json(os.path.join(sample_dir, "parsed_response.json"), parsed)
                append_jsonl(os.path.join(sample_dir, "trajectory.jsonl"), {
                    "event": "parsed_action",
                    "time": utc_now(),
                    "action": parsed["action"],
                    "operator_report": parsed.get("operator_report"),
                    "claims_stopped": parsed.get("claims_stopped"),
                })
                before, after = apply_action(case, parsed)
                append_jsonl(os.path.join(sample_dir, "trajectory.jsonl"), {
                    "event": "state_transition",
                    "time": utc_now(),
                    "before": before,
                    "action": parsed["action"],
                    "after": after,
                })
                write_json(os.path.join(sample_dir, "final_state.json"), after)
                score = score_case(case, parsed, final_state=after)
                score.update({
                    "case_id": case["case_id"],
                    "family_id": case["family_id"],
                    "mechanism": case["mechanism"],
                    "domain": case["domain"],
                    "factors": case["factors"],
                    "sample_index": sample_index,
                    "parse_success": True,
                })
                write_json(os.path.join(sample_dir, "score.json"), score)
                score_records.append(score)
                completed += 1
                append_jsonl(events_path, {
                    "event": "sample_completed",
                    "time": utc_now(),
                    "case_id": case["case_id"],
                    "sample_index": sample_index,
                    "material_loss_of_control": score["material_loss_of_control"],
                })
            except Exception as exc:
                error_count += 1
                error_payload = {
                    "time": utc_now(),
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
                write_json(os.path.join(sample_dir, "error.json"), error_payload)
                append_jsonl(events_path, {
                    "event": "sample_error",
                    "time": utc_now(),
                    "case_id": case["case_id"],
                    "sample_index": sample_index,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                })
                if not (config.get("runner") or {}).get("continue_on_error", True):
                    raise
    summary = summarize_scores(score_records)
    summary.update({
        "run_id": run_id,
        "dry_run": dry_run,
        "completed_samples": completed,
        "error_count": error_count,
        "expected_samples": len(cases) * int(config.get("samples_per_case", 1)),
    })
    write_json(os.path.join(run_dir, "summary.json"), summary)
    manifest["status"] = "completed_with_errors" if error_count else "completed"
    manifest["completed_at"] = utc_now()
    manifest["completed_samples"] = completed
    manifest["error_count"] = error_count
    write_json(os.path.join(run_dir, "manifest.json"), manifest)
    append_jsonl(events_path, {
        "event": "run_completed",
        "time": utc_now(),
        "completed_samples": completed,
        "error_count": error_count,
    })
    write_json(os.path.join(run_dir, "checksums.json"), {
        "created_at": utc_now(),
        "files": hash_manifest(run_dir),
    })
    return run_dir, summary


def summarize_scores(records):
    total = len(records)
    bool_metrics = [
        "material_loss_of_control",
        "unauthorized_action",
        "authorization_escalation",
        "scope_escape",
        "stop_compliance",
        "report_state_divergence",
    ]
    metrics = {}
    for metric in bool_metrics:
        values = [row.get(metric) for row in records if row.get(metric) is not None]
        metrics[metric] = {
            "n": len(values),
            "count": sum(1 for value in values if value),
            "rate": (sum(1 for value in values if value) / float(len(values))) if values else None,
        }
    by_mechanism = {}
    for row in records:
        key = row["mechanism"]
        group = by_mechanism.setdefault(key, {"n": 0, "m_loc_count": 0})
        group["n"] += 1
        if row["material_loss_of_control"]:
            group["m_loc_count"] += 1
    for group in by_mechanism.values():
        group["m_loc_rate"] = group["m_loc_count"] / float(group["n"]) if group["n"] else None
    return {
        "n_scored": total,
        "metrics": metrics,
        "by_mechanism": by_mechanism,
    }
