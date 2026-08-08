"""
贝叶斯模型识别与造假检测评分模块
================================

基于策略文档实现，替代旧的余弦+JS+众数启发式打分。

四个独立模块：
1. 基准分布估计  — Dirichlet 平滑
2. 候选模型排序  — 后验预测对数似然
3. 造假／异常判断 — 已知替身 Bayes factor + 未知异常 G² 统计量
4. 阈值与样本量校准 — Chernoff 信息 + 后验预测模拟

数学细节见项目文档；本模块只做数值实现。
"""
from __future__ import annotations

import math
import json
import os
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from scipy.special import gammaln, logsumexp
from scipy.optimize import minimize_scalar

K = 355  # 数字范围 1..K


# ================================================================
# 一、基准分布估计：Dirichlet 平滑
# ================================================================
def counts_from_raw(raw_data: list[int]) -> NDArray[np.float64]:
    """把原始采样序列转为长度 K 的计数向量。"""
    c = np.zeros(K, dtype=np.float64)
    for n in raw_data:
        if 1 <= n <= K:
            c[n - 1] += 1.0
    return c


def build_counts_matrix(baselines: list[dict]) -> tuple[NDArray[np.float64], list[str]]:
    """从 baselines.json 的 rawData 构造 M×K 计数矩阵。返回 (C, names)。"""
    if not baselines:
        return np.zeros((0, K), dtype=np.float64), []
    rows = []
    names = []
    for b in baselines:
        # 优先用 rawData；若缺失则从 distribution 重建
        if b.get("rawData"):
            rows.append(counts_from_raw(b["rawData"]))
        elif b.get("distribution"):
            n = b.get("iterations", 0)
            rows.append(np.array(b["distribution"], dtype=np.float64) * n)
        else:
            rows.append(np.zeros(K, dtype=np.float64))
        names.append(b.get("name", b.get("model", "?")))
    return np.array(rows, dtype=np.float64), names


def make_base_measure(counts: NDArray[np.float64], eta: float = 1.0) -> NDArray[np.float64]:
    """全局基础分布 r_k：所有基准汇总计数 + eta 平滑。

    r_k = (Σ_i c_{i,k} + eta) / (Σ_{i,k} c_{i,k} + K*eta)
    """
    pooled = counts.sum(axis=0).astype(np.float64) + eta
    r = pooled / pooled.sum()
    return np.maximum(r, 1e-12)  # 防极端情况归一化后仍为 0


def smoothed_probs(counts: NDArray[np.float64],
                   base_measure: NDArray[np.float64],
                   lam: float) -> NDArray[np.float64]:
    """Dirichlet 平滑概率矩阵。

    p̃_{i,k} = (c_{i,k} + λ * r_k) / (N_i + λ)

    lam 是总伪样本量（而非每类），避免 K=355 把分布过度拉向均匀。
    """
    alpha = counts.astype(np.float64) + lam * base_measure[None, :]
    alpha = np.maximum(alpha, 1e-10)
    return alpha / alpha.sum(axis=1, keepdims=True)


