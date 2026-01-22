---
name: data-leakage-detection
description: Detect sensitive information leakage in AI agent responses. Use when testing for API keys, credentials, system prompts, PII, or configuration exposure.
allowed-tools: data_leakage_scan, dialogue
---

# Data Leakage Detection

Detect sensitive information exposure in AI agent responses through automated scanning.

## Quick Start

Run comprehensive data leakage scan with all test cases:

```python
data_leakage_scan(prompts_file="static", use_regex=True)
```

## Targeted Scans

Filter by category for focused testing:

```python
# Secrets and credentials only
data_leakage_scan(
    prompts_file="static",
    category_filter=["secrets_credentials"],
    use_regex=True
)

# System prompt disclosure
data_leakage_scan(
    prompts_file="static",
    category_filter=["system_prompt_disclosure"],
    use_regex=True
)
```

## Available Categories

- `secrets_credentials` - API keys, tokens, passwords
- `system_prompt_disclosure` - System prompts, internal instructions
- `pii_privacy` - Personal identifiable information
- `internal_config` - Configuration, environment info
- `rag_kb_disclosure` - Knowledge base content
- `prompt_injection` - Injection-based extraction

## Additional Resources

- Test prompts: [prompt_sets/static_prompts.yaml](prompt_sets/static_prompts.yaml)
- Category details: [prompt_sets/README.md](prompt_sets/README.md)
