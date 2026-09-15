# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

"""限流感知重试、退避与熔断共享状态的单元测试

运行: cd AIG-PromptSecurity && uv run pytest tests/ -v
"""

import asyncio
import time

import pytest

from cli.model_utils.openailike import (
    OpenaiAlikeModel,
    _is_rate_limit_error,
    _retry_after_seconds,
)


class _RateLimitError(Exception):
    """模拟网关返回的 429 文案异常"""


class _FakeResponse:
    def __init__(self, headers=None):
        self.headers = headers or {}


class _FakeHeaders(dict):
    """行为兼容 httpx.Headers 的最小 dict"""


def _fake_response(headers):
    resp = _FakeResponse()
    resp.headers = _FakeHeaders(headers)
    return resp


class _APIStatusLikeError(Exception):
    """模拟 openai.APIStatusError：response.headers 携带 Retry-After"""

    def __init__(self, message, headers):
        super().__init__(message)
        self.response = _fake_response(headers)


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeChatResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, create_fn):
        self._create_fn = create_fn

    def create(self, **kwargs):
        return self._create_fn(**kwargs)


class _FakeChat:
    def __init__(self, create_fn):
        self.completions = _FakeCompletions(create_fn)


class _FakeAsyncCompletions:
    def __init__(self, create_fn):
        self._create_fn = create_fn

    async def create(self, **kwargs):
        return self._create_fn(**kwargs)


class _FakeAsyncChat:
    def __init__(self, create_fn):
        self.completions = _FakeAsyncCompletions(create_fn)


class _FakeAsyncClient:
    def __init__(self, create_fn):
        self.chat = _FakeAsyncChat(create_fn)


class _FakeClient:
    def __init__(self, create_fn):
        self.chat = _FakeChat(create_fn)


def _make_model(create_fn):
    """构造不触网、不 __init__ 的模型实例（绕开 BaseLLM 的客户端初始化）"""
    m = OpenaiAlikeModel.__new__(OpenaiAlikeModel)
    m.model_name = "fake-target"
    m.default_params = {}
    m.max_trial = 3
    m.base_wait_seconds = 1.0
    m.max_wait_seconds = 60.0
    m.rate_limit_base_wait_seconds = 8.0
    m._consecutive_rate_limit_failures = 0
    import threading

    m._rate_limit_lock = threading.Lock()
    m.semaphore = asyncio.Semaphore(1)
    m.client = _FakeClient(create_fn)
    m.async_client = _FakeAsyncClient(create_fn)
    return m


# ---------------------------------------------------------------------------
# _is_rate_limit_error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Error code: 429 - Rate limit reached for requests", True),
        ("Too Many Requests", True),
        ("Rate limit exceeded, please slow down", True),
        ("Quota exceeded for this API key", True),
        ("You have exceeded your requests per minute limit", True),
        # 不应误判：请求 ID / 无关数字中的 "429" 不算限流
        ("Request id: req_429ab3c failed", False),
        ("Connection timeout after 4290ms", False),
        ("404 not found", False),
        ("Internal server error", False),
        ("model overloaded, try again later", False),
    ],
)
def test_rate_limit_detection(message, expected):
    assert _is_rate_limit_error(_RateLimitError(message)) is expected


# ---------------------------------------------------------------------------
# _retry_after_seconds
# ---------------------------------------------------------------------------


def test_retry_after_from_response_headers():
    """openai SDK 3.x: Retry-After 位于 exc.response.headers"""
    err = _APIStatusLikeError(
        "Error code: 429", {"Retry-After": "25"}
    )
    assert _retry_after_seconds(err, 5.0) == 25.0


def test_retry_after_ms_from_response_headers():
    err = _APIStatusLikeError(
        "Error code: 429", {"Retry-After-Ms": "3000"}
    )
    assert _retry_after_seconds(err, 5.0) == 3.0


def test_retry_after_from_exception_attr():
    class _Attr(Exception):
        retry_after = 30.0

    assert _retry_after_seconds(_Attr("429"), 5.0) == 30.0


def test_retry_after_from_message_text():
    err = Exception("Rate limit exceeded, retry after 12 seconds")
    assert _retry_after_seconds(err, 5.0) == 12.0


def test_retry_after_falls_back_to_default():
    assert _retry_after_seconds(_RateLimitError("429 rate limit"), 8.0) == 8.0


def test_retry_after_ignores_absurd_values():
    """超过 600s 的建议值视为不可信，回退默认值"""
    err = _APIStatusLikeError("429", {"Retry-After": "99999"})
    assert _retry_after_seconds(err, 8.0) == 8.0


# ---------------------------------------------------------------------------
# generate() 退避与计数
# ---------------------------------------------------------------------------


def test_backoff_schedule_for_rate_limit(monkeypatch):
    """限流错误使用 8s 起步指数退避"""
    waits = []
    monkeypatch.setattr(time, "sleep", lambda w: waits.append(w))
    m = _make_model(lambda **kw: (_ for _ in ()).throw(_RateLimitError("Error code: 429")))
    m.generate(prompt="hi")
    assert waits == [8.0, 16.0, 32.0]


