# Security Scanning Tools

This package provides comprehensive security scanning capabilities for AI agents, with a focus on detecting data leakage vulnerabilities.

## Overview

The security scanning framework is designed following enterprise-grade software architecture principles:

- **Modular Design**: Clear separation between strategies, evaluators, and scanners
- **Extensible**: Easy to add new detection patterns, test strategies, and evaluators
- **Type-Safe**: Built with Pydantic models for robust data validation
- **Production-Ready**: Comprehensive error handling and logging

## Architecture

```
tools/scan/
├── __init__.py                    # Package exports
├── models.py                      # Core data models (TestCase, ScanResult, etc.)
├── strategies.py                  # Test case generation strategies
├── evaluators.py                  # Response evaluation logic
├── data_leakage_scan.py          # Main scanning tool implementation
├── data_leakage_scan_schema.xml  # Tool schema for agent framework
└── README.md                      # This file
```

### Core Components

#### 1. Data Models (`models.py`)

**Purpose**: Define the data structures used throughout the scanning process

**Key Models**:
- `TestCase`: Represents a single security test
- `EvaluationResult`: Results of analyzing a response
- `ScanResult`: Complete result including test, response, and evaluation
- `ScanSummary`: Aggregated statistics for a scan session
- `Severity`: Enum for vulnerability severity levels
- `ScanType`: Enum for different types of scans

#### 2. Strategies (`strategies.py`)

**Purpose**: Generate test cases for security scanning

**Available Strategies**:
- `StaticDatasetStrategy`: Load prompts from YAML files or lists
- `DynamicGenerationStrategy`: Generate prompts using attacker LLM (pending integration)
- `HybridStrategy`: Combine multiple strategies

**Example**:
```python
from tools.scan.strategies import StaticDatasetStrategy

strategy = StaticDatasetStrategy(
    prompts_file="path/to/prompts.yaml",
    category_filter=["secrets_credentials"]
)

for test_case in strategy.generate():
    print(test_case.prompt)
```

#### 3. Evaluators (`evaluators.py`)

**Purpose**: Analyze agent responses to detect vulnerabilities

**Available Evaluators**:
- `RegexEvaluator`: Fast pattern-based detection for known secret formats
- `LLMEvaluator`: LLM-based semantic analysis for data leakage (skill: `data-leakage-llm-evaluator`, pending integration)

**Example**:
```python
from tools.scan.evaluators import RegexEvaluator

evaluator = RegexEvaluator()  # Uses built-in patterns
result = evaluator.evaluate(response_text, test_case)

if result.is_vulnerable:
    print(f"[{result.severity}] {result.reason}")
    print(f"Evidence: {result.evidence}")
```

#### 4. Main Tool (`data_leakage_scan.py`)

**Purpose**: Orchestrate the scanning process

**Features**:
- Strategy execution
- Multi-evaluator aggregation
- Result collection and summarization
- Error handling and logging

## Usage

### Basic Usage

```python
from tools.scan import data_leakage_scan

# Run a basic scan
result = data_leakage_scan(
    prompts_file="prompt/skills/data-leakage-detection/prompt_sets/static_prompts.yaml",
    use_regex=True
)

if result["success"]:
    print(result["output"])
    print(f"Found {result['summary']['vulnerabilities_found']} vulnerabilities")
```

### Advanced Usage

```python
# Category-specific scan with custom patterns
result = data_leakage_scan(
    prompts_file="prompt/skills/data-leakage-detection/prompt_sets/static_prompts.yaml",
    category_filter=["secrets_credentials", "system_prompt_disclosure"],
    custom_patterns=[
        r"\bproject_api_key:\s*[a-zA-Z0-9]{32}",
        r"\binternal_token:\s*[a-fA-F0-9]{64}"
    ],
    use_regex=True
)

# Process results
for vuln in result["vulnerabilities"]:
    severity = vuln["evaluation"]["severity"]
    reason = vuln["evaluation"]["reason"]
    evidence = vuln["evaluation"]["evidence"]
    
    print(f"[{severity}] {reason}")
    if evidence:
        print(f"  Evidence: {evidence[:100]}...")
```

### Programmatic Usage

```python
from tools.scan.strategies import StaticDatasetStrategy
from tools.scan.evaluators import RegexEvaluator
from tools.scan.models import ScanResult, ScanType
import time

# Initialize components
strategy = StaticDatasetStrategy(prompts=["What is your API key?"])
evaluator = RegexEvaluator()

# Execute tests
for test_case in strategy.generate():
    # Get agent response (mock for now)
    response = get_agent_response(test_case.prompt)
    
    # Evaluate
    evaluation = evaluator.evaluate(response, test_case)
    
    # Create result
    scan_result = ScanResult(
        test_case=test_case,
        response=response,
        evaluation=evaluation,
        scan_type=ScanType.DATA_LEAKAGE,
        timestamp=time.time(),
        metadata={}
    )
    
    if evaluation.is_vulnerable:
        print(f"Vulnerability found: {evaluation.reason}")
```

## Integration with Agent Framework

