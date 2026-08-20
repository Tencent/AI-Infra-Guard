#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek-like 序列显著性检验（抽象参数版）
- 本模块不包含任何具体厂商配置与密钥；
- 仅依赖“OpenAI/DeepSeek 兼容”的 chat.completions 接口返回的 logprobs 结构：
  choices[0].logprobs.content[0] = {
      "token": "<生成的token>",
      "logprob": float,
      "top_logprobs": [{"token": "...", "logprob": float}, ...]
  }

注意：
- 仍按“字符切分前缀”，如需严格 tokenizer 对齐，请自行修改切分方式。
"""

# ======================  日志初始化  ======================
import logging
import os
from datetime import datetime

_LOG_DIR = "log"
os.makedirs(_LOG_DIR, exist_ok=True)

_LOGGING_FMT = "[%(asctime)s][%(levelname)s][%(threadName)s][%(name)s:%(lineno)d] %(message)s"
_LOGGING_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_LOG_FILE = os.path.join(
    _LOG_DIR,
    f"seqcheck_{datetime.now():%Y-%m-%d_%H-%M-%S}.log"
)

logging.basicConfig(
    level=logging.INFO,
    format=_LOGGING_FMT,
    datefmt=_LOGGING_DATE_FMT,
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 抑制第三方库过吵
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info("===  Sequence Tester (抽象参数版) 启动  ===")
# ======================  日志初始化结束  ======================


# ======================  业务代码  ======================
import requests
import json
import math
import time
import threading
import concurrent.futures
from typing import Any, List, Dict, Tuple, Optional
from dataclasses import dataclass

_RATE_LIMIT_COOLDOWN_SEC = 60.0
_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_UNTIL = 0.0


def _wait_for_global_rate_limit(source: str) -> None:
    while True:
        with _RATE_LIMIT_LOCK:
            wait = _RATE_LIMIT_UNTIL - time.monotonic()
        if wait <= 0:
            return
        logger.warning("[%s] 全局 429 暂停中，等待 %.1f 秒", source, wait)
        time.sleep(wait)


def _trigger_global_rate_limit_pause(source: str, status: int = 429) -> None:
    global _RATE_LIMIT_UNTIL
    now = time.monotonic()
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_UNTIL = max(_RATE_LIMIT_UNTIL, now + _RATE_LIMIT_COOLDOWN_SEC)
        wait = _RATE_LIMIT_UNTIL - now
    logger.warning("[%s] 命中 HTTP %s，触发全局暂停 %.0f 秒", source, status, wait)


# ============ 工具函数（信息量与灵敏度） ============

def _clip_p(p: float) -> float:
    return max(1e-12, min(1.0, p))


def info_variance_from_probs(probs: Dict[str, float]) -> float:
    """V_t = Var_{X~p}[-log p(X)]"""
    ps = [_clip_p(v) for v in probs.values()]
    H = -sum(p * math.log(p) for p in ps)
    E2 = sum(p * (math.log(p) ** 2) for p in ps)
    return max(0.0, E2 - H * H)


@dataclass
class TokenProbabilityResult:
    position: int
    target_token: str
    generated_token: str
    probabilities: Dict[str, float]
    prefix: str
    success: bool
    error: Optional[str] = None


class DeepSeekSequenceTester:
    """
    抽象化的检验器：
    - 你需要显式提供 base_url（完整的 chat.completions 端点）、api_key、model 等参数；
    - 假设接口为 OpenAI/DeepSeek 兼容 JSON 结构，并且支持 logprobs/top_logprobs。
    """
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        *,
        temperature: float = 0.6,
        top_logprobs: int = 20,
        max_workers: int = 3,
        request_delay: float = 0.1,
        extra_headers: Optional[Dict[str, str]] = None,
        provider: Optional[Dict[str, Any]] = None,
        extra_payload: Optional[Dict[str, Any]] = None,
        timeout_sec: float = 30.0,
        include_assistant_prefix_metadata: bool = True,
    ) -> None:
        if not (api_key and base_url and model):
            raise ValueError("api_key / base_url / model 均为必填参数")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = float(temperature)
        self.top_logprobs = int(top_logprobs)
        self.max_workers = int(max_workers)
        self.request_delay = float(request_delay)
        self.timeout_sec = float(timeout_sec)
        self.include_assistant_prefix_metadata = include_assistant_prefix_metadata
        self.provider = dict(provider) if provider else None
        self.extra_payload = dict(extra_payload) if extra_payload else {}

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        if extra_headers:
            self.headers.update(extra_headers)

        logger.info(
            "DeepSeekSequenceTester 初始化 | workers=%s | delay=%ss | model=%s | top_logprobs=%s",
            self.max_workers, self.request_delay, self.model, self.top_logprobs
        )

    # --------------------  获取下一个 token 的概率分布  --------------------
    def get_token_probabilities(self, messages: List[Dict], max_tokens: int = 1) -> Tuple[str, Dict[str, float]]:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "logprobs": True,
            "top_logprobs": self.top_logprobs,
            "temperature": self.temperature,
            "stream": False
        }
        if self.provider:
            payload["provider"] = self.provider
        if self.extra_payload:
            payload.update(self.extra_payload)
        logger.debug("API 请求 payload: %s", payload)

        max_attempts = 2
        response: Optional[requests.Response] = None
        source = f"tester:{self.model}"
        for attempt in range(1, max_attempts + 1):
            _wait_for_global_rate_limit(source)
            try:
                response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=self.timeout_sec)
            except Exception as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 429 and attempt < max_attempts:
                    _trigger_global_rate_limit_pause(source, status=429)
                    continue
                logger.error("API 请求失败: %s", e, exc_info=True)
                raise

            if response.status_code == 429 and attempt < max_attempts:
                _trigger_global_rate_limit_pause(source, status=429)
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status == 429 and attempt < max_attempts:
                    _trigger_global_rate_limit_pause(source, status=429)
                    continue
                body = ""
                if e.response is not None:
                    try:
                        body = e.response.text
                    except Exception:
                        body = "<unavailable>"
                logger.error("API 请求失败: %s | body=%s", e, (body or "")[:500], exc_info=True)
                raise
            break

        if response is None:
            raise RuntimeError("API 请求未获得响应")

        try:
            result = response.json()
        except Exception as e:
            snippet = getattr(response, 'text', '')
            logger.error("解析 API JSON 失败: %s | 响应片段=%s", e, (snippet or "")[:500], exc_info=True)
            raise

        logger.debug("API 响应: %s", json.dumps(result, ensure_ascii=False)[:2000])

        choice = result['choices'][0]
        generated_content = choice['message']['content']
        logprobs = choice.get('logprobs', {})
        token_probabilities: Dict[str, float] = {}

        # 解析 top_logprobs + OTHER 桶
        if logprobs and 'content' in logprobs and logprobs['content']:
            token_info = logprobs['content'][0]
            # 主 token
            if 'token' in token_info and 'logprob' in token_info:
                token_probabilities[token_info['token']] = math.exp(token_info['logprob'])
            # top 列表
            for top in token_info.get('top_logprobs', []) or []:
                tok = top.get('token')
                lp = top.get('logprob')
                if tok is not None and lp is not None:
                    token_probabilities[tok] = math.exp(lp)

            # OTHER 桶：保证概率归一
            s = sum(max(0.0, v) for v in token_probabilities.values())
            other = max(0.0, 1.0 - s)
            if other > 0:
                token_probabilities["<OTHER>"] = other
            # 轻度归一，稳健处理浮点误差
            s2 = sum(token_probabilities.values())
            if s2 > 0:
                for k in list(token_probabilities.keys()):
                    token_probabilities[k] = max(0.0, token_probabilities[k] / s2)

        logger.info("位置分布（含 OTHER）：%s", token_probabilities)
        return generated_content, token_probabilities

    # --------------------  单 token 并发任务  --------------------
    def _process_single_token(self, args: Tuple[int, str, str, List[Dict]]) -> TokenProbabilityResult:
        position, target_token, target_response, base_messages = args
        logger.info("开始处理位置 %s | target_token=%s", position, target_token)
        time.sleep(self.request_delay)

        try:
            current_messages = list(base_messages)
            prefix = target_response[:position]
            if prefix:
                if self.include_assistant_prefix_metadata:
                    current_messages.append({"role": "assistant", "content": prefix, "partial": True, "prefix": True})
                else:
                    current_messages.append({"role": "assistant", "content": prefix, "partial": True, "prefix": True})

            generated_token, probabilities = self.get_token_probabilities(current_messages)
            logger.info("位置 %s 完成 | generated=%s | probs_keys=%s",
                        position, generated_token, list(probabilities.keys()))

            return TokenProbabilityResult(
                position=position,
                target_token=target_token,
                generated_token=generated_token,
                probabilities=probabilities,
                prefix=prefix,
                success=True
            )
        except Exception as e:
            logger.exception("位置 %s 处理异常", position)
            return TokenProbabilityResult(
                position=position,
                target_token=target_token,
                generated_token="",
                probabilities={},
                prefix=target_response[:position],
                success=False,
                error=str(e)
            )

    # --------------------  统计量计算（并发）  --------------------
    def calculate_sequence_test_statistics_concurrent(self, question: str, target_response: str) -> Dict:
        target_tokens = list(target_response)
        base_messages = [{"role": "user", "content": question}]
        tasks = [(i, tok, target_response, base_messages) for i, tok in enumerate(target_tokens)]

        logger.info("目标回复: %s | 共 %s 个 token(字符)", target_response, len(target_tokens))
        logger.info("开始并发计算检验统计量 | 并发数=%s", self.max_workers)

        results: List[TokenProbabilityResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {executor.submit(self._process_single_token, t): t for t in tasks}
            for fut in concurrent.futures.as_completed(future_map):
                try:
                    res = fut.result()
                    results.append(res)
                    logger.info("并发任务完成 | position=%s | success=%s", res.position, res.success)
                except Exception:
                    logger.exception("并发任务异常")

        results.sort(key=lambda x: x.position)

        observed_losses: List[float] = []
        expected_means: List[float] = []
        expected_variances: List[float] = []  # V_t
        all_probs: List[Dict[str, float]] = []
        failed_positions: List[int] = []
        failed_errors: List[str] = []

        for res in results:
            if res.success and res.probabilities:
                probs = res.probabilities
                target_tok = res.target_token

                # 观测损失
                psafe = {k: _clip_p(v) for k, v in probs.items()}
                if target_tok in psafe and psafe[target_tok] > 0:
                    observed_loss = -math.log(psafe[target_tok])
                else:
                    observed_loss = -math.log(min(psafe.values()) if psafe else 1e-12)
                observed_losses.append(observed_loss)

                # 期望均值与方差（在 p 下）
                H = -sum(p * math.log(p) for p in psafe.values())
                expected_means.append(H)
                V = info_variance_from_probs(psafe)
                expected_variances.append(V)
                all_probs.append(psafe)
                logger.debug("位置 %s | 观测损失=%.4f | H=%.4f | V=%.4f",
                             res.position, observed_loss, H, V)
            else:
                # 参考分布请求失败不属于 token 分布统计口径，直接标记失败。
                failed_positions.append(res.position)
                if res.error:
                    failed_errors.append(str(res.error))
                all_probs.append({})
                logger.warning("位置 %s 处理失败，标记本次序列统计无效", res.position)

        return {
            "observed_losses": observed_losses,
            "expected_means": expected_means,
            "expected_variances": expected_variances,
            "prob_distributions": all_probs,
            "target_tokens": list(target_response),
            "detailed_results": results,
            "total_positions": len(target_tokens),
            "success_positions": len(observed_losses),
            "failed_positions": failed_positions,
            "failed_count": len(failed_positions),
            "failed_error_samples": failed_errors[:5],
        }

    # --------------------  假设检验入口（仅保留 |Z| 偏离强度）  --------------------
    def hypothesis_test(self, question: str, target_response: str,
                        alpha: float = 0.05, use_concurrent: bool = True) -> Dict:
        logger.info("开始假设检验 | 并发模式=%s", use_concurrent)
        start = time.time()

        stats_result = self.calculate_sequence_test_statistics_concurrent(question, target_response)

        elapsed = time.time() - start
        logger.info("统计量计算完成 | 用时 %.2f 秒", elapsed)

        obs = stats_result["observed_losses"]
        exp = stats_result["expected_means"]
        var = stats_result["expected_variances"]
        total_positions = int(stats_result.get("total_positions") or len(list(target_response)))
        failed_count = int(stats_result.get("failed_count") or 0)
        success_positions = int(stats_result.get("success_positions") or 0)

        m = len(obs)
        T_obs = sum(obs)
        mu_total = sum(exp)
        sigma2_total = sum(var)
        W = math.sqrt(sigma2_total) if sigma2_total > 0 else 0.0
        Z: Optional[float]
        abs_Z: Optional[float]
        token_log_dev_per_token: Optional[float]
        conclusion: str

        if total_positions == 0:
            logger.warning("检验输入为空序列，无法计算 Z/|Z|")
            Z = None
            abs_Z = None
            token_log_dev_per_token = None
            conclusion = "序列为空，无法检验"
        elif failed_count > 0:
            logger.warning(
                "参考分布请求失败 %s/%s（success=%s），本次序列统计无效",
                failed_count,
                total_positions,
                success_positions,
            )
            Z = None
            abs_Z = None
            token_log_dev_per_token = None
            conclusion = (
                f"参考分布请求失败（{failed_count}/{total_positions}），"
                "不属于 token 分布统计口径，已丢弃本次数据"
            )
        elif W <= 0:
            logger.warning("总方差为 0（W=0），Z/|Z| 不可定义")
            Z = None
            abs_Z = None
            token_log_dev_per_token = abs(T_obs - mu_total) / m
            conclusion = "方差为 0，无法检验"
        else:
            Z = (T_obs - mu_total) / W
            abs_Z = abs(Z)
            token_log_dev_per_token = abs(T_obs - mu_total) / m
            conclusion = "偏离强度已计算（|Z| 越大，偏离越强）"
            logger.info(
                "检验结果 | Z=%.4f | |Z|=%.4f | token_log_dev=%.6f",
                Z,
                abs_Z,
                token_log_dev_per_token,
            )

        return {
            "序列长度": total_positions,
            "成功位置数": success_positions,
            "失败位置数": failed_count,
            "绝对Z统计量": abs_Z,
            "每token log偏差度": token_log_dev_per_token,
            "计算时间(秒)": elapsed,
            "是否使用并发": use_concurrent,
            "检验结论": conclusion,
        }
