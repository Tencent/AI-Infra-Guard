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

import time

import openai

from skill_scan.utils.loging import logger


class LLM:
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        context_window: int | None = None,
        default_headers: dict | None = None,
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
        self.temperature = 0.7
        self.context_window = context_window

    def chat(self, message: list[dict], p=False, ret_usage=False) -> str | tuple[str, dict]:
        ret = ""
        usage = None
        retry = 0

        while True:
            ret, usage = self.chat_stream(message)
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
        if p:
            print(ret)

        if ret_usage:
            return ret, usage
        return ret

    def chat_stream(self, message: list[dict]) -> tuple[str, dict]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=message,
            temperature=self.temperature,
            stream=True,
            stream_options={"include_usage": True},
        )

        ret = ""
        usage = None

        for chunk in response:
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

        return ret, usage

    def _normalize_usage(self, usage) -> dict | None:
        if not usage:
            return None

        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
