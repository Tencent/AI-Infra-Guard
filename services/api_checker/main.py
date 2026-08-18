#!/usr/bin/env python3
"""
aig_api_checker — AI 模型指纹识别 + 中转站检测工具

5 个算法：
  A. 随机数指纹      — 让模型随机选数字1-355，统计分布区分模型
  B. 加密级Signature — Claude thinking signature AEAD验证（Anthropic专用）
  C. 黑盒审计8探针   — 中转站篡改检测（OpenAI兼容通用）
  D. PAMELA分布指纹  — 单token回答分布 JSD 匹配已发布指纹库（OpenAI兼容通用）
  E. Ventor QTest     — 基于 logprobs 与信息熵的供应商一致性量化检验

用法:
    python main.py              # 交互式菜单
    python main.py calibrate    # 算法A: 标定官方模型基准
    python main.py test         # 算法A: 测试第三方API
    python main.py detect       # 算法B: 中转站加密级检测
    python main.py audit        # 算法C: 中转站黑盒审计
    python main.py pamela       # 算法D: PAMELA 单token分布指纹匹配
    python main.py qtest ...    # 算法E: Ventor QTest（参数同原项目 CLI）
    python main.py list         # 查看已保存基准
"""

import sys

if __package__:
    from .algorithms.fingerprint import calibrate, test_model
    from .algorithms.signature import run_all_checks
    from .algorithms.relay_audit import run_relay_audit, PROBE_NAMES
    from .algorithms.pamela import match_model, STUDY_A_TASKS, ALL_LANGS, DEFAULT_REFERENCE
    from .algorithms.common import (
        load_baselines,
        resolve_baseline_name,
        DEFAULT_BASELINES_PATH,
    )
else:
    from algorithms.fingerprint import calibrate, test_model
    from algorithms.signature import run_all_checks
    from algorithms.relay_audit import run_relay_audit, PROBE_NAMES
    from algorithms.pamela import match_model, STUDY_A_TASKS, ALL_LANGS, DEFAULT_REFERENCE
    from algorithms.common import (
        load_baselines,
        resolve_baseline_name,
        DEFAULT_BASELINES_PATH,
    )

API_TYPES = ["openai", "openai-responses", "anthropic"]


def _input(prompt, default=""):
    val = input(prompt).strip()
    return val if val else default

def _input_int(prompt, default, lo=None, hi=None):
    try:
        val = int(_input(prompt, str(default)))
    except ValueError:
        val = default
    if lo is not None: val = max(lo, val)
    if hi is not None: val = min(hi, val)
    return val

def _input_api_type():
    print("\nAPI 类型:")
    for i, t in enumerate(API_TYPES, 1):
        print(f"  {i}) {t}")
    return API_TYPES[_input_int("选择 [1]: ", 1, 1, len(API_TYPES)) - 1]

def _progress():
    def fn(c, t, s, e):
        if c % 10 == 0 or c == t:
            print(f"\r  进度: {c}/{t} 成功:{s} 失败:{e}", end="")
    return fn


def _baseline_name_for_model(baselines, model):
    return resolve_baseline_name(model, baselines)


# ================================================================
#  算法 A：标定
# ================================================================
def calibrate_flow():
    print("\n=== 算法A: 标定官方模型基准 ===")
    api_type = _input_api_type()
    base_url = _input("Base URL: ")
    api_key  = _input("API Key: ")
    model    = _input("模型名称: ")
    name     = _input("基准名称: ", default=model)
    iters    = _input_int("采样次数 [200]: ", 200, 50, 500)
    conc     = _input_int("并发数 [5]: ", 5, 1, 50)
    no_think = _input("关闭推理模型思考? [Y/n]: ", "y").lower() != "n"
    if not (base_url and api_key and model):
        print("错误：必填项为空"); return

    print(f"\n采样 {iters} 次 (no_think={no_think})...")
    result = calibrate(api_type, base_url, api_key, model, name, iters, conc, _progress(), no_think)
    print()
    if "error" in result:
        print(f"失败: {result['error']}"); return
    s = result["baseline"]["stats"]
    print(f"标定完成: {name}")
    print(f"  众数={s['mode']}({s['modeCount']}次) 均值={s['mean']:.2f} 标准差={s['stdDev']:.2f} 唯一值={s['unique']}")


