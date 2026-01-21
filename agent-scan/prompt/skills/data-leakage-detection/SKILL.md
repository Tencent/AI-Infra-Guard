# Data Leakage Detection Skill

**Version:** 1.0.0  
**Category:** Security Scanning  
**Type:** Black-box / Agent Response Analysis

## Overview

Detects sensitive information exposure in AI agent responses:

- **Secrets**: API keys, tokens, passwords, bearer tokens
- **System Info**: Prompts, configs, internal instructions
- **Credentials**: Database connection strings, private keys
- **PII**: Emails, phone numbers, addresses
- **Debug Info**: File paths, env vars, internal endpoints

## Quick Start

```python
# Full scan with default patterns
data_leakage_scan(prompts_file="static", use_regex=True)

# Category-specific scan
data_leakage_scan(
    prompts_file="static",
    category_filter=["secrets_credentials"],
    use_regex=True
)
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompts_file` | str | "static" or path to YAML file |
| `prompts` | list | Explicit list of test prompts |
| `category_filter` | list | Filter categories: secrets_credentials, system_prompt_disclosure, pii_privacy, internal_config, rag_kb_disclosure, prompt_injection |
| `use_regex` | bool | Enable regex pattern detection (default: True) |
| `use_llm_judge` | bool | Enable LLM semantic analysis (default: False) |
| `custom_patterns` | list | Additional regex patterns |

## Evaluators

| Evaluator | Speed | Use Case |
|-----------|-------|----------|
| **RegexEvaluator** | Fast | Standard secret formats (API keys, tokens, connection strings) |
| **LLMEvaluator** | Slow | Encoded secrets, partial disclosure, semantic leaks |

## Test Strategies

| Strategy | Description |
|----------|-------------|
| **StaticDatasetStrategy** | Load prompts from YAML file (reproducible) |
| **DynamicGenerationStrategy** | LLM-generated context-aware attack prompts |
| **HybridStrategy** | Combine static + dynamic for comprehensive testing |

## Skill Structure

```
data-leakage-detection/
├── SKILL.md              # This file
└── prompt_sets/
    └── static_prompts.yaml    # ~27 core test prompts
```

## Related

- **Agent**: `data-leakage-detector`
- **Tool**: `tools/scan/data_leakage_scan.py`
- **Report**: `agent-security-reviewer`
