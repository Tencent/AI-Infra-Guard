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

from __future__ import annotations

import threading
import time

import openai

from skill_scan.utils.config import get_env
from skill_scan.utils.loging import logger
from skill_scan.utils.tool_format_fix import (
    has_runaway_tail,
    normalize_tool_calls,
    strip_runaway_tail,
)

# Transient failures of a single request are retried (5 trials, like mcp-scan);
# authentication / bad-request errors are raised at once. ``TimeoutError`` is
# raised by ``chat_stream`` when the whole response exceeds ``stream_timeout``.
_RETRYABLE_ERRORS = (
    TimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)
_MAX_TRIALS = 5
_RATE_LIMIT_BACKOFF = (8.0, 16.0, 32.0, 60.0)
# Check the reply for a runaway run of closing tags every this many characters.
_RUNAWAY_CHECK_STEP = 500


class LLM:
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        context_window: int | None = None,
        default_headers: dict | None = None,
        stream_timeout: float = 300,
    ):
        self.model = model
        self.model_name = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60,
            default_headers=default_headers if default_headers else None,
        )
        self.context_window = context_window
        self.stream_timeout = stream_timeout
        self._usage_lock = None
        self._usage_totals = None
        self._ensure_usage_state()

    def _ensure_usage_state(self) -> tuple[threading.Lock, dict[str, int]]:
        """Lazily initialize usage counters for ``object.__new__(LLM)`` test doubles."""
        lock = getattr(self, "_usage_lock", None)
        totals = getattr(self, "_usage_totals", None)
        if lock is None or totals is None:
            lock = threading.Lock()
            totals = {
                "calls": 0,
                "prompt_tokens": 0,
                "cached_tokens": 0,
                "uncached_prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "usage_missing_calls": 0,
            }
            self._usage_lock = lock
            self._usage_totals = totals
        return lock, totals

    def get_usage_stats(self) -> dict[str, int]:
        """Return a thread-safe snapshot of cumulative LLM token usage."""
        lock, totals = self._ensure_usage_state()
        with lock:
            return dict(totals)

    def reset_usage_stats(self) -> None:
        """Reset cumulative LLM token usage counters to zero."""
        lock, totals = self._ensure_usage_state()
        with lock:
            for key in totals:
                totals[key] = 0

    def _record_usage(self, usage: dict | None) -> None:
        """Accumulate normalized usage metrics from a single ``chat`` invocation."""
        lock, totals = self._ensure_usage_state()
        with lock:
            totals["calls"] += 1
            if not isinstance(usage, dict):
                totals["usage_missing_calls"] += 1
                return
            prompt = int(usage.get("prompt_tokens") or 0)
            cached = int(usage.get("cached_tokens") or 0)
            uncached = max(0, prompt - cached)
            completion = int(usage.get("completion_tokens") or 0)
            total = usage.get("total_tokens")
            total_int = int(total) if total is not None else (prompt + completion)
            if (
                usage.get("prompt_tokens") is None
                and usage.get("completion_tokens") is None
                and usage.get("total_tokens") is None
            ):
                totals["usage_missing_calls"] += 1
            totals["prompt_tokens"] += prompt
            totals["cached_tokens"] += cached
            totals["uncached_prompt_tokens"] += uncached
            totals["completion_tokens"] += completion
            totals["total_tokens"] += total_int

    def chat(self, message: list[dict], p=False, ret_usage=False) -> str | tuple[str, dict]:
        ret = ""
        usage = None
        retry = 0

        while True:
            ret, usage = self._chat_stream_with_retry(message)
            if ret != "":
                break
            else:
                retry += 1
                logger.error(f"LLM chat error, retry {retry}")
                time.sleep(1.3)
                if retry > 5:
                    logger.error("LLM chat error, retry 5 times, exit")
                    ret = "Failed to connect to the LLM after 5 retries; model output is empty. Please wait a minute and try again."
                    break
        self._record_usage(usage)
        ret, fixed = normalize_tool_calls(ret)
        if fixed:
            logger.info("Normalized malformed tool call in LLM response")
        if p:
            print(ret)

        if ret_usage:
            return ret, usage
        return ret

    def _chat_stream_with_retry(self, message: list[dict]) -> tuple[str, dict]:
        for attempt in range(_MAX_TRIALS):
            try:
                return self.chat_stream(message)
            except _RETRYABLE_ERRORS as exc:
                if attempt >= _MAX_TRIALS - 1:
                    raise
                if isinstance(exc, openai.RateLimitError):
                    delay = _RATE_LIMIT_BACKOFF[min(attempt, len(_RATE_LIMIT_BACKOFF) - 1)]
                else:
                    delay = min(2.0**attempt, 8.0)
                logger.error(
                    f"LLM chat failed (trial {attempt + 1}/{_MAX_TRIALS}): "
                    f"{type(exc).__name__}: {exc}; backoff {delay:.1f}s"
                )
                time.sleep(delay)
        raise RuntimeError("unreachable")

    def chat_stream(self, message: list[dict]) -> tuple[str, dict]:
        started = time.monotonic()
        request_options = {}
        reasoning_effort = (get_env("REASONING_EFFORT") or "").strip()
        if reasoning_effort:
            request_options["reasoning_effort"] = reasoning_effort
        response = self.client.chat.completions.create(
            model=self.model,
            messages=message,
            stream=True,
            stream_options={"include_usage": True},
            **request_options,
        )

        ret = ""
        usage = None
        next_check = _RUNAWAY_CHECK_STEP

        for chunk in response:
            # A provider may keep a broken stream alive with empty heartbeat
            # chunks. The SDK read timeout resets for every chunk, so enforce
            # a deadline for the complete response as well.
            deadline = getattr(self, "stream_timeout", 300)
            if time.monotonic() - started > deadline:
                close = getattr(response, "close", None)
                if close:
                    close()
                raise TimeoutError(
                    f"LLM streaming response exceeded the {deadline}-second deadline"
                )
            _usage = getattr(chunk, "usage", None)
            if _usage:
                usage = self._normalize_usage(_usage)

            choices = getattr(chunk, "choices", None)
            if not isinstance(choices, list) or not choices:
                continue
            choice = choices[0]

            delta = getattr(choice, "delta", None)
            if not delta:
                continue

            content = getattr(delta, "content", None)
            if content:
                ret += content
                if len(ret) >= next_check:
                    next_check = len(ret) + _RUNAWAY_CHECK_STEP
                    if has_runaway_tail(ret):
                        # The model keeps writing closing tags after a finished
                        # call until the server cuts the stream (minutes).
                        close = getattr(response, "close", None)
                        if close:
                            close()
                        received = len(ret)
                        ret = strip_runaway_tail(ret)
                        logger.warning(
                            "LLM reply ended in a run of closing tags; stream cut, "
                            f"kept {len(ret)} of {received} characters received"
                        )
                        break

        return ret, usage

    def _normalize_usage(self, usage) -> dict | None:
        if not usage:
            return None

        prompt_details = getattr(usage, "prompt_tokens_details", None)
        cached = (
            getattr(prompt_details, "cached_tokens", None)
            if prompt_details is not None
            else None
        )
        if cached is None and isinstance(prompt_details, dict):
            cached = prompt_details.get("cached_tokens")
        if cached is None:
            cached = getattr(usage, "cached_tokens", None)
        if cached is None:
            cached = getattr(usage, "prompt_cache_hit_tokens", None)

        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "cached_tokens": cached,
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
