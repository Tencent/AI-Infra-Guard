"""
Configuration for SkillJack experiments.

All settings can be overridden via environment variables.
Copy this file to config_local.py and adjust as needed.
"""
from __future__ import annotations

import os


# ── LLM API Configuration ────────────────────────────────────────────────
# Set these via environment variables or edit config_local.py

# Your LLM API endpoint (OpenAI-compatible format)
LLM_API_KEY = os.environ.get("SKILLJACK_API_KEY", "your-api-key-here")
LLM_BASE_URL = os.environ.get("SKILLJACK_BASE_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.environ.get("SKILLJACK_MODEL", "deepseek-chat")
LLM_MAX_TOKENS = int(os.environ.get("SKILLJACK_MAX_TOKENS", "8192"))
LLM_TEMPERATURE = float(os.environ.get("SKILLJACK_TEMPERATURE", "0.3"))
LLM_TIMEOUT = int(os.environ.get("SKILLJACK_TIMEOUT", "120"))
LLM_MAX_RETRIES = int(os.environ.get("SKILLJACK_MAX_RETRIES", "5"))


# ── SkillX Integration ────────────────────────────────────────────────────
# Path to a local SkillX installation (unmodified)
# SkillX: https://arxiv.org/abs/2604.04804 (ICML 2026)
SKILLX_PATH = os.environ.get("SKILLX_PATH", "../SkillX")


# ── AutoSkill Integration (for cross-system experiments) ──────────────────
# Path to a local Anything2Skill / AutoSkill installation
# AutoSkill: https://arxiv.org/abs/2606.09316
AUTOSKILL_PATH = os.environ.get("AUTOSKILL_PATH", "../anything2skill")


# ── Data Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "poisoned_trajectories")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")  # generated at runtime


# ── SkillX Skill DB (clean baseline) ──────────────────────────────────────
# Path to SkillX's vanilla skill database for clean baseline skills
SKILLX_DB_PATH = os.environ.get(
    "SKILLX_DB_PATH",
    os.path.join(SKILLX_PATH, "skillx_db", "appworld", "vanilla-iter1", "func_atomic_skills.json")
)


# ── Experiment Parameters ─────────────────────────────────────────────────
REWARD_THRESHOLD = 0.999        # Trajectory filter: only reward >= this
EXTRACTION_BATCH_SIZE = 5       # Batch size for plan/skill extraction
EXTRACTION_MAX_CONCURRENT = 3   # Max concurrent LLM calls during extraction
ROUTER_TOP_K = 3                # Number of skills the router selects per query
AGENT_MAX_STEPS = 5             # Max agent interaction steps per task
LLM_JUDGE_TEMPERATURE = 0.1     # Temperature for LLM judge (low = deterministic)


# ── Attack Types ──────────────────────────────────────────────────────────
ATTACK_TYPES = [
    "data_exfiltration",
    "privilege_escalation",
    "unauthorized_transfer",
    "persistent_backdoor",
]
