"""
公共模块：HTTP 客户端、统计计算、基准存储。
被三个算法模块共享。
"""

import json
import math
import os
import re
import tempfile
import requests
import numpy as np
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone

NUMBER_RANGE = 355
MIN_SAMPLES = 40
TIMEOUT = 60
BUNDLED_BASELINES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "baselines.json"),
)
DATA_DIR = os.environ.get(
    "AIG_API_CHECKER_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "..", "runtime"),
)
DEFAULT_BASELINES_PATH = os.environ.get(
    "AIG_API_CHECKER_BASELINES",
    os.path.join(DATA_DIR, "baselines.json"),
)


# ================================================================
#  HTTP 客户端
# ================================================================
def _ua_headers(extra=None):
    """带 User-Agent 的请求头（避免被 Cloudflare 拦截）"""
    h = {"User-Agent": "aig-api-checker/1.0"}
    if extra:
        h.update(extra)
    return h


def http_post_json(url, headers, body, timeout=TIMEOUT):
    """POST JSON，返回 (status, json_dict)"""
    resp = requests.post(
        url,
        headers=headers,
        json=body,
        timeout=timeout,
        allow_redirects=False,
    )
    if resp.status_code >= 400:
        return resp.status_code, {"error": f"API错误: {resp.status_code} - {resp.text[:300]}"}
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, {"error": f"非JSON响应: {resp.text[:200]}"}


def http_get_json(url, headers, timeout=30):
    """GET JSON"""
    resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=False)
    if resp.status_code >= 400:
        return resp.status_code, {"error": f"API错误: {resp.status_code} - {resp.text[:300]}"}
    return resp.status_code, resp.json()


# ================================================================
#  统计计算（算法 A 共享）
# ================================================================
def calculate_distribution(numbers):
    """计算 1~NUMBER_RANGE 的概率分布（长度 355 的数组）"""
    counts = [0] * NUMBER_RANGE
    for n in numbers:
        if 1 <= n <= NUMBER_RANGE:
            counts[n - 1] += 1
    total = len(numbers) or 1
    return [c / total for c in counts]