def test_backoff_schedule_for_generic_error(monkeypatch):
    waits = []
    monkeypatch.setattr(time, "sleep", lambda w: waits.append(w))
    m = _make_model(lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    m.generate(prompt="hi")
    assert waits == [1.0, 2.0, 4.0]


def test_retry_then_success(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(time, "sleep", lambda w: None)

    def create(**kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _RateLimitError("Rate limit reached")
        return _FakeChatResponse("ok")

    m = _make_model(create)
    assert m.generate(prompt="hi") == "ok"
    assert calls["n"] == 2
    assert m.get_consecutive_rate_limit_failures() == 0


def test_consecutive_failures_accumulate_and_reset(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda w: None)
    m = _make_model(lambda **kw: (_ for _ in ()).throw(_RateLimitError("429 too many requests")))
    m.generate(prompt="hi")
    assert m.get_consecutive_rate_limit_failures() == 3
    m.reset_rate_limit_failures()
    assert m.get_consecutive_rate_limit_failures() == 0


# ---------------------------------------------------------------------------
# 熔断器与模型实例共享状态（review 要求的核心断言）
# ---------------------------------------------------------------------------


class _FakeMetric:
    def __init__(self):
        self.score = 0.0
        self.reason = "fake metric reason"

    async def a_measure(self, test_case):
        self.score = 0.0
        self.reason = "fake metric reason"


def _make_red_teamer(threshold=3):
    from deepteam.red_teamer.red_teamer import RedTeamer

    rt = RedTeamer.__new__(RedTeamer)
    rt.rate_limit_circuit_breaker_threshold = threshold
    rt.asyncRandomId = "test"
    rt.semaphore = asyncio.Semaphore(1)
    rt._translation_cache = {}
    return rt


def _make_attack():
    from deepteam.attacks.attack_simulator import SimulatedAttack
    from deepteam.vulnerabilities.bias.types import BiasType

    return SimulatedAttack(
        vulnerability="bias",
        vulnerability_type=BiasType.RACE,
        original_input="test",
        input="test",
    ), BiasType.RACE


async def _ok_callback(inp):
    return "normal answer"


@pytest.mark.asyncio
async def test_circuit_breaker_trips_after_consecutive_429():
    """连续 N 次限流失败后，熔断器触发：用例被跳过且不再发请求"""
    rt = _make_red_teamer(threshold=3)
    m = _make_model(lambda **kw: (_ for _ in ()).throw(_RateLimitError("Error code: 429 - rate limit")))
    callback = m.a_generate
    # 模拟连续失败达到阈值（绕开真实退避等待）
    for _ in range(3):
        m.note_rate_limit_failure()

    attack, vuln_type = _make_attack()
    tc = await rt._a_attack(
        model_callback=callback,
        simulated_attack=attack,
        vulnerability="bias",
        vulnerability_type=vuln_type,
        metrics_map={vuln_type: _FakeMetric},
        ignore_errors=True,
    )
    assert tc.error is not None
    assert "Skipped" in tc.error
    assert "circuit breaker" in tc.error


@pytest.mark.asyncio
async def test_circuit_breaker_not_tripped_below_threshold():
    """计数低于阈值时不跳过，正常走 model_callback 路径"""
    rt = _make_red_teamer(threshold=3)
    m = _make_model(lambda **kw: _FakeChatResponse("fine"))
    callback = m.a_generate
    m.note_rate_limit_failure()  # 1 < 3

    attack, vuln_type = _make_attack()
    tc = await rt._a_attack(
        model_callback=callback,
        simulated_attack=attack,
        vulnerability="bias",
        vulnerability_type=vuln_type,
        metrics_map={vuln_type: _FakeMetric},
        ignore_errors=True,
    )
    assert tc.error is None
    assert tc.actual_output == "fine"


@pytest.mark.asyncio
async def test_circuit_breaker_reset_on_success():
    """成功响应后模型侧计数清零，熔断解除"""
    rt = _make_red_teamer(threshold=3)
    m = _make_model(lambda **kw: _FakeChatResponse("fine"))
    callback = m.a_generate
    for _ in range(2):
        m.note_rate_limit_failure()
    assert m.get_consecutive_rate_limit_failures() == 2

    attack, vuln_type = _make_attack()
    tc = await rt._a_attack(
        model_callback=callback,
        simulated_attack=attack,
        vulnerability="bias",
        vulnerability_type=vuln_type,
        metrics_map={vuln_type: _FakeMetric},
        ignore_errors=True,
    )
    assert tc.error is None
    # 成功路径触发 _reset_consecutive_rate_limit_failures
    assert m.get_consecutive_rate_limit_failures() == 0


@pytest.mark.asyncio
async def test_circuit_breaker_graceful_without_model_instance():
    """model_callback 不是 bound method 时熔断器退化为不生效（保持原行为）"""
    rt = _make_red_teamer(threshold=3)
    attack, vuln_type = _make_attack()
    tc = await rt._a_attack(
        model_callback=_ok_callback,
        simulated_attack=attack,
        vulnerability="bias",
        vulnerability_type=vuln_type,
        metrics_map={vuln_type: _FakeMetric},
        ignore_errors=True,
    )
    assert tc.error is None
    assert tc.actual_output == "normal answer"