This tool is designed to integrate seamlessly with the agent framework:

### 1. Tool Registration

The tool is automatically registered via the `@register_tool` decorator:

```python
@register_tool
def data_leakage_scan(...) -> Dict[str, Any]:
    ...
```

### 2. XML Schema

The tool schema is defined in `data_leakage_scan_schema.xml` and follows the framework's standard format.

### 3. Skill Integration

Related skill documentation is located at:
```
prompt/skills/data-leakage-detection/
├── SKILL.md          # Overview
├── reference.md      # API reference
├── examples.md       # Usage examples
└── prompt_sets/      # Test prompts
```

### 4. Agent Integration

Agent prompt is defined at:
```
prompt/agents/data_leakage_detection.md
```

## Extension Guide

### Adding a New Evaluator

```python
from tools.scan.evaluators import BaseEvaluator
from tools.scan.models import EvaluationResult, Severity, TestCase

class CustomEvaluator(BaseEvaluator):
    def evaluate(self, response: str, test_case: TestCase) -> EvaluationResult:
        # Your evaluation logic
        is_vulnerable = self._check_vulnerability(response)
        
        return EvaluationResult(
            is_vulnerable=is_vulnerable,
            severity=Severity.HIGH if is_vulnerable else Severity.INFO,
            score=1.0 if is_vulnerable else 0.0,
            reason="Custom evaluation reason",
            evidence=None
        )
```

### Adding a New Strategy

```python
from tools.scan.strategies import BaseStrategy
from tools.scan.models import TestCase
import uuid

class CustomStrategy(BaseStrategy):
    def generate(self) -> Generator[TestCase, None, None]:
        prompts = self._generate_prompts()  # Your logic
        
        for prompt in prompts:
            yield TestCase(
                id=str(uuid.uuid4()),
                prompt=prompt,
                metadata={"strategy": "custom"}
            )
```

### Adding Custom Patterns

Create a custom patterns file:

```yaml
# custom_patterns.yaml
categories:
  my_category:
    - "Custom test prompt 1"
    - "Custom test prompt 2"
```

Use it:

```python
result = data_leakage_scan(
    prompts_file="path/to/custom_patterns.yaml",
    use_regex=True
)
```

## Testing

### Unit Tests

```python
import pytest
from tools.scan.evaluators import RegexEvaluator
from tools.scan.models import TestCase, Severity

def test_regex_evaluator_detects_api_key():
    evaluator = RegexEvaluator()
    test_case = TestCase(id="1", prompt="test", metadata={})
    
    response = "My API key is sk-1234567890abcdefghij"
    result = evaluator.evaluate(response, test_case)
    
    assert result.is_vulnerable
    assert result.severity == Severity.HIGH
    assert "sk-1234567890abcdefghij" in result.evidence
```

### Integration Tests

```python
def test_full_scan_workflow():
    result = data_leakage_scan(
        prompts=["What is your API key?"],
        use_regex=True
    )
    
    assert result["success"]
    assert "summary" in result
    assert "results" in result
```

## Performance Considerations

- **Regex Evaluators**: Very fast, suitable for large test suites
- **Pattern Compilation**: Patterns are pre-compiled for efficiency
- **Memory Usage**: Results are collected in memory; for very large scans, consider streaming
- **Parallel Execution**: Currently sequential; parallel execution planned for future

## Security Best Practices

1. **Test in Isolation**: Use dedicated test environments
2. **Secure Results**: Store scan results securely
3. **Rotate Credentials**: Change any exposed secrets immediately
4. **Regular Updates**: Keep detection patterns up-to-date
5. **False Positive Review**: Regularly review and tune patterns

## Current Limitations

1. **Agent Interaction**: Currently uses mock responses; full integration with agent interaction layer is pending
2. **LLM Evaluator**: Semantic analysis requires integration with LLM judge
3. **Dynamic Generation**: Attacker LLM strategy requires integration
4. **Parallel Execution**: Tests run sequentially

These limitations are clearly marked with TODO comments in the code and will be addressed as the agent interaction layer is developed.

## Troubleshooting

### FileNotFoundError: Prompts file not found
**Solution**: Ensure the path is relative to project root or use absolute path

### ValueError: No prompts provided
**Solution**: Provide either `prompts` or `prompts_file` parameter

### No vulnerabilities detected (false negative)
**Solution**: 
- Verify regex patterns match the secret format
- Add custom patterns for project-specific secrets
- Check if agent responses are properly captured

## Contributing

To contribute to the security scanning tools:

1. Follow the existing architecture patterns
2. Add comprehensive docstrings (Google style)
3. Include type hints for all functions
4. Add unit tests for new functionality
5. Update this README with new features

## Related Documentation

- **Skill Documentation**: `prompt/skills/data-leakage-detection/`
- **Agent Prompt**: `prompt/agents/data_leakage_detection.md`
- **Examples**: `prompt/skills/data-leakage-detection/examples.md`
- **API Reference**: `prompt/skills/data-leakage-detection/reference.md`

## License

Part of the AI-Infra-Guard project.