def calculate_stats(numbers):
    """计算统计特征：均值/中位数/标准差/众数等"""
    if not numbers:
        return {}
    sorted_nums = sorted(numbers)
    n = len(numbers)
    mean = sum(numbers) / n
    variance = sum((x - mean) ** 2 for x in numbers) / n
    freq = Counter(numbers)
    mode_val, mode_count = numbers[0], 0
    for k, v in freq.items():
        if v > mode_count:
            mode_count, mode_val = v, k
    return {
        "mean": mean, "median": sorted_nums[n // 2],
        "stdDev": math.sqrt(variance),
        "min": sorted_nums[0], "max": sorted_nums[-1],
        "unique": len(set(numbers)),
        "mode": mode_val, "modeCount": mode_count,
    }


def calculate_similarity(dist1, dist2, stats1=None, stats2=None):
    """
    综合相似度 = 0.5*众数匹配 + 0.5*(余弦相似度 × exp(-JS散度))
    """
    dot = sum(a * b for a, b in zip(dist1, dist2))
    norm1 = math.sqrt(sum(a * a for a in dist1))
    norm2 = math.sqrt(sum(b * b for b in dist2))
    cosine = dot / (norm1 * norm2) if (norm1 and norm2) else 0.0

    eps = 1e-10
    js = 0.0
    for p, q in zip(dist1, dist2):
        p, q = p + eps, q + eps
        m = (p + q) / 2
        js += (p * math.log(p / m) + q * math.log(q / m)) / 2

    distrib_score = cosine * math.exp(-js)

    mode_score = 0.0
    if stats1 and stats2 and "mode" in stats1 and "mode" in stats2:
        if stats1["mode"] == stats2["mode"]:
            mode_score = 1.0
        else:
            mode_score = max(0.0, 1 - abs(stats1["mode"] - stats2["mode"]) / 50)

    return {
        "cosineSimilarity": cosine,
        "jsDivergence": js,
        "modeScore": mode_score,
        "distribScore": distrib_score,
        "overallScore": mode_score * 0.5 + distrib_score * 0.5,
    }


# ================================================================
#  基准存储
# ================================================================
def build_baseline(name, model, api_type, results, no_think=False):
    """把采样数据构造成可保存的基准 dict。

    保存 rawData（原始序列）和 counts（长度 K 的计数向量），
    供 bayes_score 模块做 Dirichlet 后验推断。
    """
    counts = [0] * NUMBER_RANGE
    for n in results:
        if 1 <= n <= NUMBER_RANGE:
            counts[n - 1] += 1
    return {
        "name": name, "model": model, "apiType": api_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "iterations": len(results),
        "noThink": no_think,
        "distribution": calculate_distribution(results),
        "stats": calculate_stats(results),
        "counts": counts,
        "rawData": results,
    }


def save_baselines(baselines, filepath=DEFAULT_BASELINES_PATH):
    directory = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(directory, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(prefix=".baselines-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(baselines, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temporary_path, filepath)
    except Exception:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise


def load_baselines(filepath=DEFAULT_BASELINES_PATH):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        if (
            os.path.abspath(filepath) == os.path.abspath(DEFAULT_BASELINES_PATH)
            and os.path.abspath(filepath) != BUNDLED_BASELINES_PATH
        ):
            try:
                with open(BUNDLED_BASELINES_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
        return []


def append_baseline(baseline, filepath=DEFAULT_BASELINES_PATH):
    baselines = load_baselines(filepath)
    baselines.append(baseline)
    save_baselines(baselines, filepath)
    return baselines


# ================================================================
#  并发采样（算法 A 用）
# ================================================================
RANDOM_PROMPT = "请从1到355之间随机选择一个数字，只输出这个数字，不要有任何其他内容。"


def _call_api_for_number(api_type, base_url, api_key, model, no_think=False):
    """调用 API 获取一个"随机"数字文本。

    no_think=True 时，对支持的推理模型（DeepSeek/GLM/MiniMax/Qwen）发送
    thinking={"type":"disabled"} 关闭思考，max_tokens 降到 100，大幅加速；
    不支持关闭思考的模型自动回退到大 max_tokens 模式。
    """
    base = base_url.rstrip("/")
    if api_type == "anthropic":
        headers = _ua_headers({
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        })
        body = {"model": model, "max_tokens": 10,
                "messages": [{"role": "user", "content": RANDOM_PROMPT}], "temperature": 1.0}
        _, data = http_post_json(f"{base}/messages", headers, body)
        if "error" not in data:
            return data["content"][0]["text"].strip()
    elif api_type == "openai-responses":
        headers = _ua_headers({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })
        # Responses 的默认温度即 1；省略该可选字段可兼容不接受
        # temperature 的推理模型和 OpenAI-compatible 实现。
        body = {"model": model, "input": [{"role": "user", "content": RANDOM_PROMPT}],
                "max_output_tokens": 10}
        _, data = http_post_json(f"{base}/responses", headers, body)
        if "error" not in data:
            msg = next((o for o in data.get("output", []) if o.get("type") == "message"), None)
            if msg and msg.get("content"):
                block = next((c for c in msg["content"] if c.get("type") == "output_text"), None)
                if block:
                    return block["text"].strip()
    else:  # openai
        headers = _ua_headers({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })
        # no_think 模式：关闭思考 + 小 max_tokens，响应快且省钱
        # 大 max_tokens 模式：兼容无法关闭思考的推理模型（如 Kimi-K3）
        if no_think:
            body = {"model": model, "messages": [{"role": "user", "content": RANDOM_PROMPT}],
                    "temperature": 1.0, "max_tokens": 100,
                    "thinking": {"type": "disabled"}}
        else:
            body = {"model": model, "messages": [{"role": "user", "content": RANDOM_PROMPT}],
                    "temperature": 1.0, "max_tokens": 2048}
        _, data = http_post_json(f"{base}/chat/completions", headers, body)
        if "error" not in data:
            try:
                return data["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError, AttributeError):
                return None
        # no_think 导致报错时自动回退到普通模式（部分模型不支持 thinking 参数）
        if no_think and data.get("error"):
            body2 = {"model": model, "messages": [{"role": "user", "content": RANDOM_PROMPT}],
                     "temperature": 1.0, "max_tokens": 2048}
            _, data2 = http_post_json(f"{base}/chat/completions", headers, body2)
            if "error" not in data2:
                try:
                    return data2["choices"][0]["message"]["content"].strip()
                except (KeyError, IndexError, AttributeError):
                    return None
    return None


def extract_number(text):
    """从模型输出中提取 1~355 范围内的整数"""
    match = re.search(r"\d+", text or "")
    if match:
        num = int(match.group())
        if 1 <= num <= NUMBER_RANGE:
            return num
    return None


def collect_samples(api_type, base_url, api_key, model,
                    iterations=200, concurrency=5, on_progress=None, no_think=False,
                    cancel_event=None):
    """并发采集 N 个随机数样本。

    no_think=True 时关闭推理模型思考（支持的模型自动加速，不支持的回退）。
    """
    results = []
    error_count = 0
    completed = 0
    if cancel_event is not None and cancel_event.is_set():
        return results, error_count
    pool = ThreadPoolExecutor(max_workers=concurrency)
    pending = {
        pool.submit(_call_api_for_number, api_type, base_url, api_key, model, no_think)
        for _ in range(iterations)
    }
    cancelled = False
    try:
        while pending:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            done, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
            for fut in done:
                completed += 1
                try:
                    text = fut.result()
                    num = extract_number(text) if text else None
                    if num is not None:
                        results.append(num)
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1
                if on_progress:
                    on_progress(completed, iterations, len(results), error_count)
    finally:
        if cancelled:
            for future in pending:
                future.cancel()
        pool.shutdown(wait=not cancelled, cancel_futures=cancelled)
    return results, error_count


def match_baselines(test_results, baselines):
    """将测试样本与所有基准对比，按后验预测似然降序返回。

    判定使用 Dirichlet-multinomial 后验预测似然（bayes_score.identify_model）。
    余弦相似度、JS 散度、众数仅作为解释性指标保留，不参与排序。
    """
    from .bayes_score import build_counts_matrix, make_base_measure, identify_model, smoothed_probs, DEFAULT_LAMBDA

    if not baselines:
        return []

    C, names = build_counts_matrix(baselines)
    r = make_base_measure(C)
    # 测试样本计数向量
    test_counts = counts_from_raw_list(test_results)

    ident = identify_model(C, test_counts, DEFAULT_LAMBDA, r)
    order = np.argsort(ident["log_predictive"])[::-1]

    # 旧指标仅用于解释
    test_dist = calculate_distribution(test_results)
    test_stats = calculate_stats(test_results)

    matches = []
    for i in order:
        b = baselines[i]
        sim = calculate_similarity(test_dist, b["distribution"], test_stats, b.get("stats"))
        matches.append({
            "name": b.get("name", b.get("model", "?")),
            "model": b.get("model", "?"),
            "score": float(ident["posterior"][i]),  # 后验概率，替代旧的 overallScore
            "logPredictive": float(ident["log_predictive"][i]),
            "modeMatch": test_stats.get("mode") == b.get("stats", {}).get("mode"),
            # 旧指标保留用于解释
            "similarity": sim,
            "testStats": test_stats,
        })
    return matches


def counts_from_raw_list(raw_data):
    """把原始采样序列转为长度 K 的 numpy 计数向量。"""
    import numpy as np
    c = np.zeros(NUMBER_RANGE, dtype=np.float64)
    for n in raw_data:
        if 1 <= n <= NUMBER_RANGE:
            c[n - 1] += 1.0
    return c
