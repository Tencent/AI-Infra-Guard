import os
from typing import Optional
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


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """获取环境变量，如果不存在则返回默认值"""
    return os.environ.get(key, default)


# ===== 主要 LLM 配置 =====
DEFAULT_MODEL = get_env("DEFAULT_MODEL", "deepseek/deepseek-v3.2-exp")
DEFAULT_BASE_URL = get_env("DEFAULT_BASE_URL", "https://openrouter.ai/api/v1")

# ===== 专用 LLM 配置 =====
# Thinking 模型
THINKING_MODEL = get_env("THINKING_MODEL", "google/gemini-2.5-pro")
THINKING_BASE_URL = get_env("THINKING_BASE_URL", DEFAULT_BASE_URL)
THINKING_API_KEY = get_env("THINKING_API_KEY")  # 可选，不设置则使用主 API Key

# Coding 模型
CODING_MODEL = get_env("CODING_MODEL", "anthropic/claude-sonnet-4.5")
CODING_BASE_URL = get_env("CODING_BASE_URL", DEFAULT_BASE_URL)
CODING_API_KEY = get_env("CODING_API_KEY")  # 可选，不设置则使用主 API Key

# Fast 模型
FAST_MODEL = get_env("FAST_MODEL", "google/gemini-2.0-flash-exp")
FAST_BASE_URL = get_env("FAST_BASE_URL", DEFAULT_BASE_URL)
FAST_API_KEY = get_env("FAST_API_KEY")  # 可选，不设置则使用主 API Key

# ===== Debug 和日志配置 =====
LAMINAR_API_KEY = get_env("LAMINAR_API_KEY")
LOG_LEVEL = get_env("LOG_LEVEL", "INFO")