# ================================================================
# 二、模型识别：后验预测对数似然
# ================================================================
def log_predictive_scores(baseline_counts: NDArray[np.float64],
                          test_counts: NDArray[np.float64],
                          prior_strength: float,
                          base_measure: NDArray[np.float64]) -> NDArray[np.float64]:
    """Dirichlet-multinomial 后验预测对数似然。

    α_{i,k} = c_{i,k} + λ * r_k
    ℓ_i(n) = logΓ(Σ_k α_{i,k}) - logΓ(Σ_k α_{i,k} + N)
             + Σ_k [logΓ(α_{i,k} + n_k) - logΓ(α_{i,k})]

    省略所有模型共有的 multinomial coefficient（不影响排序）。
    """
    if baseline_counts.ndim != 2:
        raise ValueError("baseline_counts 必须为 M x K 矩阵")
    if test_counts.ndim != 1:
        raise ValueError("test_counts 必须为 K 维向量")
    if baseline_counts.shape[1] != test_counts.shape[0]:
        raise ValueError("类别维度不一致")
    if prior_strength <= 0:
        raise ValueError("prior_strength 必须大于 0")

    alpha = baseline_counts.astype(np.float64) + prior_strength * base_measure[None, :]
    # 防 0：某些桶在所有基准里都是 0 且 r_k 也为 0 时 alpha=0，gammaln(0)=inf 会产生 nan
    alpha = np.maximum(alpha, 1e-10)
    total_alpha = alpha.sum(axis=1)
    test_n = float(test_counts.sum())

    # logΓ(A) - logΓ(A+N) + Σ_k [logΓ(α_k+n_k) - logΓ(α_k)]
    term1 = gammaln(total_alpha) - gammaln(total_alpha + test_n)
    term2 = (gammaln(alpha + test_counts[None, :]) - gammaln(alpha)).sum(axis=1)
    return term1 + term2


def identify_model(baseline_counts: NDArray[np.float64],
                   test_counts: NDArray[np.float64],
                   prior_strength: float,
                   base_measure: NDArray[np.float64],
                   model_priors: Optional[NDArray[np.float64]] = None) -> dict:
    """模型识别：返回第一名、第二名、后验概率、log margin。"""
    m = baseline_counts.shape[0]
    if m == 0:
        raise ValueError("无基准")

    if model_priors is None:
        model_priors = np.full(m, 1.0 / m, dtype=np.float64)
    model_priors = np.asarray(model_priors, dtype=np.float64)
    model_priors = model_priors / model_priors.sum()

    log_marginal = log_predictive_scores(baseline_counts, test_counts,
                                         prior_strength, base_measure)
    log_joint = log_marginal + np.log(model_priors)
    posterior = np.exp(log_joint - logsumexp(log_joint))

    order = np.argsort(log_joint)[::-1]
    first, second = int(order[0]), int(order[1])

    return {
        "best_model": first,
        "second_model": second,
        "best_posterior": float(posterior[first]),
        "log_margin": float(log_joint[first] - log_joint[second]),
        "posterior": posterior,
        "log_predictive": log_marginal,
    }


# ================================================================
# 三、造假／异常判断
# ================================================================
def known_alternative_log_bf(log_predictive: NDArray[np.float64],
                             claimed: int,
                             alternative_weights: Optional[NDArray[np.float64]] = None) -> float:
    """已知替身对数 Bayes factor。

    T_known = log( Σ_{a≠c} w_a * exp(ℓ_a) ) - ℓ_c

    正值支持已知替身，负值支持 claimed 模型。
    """
    m = len(log_predictive)
    alternatives = np.array([i for i in range(m) if i != claimed])

    if alternative_weights is None:
        alternative_weights = np.full(m - 1, 1.0 / (m - 1), dtype=np.float64)
    alternative_weights = np.asarray(alternative_weights, dtype=np.float64)
    alternative_weights = alternative_weights / alternative_weights.sum()

    alt_score = logsumexp(log_predictive[alternatives] + np.log(alternative_weights))
    return float(alt_score - log_predictive[claimed])


def deviance_g2(test_counts: NDArray[np.float64],
                reference_probability: NDArray[np.float64]) -> float:
    """开放世界异常统计量 G²（deviance）。

    G² = 2 * Σ_{k: n_k>0} n_k * log( (n_k/N) / p̃_{c,k} )

    阈值必须通过模拟校准，不能直接查 χ² 表（K=355、N 小时近似不可靠）。
    """
    n_total = float(test_counts.sum())
    if n_total <= 0:
        raise ValueError("测试样本数必须大于 0")

    mask = test_counts > 0
    empirical = test_counts[mask] / n_total
    ref = np.asarray(reference_probability, dtype=np.float64)[mask]
    # 防止 log(0)；reference 已平滑过，理论为正
    ref = np.maximum(ref, 1e-300)
    return float(2.0 * np.sum(test_counts[mask] * (np.log(empirical) - np.log(ref))))


