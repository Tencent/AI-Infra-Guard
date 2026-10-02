import asyncio
import unittest
from unittest.mock import patch

from mcp_scan.utils.llm_retry import (
    acall_with_retry,
    backoff_delay,
    call_with_retry,
    is_rate_limit_error,
    retry_after_seconds,
)


class _RateLimitError(Exception):
    def __init__(self, message="Rate limit exceeded", status_code=429, headers=None):
        super().__init__(message)
        self.status_code = status_code
        if headers is not None:
            self.response = _Response(headers)


class _Response:
    def __init__(self, headers):
        self.headers = headers


class RateLimitDetectionTests(unittest.TestCase):
    def test_status_code_429_detected(self):
        self.assertTrue(is_rate_limit_error(_RateLimitError()))

    def test_wrapped_429_without_message_detected(self):
        # SDK 把 429 包装成不含限流字样的异常，状态码仍在
        self.assertTrue(
            is_rate_limit_error(_RateLimitError(message="gateway error", status_code=429))
        )

    def test_status_code_42900_detected(self):
        # 部分网关用自定义码 42900 表示限流
        self.assertTrue(
            is_rate_limit_error(_RateLimitError(message="gateway error", status_code=42900))
        )

    def test_retry_after_header_implies_rate_limited(self):
        # 无限流字样、状态码也非 429，但携带 Retry-After —— 按限流处理
        exc = _RateLimitError(
            message="service temporarily unavailable",
            status_code=503,
            headers={"retry-after": "30"},
        )
        self.assertTrue(is_rate_limit_error(exc))

    def test_message_markers_detected(self):
        for message in ("Too many requests", "quota exceeded", "RESOURCE_EXHAUSTED", "HTTP 429"):
            self.assertTrue(is_rate_limit_error(Exception(message)), message)

    def test_non_rate_error_not_detected(self):
        self.assertFalse(is_rate_limit_error(Exception("invalid api key")))
        self.assertFalse(
            is_rate_limit_error(_RateLimitError(message="internal error", status_code=500))
        )


class RetryAfterTests(unittest.TestCase):
    def test_extracts_retry_after_seconds(self):
        exc = _RateLimitError(headers={"retry-after": "12"})
        self.assertEqual(retry_after_seconds(exc), 12.0)

    def test_missing_headers_returns_none(self):
        self.assertIsNone(retry_after_seconds(_RateLimitError()))
        self.assertIsNone(retry_after_seconds(Exception("boom")))

    def test_invalid_value_returns_none(self):
        exc = _RateLimitError(headers={"retry-after": "not-a-number"})
        self.assertIsNone(retry_after_seconds(exc))


class BackoffScheduleTests(unittest.TestCase):
    def test_rate_limit_backoff_schedule(self):
        self.assertEqual(backoff_delay(0, True, None), 8.0)
        self.assertEqual(backoff_delay(1, True, None), 16.0)
        self.assertEqual(backoff_delay(2, True, None), 32.0)
        self.assertEqual(backoff_delay(99, True, None), 60.0)

    def test_retry_after_honored_and_capped(self):
        self.assertEqual(backoff_delay(0, True, 20.0), 20.0)
        self.assertEqual(backoff_delay(0, True, 300.0), 60.0)
        self.assertEqual(backoff_delay(0, True, 0.0), 8.0)

    def test_other_errors_exponential(self):
        self.assertEqual(backoff_delay(0, False, None), 1.0)
        self.assertEqual(backoff_delay(1, False, None), 2.0)
        self.assertEqual(backoff_delay(3, False, None), 8.0)


class _NoSleep:
    """替换 sleep，记录等待时长并立即返回。"""

    def __init__(self):
        self.delays = []

    def sleep_sync(self, seconds):
        self.delays.append(seconds)

    async def sleep_async(self, seconds):
        self.delays.append(seconds)


class CallWithRetryTests(unittest.TestCase):
    def setUp(self):
        self.no_sleep = _NoSleep()

    def test_recovers_after_rate_limit(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise _RateLimitError()
            return "ok"

        with (
            patch("mcp_scan.utils.llm_retry.time.sleep", self.no_sleep.sleep_sync),
        ):
            result = call_with_retry(flaky, what="test")

        self.assertEqual(result, "ok")
        self.assertEqual(self.no_sleep.delays, [8.0, 16.0])

    def test_raises_after_max_trials(self):
        def always_fails():
            raise _RateLimitError()

        with patch("mcp_scan.utils.llm_retry.time.sleep", self.no_sleep.sleep_sync):
            with self.assertRaises(_RateLimitError):
                call_with_retry(always_fails, what="test")

        self.assertEqual(len(self.no_sleep.delays), 4)

    def test_non_rate_error_backoff(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise Exception("connection reset")
            return 42

        with patch("mcp_scan.utils.llm_retry.time.sleep", self.no_sleep.sleep_sync):
            self.assertEqual(call_with_retry(flaky), 42)
        self.assertEqual(self.no_sleep.delays, [1.0])

    def test_retry_after_from_header_used(self):
        exc = _RateLimitError(headers={"retry-after": "25"})
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise exc
            return "ok"

        with patch("mcp_scan.utils.llm_retry.time.sleep", self.no_sleep.sleep_sync):
            self.assertEqual(call_with_retry(flaky), "ok")
        self.assertEqual(self.no_sleep.delays, [25.0])


class AsyncCallWithRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_recovers_after_rate_limit(self):
        no_sleep = _NoSleep()
        calls = []

        async def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise _RateLimitError()
            return "ok"

        with patch("mcp_scan.utils.llm_retry.asyncio.sleep", no_sleep.sleep_async):
            result = await acall_with_retry(flaky, what="test")

        self.assertEqual(result, "ok")
        self.assertEqual(no_sleep.delays, [8.0])

    async def test_raises_after_max_trials(self):
        no_sleep = _NoSleep()

        async def always_fails():
            raise _RateLimitError()

        with patch("mcp_scan.utils.llm_retry.asyncio.sleep", no_sleep.sleep_async):
            with self.assertRaises(_RateLimitError):
                await acall_with_retry(always_fails, what="test")

        self.assertEqual(len(no_sleep.delays), 4)


if __name__ == "__main__":
    unittest.main()
