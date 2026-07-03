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

import os
from pathlib import Path

# Package root directory (skill_scan/), used to locate bundled resources such as prompt/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Auto-load the .env file: check the package root first, then the current working directory
try:
    from dotenv import load_dotenv

    _loaded = False
    for _env_candidate in (Path(base_dir) / ".env", Path.cwd() / ".env"):
        if _env_candidate.exists():
            load_dotenv(_env_candidate)
            _loaded = True
            break
    del _env_candidate, _loaded
except ImportError:
    pass


def get_env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def get_env_int(key: str, default: int) -> int:
    value = get_env(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ===== Primary LLM configuration =====
DEFAULT_MODEL = get_env("DEFAULT_MODEL", "deepseek/deepseek-v3.2-exp")
DEFAULT_BASE_URL = get_env("DEFAULT_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL_CONTEXT_WINDOW = get_env_int("DEFAULT_MODEL_CONTEXT_WINDOW", 128000)

# ===== Specialized LLM configuration =====
THINKING_MODEL = get_env("THINKING_MODEL", "google/gemini-2.5-pro")
THINKING_BASE_URL = get_env("THINKING_BASE_URL", DEFAULT_BASE_URL)
THINKING_API_KEY = get_env("THINKING_API_KEY")
THINKING_MODEL_CONTEXT_WINDOW = get_env_int("THINKING_MODEL_CONTEXT_WINDOW", 128000)

CODING_MODEL = get_env("CODING_MODEL", "anthropic/claude-sonnet-4.5")
CODING_BASE_URL = get_env("CODING_BASE_URL", DEFAULT_BASE_URL)
CODING_API_KEY = get_env("CODING_API_KEY")
CODING_MODEL_CONTEXT_WINDOW = get_env_int("CODING_MODEL_CONTEXT_WINDOW", 128000)

FAST_MODEL = get_env("FAST_MODEL", "google/gemini-2.0-flash-exp")
FAST_BASE_URL = get_env("FAST_BASE_URL", DEFAULT_BASE_URL)
FAST_API_KEY = get_env("FAST_API_KEY")
FAST_MODEL_CONTEXT_WINDOW = get_env_int("FAST_MODEL_CONTEXT_WINDOW", 128000)

# ===== Debug and logging configuration =====
LAMINAR_API_KEY = get_env("LAMINAR_API_KEY")
LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