# ================================================================
#  算法 A：测试
# ================================================================
def test_flow():
    print("\n=== 算法A: 测试第三方API (贝叶斯模型识别 + 造假判定) ===")
    if not load_baselines():
        print(f"没有基准，请先标定 ({DEFAULT_BASELINES_PATH})"); return

    baselines = load_baselines()
    print("\n可用基准:")
    for i, b in enumerate(baselines, 1):
        print(f"  {i}. {b.get('name','?')}")

    api_type = _input_api_type()
    base_url = _input("Base URL: ")
    api_key  = _input("API Key: ")
    model    = _input("模型名称: ")
    iters    = _input_int("采样次数 [200]: ", 200, 50, 500)
    conc     = _input_int("并发数 [5]: ", 5, 1, 50)
    no_think = _input("关闭推理模型思考? [Y/n]: ", "y").lower() != "n"
    baseline_name = _baseline_name_for_model(baselines, model)
    if not (base_url and api_key and model):
        print("错误：必填项为空"); return

    print(f"\n采样 {iters} 次 (no_think={no_think})...")
    result = test_model(api_type, base_url, api_key, model, iters, conc, _progress(), no_think,
                        baseline_name)
    print()
    if "error" in result:
        print(f"失败: {result['error']}"); return

    # 旧的解释性指标
    ts = result["matches"][0]["testStats"]
    print(f"样本统计: 众数={ts['mode']} 均值={ts['mean']:.2f} 标准差={ts['stdDev']:.2f}\n")

    # 贝叶斯评估结果
    bayes = result.get("bayes", {})
    if "error" not in bayes:
        print("=" * 60)
        print("模型识别（后验预测似然）")
        print("=" * 60)
        print(f"  最可能: {bayes.get('best_model_name','?')}  "
              f"(后验={bayes.get('best_posterior',0)*100:.1f}%)")
        print(f"  次可能: {bayes.get('second_model_name','?')}")
        print(f"  log margin: {bayes.get('log_margin',0):.2f}  "
              f"证据: {bayes.get('evidence_level','?')}")

        print(f"\n  Top 5:")
        print(f"  {'#':<3} {'模型':<22} {'后验':<10} {'log似然':<10}")
        print("  " + "-" * 55)
        for i, t in enumerate(bayes.get("top5", []), 1):
            print(f"  {i:<3} {t['name']:<22} {t['posterior']*100:>7.2f}%  {t['log_predictive']:>8.2f}")

        forgery = bayes.get("forgery")
        if forgery:
            print(f"\n{'='*60}")
            print("造假判定（四状态）")
            print(f"{'='*60}")
            print(f"  声称模型: {forgery.get('claimed_model_name','?')}")
            print(f"  判定: {forgery.get('status_cn', forgery.get('status','?'))}")
            print(f"  最匹配: {forgery.get('best_model_name','?')}")
            print(f"  已知替身 log BF: {forgery.get('known_alt_log_bf',0):.2f}  "
                  f"(阈值: ≤{forgery.get('tau_accept',0):.2f} 支持 / "
                  f"≥{forgery.get('tau_reject',0):.2f} 嫌疑)")
            print(f"  G² 异常统计: {forgery.get('g2',0):.2f}  "
                  f"(阈值: {forgery.get('g2_threshold',0):.2f})")

    print(f"\n{'='*60}")
    print("解释性指标（仅参考，不参与判定）")
    print(f"{'='*60}")
    print(f"{'#':<3} {'基准':<22} {'后验':<10} {'余弦':<10} {'JS散度':<8}")
    print("-" * 60)
    for i, m in enumerate(result["matches"][:5], 1):
        s = m["similarity"]
        print(f"{i:<3} {m['name']:<20} {m['score']*100:>7.2f}%  "
              f"{s['cosineSimilarity']*100:>7.2f}%  {s['jsDivergence']:.4f}")


