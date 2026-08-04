# SkillJack

Persistent Skill Backdoors in Self-Evolving Agents

## Repository Structure

```
SkillJack/
├── skilljack/                    # Core code
│   ├── __init__.py
│   ├── config.py                 # Configuration (API keys, paths, params)
│   ├── llm_adapter.py            # LLM API wrapper (OpenAI-compatible)
│   ├── llm_skill_router.py       # LLM-native skill routing
│   ├── poison_generator.py       # Disguised poisoned trajectories (small-scale)
│   ├── naive_payload_generator.py    # Naive (directly malicious) trajectories
│   ├── large_scale_generator.py  # Disguised trajectories (large-scale)
│   ├── large_scale_naive_generator.py   # Naive trajectories (large-scale)
│   ├── improved_unauth_transfer.py    # Improved unauthorized_transfer trajectories
│   ├── extract_skills.py         # SkillX extraction pipeline runner
│   ├── security_analyzer.py      # Pattern detection + LLM judge
│   ├── retrieval_test.py         # LLM-native routing + persistence test
│   ├── execution_verification.py # End-to-end mock-based execution verification
│   ├── run_full_experiments.py   # Main experiments
│   ├── run_extended_experiments.py   # Extended experiments (ablation, defense)
│   └── cross_system_experiment.py    # Cross-system generalization experiment
├── data/
│   └── poisoned_trajectories/    # Pre-generated trajectory datasets (JSONL)
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure LLM API

```bash
cp .env.example .env
# Edit .env with your API key and endpoint
```

Or set environment variables directly:

```bash
export SKILLJACK_API_KEY="your-api-key"
export SKILLJACK_BASE_URL="https://api.openai.com/v1/chat/completions"
export SKILLJACK_MODEL="deepseek-chat"
```

### 3. Install Target Systems (External)

SkillJack uses two unmodified target systems for experiments:

- **SkillX**: Main target system
- **Anything2Skill / AutoSkill**: Cross-system validation

Clone them as sibling directories:

```bash
cd ..
git clone <skillx-repo> SkillX
git clone <autoskill-repo> anything2skill
```

### 4. Run Experiments

```bash
# Main experiments
python -m skilljack.run_full_experiments --exp all

# Extended experiments (ablation, defense)
python -m skilljack.run_extended_experiments --exp all

# Cross-system experiment (requires Anything2Skill)
python -m skilljack.cross_system_experiment
```

Pre-generated trajectory datasets are provided in `data/poisoned_trajectories/`.

## Dataset

| Component | Count | Description |
|-----------|-------|-------------|
| Disguised poisoned trajectories | 65 | 20 data_exfil + 15 priv_esc + 15 unauth_transfer + 15 backdoor |
| Naive poisoned trajectories | 65 | Directly malicious, 1:1 paired with disguised |
| Clean trajectories | 20 | Benign AppWorld tasks |
| Improved unauthorized_transfer | 15 | Structural malice (fee skimming, token leakage, etc.) |

## License

This project is for research purposes only.
