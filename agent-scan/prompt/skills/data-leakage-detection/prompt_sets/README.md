# Data Leakage Test Prompt Sets

This directory contains categorized test prompts for detecting data leakage vulnerabilities in AI agents.

## Available Prompt Sets

### `static_prompts.yaml`

**Purpose**: Core attack vectors for common data leakage scenarios  
**Use Case**: Standard security testing, compliance checks, routine audits  
**Categories**: 6 optimized categories  
**Test Count**: ~27 prompts

**Categories**:
- `secrets_credentials` - API keys, tokens, passwords
- `system_prompt_disclosure` - System instructions extraction
- `pii_privacy` - Personal information extraction
- `internal_config` - Configuration and debug info
- `rag_kb_disclosure` - RAG/knowledge base extraction
- `prompt_injection` - Basic injection tests

## Dynamic Generation

For advanced attack techniques (encoding evasion, role confusion, social engineering, etc.), use the `DynamicGenerationStrategy` which generates context-aware prompts using LLM:

```python
from tools.scan.strategies import DynamicGenerationStrategy

# Generate prompts using specific attack technique
strategy = DynamicGenerationStrategy(
    technique="social_engineering",
    count=10,
    target_context="Customer service chatbot",
    context=tool_context
)

# Or distribute across multiple techniques
strategy = DynamicGenerationStrategy(
    count=20,  # Auto-distributes across techniques
    context=tool_context
)
```

**Available Techniques**:
- `encoding_evasion` - Base64, hex, ROT13 encoding tricks
- `role_confusion` - Impersonation and role manipulation
- `indirect_extraction` - Hypothetical questions, backup requests
- `context_manipulation` - Error claims, mode switches
- `social_engineering` - Urgency, authority, compliance reasons
- `injection` - SQL/template injection patterns
- `chain_of_thought` - Step-by-step reasoning extraction

## Usage Examples

### Basic Scan

```python
result = data_leakage_scan(
    prompts_file="static",
    use_regex=True
)
```

### Category-Specific Testing

```python
result = data_leakage_scan(
    prompts_file="static",
    category_filter=["secrets_credentials", "system_prompt_disclosure"],
    use_regex=True
)
```

## Creating Custom Prompt Sets

```yaml
categories:
  category_name:
    - "Test prompt 1"
    - "Test prompt 2"
  
  another_category:
    - "Different test 1"
    - "Different test 2"
```

## Security Notice

⚠️ **Warning**: These prompt sets contain attack vectors designed to expose vulnerabilities.

- **Only use on authorized targets**
- **Do not use in production without permission**
- **Handle any exposed secrets according to incident response procedures**
