#!/usr/bin/env python3
"""Infra-attack module entry point.

Usage:
  python3 run.py --target http://host:port --out reports/<run_id>/infra-attack_findings.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
MODULE_DIR = THIS_DIR.parent
SKILL_ROOT = MODULE_DIR.parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(THIS_DIR))

from fingerprint_engine import FingerprintEngine
from vuln_engine import VulnEngine
from common.http_probe import normalize_target, is_reachable, http_get  # noqa: E402
from aig_data import discover as discover_aig_data, download_to_temp  # noqa: E402


def severity_to_label(sev: str) -> str:
    sev = (sev or "info").strip().lower()
    zh_map = {
        "严重": "critical",
        "危急": "critical",
        "高": "high",
        "高危": "high",
        "中": "medium",
        "中危": "medium",
        "低": "low",
        "低危": "low",
        "信息": "info",
    }
    sev = zh_map.get(sev, sev)
    return sev if sev in ("critical", "high", "medium", "low", "info") else "info"


def run(target: str, fp_dir: Path, vuln_dir: Path, data_source: str = "bundled") -> dict:
    started = datetime.now(timezone.utc).isoformat()
    target = normalize_target(target)

    findings = []
    operators_run = 0
    operators_skipped = 0
    cascade = []

    if not is_reachable(target, timeout=2.0):
        return {
            "module": "infra-attack",
            "target": target,
            "started_at": started,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "findings": [],
            "stats": {"operators_run": 0, "operators_skipped": 0, "duration_sec": 0, "error": "unreachable"},
            "cascade_targets": [],
        }

    # 1. Fingerprint
    fp_engine = FingerprintEngine(fp_dir)
    primary = http_get(target, timeout=8.0)
    fp_match = fp_engine.match(target, primary_response=primary)

    if not fp_match:
        # Even with no fingerprint, still report what we saw
        findings.append({
            "id": "INFO-NO-FINGERPRINT",
            "title": "未识别为已知 AI 服务",
            "severity": "info",
            "evidence": f"status={primary.status_code}, title={primary.title!r}, server={primary.headers.get('Server', '')}",
            "remediation": "若该服务确实是 AI 类组件，请上报 fingerprint 规则",
            "references": [],
        })
        operators_run += 1
    else:
        findings.append({
            "id": f"FP-{fp_match.product.upper()}",
            "title": f"识别到 {fp_match.product} {fp_match.version or '(版本未知)'}",
            "severity": "info",
            "evidence": f"matched on {fp_match.path_hit}: {fp_match.matcher_hit[:200]}",
            "remediation": "若不希望对外暴露此服务，建议加访问控制",
            "references": [],
        })
        operators_run += 1

        # Cascade: if it's a known LLM-serving infra, propose model-attack
        if fp_match.product.lower() in {"ollama", "vllm", "lmstudio", "fastchat", "huggingface-tgi", "anythingllm"}:
            cascade.append({
                "target_types": ["llm_endpoint"],
                "extracted": {
                    "base_url": target.rstrip("/") + "/v1",
                    "models_listed": [],
                    "inferred_from_infra": fp_match.product,
                }
            })

        # 2. CVE matching
        vuln_engine = VulnEngine(vuln_dir)
        cve_matches = vuln_engine.match(fp_match.product, fp_match.version)
        for cve in cve_matches:
            findings.append({
                "id": cve.cve_id,
                "title": cve.summary or f"{cve.cve_id} 影响 {fp_match.product}",
                "severity": severity_to_label(cve.severity),
                "evidence": f"version={fp_match.version} matches rule `{cve.rule}`",
                "remediation": cve.advice or "升级到不受影响的版本",
                "references": cve.references[:5],
                "cvss": cve.cvss,
                "details": cve.details[:500],
            })
            operators_run += 1

    ended = datetime.now(timezone.utc).isoformat()
    duration = (datetime.fromisoformat(ended) - datetime.fromisoformat(started)).total_seconds()

    return {
        "module": "infra-attack",
        "target": target,
        "started_at": started,
        "ended_at": ended,
        "findings": findings,
        "stats": {
            "operators_run": operators_run,
            "operators_skipped": operators_skipped,
            "duration_sec": round(duration, 2),
            "data_source": data_source,
            "fingerprints_dir": str(fp_dir),
            "vuln_dir": str(vuln_dir),
            "fingerprint": {"product": fp_match.product, "version": fp_match.version} if fp_match else None,
        },
        "cascade_targets": cascade,
    }


def resolve_data_dirs(args) -> tuple[Path, Path, str]:
    explicit_fp = Path(args.fp_dir) if args.fp_dir else None
    explicit_vuln = Path(args.vuln_dir) if args.vuln_dir else None
    if explicit_fp or explicit_vuln:
        return (
            explicit_fp or MODULE_DIR / "data" / "fingerprints",
            explicit_vuln or MODULE_DIR / "data" / "vuln",
            "explicit",
        )

    aig = discover_aig_data(args.aig_data_dir, args.aig_root)
    if not aig and args.download_aig_data:
        aig = download_to_temp(args.aig_repo, keep=True)
    if aig:
        vuln_base = aig.vuln_en_dir if args.vuln_lang == "en" and aig.vuln_en_dir.exists() else aig.vuln_dir
        return aig.fingerprints_dir, vuln_base, f"aig:{aig.source}"

    return MODULE_DIR / "data" / "fingerprints", MODULE_DIR / "data" / "vuln", "bundled"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fp-dir", help="指纹规则目录；默认自动使用 AIG data 或内置数据")
    ap.add_argument("--vuln-dir", help="漏洞规则目录；默认自动使用 AIG data 或内置数据")
    ap.add_argument("--aig-data-dir", help="AI-Infra-Guard/data 路径")
    ap.add_argument("--aig-root", help="AI-Infra-Guard 仓库根目录")
    ap.add_argument("--download-aig-data", action="store_true", help="未找到本地 AIG data 时下载 AI-Infra-Guard 到临时目录")
    ap.add_argument("--aig-repo", default=os.environ.get("AIG_REPO", "https://github.com/tencent/AI-Infra-Guard.git"))
    ap.add_argument("--vuln-lang", choices=["zh", "en"], default="zh", help="AIG 漏洞规则语言，默认 zh")
    args = ap.parse_args()

    fp_dir, vuln_dir, data_source = resolve_data_dirs(args)
    result = run(args.target, fp_dir, vuln_dir, data_source=data_source)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # Print summary
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in result["findings"]:
        counts[f.get("severity", "info")] = counts.get(f.get("severity", "info"), 0) + 1
    print(f"infra-attack: target={result['target']}")
    print(f"  fingerprint: {result['stats'].get('fingerprint')}")
    print(f"  data_source: {result['stats'].get('data_source')}")
    print(f"  findings: critical={counts['critical']} high={counts['high']} medium={counts['medium']} low={counts['low']} info={counts['info']}")
    print(f"  duration: {result['stats']['duration_sec']}s")
    print(f"  → wrote {out}")
    if result.get("cascade_targets"):
        print(f"  → cascade: {len(result['cascade_targets'])} target(s) for follow-up modules")


if __name__ == "__main__":
    main()