# ================================================================
#  算法 B：加密级 Signature 检测
# ================================================================
def detect_flow():
    print("\n=== 算法B: 中转站加密级检测 (thinking signature + 10项) ===")
    print("  原理: signature是Anthropic服务端AEAD加密,中转站无法伪造\n")
    base_url = _input("Base URL (如 https://api.anthropic.com): ")
    api_key  = _input("API Key: ")
    model    = _input("模型名称 (如 claude-sonnet-4-5-20250514): ")
    if not (base_url and api_key and model):
        print("错误：必填项为空"); return
    skip_fp  = _input("跳过随机数指纹? [y/N]: ", "n").lower() == "y"
    skip_lat = _input("跳过延迟检测? [y/N]: ", "n").lower() == "y"

    print("\n检测中（1-2分钟）...\n")
    result = run_all_checks(base_url, api_key, model, skip_fp, skip_lat)
    print(f"\n结果: {result['summary']}")
    print(f"\n{'#':<4} {'检测项':<24} {'结果':<6} {'详情'}")
    print("-" * 80)
    for i, c in enumerate(result["checks"], 1):
        tag = "*" if c.critical else " "
        print(f" {tag}{i:<2} {c.name:<22} {'PASS' if c.passed else 'FAIL':<6} {c.detail[:50]}")
    passed = sum(1 for c in result["checks"] if c.passed)
    print(f"\n通过: {passed}/{len(result['checks'])}  评分: {result['score']:.0f}/100")
    v_map = {"native": "原生透传", "suspect": "存在可疑", "proxy": "疑似替身"}
    print(f"结论: {v_map[result['verdict']]}")


# ================================================================
#  算法 C：黑盒审计 8 探针
# ================================================================
def audit_flow():
    print("\n=== 算法C: 中转站黑盒审计 (8探针) ===")
    base_url = _input("中转 base URL (如 https://relay.example.com/v1): ")
    api_key  = _input("API Key: ")
    model    = _input("模型名称: ")
    if not (base_url and api_key and model):
        print("错误：必填项为空"); return

    print("\n审计中 (full 8探针)...\n")
    result = run_relay_audit(base_url, api_key, model, "full")
    print(f"风险等级: {result['verdict']}  分数: {result['score']}/100\n")

    if result["findings"]:
        print("风险发现:")
        for i, f in enumerate(result["findings"], 1):
            print(f"  {i}. [{f.severity}] {f.title} (+{f.score})")
            print(f"     建议: {f.recommendation}")
    else:
        print("轻量探针未发现明显问题。")

    print("\n探针结果:")
    for r in result["probe_results"]:
        status = "PASS" if r.ok else "FAIL"
        lat = f" {r.latency_ms}ms" if r.latency_ms else ""
        print(f"  [{status}] {r.name} ({PROBE_NAMES.get(r.name, r.name)}){lat}")
    print("\n(结论是风险信号，不是安全认证)")


# ================================================================
#  算法 D：PAMELA 单 token 分布指纹
# ================================================================
def pamela_flow():
    print("\n=== 算法D: PAMELA 单token分布指纹 (JSD匹配已发布指纹库) ===")
    print(f"  探针: {len(STUDY_A_TASKS)} 个任务 x 多语言; 参考库: {DEFAULT_REFERENCE}")
    base_url = _input("Base URL (OpenAI兼容, 如 https://openrouter.ai/api/v1): ")
    api_key  = _input("API Key: ")
    model    = _input("模型名称: ")
    if not (base_url and api_key and model):
        print("错误：必填项为空"); return
    reps     = _input_int("每单元采样次数 [10]: ", 10, 5, 30)
    langs_in = _input(f"语言 (逗号分隔 {','.join(ALL_LANGS)}) [全部]: ", "")
    langs    = [s.strip() for s in langs_in.split(",") if s.strip() in ALL_LANGS] or None
    conc     = _input_int("并发数 [8]: ", 8, 1, 32)
    ref_in   = _input("参考指纹库路径 [默认]: ", "")
    n_cells  = len(STUDY_A_TASKS) * (len(langs) if langs else len(ALL_LANGS))
    print(f"\n采样 {model}: {n_cells} 单元 x {reps} 次 ≈ {n_cells * reps} 请求...")
    result = match_model(base_url, api_key, model, reps=reps, langs=langs,
                         concurrency=conc, reference_path=ref_in or None,
                         on_progress=_progress())
    print()
    if "error" in result:
        print(f"失败: {result['error']}"); return
    print(f"参考库: {result['reference_models']} 模型, {result['reference_cells']} 单元")
    print(f"候选: {result['candidate_cells']} 有效单元 -> {result['candidate_file']}")
    print(f"\nTop 5 最接近的参考指纹 (mean JSD, 越小越接近):")
    print(f"{'rank':>4}  {'mean_jsd':>9}  {'cells':>5}  model")
    for i, (m, score, n) in enumerate(result["ranked"][:5], 1):
        print(f"{i:>4}  {score:>9.4f}  {n:>5}  {m}")
    if result["ranked"]:
        best, bscore, _ = result["ranked"][0]
        print(f"\n最佳匹配: {best} (mean JSD {bscore:.4f})")
        if best != model:
            print(f"提示: 与声称模型 '{model}' 不一致，可能为替身/改名模型。")


