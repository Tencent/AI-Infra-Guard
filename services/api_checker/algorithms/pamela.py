"""
算法 D：PAMELA 单 token 分布指纹（移植自 pamela-publish-py 的 match.py + normalize.py）。

原理：用 PAMELA 研究的 study-A 探针任务（随机数字/字母/单词/颜色/动物/城市/抛硬币等
paper==1 的 10 个任务）在多语言（en/ru/zh/ar）下采样模型的单 token 回答分布，
作为行为指纹；与已发布的参考指纹库（pamela-publish-data/results/distributions.json）
逐 (task, lang) 单元计算 Jensen–Shannon 散度（JSD），均值最小者即指纹最接近的模型。

格式兼容：
  - 参考库直接读取 pamela-publish-data/results/distributions.json（Zenodo 21278557）；
  - 候选分布输出 pamela/results/candidate-distributions.json，字段与
    pamela-publish-py/results/candidate-distributions.json 完全一致，
    可反过来喂给 pamela-publish-py/match.py --candidate 使用。

纯 Python 标准库，无第三方依赖。
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
import unicodedata
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .common import http_post_json

ALGO_DIR = Path(__file__).resolve().parent
ROOT = ALGO_DIR.parent
PAMELA_DIR = ROOT / "pamela"
CONFIG_DIR = PAMELA_DIR / "config"
DATA_DIR = Path(os.environ.get("AIG_API_CHECKER_DATA_DIR", ROOT / "runtime"))
RESULTS_DIR = DATA_DIR / "pamela" / "results"

# 默认使用随服务打包的参考指纹库；部署方可用环境变量挂载更新后的数据。
DEFAULT_REFERENCE = Path(os.environ.get(
    "AIG_PAMELA_REFERENCE",
    PAMELA_DIR / "reference" / "distributions.json",
))

MIN_N = 10  # 参考单元最少有效样本数（与 pamela match.py 一致）


# ================================================================
#  配置加载（pamela config 原样复制）
# ================================================================
def _read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


_prompts = _read_json(CONFIG_DIR / "prompts.json")
_color_lex = _read_json(CONFIG_DIR / "color-lexicon.json")
_run_cfg = _read_json(CONFIG_DIR / "run.config.json")
_task_by_id = {t["id"]: t for t in _prompts["tasks"]}
STUDY_A_TASKS = [t["id"] for t in _prompts["tasks"] if t.get("paper") == 1]
ALL_LANGS = list(_prompts["system_prompts"].keys())


# ================================================================
#  答案归一化（逐行移植 pamela-publish-py/normalize.py）
# ================================================================
AR_DIGITS = {'٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6',
             '٧': '7', '٨': '8', '٩': '9', '۰': '0', '۱': '1', '۲': '2', '۳': '3',
             '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
ZH_DIGITS = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6,
             '七': 7, '八': 8, '九': 9}

REFUSAL_RE = re.compile(
    r"(i can.?t|i cannot|i'm sorry|as an ai|не могу|извин|抱歉|无法|لا أستطيع|عذراً|آسف)", re.I)

COIN = {
    "en": {"heads": "h", "tails": "t"},
    "ru": {"орёл": "h", "орел": "h", "решка": "t"},
    "zh": {"正面": "h", "正": "h", "反面": "t", "反": "t"},
    "ar": {"صورة": "h", "كتابة": "t"},
}


def _zh_number(s):
    m = re.match(r"^([零一二两三四五六七八九])?十?([零一二两三四五六七八九])?$", s)
    if not m or (not m.group(1) and not m.group(2) and "十" not in s):
        return None
    if "十" not in s:
        return ZH_DIGITS[m.group(1)] if m.group(1) else None
    return (ZH_DIGITS[m.group(1)] if m.group(1) else 1) * 10 + \
           (ZH_DIGITS[m.group(2)] if m.group(2) else 0)


def _basic_clean_str(raw):
    return unicodedata.normalize("NFC", raw) \
        .replace("«", " ").replace("»", " ").replace("”", " ").replace("“", " ") \
        .replace("„", " ").replace("’", " ").replace("‘", " ").replace("`", " ") \
        .replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ") \
        .replace("{", " ").replace("}", " ").replace("*", " ").replace("_", " ") \
        .replace("#", " ").replace("-", " ") \
        .replace(",", " ").replace(".", " ").replace("!", " ").replace("?", " ") \
        .replace("。", " ").replace("！", " ").replace("？", " ").replace("、", " ") \
        .replace("：", " ").replace(":", " ").replace(";", " ").replace("؛", " ") \
        .replace("؟", " ").replace('"', " ").replace("'", " ") \
        .replace(" ", " ").split()


def normalize(rec):
    """Return {normalized, answer_class, color_canon} for one raw response record."""
    task = _task_by_id.get(rec["task_id"])
    out = {"normalized": None, "answer_class": "invalid", "color_canon": None}
    if not task:
        return out
    if rec.get("raw") is None or not str(rec["raw"]).strip():
        return {**out, "answer_class": "empty"}
    if REFUSAL_RE.search(rec["raw"]):
        return {**out, "answer_class": "refusal"}

    s = " ".join(_basic_clean_str(rec["raw"])).strip()
    if not s:
        return {**out, "answer_class": "empty"}
    s = re.sub(r"[٠-٩۰-۹]", lambda d: AR_DIGITS[d.group(0)], s)

    if task["normalize_as"] == "integer":
        n = None
        m = re.search(r"-?\d+", s)
        if m:
            n = int(m.group(0))
        elif rec["lang"] == "zh":
            n = _zh_number(s)
        if n is None:
            return out
        rng = re.search(r"(\d+)-(\d+)", task["answer_space"])
        in_range = not rng or (int(rng.group(1)) <= n <= int(rng.group(2)))
        return {**out, "normalized": str(n), "answer_class": "valid" if in_range else "invalid"}

    if task["normalize_as"] == "binary":
        w = s.lower().split(" ")[0]
        c = COIN.get(rec["lang"], {}).get(w)
        return {**out, "normalized": c, "answer_class": "valid"} if c else out

    words = s.lower().split(" ")
    if task["normalize_as"] == "word" and len(words) > 3:
        return out  # whole sentence => off-format
    w = words[0]
    if not w:
        return {**out, "answer_class": "empty"}
    if task["normalize_as"] == "grapheme" and len(w) > 1 and rec["lang"] != "zh":
        single = next((x for x in words if len(x) == 1), None)
        if not single:
            return out
        return {**out, "normalized": single, "answer_class": "valid"}
    res = {**out, "normalized": w, "answer_class": "valid"}
    if task["category"] == "color":
        res["color_canon"] = _color_lex["map"].get(rec["lang"], {}).get(w)
    return res


# ================================================================
#  JSD 与参考库（移植 pamela-publish-py/match.py）
# ================================================================
def jsd(p, q):
    support = set(p) | set(q)
    d = 0.0
    for x in support:
        px = p.get(x, 0.0)
        qx = q.get(x, 0.0)
        mx = (px + qx) / 2.0
        if px > 0:
            d += 0.5 * px * math.log2(px / mx)
        if qx > 0:
            d += 0.5 * qx * math.log2(qx / mx)
    return d


def load_reference(path):
    doc = _read_json(path)
    by_cell = defaultdict(dict)
    models = set()
    study_a = set(STUDY_A_TASKS)
    for d in doc["distributions"]:
        if d["task_id"] not in study_a or d["n_valid"] < MIN_N:
            continue
        by_cell[(d["task_id"], d["lang"])][d["model"]] = d["dist"]
        models.add(d["model"])
    return {"by_cell": by_cell, "models": sorted(models)}


def rank(reference, candidate_cells):
    """candidate_cells[(task,lang)] = dist  -> ranked [(model, mean_jsd, n_cells)]."""
    by_cell = reference["by_cell"]
    scores = []
    for model in reference["models"]:
        divs = []
        for cell, cdist in candidate_cells.items():
            rdist = by_cell.get(cell, {}).get(model)
            if rdist:
                divs.append(jsd(cdist, rdist))
        if divs:
            scores.append((model, sum(divs) / len(divs), len(divs)))
    scores.sort(key=lambda x: x[1])
    return scores


# ================================================================
#  在线采样（OpenAI 兼容端点，请求体与 pamela lib.chat_completion 一致）
# ================================================================
def _chat_once(base_url, api_key, model, system, user):
    """单次 chat completion，返回 raw 文本；失败返回 None。

    请求体与 pamela-publish-py/lib.py 一致（temperature=1.0, max_tokens=16,
    reasoning disabled）；若端点不兼容扩展字段则回退到精简请求体。
    """
    base = base_url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/tomasbruckner/pamela",
        "X-Title": "PAMELA LLM study",
        "User-Agent": "aig-api-checker/1.0",
    }
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    body = {"model": model, "messages": messages, "temperature": 1.0,
            "max_tokens": _run_cfg["request"]["max_tokens"],
            "reasoning": {"enabled": False}, "usage": {"include": True}}
    timeout = _run_cfg["request"]["timeout_ms"] / 1000.0
    try:
        _, data = http_post_json(f"{base}/chat/completions", headers, body, timeout=timeout)
        if "error" not in data:
            return data["choices"][0]["message"]["content"]
        # 回退：去掉 OpenRouter 扩展字段重试
        body2 = {"model": model, "messages": messages, "temperature": 1.0,
                 "max_tokens": _run_cfg["request"]["max_tokens"]}
        _, data2 = http_post_json(f"{base}/chat/completions", headers, body2, timeout=timeout)
        if "error" not in data2:
            return data2["choices"][0]["message"]["content"]
    except Exception:
        pass
    return None


def sample_candidate(base_url, api_key, model, reps=10, langs=None, tasks_filter=None,
                     concurrency=8, on_progress=None):
    """采样候选模型的 study-A 单元分布。

    返回 (candidate_cells, counts, off)：
      candidate_cells[(task,lang)] = {answer: prob}
      counts[(task,lang)] = {answer: n}；off[(task,lang)] = 无效/失败数
    """
    langs = langs or ALL_LANGS
    tasks = [t for t in _prompts["tasks"] if t.get("paper") == 1 and
             (not tasks_filter or t["id"] in tasks_filter)]
    grid = []
    for task in tasks:
        for lang in langs:
            if lang not in task["prompts"] or lang not in _prompts["system_prompts"]:
                continue
            for _ in range(reps):
                grid.append({"task_id": task["id"], "lang": lang,
                             "system": _prompts["system_prompts"][lang],
                             "user": task["prompts"][lang]})

    counts = defaultdict(lambda: defaultdict(int))
    off = defaultdict(int)
    total = len(grid)
    completed = [0]
    result_lock = threading.Lock()

    def worker(cell):
        raw = _chat_once(base_url, api_key, model, cell["system"], cell["user"])
        key = (cell["task_id"], cell["lang"])
        normalized = (
            normalize({"task_id": cell["task_id"], "lang": cell["lang"], "raw": raw})
            if raw is not None
            else None
        )
        with result_lock:
            if normalized and normalized["answer_class"] == "valid":
                counts[key][str(normalized["normalized"])] += 1
            else:
                off[key] += 1
            completed[0] += 1
            progress = (
                completed[0],
                total,
                sum(sum(c.values()) for c in counts.values()),
                sum(off.values()),
            )
        if on_progress:
            on_progress(*progress)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = [pool.submit(worker, c) for c in grid]
        for _ in as_completed(futs):
            pass

    candidate_cells = {}
    for cell, c in counts.items():
        n = sum(c.values())
        if n == 0:
            continue
        candidate_cells[cell] = {k: v / n for k, v in c.items()}
    return candidate_cells, counts, off


def build_candidate_distributions(model, counts, off):
    """构造与 pamela distributions.json 记录形状完全一致的候选分布列表。"""
    dists = []
    for (task, lang), c in sorted(counts.items()):
        n = sum(c.values())
        if n == 0:
            continue
        entries = sorted(c.items(), key=lambda kv: -kv[1])
        probs = [v / n for _, v in entries]
        dists.append({
            "model": model, "task_id": task, "lang": lang,
            "temperature": 1, "n_valid": n, "n_off_format": off[(task, lang)],
            "dist": {k: round(v / n, 4) for k, v in entries},
            "entropy_bits": round(-sum(p * math.log2(p) for p in probs if p > 0), 3),
            "mode": entries[0][0] if entries else None,
            "mode_share": round(entries[0][1] / n, 3) if entries else None,
        })
    return dists


def save_candidate_distributions(model, counts, off, path=None):
    """写入 pamela/results/candidate-distributions.json（与 pamela-publish-py 同构）。"""
    path = Path(path) if path else RESULTS_DIR / "candidate-distributions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    dists = build_candidate_distributions(model, counts, off)
    path.write_text(json.dumps({"model": model, "distributions": dists},
                               indent=2, ensure_ascii=False))
    return path, len(dists)


# ================================================================
#  主流程：采样 + 匹配参考指纹库
# ================================================================
def match_model(base_url, api_key, model, reps=10, langs=None, tasks=None,
                concurrency=8, reference_path=None, on_progress=None):
    """采样候选模型并对 PAMELA 参考库排名。返回结果 dict 或 {"error": ...}。"""
    ref_path = Path(reference_path) if reference_path else DEFAULT_REFERENCE
    if not ref_path.exists():
        return {"error": f"参考指纹库不存在: {ref_path}\n请先下载 pamela-publish-data (Zenodo 21278557)"}
    reference = load_reference(ref_path)

    tasks_filter = set(tasks) if tasks else None
    candidate_cells, counts, off = sample_candidate(
        base_url, api_key, model, reps=reps, langs=langs,
        tasks_filter=tasks_filter, concurrency=concurrency, on_progress=on_progress)
    if not candidate_cells:
        return {"error": "没有有效样本单元（全部请求失败或回答均无效）"}

    saved_path, n_dists = save_candidate_distributions(model, counts, off)
    ranked = rank(reference, candidate_cells)
    return {
        "model": model,
        "reference_models": len(reference["models"]),
        "reference_cells": sum(len(v) for v in reference["by_cell"].values()),
        "candidate_cells": len(candidate_cells),
        "candidate_file": str(saved_path),
        "n_distributions": n_dists,
        "ranked": ranked,  # [(model, mean_jsd, n_cells)] 升序
    }
