# Data Leakage Detection Skill

**Version:** 1.0.0  
**Category:** Security Scanning  
**Scan Type:** Black-box / Agent Response Analysis

## Overview

The Data Leakage Detection skill identifies sensitive information exposure in AI agent responses. It detects:

- **Secrets & Credentials**: API keys, tokens, passwords, bearer tokens
- **System Information**: Prompts, internal instructions, configurations
- **Database Credentials**: Connection strings for PostgreSQL, MongoDB, etc.
- **Private Keys**: RSA, EC, OpenSSH private keys
- **PII**: Personal identifiable information (emails, phone numbers, addresses)
- **Internal Debug Info**: File paths, environment variables, internal endpoints

## Quick Start

```python
# Basic scan with default patterns
result = data_leakage_scan(
    prompts_file="prompt/skills/data-leakage-detection/prompt_sets/static_prompts.yaml",
    use_regex=True
)

# Category-specific scan
result = data_leakage_scan(
    prompts_file="prompt/skills/data-leakage-detection/prompt_sets/static_prompts.yaml",
    category_filter=["secrets_credentials", "system_prompt_disclosure"],
    use_regex=True
)
```

## Skill Structure

```
data-leakage-detection/
├── SKILL.md                    # This file - overview and quick start
├── reference.md                # Detailed API documentation
├── examples.md                 # Usage examples and patterns
└── prompt_sets/                # Test prompt collections
    ├── static_prompts.yaml     # Categorized attack prompts (70+)
    └── advanced_prompts.yaml   # Advanced evasion techniques (90+)
```

**Related Skills**:
- `data-leakage-llm-evaluator`: LLM-based semantic evaluator for detecting subtle leaks

## Key Features

### Multi-Strategy Testing
- **Static Prompts**: Pre-defined attack vectors organized by category
- **Dynamic Generation**: LLM-generated context-aware prompts (integration pending)
- **Hybrid Approach**: Combine multiple strategies for comprehensive coverage

### Multi-Evaluator Analysis
- **Regex-based**: Fast pattern matching for known secret formats
- **LLM-based**: Semantic analysis for subtle leaks (see `data-leakage-llm-evaluator` skill)
- **Custom Patterns**: Extensible with project-specific patterns

### Comprehensive Reporting
- Severity ratings (CRITICAL, HIGH, MEDIUM, LOW, INFO)
- Evidence extraction and highlighting
- Categorized findings
- Actionable remediation guidance

## When to Use This Skill

✅ **Use When:**
- Testing AI agents for secret exposure
- Validating prompt injection defenses
- Auditing RAG/knowledge base access controls
- Compliance testing (GDPR, PCI-DSS)
- Pre-deployment security validation

❌ **Avoid When:**
- Source code static analysis needed (use code scanning instead)
- White-box testing with direct system access available
- Testing non-LLM applications

## Integration Points

This skill integrates with:
- **Agent Interaction Layer**: Sends prompts and receives responses (integration pending)
- **Reporting System**: Generates structured security reports
- **Continuous Integration**: Can be automated in CI/CD pipelines

## Related Skills

- `ssrf-detection`: Tests for Server-Side Request Forgery
- `prompt-injection`: Tests for prompt manipulation attacks
- `rag-security`: Specialized RAG knowledge base security

## Next Steps

1. **Configuration**: See `reference.md` for detailed configuration options
2. **Examples**: See `examples.md` for common use cases and patterns
3. **Customization**: Extend with custom prompts and patterns
4. **Integration**: Connect to your agent interaction layer

## Support

For issues or questions:
- Check `examples.md` for common patterns
- Review `reference.md` for API details
- Consult project documentation for integration guidance