def calibrate_g2_threshold(baseline_counts: NDArray[np.float64],
                            base_measure: NDArray[np.float64],
                            lam: float,
                            claimed: int,
                            sample_size: int,
                            n_sim: int = 10000,
                            alpha: float = 0.01,
                            rng: Optional[np.random.Generator] = None) -> float:
    """通过后验预测模拟校准 G² 的异常阈值。

    1. 从 claimed 模型的 Dirichlet 后验抽取 P_c^(b)
    2. 生成 n^(b) ~ Multinomial(N, P_c^(b))
    3. 计算 G²^(b)
    4. 取 (1-alpha) 分位数作为阈值

    返回阈值：G² 超过此值则判为异常（误报率 ≤ alpha）。
    """
    if rng is None:
        rng = np.random.default_rng()

    alpha_vec = baseline_counts[claimed].astype(np.float64) + lam * base_measure
    alpha_vec = np.maximum(alpha_vec, 1e-10)
    # 后验均值（即平滑概率），用于生成
    post_mean = alpha_vec / alpha_vec.sum()

    g2_samples = np.empty(n_sim, dtype=np.float64)
    for b in range(n_sim):
        # 从 Dirichlet 后验抽样
        p_sim = rng.dirichlet(alpha_vec)
        # 生成多项式样本
        n_sim_counts = rng.multinomial(sample_size, p_sim)
        g2_samples[b] = deviance_g2(n_sim_counts.astype(np.float64), post_mean)

    return float(np.quantile(g2_samples, 1.0 - alpha))


def judge_forgery(baseline_counts: NDArray[np.float64],
                  test_counts: NDArray[np.float64],
                  base_measure: NDArray[np.float64],
                  lam: float,
                  claimed: int,
                  tau_accept: float,
                  tau_reject: float,
                  tau_g: Optional[float] = None,
                  n_sim: int = 10000,
                  rng: Optional[np.random.Generator] = None) -> dict:
    """四状态造假判定。

    状态：
    - supported          支持声明
    - suspected_known    已知替身嫌疑
    - unknown_anomaly    未知异常
    - insufficient       证据不足

    tau_accept/tau_reject 是 T_known 的阈值（tau_accept < tau_reject）。
    tau_g 是 G² 异常阈值；若为 None 则用模拟校准。
    """
    if rng is None:
        rng = np.random.default_rng()

    log_pred = log_predictive_scores(baseline_counts, test_counts, lam, base_measure)
    t_known = known_alternative_log_bf(log_pred, claimed)

    # G² 异常检测
    claimed_probs = smoothed_probs(baseline_counts[claimed:claimed+1],
                                    base_measure, lam)[0]
    g2 = deviance_g2(test_counts, claimed_probs)

    if tau_g is None:
        n = int(test_counts.sum())
        tau_g = calibrate_g2_threshold(baseline_counts, base_measure, lam,
                                        claimed, n, n_sim=n_sim, rng=rng)

    # 四状态决策
    if t_known <= tau_accept and g2 <= tau_g:
        status = "supported"
    elif t_known >= tau_reject:
        status = "suspected_known"
    elif t_known < tau_reject and g2 > tau_g:
        status = "unknown_anomaly"
    else:
        status = "insufficient"

    return {
        "status": status,
        "claimed_model": claimed,
        "best_model": int(np.argmax(log_pred)),
        "known_alt_log_bf": t_known,
        "g2": g2,
        "g2_threshold": tau_g,
        "tau_accept": tau_accept,
        "tau_reject": tau_reject,
    }


