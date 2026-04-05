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

import os
from pathlib import Path

# Configuration settings
# 获取项目根目录（config.py 在 utils/ 目录下，所以需要获取父目录）
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 自动加载 .env 文件
try:
    from dotenv import load_dotenv

    env_file = Path(base_dir) / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv 未安装，跳过
    pass


def get_env(key: str, default: str | None = None) -> str | None:
    """获取环境变量，如果不存在则返回默认值"""
    return os.environ.get(key, default)


def get_env_int(key: str, default: int) -> int:
    """获取整型环境变量，非法值时回退到默认值"""
    value = get_env(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ===== 主要 LLM 配置 =====
DEFAULT_MODEL = get_env("DEFAULT_MODEL", "deepseek/deepseek-v3.2-exp")
DEFAULT_BASE_URL = get_env("DEFAULT_BASE_URL", "https://openrouter.ai/api/v1")
# 上下文窗口仅作为压缩阈值的参考值，用户可按实际模型覆盖。
DEFAULT_MODEL_CONTEXT_WINDOW = get_env_int("DEFAULT_MODEL_CONTEXT_WINDOW", 128000)

# ===== 专用 LLM 配置 =====
# Thinking 模型
THINKING_MODEL = get_env("THINKING_MODEL", "google/gemini-2.5-pro")
THINKING_BASE_URL = get_env("THINKING_BASE_URL", DEFAULT_BASE_URL)
THINKING_API_KEY = get_env("THINKING_API_KEY")  # 可选，不设置则使用主 API Key
THINKING_MODEL_CONTEXT_WINDOW = get_env_int("THINKING_MODEL_CONTEXT_WINDOW", 128000)

# Coding 模型
CODING_MODEL = get_env("CODING_MODEL", "anthropic/claude-sonnet-4.5")
CODING_BASE_URL = get_env("CODING_BASE_URL", DEFAULT_BASE_URL)
CODING_API_KEY = get_env("CODING_API_KEY")  # 可选，不设置则使用主 API Key
CODING_MODEL_CONTEXT_WINDOW = get_env_int("CODING_MODEL_CONTEXT_WINDOW", 128000)


# Fast 模型
FAST_MODEL = get_env("FAST_MODEL", "google/gemini-2.0-flash-exp")
FAST_BASE_URL = get_env("FAST_BASE_URL", DEFAULT_BASE_URL)
FAST_API_KEY = get_env("FAST_API_KEY")  # 可选，不设置则使用主 API Key
FAST_MODEL_CONTEXT_WINDOW = get_env_int("FAST_MODEL_CONTEXT_WINDOW", 128000)

# ===== Debug 和日志配置 =====
LAMINAR_API_KEY = get_env("LAMINAR_API_KEY")
LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
