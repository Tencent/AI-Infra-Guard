# Security Scanning Tools

Security scanning framework for AI agents, focused on data leakage detection.

## Architecture

```
tools/scan/
├── data_leakage_scan.py    # Main tool (entry point)
├── strategies.py           # Test case generation
├── evaluators.py           # Response evaluation (Regex, LLM)
├── models.py               # Data models (TestCase, ScanResult, etc.)
├── report.py               # Report generation
└── data_leakage_scan_schema.xml  # Tool schema
```

## Quick Start

```python
from tools.scan import data_leakage_scan

# Basic scan
result = data_leakage_scan(
    prompts_file="static",
    use_regex=True
)

# Category-specific with custom patterns
result = data_leakage_scan(
    prompts_file="static",
    category_filter=["secrets_credentials", "system_prompt_disclosure"],
    custom_patterns=[r"\bproject_token:\s*[a-zA-Z0-9]{32}"],
    use_regex=True
)

# Process results
if result["success"]:
    print(f"Found {result['summary']['vulnerabilities_found']} vulnerabilities")
    for vuln in result["vulnerabilities"]:
        print(f"[{vuln['evaluation']['severity']}] {vuln['evaluation']['reason']}")
```

## Components

### Strategies (`strategies.py`)

| Strategy | Description |
|----------|-------------|
| `StaticDatasetStrategy` | Load prompts from YAML files or lists |
| `DynamicGenerationStrategy` | Generate prompts via attacker LLM |
| `HybridStrategy` | Combine multiple strategies |

### Evaluators (`evaluators.py`)

| Evaluator | Speed | Detects |
|-----------|-------|---------|
| `RegexEvaluator` | Fast | API keys, tokens, connection strings, private keys |
| `LLMEvaluator` | Slow | Encoded secrets, partial disclosure, semantic leaks |

### Models (`models.py`)

- `TestCase`: Single security test
- `EvaluationResult`: Analysis result with severity/evidence
- `ScanResult`: Complete result (test + response + evaluation)
- `ScanSummary`: Aggregated statistics

## Extension

### Add Custom Evaluator

```python
from tools.scan.evaluators import BaseEvaluator
from tools.scan.models import EvaluationResult, Severity, TestCase

class CustomEvaluator(BaseEvaluator):
    def evaluate(self, response: str, test_case: TestCase, context=None) -> EvaluationResult:
        is_vuln = self._check(response)
        return EvaluationResult(
            is_vulnerable=is_vuln,
            severity=Severity.HIGH if is_vuln else Severity.INFO,
            score=1.0 if is_vuln else 0.0,
            reason="Custom check",
            evidence=None
        )
```

### Add Custom Strategy

```python
from tools.scan.strategies import BaseStrategy
from tools.scan.models import TestCase
import uuid

class CustomStrategy(BaseStrategy):
    def generate(self):
        for prompt in self._get_prompts():
            yield TestCase(
                id=str(uuid.uuid4()),
                prompt=prompt,
                metadata={"strategy": "custom"}
            )
```

## Related

- **Skill**: `prompt/skills/data-leakage-detection/`
- **Agent**: `prompt/agents/data_leakage_detection.md`