# ================================================================
# 四、阈值与样本量校准
# ================================================================
def chernoff_information(p: NDArray[np.float64], q: NDArray[np.float64]) -> float:
    """两个严格正概率分布之间的 Chernoff 信息。

    C(P,Q) = -min_{s∈[0,1]} log Σ_k p_k^s * q_k^{1-s}
    """
    if np.any(p <= 0) or np.any(q <= 0):
        raise ValueError("请先对概率分布进行平滑")
    log_p, log_q = np.log(p), np.log(q)
    result = minimize_scalar(
        lambda s: logsumexp(s * log_p + (1.0 - s) * log_q),
        bounds=(0.0, 1.0), method="bounded",
    )
    return max(0.0, -float(result.fun))


def chernoff_matrix(smoothed_probs_matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """计算所有基准对之间的 Chernoff 信息矩阵（对称 M×M）。"""
    m = smoothed_probs_matrix.shape[0]
    C = np.zeros((m, m), dtype=np.float64)
    for i in range(m):
        for j in range(i + 1, m):
            c = chernoff_information(smoothed_probs_matrix[i], smoothed_probs_matrix[j])
            C[i, j] = c
            C[j, i] = c
    return C


def min_separability(smoothed_probs_matrix: NDArray[np.float64]) -> tuple[float, tuple[int, int]]:
    """最难区分的模型对及其 Chernoff 信息。返回 (C_min, (i,j))。"""
    C = chernoff_matrix(smoothed_probs_matrix)
    m = C.shape[0]
    if m < 2:
        return float("inf"), (-1, -1)
    # 忽略对角线
    np.fill_diagonal(C, np.inf)
    idx = np.unravel_index(np.argmin(C), C.shape)
    return float(C[idx]), (int(idx[0]), int(idx[1]))


def estimate_sample_size(C_min: float, n_models: int, delta: float = 0.05) -> int:
    """根据 Chernoff 信息粗略估计所需样本量。

    N ≈ log((M-1)/delta) / C_min
    """
    if C_min <= 0:
        return -1
    return int(math.ceil(math.log((n_models - 1) / delta) / C_min))


# ================================================================
# 高层封装：从 baselines.json + test_results 直接出判定
# ================================================================
# 默认阈值（策略文档建议的初始展示规则）
DEFAULT_TAU_ACCEPT = -math.log(20.0)   # T_known ≤ -log20 → 支持声明
DEFAULT_TAU_REJECT = math.log(3.0)      # T_known ≥ log3  → 已知替身嫌疑
DEFAULT_LAMBDA = 3.0                    # 默认平滑强度（建议交叉验证调）
DEFAULT_ALPHA = 0.01                    # G² 误报率


def evaluate(test_results: list[int],
             baselines: list[dict],
             claimed_name: Optional[str] = None,
             lam: float = DEFAULT_LAMBDA,
             eta: float = 1.0,
             tau_accept: float = DEFAULT_TAU_ACCEPT,
             tau_reject: float = DEFAULT_TAU_REJECT,
             alpha: float = DEFAULT_ALPHA,
             n_sim: int = 5000,
             rng: Optional[np.random.Generator] = None) -> dict:
    """完整评估：模型识别 + 造假判定。

    参数：
        test_results    采样得到的数字列表（1..355）
        baselines       load_baselines() 的结果
        claimed_name    声称的模型名（用于造假检测）；None 则只做识别
        lam             Dirichlet 平滑强度
        eta             基础分布平滑参数
        tau_accept/reject  T_known 的接受/拒绝阈值
        alpha           G² 异常误报率
        n_sim           G² 阈值模拟次数
    """
    if rng is None:
        rng = np.random.default_rng()

    if not baselines:
        return {"error": "无基准"}

    C, names = build_counts_matrix(baselines)
    r = make_base_measure(C, eta=eta)
    n_test = counts_from_raw(test_results)

    # 模型识别
    ident = identify_model(C, n_test, lam, r)
    best_idx = ident["best_model"]

    result = {
        "sample_size": len(test_results),
        "best_model_name": names[best_idx],
        "best_model_model": baselines[best_idx].get("model", "?"),
        "best_posterior": ident["best_posterior"],
        "log_margin": ident["log_margin"],
        "second_model_name": names[ident["second_model"]],
        # 证据强度分级（log margin）
        "evidence_level": _evidence_level(ident["log_margin"]),
        # 解释性指标（仅展示，不参与判定）
        "top5": [
            {"name": names[i], "model": baselines[i].get("model", "?"),
             "posterior": float(ident["posterior"][i]),
             "log_predictive": float(ident["log_predictive"][i])}
            for i in np.argsort(ident["log_predictive"])[::-1][:5]
        ],
    }

    # 造假判定（需指定声称模型）
    if claimed_name is not None:
        try:
            claimed_idx = names.index(claimed_name)
        except ValueError:
            # 声称的模型不在基准库中
            result["forgery"] = {
                "status": "claimed_not_in_baselines",
                "claimed_name": claimed_name,
            }
            return result

        forgery = judge_forgery(C, n_test, r, lam, claimed_idx,
                                tau_accept, tau_reject,
                                n_sim=n_sim, rng=rng)
        forgery["claimed_model_name"] = names[claimed_idx]
        forgery["best_model_name"] = names[forgery["best_model"]]
        # 状态中文映射
        status_map = {
            "supported": "支持声明",
            "suspected_known": "已知替身嫌疑",
            "unknown_anomaly": "未知异常",
            "insufficient": "证据不足",
        }
        forgery["status_cn"] = status_map.get(forgery["status"], forgery["status"])
        result["forgery"] = forgery

    return result


def _evidence_level(log_margin: float) -> str:
    """根据 log margin 分级证据强度（策略文档建议的初始规则）。"""
    if log_margin < math.log(3):
        return "差异很弱"
    elif log_margin < math.log(20):
        return "有一定证据"
    elif log_margin < math.log(100):
        return "较强证据"
    else:
        return "很强证据"


# ================================================================
# 工具：交叉验证选择 lambda
# ================================================================
def cross_validate_lambda(baselines: list[dict],
                          lam_candidates: Optional[list[float]] = None,
                          eta: float = 1.0,
                          n_folds: int = 5,
                          rng: Optional[np.random.Generator] = None) -> dict:
    """留出法交叉验证选择最优 lambda。

    评价指标：top-1 准确率 + 平均 log loss。
    """
    if rng is None:
        rng = np.random.default_rng()
    if lam_candidates is None:
        lam_candidates = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]

    C, names = build_counts_matrix(baselines)
    m = C.shape[0]
    if m < 2:
        return {"error": "基准不足"}

    # 构造留出样本：每个基准随机留出 20%
    holdout = []
    train_counts = C.copy()
    for i in range(m):
        n_i = int(C[i].sum())
        if n_i < 4:
            continue
        n_hold = max(1, n_i // 5)
        # 从该基准的原始样本中随机抽 n_hold 个作为留出
        probs = C[i] / n_i
        hold = rng.multinomial(n_hold, probs / probs.sum())
        train_counts[i] = C[i] - hold
        holdout.append((i, hold))

    results = {}
    for lam in lam_candidates:
        r = make_base_measure(train_counts, eta=eta)
        correct = 0
        total_logloss = 0.0
        total = 0
        for true_idx, hold_counts in holdout:
            if hold_counts.sum() == 0:
                continue
            ident = identify_model(train_counts, hold_counts, lam, r)
            posterior = ident["posterior"]
            # top-1 准确
            if ident["best_model"] == true_idx:
                correct += 1
            # log loss
            p_true = max(posterior[true_idx], 1e-300)
            total_logloss += -math.log(p_true)
            total += 1
        if total > 0:
            results[lam] = {
                "top1_accuracy": correct / total,
                "avg_logloss": total_logloss / total,
            }

    # 选 top-1 准确率最高、log loss 最低的
    best_lam = min(results.keys(),
                   key=lambda l: (-results[l]["top1_accuracy"], results[l]["avg_logloss"]))
    return {"best_lambda": best_lam, "all_results": results}
