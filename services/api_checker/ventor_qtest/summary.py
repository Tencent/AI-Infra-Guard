#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汇总指定 JSON（或通配模式）并输出供应商排名 CSV —— 无命令行参数版。

使用方式：
1) 编辑【配置区】常量（输入文件/模式、输出路径、排序字段与方向等）。
2) 直接运行： `python summarize_results_no_cli.py`
3) 结果会写入配置中指定的 CSV；可选生成明细表。

仅依赖标准库，也提供 run(...) 编程式入口。
"""

from __future__ import annotations
import csv
import glob
import json
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional

# ========================= 配置区（按需修改） =========================
# A. 直接列出要读取的 JSON 文件（可留空，留空则使用 B 的通配模式）
INPUT_PATHS: List[str] = []

# B. 通配模式（当 INPUT_PATHS 为空时生效，可多个）
_DATA_DIR = Path(os.environ.get(
    "AIG_API_CHECKER_DATA_DIR",
    Path(__file__).resolve().parents[1] / "runtime",
))
_QTEST_RESULT_DIR = _DATA_DIR / "qtest" / "result"
INPUT_PATTERNS: List[str] = [
    str(_QTEST_RESULT_DIR / "deepseek_exp32" / "*.json"),
]

# 输出：供应商聚合排名表
OUTPUT_RANK_CSV: str = str(_QTEST_RESULT_DIR / "summary_exp32" / "vendors_rank.csv")

# 可选：明细表（每次运行一行）；留空或 None 则不导出
OUTPUT_LONG_CSV: Optional[str] = str(_QTEST_RESULT_DIR / "summary_exp32" / "runs_long.csv")

# 排序字段与方向（见 SORTABLE_FIELDS）
SORT_BY: str = "mean_abs_Z"  # 可选：mean_abs_Z | median_abs_Z | n_valid | n_total
DESCENDING: bool = False      # True=降序，False=升序

# ======================= 结束配置区 ================================

# --------------------------- 工具函数 ---------------------------

def _to_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _parse_ts(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        ts2 = ts.replace(" ", "T").replace("+0000", "+00:00")
        # 文件名友好的时间戳（冒号替换为破折号）修复
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}", ts2):
            ts2 = ts2[:10] + "T" + ts2[11:13] + ":" + ts2[14:16] + ":" + ts2[17:19] + ts2[19:]
        return datetime.fromisoformat(ts2)
    except Exception:
        return None


def _canonical_model(model: str) -> str:
    m = str(model or "").strip().lower()
    if not m:
        return ""
    if m.startswith("pro/"):
        m = m[4:]

    if "kimi-k2.5" in m:
        return "moonshotai/kimi-k2.5"
    if "kimi-k2-0905" in m:
        return "moonshotai/kimi-k2-0905"
    if "deepseek-chat" in m:
        return "deepseek-chat"
    return m


@dataclass
class RunRow:
    filename: str
    question: str
    question_slug: str
    run_index: int
    timestamp_utc: Optional[datetime]
    vendor: str
    model: str = ""
    model_canonical: str = ""
    official_baseline_vendor: str = ""
    skipped: bool = False
    reason: str = ""
    error: str = ""
    length: Optional[int] = None
    abs_Z: Optional[float] = None
    token_log_dev: Optional[float] = None


# --------------------------- 读取 JSON → 明细行 ---------------------------

def _load_json_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _iter_run_rows(files: Iterable[str]) -> Iterable[RunRow]:
    for fp in files:
        try:
            payload = _load_json_file(fp)
        except Exception as e:
            print(f"[warn] 跳过无效 JSON: {fp}: {e}")
            continue

        question = payload.get("question", "")
        qslug = payload.get("question_slug", "")
        run_index = int(payload.get("run_index", 0) or 0)
        ts_raw = payload.get("timestamp_utc", "")
        ts = _parse_ts(ts_raw)
        summaries = payload.get("summaries", {}) or {}
        details = payload.get("details", {}) or {}
        vendor_models = payload.get("vendor_models", {}) or {}
        vendor_meta = payload.get("vendor_meta", {}) or {}

        official_baseline_vendor = str(payload.get("official_baseline_vendor") or "").strip()
        if not official_baseline_vendor and isinstance(payload.get("payload"), dict):
            official_baseline_vendor = str((payload.get("payload") or {}).get("official_baseline_vendor") or "").strip()

        for vendor, summ in summaries.items():
            model_name = str(vendor_models.get(vendor) or "").strip()
            if not model_name:
                meta = vendor_meta.get(vendor) or {}
                if isinstance(meta, dict):
                    model_name = str(meta.get("model") or "").strip()
            model_canonical = _canonical_model(model_name)

            # 跳过/错误
            if isinstance(summ, dict) and summ.get("skipped"):
                yield RunRow(
                    filename=fp,
                    question=question,
                    question_slug=qslug,
                    run_index=run_index,
                    timestamp_utc=ts,
                    vendor=vendor,
                    model=model_name,
                    model_canonical=model_canonical,
                    official_baseline_vendor=official_baseline_vendor,
                    skipped=True,
                    reason=str(summ.get("reason", ""))[:120]
                )
                continue
            if isinstance(summ, dict) and "error" in summ and not summ.get("len"):
                yield RunRow(
                    filename=fp,
                    question=question,
                    question_slug=qslug,
                    run_index=run_index,
                    timestamp_utc=ts,
                    vendor=vendor,
                    model=model_name,
                    model_canonical=model_canonical,
                    official_baseline_vendor=official_baseline_vendor,
                    skipped=True,
                    reason="error",
                    error=str(summ.get("error", ""))[:160]
                )
                continue

            # 正常数据
            detail_stats = (details.get(vendor) or {}).get("stats", {}) or {}
            z_val = _to_float(summ.get("Z"))
            abs_z_val = _to_float(summ.get("abs_Z"))
            if abs_z_val is None and z_val is not None:
                abs_z_val = abs(z_val)
            length_val = int(summ.get("len") or 0) if summ.get("len") is not None else None

            token_log_dev_val = _to_float(summ.get("token_log_dev"))
            if token_log_dev_val is None and length_val is not None and length_val > 0:
                obs_total = _to_float(detail_stats.get("总观测损失"))
                exp_total = _to_float(detail_stats.get("总期望损失"))
                if obs_total is not None and exp_total is not None:
                    token_log_dev_val = abs(obs_total - exp_total) / length_val
            if token_log_dev_val is None and length_val is not None and length_val > 0 and abs_z_val is not None:
                w_val = _to_float(summ.get("W"))
                if w_val is None:
                    w_val = _to_float(detail_stats.get("信息标准差W"))
                if w_val is not None:
                    token_log_dev_val = abs_z_val * w_val / length_val

            yield RunRow(
                filename=fp,
                question=question,
                question_slug=qslug,
                run_index=run_index,
                timestamp_utc=ts,
                vendor=vendor,
                model=model_name,
                model_canonical=model_canonical,
                official_baseline_vendor=official_baseline_vendor,
                skipped=False,
                length=length_val,
                abs_Z=abs_z_val,
                token_log_dev=token_log_dev_val,
            )


# --------------------------- 聚合成供应商级概览 ---------------------------

@dataclass
class VendorAgg:
    vendor: str
    n_total: int = 0
    n_valid: int = 0
    n_skipped: int = 0
    n_errors: int = 0
    abs_Z_vals: List[float] = field(default_factory=list)
    token_log_dev_vals: List[float] = field(default_factory=list)
    lens: List[int] = field(default_factory=list)
    questions: set = field(default_factory=set)
    models: set = field(default_factory=set)
    official_baseline_vendors: set = field(default_factory=set)
    t_first: Optional[datetime] = None
    t_last: Optional[datetime] = None

    def add(self, r: RunRow):
        self.n_total += 1
        if r.skipped:
            self.n_skipped += 1
        else:
            has_any_metric = (r.length is not None and r.length > 0)
            if has_any_metric:
                self.n_valid += 1
                abs_z = r.abs_Z
                if abs_z is not None:
                    self.abs_Z_vals.append(abs_z)
                if r.token_log_dev is not None:
                    self.token_log_dev_vals.append(r.token_log_dev)
                if r.length is not None and r.length > 0:
                    self.lens.append(r.length)
            else:
                self.n_errors += 1
        if r.question_slug:
            self.questions.add(r.question_slug)
        if r.model_canonical:
            self.models.add(r.model_canonical)
        elif r.model:
            self.models.add(_canonical_model(r.model))
        if r.official_baseline_vendor:
            self.official_baseline_vendors.add(r.official_baseline_vendor)
        if r.timestamp_utc:
            if not self.t_first or r.timestamp_utc < self.t_first:
                self.t_first = r.timestamp_utc
            if not self.t_last or r.timestamp_utc > self.t_last:
                self.t_last = r.timestamp_utc

    def to_row(self) -> Dict[str, Any]:
        def _avg(xs):
            return round(mean(xs), 6) if xs else None
        def _med(xs):
            return round(median(xs), 6) if xs else None
        model = ""
        if len(self.models) == 1:
            model = next(iter(self.models))
        elif len(self.models) > 1:
            model = "mixed"
        baseline_hint = ""
        if len(self.official_baseline_vendors) == 1:
            baseline_hint = next(iter(self.official_baseline_vendors))
        out = {
            "vendor": self.vendor,
            "model": model,
            "official_baseline_vendor_hint": baseline_hint,
            "n_total": self.n_total,
            "n_valid": self.n_valid,
            "n_skipped": self.n_skipped,
            "n_errors": self.n_errors,
            "mean_abs_Z": _avg(self.abs_Z_vals),
            "median_abs_Z": _med(self.abs_Z_vals),
            "mean_token_log_dev": _avg(self.token_log_dev_vals),
            "mean_len": _avg(self.lens),
            "q_coverage": len(self.questions),
            "first_seen": self.t_first.isoformat() if self.t_first else "",
            "last_seen": self.t_last.isoformat() if self.t_last else "",
        }
        return out


# --------------------------- 主流程 ---------------------------

SORTABLE_FIELDS = {
    "mean_abs_Z": (False, float),
    "median_abs_Z": (False, float),
    "n_valid": (True, int),
    "n_total": (True, int),
}


def _is_self_vendor_name(vendor: str) -> bool:
    v = str(vendor or "").lower()
    if not v:
        return False
    if "official-baseline" in v:
        return True
    if v.endswith("-self") or v.endswith("_self") or v.endswith("self"):
        return True
    return "-self-" in v or "_self_" in v


def _self_priority(row: Dict[str, Any]) -> int:
    vendor = str(row.get("vendor") or "")
    hint = str(row.get("official_baseline_vendor_hint") or "")
    if hint and vendor == hint:
        return 0
    v = vendor.lower()
    if "official-baseline" in v:
        return 1
    if _is_self_vendor_name(vendor):
        return 2
    return 99


def _delta(a: Any, b: Any) -> Optional[float]:
    av = _to_float(a)
    bv = _to_float(b)
    if av is None or bv is None:
        return None
    return round(av - bv, 6)


def _attach_self_stats(agg_rows: List[Dict[str, Any]]) -> None:
    self_baseline_by_model: Dict[str, Dict[str, Any]] = {}

    for row in agg_rows:
        model = str(row.get("model") or "").strip()
        if not model or model == "mixed":
            continue
        priority = _self_priority(row)
        if priority >= 99:
            continue
        mean_abs_z = _to_float(row.get("mean_abs_Z"))
        n_valid = int(row.get("n_valid") or 0)
        key = (
            priority,
            1 if mean_abs_z is None else 0,
            mean_abs_z if mean_abs_z is not None else 0.0,
            -n_valid,
            str(row.get("vendor") or ""),
        )
        best = self_baseline_by_model.get(model)
        if best is None or key < best["key"]:
            self_baseline_by_model[model] = {"key": key, "row": row}

    for row in agg_rows:
        model = str(row.get("model") or "").strip()
        baseline = self_baseline_by_model.get(model, {}).get("row") if model else None
        if not baseline:
            row["self_vendor"] = ""
            row["is_self_vendor"] = False
            row["self_mean_abs_Z"] = None
            row["self_mean_token_log_dev"] = None
            row["delta_abs_Z_vs_self"] = None
            row["delta_token_log_dev_vs_self"] = None
            continue

        row["self_vendor"] = baseline.get("vendor", "")
        row["is_self_vendor"] = (row.get("vendor") == baseline.get("vendor"))
        row["self_mean_abs_Z"] = baseline.get("mean_abs_Z")
        row["self_mean_token_log_dev"] = baseline.get("mean_token_log_dev")
        row["delta_abs_Z_vs_self"] = _delta(row.get("mean_abs_Z"), baseline.get("mean_abs_Z"))
        row["delta_token_log_dev_vs_self"] = _delta(
            row.get("mean_token_log_dev"),
            baseline.get("mean_token_log_dev"),
        )


def _collect_files(paths: List[str], patterns: List[str]) -> List[str]:
    files: List[str] = []
    if paths:
        files.extend(paths)
    else:
        for pat in patterns:
            files.extend(glob.glob(pat))
    files = sorted(set(files))
    return files


def _write_csv(rows: List[Dict[str, Any]], out_path: str):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    field_order = [
        "vendor", "model", "is_self_vendor", "self_vendor",
        "n_total", "n_valid", "n_skipped", "n_errors",
        "mean_abs_Z", "median_abs_Z", "mean_token_log_dev", "mean_len",
        "self_mean_abs_Z", "delta_abs_Z_vs_self",
        "self_mean_token_log_dev", "delta_token_log_dev_vs_self",
        "q_coverage", "first_seen", "last_seen",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_order)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in field_order})


def _write_long_csv(run_rows: List[RunRow], out_path: str):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    field_order = [
        "filename", "timestamp_utc", "question_slug", "question", "run_index", "vendor", "model", "model_canonical",
        "official_baseline_vendor",
        "skipped", "reason", "error", "length", "abs_Z", "token_log_dev",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=field_order)
        w.writeheader()
        for r in run_rows:
            w.writerow({
                "filename": r.filename,
                "timestamp_utc": r.timestamp_utc.isoformat() if r.timestamp_utc else "",
                "question_slug": r.question_slug,
                "question": r.question,
                "run_index": r.run_index,
                "vendor": r.vendor,
                "model": r.model,
                "model_canonical": r.model_canonical,
                "official_baseline_vendor": r.official_baseline_vendor,
                "skipped": r.skipped,
                "reason": r.reason,
                "error": r.error,
                "length": r.length if r.length is not None else "",
                "abs_Z": r.abs_Z if r.abs_Z is not None else "",
                "token_log_dev": r.token_log_dev if r.token_log_dev is not None else "",
            })


def summarize(inputs: Optional[List[str]] = None,
              patterns: Optional[List[str]] = None,
              sort_by: Optional[str] = None,
              desc: Optional[bool] = None) -> tuple[List[Dict[str, Any]], List[RunRow], List[str]]:
    """解析运行结果并返回 (供应商聚合, 运行明细, 文件列表)。"""
    chosen_paths = inputs if (inputs is not None and len(inputs) > 0) else INPUT_PATHS
    patterns = patterns if patterns is not None else INPUT_PATTERNS
    files = _collect_files(chosen_paths, patterns)
    if not files:
        print("[error] 没有找到匹配的 JSON 文件。请检查输入配置。")
        return ([], [], [])

    run_rows = list(_iter_run_rows(files))
    if not run_rows:
        print("[error] 没有解析到任何有效的运行记录。")
        return ([], [], files)

    agg_map: Dict[str, VendorAgg] = {}
    for r in run_rows:
        agg_map.setdefault(r.vendor, VendorAgg(vendor=r.vendor)).add(r)
    agg_rows = [va.to_row() for va in agg_map.values()]
    _attach_self_stats(agg_rows)

    sort_key = (sort_by or SORT_BY)
    if sort_key not in SORTABLE_FIELDS:
        print(f"[warn] 不支持的排序字段 {sort_key}，将使用 mean_abs_Z")
        sort_key = "mean_abs_Z"
    _is_higher_better, caster = SORTABLE_FIELDS[sort_key]
    descending = (desc if desc is not None else DESCENDING)

    def _key(r: Dict[str, Any]):
        v = r.get(sort_key)
        is_null = (v is None or v == "")
        try:
            num = caster(v) if not is_null else 0
        except Exception:
            num = 0
        if descending:
            num = -num
        return (is_null, num)

    agg_rows.sort(key=_key)
    return (agg_rows, run_rows, files)


def export_reports(agg_rows: List[Dict[str, Any]],
                   run_rows: List[RunRow],
                   *,
                   csv_path: str,
                   long_csv_path: Optional[str] = None,
                   json_path: Optional[str] = None) -> None:
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    _write_csv(agg_rows, csv_path)
    print(f"[ok] 供应商排名 CSV 已生成：{csv_path} (共 {len(agg_rows)} 家供应商)")

    if long_csv_path:
        Path(long_csv_path).parent.mkdir(parents=True, exist_ok=True)
        _write_long_csv(run_rows, long_csv_path)
        print(f"[ok] 明细 CSV 已生成：{long_csv_path} (共 {len(run_rows)} 条记录)")

    if json_path:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(agg_rows, fh, ensure_ascii=False, indent=2)
        print(f"[ok] JSON 摘要已生成：{json_path}")


def run(inputs: Optional[List[str]] = None,
        out: Optional[str] = None,
        long_out: Optional[str] = None,
        sort_by: Optional[str] = None,
        desc: Optional[bool] = None) -> int:
    """编程式入口。返回 0 表示成功，非零表示失败。"""
    agg_rows, run_rows, _ = summarize(inputs=inputs, patterns=None, sort_by=sort_by, desc=desc)
    if not agg_rows and not run_rows:
        return 2

    out_path = out or OUTPUT_RANK_CSV
    long_target = OUTPUT_LONG_CSV if long_out is None else long_out
    export_reports(
        agg_rows,
        run_rows,
        csv_path=out_path,
        long_csv_path=long_target,
    )

    print("\nTop 5:")
    for i, r in enumerate(agg_rows[:5], 1):
        print(
            f"{i:>2}. {r['vendor']:<18} mean_abs_Z={r.get('mean_abs_Z')} "
            f"token_log_dev={r.get('mean_token_log_dev')} n_valid={r.get('n_valid')}"
        )

    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
