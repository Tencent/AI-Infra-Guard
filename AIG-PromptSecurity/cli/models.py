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

from cli.model_utils import BaseLLM
from cli.model_utils.openailike import OpenaiAlikeModel

def create_model(model_name: str, base_url: str, api_key: str, max_concurrent: int) -> BaseLLM:
    """创建模型实例"""
    return OpenaiAlikeModel(
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        max_concurrent=max_concurrent
    )


def complete(model_name: str, base_url: str, api_key: str, prompt: str, max_concurrent: int = 1, on_attempt=None) -> str:
    """Send one prompt to an OpenAI-compatible model and return the reply text."""
    text = create_model(model_name, base_url, api_key, max_concurrent).generate(prompt, on_attempt=on_attempt)
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("模型没有返回内容")
    return text.strip()