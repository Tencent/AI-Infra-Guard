"""
算法 A：随机数指纹
==================
让 AI 模型"随机选数字 1-355"，通过分布指纹区分不同模型。

评分引擎：
- 模型识别用 Dirichlet-multinomial 后验预测似然（bayes_score）
- 造假检测用已知替身 Bayes factor + 开放世界 G² 异常统计
- 旧的余弦/JS/众数仅作解释展示，不参与判定
"""
from .common import (
    collect_samples, calculate_stats, match_baselines,
    build_baseline, append_baseline, load_baselines,
    MIN_SAMPLES,
)
from .bayes_score import evaluate as bayes_evaluate


def calibrate(api_type, base_url, api_key, model, name,
              iterations=200, concurrency=5, on_progress=None, no_think=False,
              cancel_event=None):
    """标定官方模型基准"""
    results, errors = collect_samples(
        api_type, base_url, api_key, model,
        iterations=iterations, concurrency=concurrency, on_progress=on_progress,
        no_think=no_think, cancel_event=cancel_event,
    )
    if len(results) < MIN_SAMPLES:
        return {"error": f"样本不足({len(results)}/{MIN_SAMPLES})", "results": results, "errors": errors}
    baseline = build_baseline(name, model, api_type, results, no_think=no_think)
    append_baseline(baseline)
    return {"baseline": baseline, "results": results, "errors": errors}


def test_model(api_type, base_url, api_key, model,
               iterations=200, concurrency=5, on_progress=None, no_think=False,
               claimed_name=None, cancel_event=None):
    """测试第三方 API。

    claimed_name: 声称的模型名（基准库中的 name 字段）。若提供，
                  则额外执行四状态造假判定；否则只做模型识别。
    """
    baselines = load_baselines()
    if not baselines:
        return {"error": "没有可用基准，请先标定"}
    results, errors = collect_samples(
        api_type, base_url, api_key, model,
        iterations=iterations, concurrency=concurrency, on_progress=on_progress,
        no_think=no_think, cancel_event=cancel_event,
    )
    if len(results) < MIN_SAMPLES:
        return {"error": f"样本不足({len(results)}/{MIN_SAMPLES})", "results": results, "errors": errors}

    # 旧的 matches 接口（兼容，按后验概率排序 + 旧解释指标）
    matches = match_baselines(results, baselines)

    # 新的完整贝叶斯评估
    bayes_result = bayes_evaluate(results, baselines, claimed_name=claimed_name)

    return {
        "matches": matches,
        "bayes": bayes_result,
        "results": results,
        "errors": errors,
    }
