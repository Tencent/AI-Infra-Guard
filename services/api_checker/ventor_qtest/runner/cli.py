"""Command line interface for orchestrating tests and generating reports."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

from .openrouter import (
    build_openrouter_vendors,
    extract_provider_tags,
    fetch_model_endpoints,
)
from .questions import build_questions
from .. import summary as summary_module

try:  # Optional YAML support
    import yaml  # type: ignore
except Exception:  # pragma: no cover - PyYAML may be unavailable
    yaml = None

# 在模块导入时即加载 .env（在项目根目录自动查找）
load_dotenv()


DEFAULT_QUESTIONS = build_questions()
DEFAULT_OPENROUTER_MODEL = "moonshotai/kimi-k2.5"
DEFAULT_TESTER_PROVIDER = "moonshotai"
DEFAULT_TESTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
API_CHECKER_DATA_DIR = Path(os.environ.get(
    "AIG_API_CHECKER_DATA_DIR",
    Path(__file__).resolve().parents[2] / "runtime",
))
QTEST_DATA_DIR = API_CHECKER_DATA_DIR / "qtest"


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8") as fh:
        if suffix in {".yml", ".yaml"}:
            if yaml is None:
                raise RuntimeError("需要 PyYAML 才能读取 YAML 配置文件。")
            raw = yaml.safe_load(fh)
        else:
            raw = json.load(fh)
    return _expand_env_vars(raw)


# ─── 环境变量替换 ───
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env_vars(obj: Any) -> Any:
    """递归替换配置值中的 ``${VAR}`` 占位符为对应的环境变量值。

    - 如果整个字符串就是一个 ``${VAR}``，替换为该环境变量的值。
    - 如果字符串中包含多个 ``${VAR}``，逐个替换。
    - 如果环境变量不存在，保留原始占位符并打印警告。
    """
    if isinstance(obj, str):
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None and var_name == "AIG_API_CHECKER_DATA_DIR":
                value = str(API_CHECKER_DATA_DIR)
            if value is None:
                print(f"[warn] 环境变量 {var_name} 未设置，保留占位符 ${{{var_name}}}")
                return match.group(0)
            return value
        return _ENV_VAR_PATTERN.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    return obj


def _save_config(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        if yaml is None:
            raise RuntimeError("需要 PyYAML 才能写入 YAML 配置文件。")
        content = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    else:
        content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(path, 0o600)


def _suite_for_dump(suite_conf: Dict[str, Any], distinct_tester_key: bool) -> Dict[str, Any]:
    """Return a reusable config without serializing live API keys."""
    sanitized = copy.deepcopy(suite_conf)
    tester = sanitized.get("tester")
    if isinstance(tester, dict) and "api_key" in tester:
        tester["api_key"] = (
            "${QTEST_TESTER_API_KEY}"
            if distinct_tester_key
            else "${OPENROUTER_API_KEY}"
        )
    for vendor in sanitized.get("vendors", []):
        if isinstance(vendor, dict) and "api_key" in vendor:
            vendor["api_key"] = "${OPENROUTER_API_KEY}"
    return sanitized


def _summarize_reports(report_conf: Dict[str, Any]) -> Tuple[int, int]:
    inputs = report_conf.get("inputs")
    patterns = report_conf.get("patterns") or report_conf.get("input_patterns")
    sort_by = report_conf.get("sort_by")
    descending = report_conf.get("descending")

    agg_rows, run_rows, _ = summary_module.summarize(
        inputs=inputs,
        patterns=patterns,
        sort_by=sort_by,
        desc=descending,
    )
    if not agg_rows and not run_rows:
        return (0, 0)

    csv_path = report_conf.get("output_rank_csv") or summary_module.OUTPUT_RANK_CSV
    long_csv_path = report_conf.get("output_long_csv", summary_module.OUTPUT_LONG_CSV)
    json_path = report_conf.get("output_json")

    summary_module.export_reports(
        agg_rows,
        run_rows,
        csv_path=csv_path,
        long_csv_path=long_csv_path,
        json_path=json_path,
    )
    return (len(agg_rows), len(run_rows))


def _split_csv(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _slugify(text: str, max_len: int = 60) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "-", str(text or "").strip().lower()).strip("-")
    if not cleaned:
        return "suite"
    if len(cleaned) > max_len:
        return cleaned[:max_len].rstrip("-")
    return cleaned


def _fmt_num(value: Any, digits: int = 2) -> str:
    try:
        number = float(value)
    except Exception:
        return "-"
    return f"{number:.{digits}f}"


def _fmt_percent(value: Any) -> str:
    try:
        number = float(value)
    except Exception:
        return "-"
    return f"{number:.1f}%"


def _build_openrouter_suite(args: argparse.Namespace) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
    openrouter_key = str(args.openrouter_api_key or "").strip() or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not openrouter_key:
        raise RuntimeError("缺少 OpenRouter API Key，请通过 --openrouter-api-key 或环境变量 OPENROUTER_API_KEY 提供。")

    openrouter_model = str(args.openrouter_model or "").strip() or DEFAULT_OPENROUTER_MODEL
    endpoints = fetch_model_endpoints(
        openrouter_model,
        api_key=openrouter_key,
        timeout=float(args.timeout_sec),
    )
    all_tags = extract_provider_tags(endpoints)
    all_tag_set = set(all_tags)

    include_tags = _split_csv(args.include_tags)
    exclude_tags = set(_split_csv(args.exclude_tags))

    if include_tags:
        missing = [tag for tag in include_tags if tag not in all_tag_set]
        if missing:
            print(f"[warn] include_tags 中有 {len(missing)} 个 tag 未命中: {', '.join(missing)}")
        selected_tags = [tag for tag in all_tags if tag in set(include_tags)]
    else:
        selected_tags = list(all_tags)

    if exclude_tags:
        selected_tags = [tag for tag in selected_tags if tag not in exclude_tags]

    if int(args.provider_limit) > 0:
        selected_tags = selected_tags[: int(args.provider_limit)]

    if not selected_tags:
        raise RuntimeError("筛选后没有可用 provider tag。")

    vendors = build_openrouter_vendors(
        api_key=openrouter_key,
        model=openrouter_model,
        provider_tags=selected_tags,
        name_prefix=args.vendor_name_prefix,
    )

    suite_name = str(args.suite_name or "").strip() or f"openrouter-auto-{_slugify(openrouter_model, max_len=48)}"
    tester_api_key = str(args.tester_api_key or "").strip() or openrouter_key
    tester_model = str(args.tester_model or "").strip() or openrouter_model
    tester_provider = str(args.tester_provider or "").strip()

    tester_conf: Dict[str, Any] = {
        "api_key": tester_api_key,
        "base_url": str(args.tester_base_url or "").strip() or DEFAULT_TESTER_BASE_URL,
        "model": tester_model,
        "temperature": float(args.temperature),
        "top_logprobs": int(args.top_logprobs),
        "max_workers": int(args.tester_max_workers),
        "request_delay": float(args.tester_request_delay),
        "timeout_sec": float(args.timeout_sec),
    }
    if tester_provider and tester_provider.lower() not in {"none", "null", "off"}:
        tester_conf["provider"] = {"order": [tester_provider], "allow_fallbacks": False}

    questions = list(args.question or []) or list(DEFAULT_QUESTIONS)

    suite_conf: Dict[str, Any] = {
        "name": suite_name,
        "result_dir": args.result_dir,
        "questions": questions,
        "runs_per_question": max(1, int(args.runs_per_question)),
        "digits": max(1, int(args.digits)),
        "temperature": float(args.temperature),
        "top_logprobs": max(1, int(args.top_logprobs)),
        "vendor_max_workers": max(1, int(args.vendor_max_workers)),
        "tester": tester_conf,
        "vendors": vendors,
        "payload": {
            "suite_name": suite_name,
            "openrouter_model": openrouter_model,
            "openrouter_provider_tags": selected_tags,
            "openrouter_provider_count": len(selected_tags),
            "openrouter_discovered_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }
    return suite_conf, endpoints, selected_tags


def _handle_openrouter_providers(args: argparse.Namespace) -> int:
    api_key = str(args.api_key or "").strip() or os.environ.get("OPENROUTER_API_KEY", "").strip() or None
    endpoints = fetch_model_endpoints(
        str(args.model or "").strip() or DEFAULT_OPENROUTER_MODEL,
        api_key=api_key,
        timeout=float(args.timeout),
    )
    if args.json:
        print(json.dumps(endpoints, ensure_ascii=False, indent=2))
        return 0

    model = str(args.model or "").strip() or DEFAULT_OPENROUTER_MODEL
    print(f"[ok] {model} 可用 provider: {len(endpoints)}")
    for idx, endpoint in enumerate(endpoints, start=1):
        print(
            f"{idx:>2}. {str(endpoint.get('provider_name') or '-'):12} "
            f"tag={str(endpoint.get('tag') or '-'):20} "
            f"quant={str(endpoint.get('quantization') or '-'):8} "
            f"uptime={_fmt_percent(endpoint.get('uptime_last_30m')):>7} "
            f"latency={_fmt_num(endpoint.get('latency_last_30m')):>6}s "
            f"tps={_fmt_num(endpoint.get('throughput_last_30m')):>6}"
        )
    return 0


def _handle_openrouter_run(args: argparse.Namespace) -> int:
    suite_conf, endpoints, selected_tags = _build_openrouter_suite(args)
    openrouter_model = str(args.openrouter_model or "").strip() or DEFAULT_OPENROUTER_MODEL

    print(f"[ok] 已发现 {len(endpoints)} 个 endpoint，已选择 {len(selected_tags)} 个 provider：")
    endpoint_map = {str(item.get("tag")): item for item in endpoints}
    for idx, tag in enumerate(selected_tags, start=1):
        endpoint = endpoint_map.get(tag, {})
        provider_name = str(endpoint.get("provider_name") or "-")
        print(f"{idx:>2}. {provider_name:12} tag={tag}")

    report_conf: Dict[str, Any] = {
        "patterns": [str(Path(args.result_dir) / "*.json")],
        "sort_by": args.sort_by,
        "descending": bool(args.descending),
    }

    model_slug = _slugify(openrouter_model, max_len=48)
    summary_dir = Path(args.summary_dir)
    summary_dir.mkdir(parents=True, exist_ok=True)

    rank_csv = args.output_rank_csv or str(summary_dir / f"{model_slug}_vendors_rank.csv")
    long_csv = args.output_long_csv or str(summary_dir / f"{model_slug}_runs_long.csv")
    json_output = args.output_json or str(summary_dir / f"{model_slug}_vendors_rank.json")
    report_conf["output_rank_csv"] = rank_csv
    report_conf["output_long_csv"] = long_csv
    report_conf["output_json"] = json_output

    if args.dump_config:
        payload = {
            "tests": [
                _suite_for_dump(
                    suite_conf,
                    distinct_tester_key=bool(str(args.tester_api_key or "").strip()),
                ),
            ],
            "report": report_conf,
        }
        dump_path = Path(args.dump_config)
        _save_config(dump_path, payload)
        print(f"[ok] 自动生成配置已写入: {dump_path}")

    if args.dry_run:
        print("[ok] dry-run 模式，未执行测试。")
        return 0

    from .orchestrator import run_tests

    run_tests(suite_conf)
    if args.no_summary:
        return 0

    agg_count, run_count = _summarize_reports(report_conf)
    print(f"\n[ok] 汇总已完成：{agg_count} 家供应商，{run_count} 条运行记录。")
    print(f"[ok] 排名输出: {rank_csv}")
    print(f"[ok] 明细输出: {long_csv}")
    print(f"[ok] JSON 输出: {json_output}")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ventor QTest runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="执行配置文件中的测试并生成报告")
    run_parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[1] / "config" / "default.yaml"),
        help="配置文件路径（支持 JSON/YAML）",
    )

    providers_parser = subparsers.add_parser(
        "openrouter-providers",
        help="从 OpenRouter 自动获取模型的 provider 列表",
    )
    providers_parser.add_argument(
        "--model",
        default=DEFAULT_OPENROUTER_MODEL,
        help=f"模型 ID（默认: {DEFAULT_OPENROUTER_MODEL}）",
    )
    providers_parser.add_argument(
        "--api-key",
        default="",
        help="OpenRouter API Key（可选，默认读取 OPENROUTER_API_KEY）",
    )
    providers_parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="请求超时秒数（默认 30）",
    )
    providers_parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 打印完整 endpoints 数据",
    )

    openrouter_run_parser = subparsers.add_parser(
        "openrouter-run",
        help="输入 API Key 后自动发现 provider，并一键执行测试",
    )
    openrouter_run_parser.add_argument(
        "--openrouter-model",
        default=DEFAULT_OPENROUTER_MODEL,
        help=f"OpenRouter 模型 ID（默认: {DEFAULT_OPENROUTER_MODEL}）",
    )
    openrouter_run_parser.add_argument(
        "--openrouter-api-key",
        default="",
        help="OpenRouter API Key（可用 OPENROUTER_API_KEY 替代）",
    )
    openrouter_run_parser.add_argument(
        "--include-tags",
        default="",
        help="仅保留这些 provider tag（逗号分隔）",
    )
    openrouter_run_parser.add_argument(
        "--exclude-tags",
        default="",
        help="排除这些 provider tag（逗号分隔）",
    )
    openrouter_run_parser.add_argument(
        "--provider-limit",
        type=int,
        default=0,
        help="最多选择前 N 个 provider（0 表示不限制）",
    )
    openrouter_run_parser.add_argument(
        "--vendor-name-prefix",
        default="or",
        help="自动生成 vendor 名称前缀（默认: or）",
    )
    openrouter_run_parser.add_argument(
        "--suite-name",
        default="",
        help="测试套件名称（默认自动生成）",
    )
    openrouter_run_parser.add_argument(
        "--question",
        action="append",
        default=[],
        help="测试问题，可重复传入；留空则使用内置默认问题集",
    )
    openrouter_run_parser.add_argument(
        "--runs-per-question",
        type=int,
        default=1,
        help="每个问题运行次数（默认 1）",
    )
    openrouter_run_parser.add_argument(
        "--digits",
        type=int,
        default=100,
        help="保留数字位数（默认 100）",
    )
    openrouter_run_parser.add_argument(
        "--temperature",
        type=float,
        default=0.6,
        help="生成温度（默认 0.6）",
    )
    openrouter_run_parser.add_argument(
        "--top-logprobs",
        type=int,
        default=20,
        help="top_logprobs（默认 20）",
    )
    openrouter_run_parser.add_argument(
        "--vendor-max-workers",
        type=int,
        default=2,
        help="供应商并发数（默认 2）",
    )
    openrouter_run_parser.add_argument(
        "--result-dir",
        default=str(QTEST_DATA_DIR / "result" / "openrouter_auto"),
        help="结果 JSON 输出目录（默认位于 AIG_API_CHECKER_DATA_DIR/qtest）",
    )
    openrouter_run_parser.add_argument(
        "--timeout-sec",
        type=float,
        default=45.0,
        help="请求超时秒数（默认 45）",
    )

    openrouter_run_parser.add_argument(
        "--tester-api-key",
        default="",
        help="参考分布 API Key（默认复用 OpenRouter key）",
    )
    openrouter_run_parser.add_argument(
        "--tester-base-url",
        default=DEFAULT_TESTER_BASE_URL,
        help=f"参考分布端点（默认: {DEFAULT_TESTER_BASE_URL}）",
    )
    openrouter_run_parser.add_argument(
        "--tester-model",
        default="",
        help="参考分布模型（默认复用 openrouter-model）",
    )
    openrouter_run_parser.add_argument(
        "--tester-provider",
        default=DEFAULT_TESTER_PROVIDER,
        help=f"参考分布 provider tag（默认: {DEFAULT_TESTER_PROVIDER}，设为 none 关闭）",
    )
    openrouter_run_parser.add_argument(
        "--tester-max-workers",
        type=int,
        default=2,
        help="参考分布并发数（默认 2）",
    )
    openrouter_run_parser.add_argument(
        "--tester-request-delay",
        type=float,
        default=0.3,
        help="参考分布请求间隔（默认 0.3）",
    )

    openrouter_run_parser.add_argument(
        "--summary-dir",
        default=str(QTEST_DATA_DIR / "result" / "summary_openrouter_auto"),
        help="汇总输出目录（默认位于 AIG_API_CHECKER_DATA_DIR/qtest）",
    )
    openrouter_run_parser.add_argument(
        "--output-rank-csv",
        default="",
        help="自定义排名 CSV 输出路径",
    )
    openrouter_run_parser.add_argument(
        "--output-long-csv",
        default="",
        help="自定义明细 CSV 输出路径",
    )
    openrouter_run_parser.add_argument(
        "--output-json",
        default="",
        help="自定义聚合 JSON 输出路径",
    )
    openrouter_run_parser.add_argument(
        "--sort-by",
        default="mean_abs_Z",
        help="汇总排序字段（默认 mean_abs_Z）",
    )
    openrouter_run_parser.add_argument(
        "--descending",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="汇总是否降序（默认 false，可用 --descending）",
    )
    openrouter_run_parser.add_argument(
        "--dump-config",
        default="",
        help="把自动生成配置写入 JSON/YAML 文件",
    )
    openrouter_run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只发现 provider 和生成配置，不执行测试",
    )
    openrouter_run_parser.add_argument(
        "--no-summary",
        action="store_true",
        help="测试完成后不做汇总",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        from .orchestrator import run_tests

        config_path = Path(args.config)
        config = _load_config(config_path)
        tests_config = config.get("tests", config)
        run_tests(tests_config)

        report_conf = config.get("report")
        if report_conf:
            agg_count, run_count = _summarize_reports(report_conf)
            print(f"\n[ok] 汇总已完成：{agg_count} 家供应商，{run_count} 条运行记录。")
        return 0

    if args.command == "openrouter-providers":
        return _handle_openrouter_providers(args)

    if args.command == "openrouter-run":
        return _handle_openrouter_run(args)

    parser.error("未知命令")
    return 2


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