# ================================================================
#  算法 E：Ventor QTest 供应商一致性检验
# ================================================================
def qtest_flow():
    print("\n=== 算法E: Ventor QTest 供应商一致性量化检验 ===")
    print("该功能使用独立配置运行，不会更改现有算法或基准数据。")
    print("命令示例:")
    print("  python main.py qtest run")
    print("  python main.py qtest run --config path/to/config.yaml")
    print("  python main.py qtest afl-run --config path/to/afl.yaml")
    print("  python main.py qtest openrouter-providers --model moonshotai/kimi-k2.5")
    print("  python main.py qtest openrouter-run --openrouter-model moonshotai/kimi-k2.5 ...")


def qtest_command(argv):
    """将 qtest 后的参数原样交给内置 Ventor CLI。"""
    if __package__:
        from .ventor_qtest.runner.cli import main as qtest_main
    else:
        from ventor_qtest.runner.cli import main as qtest_main

    if not argv:
        qtest_flow()
        return 0
    return qtest_main(argv)


# ================================================================
#  查看基准
# ================================================================
def list_flow():
    baselines = load_baselines()
    print(f"\n已保存基准 ({len(baselines)} 个)  路径: {DEFAULT_BASELINES_PATH}")
    if not baselines:
        print("  (空)"); return
    for i, b in enumerate(baselines, 1):
        s = b.get("stats", {})
        print(f"  {i}. {b.get('name','?'):<22} {b.get('model','?'):<16} 样本={b.get('iterations','?')} 众数={s.get('mode','?')} 均值={s.get('mean',0):.1f}")


# ================================================================
#  主入口
# ================================================================
def run_cli():
    print("=" * 60)
    print("  aig_api_checker — AI模型指纹识别 + 中转站检测")
    print("=" * 60)
    print("\n  [1] 标定官方模型基准      (算法A 随机数指纹)")
    print("  [2] 测试第三方API         (算法A 随机数指纹)")
    print("  [3] 中转站加密级检测      (算法B signature+10项)")
    print("  [4] 中转站黑盒审计        (算法C 8探针)")
    print("  [5] 查看已保存基准")
    print("  [6] PAMELA分布指纹匹配    (算法D 单token分布JSD)")
    print("  [7] Ventor供应商一致性检验 (算法E Z-test/logprobs)")
    print("  [q] 退出")
    while True:
        c = input("\n请选择: ").strip().lower()
        {"1": calibrate_flow, "2": test_flow, "3": detect_flow,
         "4": audit_flow, "5": list_flow, "6": pamela_flow,
         "7": qtest_flow}.get(c, lambda: print("无效"))()
        if c in ("q", "quit", "exit"):
            print("再见！"); break


def main():
    args = sys.argv[1:]
    if not args:
        run_cli()
    elif args[0] in ("calibrate", "cal"):
        calibrate_flow()
    elif args[0] in ("test", "check"):
        test_flow()
    elif args[0] in ("detect", "proxy"):
        detect_flow()
    elif args[0] in ("audit", "relay"):
        audit_flow()
    elif args[0] in ("pamela", "dist"):
        pamela_flow()
    elif args[0] in ("qtest", "ventor"):
        return qtest_command(args[1:])
    elif args[0] in ("list", "ls"):
        list_flow()
    elif args[0] in ("-h", "--help", "help"):
        print(__doc__)
    else:
        print(f"未知命令: {args[0]}\n{__doc__}")


if __name__ == "__main__":
    main()
