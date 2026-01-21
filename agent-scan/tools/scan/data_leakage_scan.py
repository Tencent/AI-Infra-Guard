"""
Data leakage scanning tool.

This tool implements security scanning for detecting sensitive information leakage
in AI agent responses, including API keys, credentials, PII, and system prompts.
"""

import time
import os
import uuid
from typing import Any, Dict, List, Optional
from utils.loging import logger
from utils.aig_logger import scanLogger
from utils.tool_context import ToolContext
from tools.registry import register_tool

from .models import (
    TestCase,
    ScanResult,
    EvaluationResult,
    ScanType,
    Severity,
    ScanSummary,
    AgentSecurityReport,
)
from .evaluators import BaseEvaluator, RegexEvaluator, LLMEvaluator
from .strategies import BaseStrategy, StaticDatasetStrategy
from .report import generate_report


def _aggregate_evaluations(
    response: str,
    test_case: TestCase,
    evaluators: List[BaseEvaluator],
    context: Optional[ToolContext] = None
) -> EvaluationResult:
    """
    Aggregate results from multiple evaluators into a single decision.
    
    Args:
        response: The agent's response text
        test_case: The test case that generated the response
        evaluators: List of evaluators to run
        context: Tool context for LLM-based evaluators
        
    Returns:
        Aggregated EvaluationResult with highest severity finding
    """
    severity_rank = {
        Severity.INFO: 0,
        Severity.LOW: 1,
        Severity.MEDIUM: 2,
        Severity.HIGH: 3,
    }
    
    def _get_severity_rank(sev: str) -> int:
        try:
            return severity_rank.get(Severity(sev), 0)
        except Exception:
            return 0
    
    findings = []
    for evaluator in evaluators:
        try:
            eval_result = evaluator.evaluate(response, test_case, context)
            findings.append({
                "evaluator": evaluator.__class__.__name__,
                "is_vulnerable": bool(eval_result.is_vulnerable),
                "severity": getattr(eval_result.severity, "value", str(eval_result.severity)),
                "score": float(getattr(eval_result, "score", 0.0) or 0.0),
                "reason": eval_result.reason,
                "evidence": eval_result.evidence,
            })
        except Exception as e:
            logger.exception(f"Evaluator {evaluator.__class__.__name__} failed: {e}")
            findings.append({
                "evaluator": evaluator.__class__.__name__,
                "error": str(e),
                "is_vulnerable": False,
                "severity": Severity.INFO.value,
            })
    
    # Find vulnerable findings
    vulnerable_findings = [f for f in findings if f.get("is_vulnerable")]
    
    if not vulnerable_findings:
        return EvaluationResult(
            is_vulnerable=False,
            severity=Severity.INFO,
            score=0.0,
            reason="No vulnerabilities detected by any evaluator.",
        )
    
    # Select highest severity finding
    top = max(
        vulnerable_findings,
        key=lambda f: _get_severity_rank(str(f.get("severity") or "")),
    )
    
    summary = ", ".join(
        f'{f["evaluator"]}({f.get("severity")})' for f in vulnerable_findings
    )
    
    return EvaluationResult(
        is_vulnerable=True,
        severity=Severity(top["severity"]),
        score=max(float(f.get("score") or 0.0) for f in vulnerable_findings),
        reason=f"Vulnerabilities detected by: {summary}",
        evidence=top.get("evidence"),
    )


@register_tool
def data_leakage_scan(
    prompts_file: Optional[str] = None,
    prompts: Optional[List[str]] = None,
    category_filter: Optional[List[str]] = None,
    use_regex: bool = True,
    use_llm_judge: bool = False,
    custom_patterns: Optional[List[str]] = None,
    context: Optional[ToolContext] = None
) -> Dict[str, Any]:
    """
    Perform data leakage security scan on an AI agent.
    
    This tool executes a comprehensive security scan to detect sensitive information
    leakage, including:
    - API keys and credentials
    - Database connection strings
    - System prompts and internal instructions
    - PII (Personal Identifiable Information)
    - Internal configurations and debug information
    
    Args:
        prompts_file: Path to YAML file containing test prompts (relative to project root)
        prompts: Explicit list of test prompts (overrides prompts_file)
        category_filter: List of category names to test (e.g., ["secrets_credentials", "pii_privacy"])
        use_regex: Whether to use regex-based pattern detection (default: True)
        use_llm_judge: Whether to use LLM-based semantic analysis (default: False, requires integration)
        custom_patterns: Additional regex patterns to check
        context: Tool execution context
        
    Returns:
        Dictionary containing:
            - success: Whether scan completed successfully
            - output: Human-readable summary
            - results: List of ScanResult objects
            - summary: ScanSummary with statistics
            - vulnerabilities: List of vulnerable findings only
            - report: Frontend-compatible AgentSecurityReport (schema: agent-security-report@1)
            
    Example:
        ```python
        result = data_leakage_scan(
            prompts_file="prompt_sets/static_prompts.yaml",
            category_filter=["secrets_credentials"],
            use_regex=True
        )
        ```
    """
    try:
        start_time = time.time()
        
        # Validate context
        if context is None:
            return {
                "success": False,
                "error": "ToolContext is required. Configure agent provider before scanning."
            }
        
        # Initialize strategy
        if prompts is not None:
            strategy = StaticDatasetStrategy(prompts=prompts)
        elif prompts_file:
            # Handle different path formats
            from utils.config import base_dir
            
            # Support skill-relative paths (e.g., "@skill/prompt_sets/static_prompts.yaml")
            if prompts_file.startswith("@skill/"):
                skill_name = "data-leakage-detection"  # Default skill name
                relative_path = prompts_file.replace("@skill/", "")
                full_path = os.path.join(base_dir, "prompt", "skills", skill_name, relative_path)
            # Support short names for built-in prompt sets
            elif prompts_file in ["static", "basic", "default"]:
                full_path = os.path.join(base_dir, "prompt/skills/data-leakage-detection/prompt_sets/static_prompts.yaml")
            # Absolute or relative from project root
            else:
                full_path = os.path.join(base_dir, prompts_file) if not os.path.isabs(prompts_file) else prompts_file
            
            strategy = StaticDatasetStrategy(prompts_file=full_path, category_filter=category_filter)
        else:
            return {
                "success": False,
                "error": "Either 'prompts' or 'prompts_file' must be provided"
            }
        
        # Initialize evaluators
        evaluators: List[BaseEvaluator] = []
        
        if use_regex:
            # Always use default patterns
            evaluators.append(RegexEvaluator())
            # Add custom patterns as additional evaluator if provided
            if custom_patterns:
                evaluators.append(RegexEvaluator(patterns=custom_patterns))
        
        if use_llm_judge:
            evaluators.append(LLMEvaluator())
        
        if not evaluators:
            return {
                "success": False,
                "error": "At least one evaluator (use_regex or use_llm_judge) must be enabled"
            }
        
        # Execute scan
        results: List[ScanResult] = []
        vulnerabilities: List[ScanResult] = []
        
        # Get total test count for progress reporting
        test_cases = list(strategy.generate())
        total_tests = len(test_cases)
        
        logger.info(f"Starting data leakage scan with {len(evaluators)} evaluators, {total_tests} test cases")
        
        # Log scan start
        scan_step_id = "scan_data_leakage"
        scanLogger.status_update(
            scan_step_id,
            f"Starting data leakage scan ({total_tests} tests)",
            "",
            "running"
        )
        
        for idx, test_case in enumerate(test_cases, 1):
            # Log progress
            tool_id = str(uuid.uuid4())
            category = test_case.metadata.get("category", "general")
            scanLogger.tool_used(
                scan_step_id,
                tool_id,
                f"Testing [{idx}/{total_tests}]: {category}",
                "doing",
                "data_leakage_scan",
                test_case.prompt[:50] + "..." if len(test_case.prompt) > 50 else test_case.prompt
            )
            
            # Get agent response
            agent_response = _get_agent_response(test_case, context)
            
            # Evaluate response
            evaluation = _aggregate_evaluations(agent_response, test_case, evaluators, context)
            
            # Create scan result
            scan_result = ScanResult(
                test_case=test_case,
                response=agent_response,
                evaluation=evaluation,
                scan_type=ScanType.DATA_LEAKAGE,
                timestamp=time.time(),
                metadata={"evaluator_count": len(evaluators)}
            )
            
            results.append(scan_result)
            
            # Log test completion
            status_msg = "vulnerable" if evaluation.is_vulnerable else "safe"
            scanLogger.tool_used(
                scan_step_id,
                tool_id,
                f"Test [{idx}/{total_tests}] {status_msg}",
                "done",
                "data_leakage_scan",
                ""
            )
            
            if evaluation.is_vulnerable:
                vulnerabilities.append(scan_result)
                logger.warning(
                    f"Vulnerability found: {evaluation.severity.value} - {evaluation.reason}"
                )
                scanLogger.action_log(
                    tool_id,
                    "data_leakage_scan",
                    scan_step_id,
                    f"[{evaluation.severity.value}] {evaluation.reason}"
                )
        
        # Generate summary
        duration = time.time() - start_time
        by_severity = {}
        for vuln in vulnerabilities:
            sev = vuln.evaluation.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        summary = ScanSummary(
            total_tests=len(results),
            vulnerabilities_found=len(vulnerabilities),
            by_severity=by_severity,
            scan_type=ScanType.DATA_LEAKAGE,
            duration=duration
        )
        
        # Format output
        output_lines = [
            f"Data Leakage Scan Complete",
            f"{'='*50}",
            f"Total tests: {summary.total_tests}",
            f"Vulnerabilities found: {summary.vulnerabilities_found}",
            f"Duration: {summary.duration:.2f}s",
            "",
            "Findings by severity:"
        ]
        
        for sev in ["HIGH", "MEDIUM", "LOW"]:
            count = by_severity.get(sev, 0)
            if count > 0:
                output_lines.append(f"  {sev}: {count}")
        
        if vulnerabilities:
            output_lines.extend(["", "Vulnerability Details:", ""])
            for i, vuln in enumerate(vulnerabilities, 1):
                output_lines.extend([
                    f"{i}. [{vuln.evaluation.severity.value}] {vuln.evaluation.reason}",
                    f"   Prompt: {vuln.test_case.prompt[:80]}...",
                    f"   Evidence: {vuln.evaluation.evidence[:80] if vuln.evaluation.evidence else 'N/A'}...",
                    ""
                ])
        
        logger.info(f"Scan completed: {summary.vulnerabilities_found} vulnerabilities in {duration:.2f}s")
        
        # Log scan completion
        scanLogger.status_update(
            scan_step_id,
            f"Scan completed: {summary.vulnerabilities_found} vulnerabilities found",
            "",
            "completed"
        )
        
        # Generate frontend-compatible report
        plugins_used = []
        if use_regex:
            plugins_used.append("RegexEvaluator")
        if use_llm_judge:
            plugins_used.append("LLMEvaluator")
        
        report = generate_report(
            results=results,
            summary=summary,
            agent_name="",  # To be set by caller
            agent_type="",  # To be set by caller
            plugins=plugins_used,
            start_time=int(start_time),
            end_time=int(time.time()),
        )
        
        return {
            "success": True,
            "output": "\n".join(output_lines),
            "results": [r.dict() for r in results],
            "summary": summary.dict(),
            "vulnerabilities": [v.dict() for v in vulnerabilities],
            "report": report.dict(),  # Frontend-compatible format
        }
        
    except Exception as e:
        logger.exception(f"Data leakage scan failed: {e}")
        return {
            "success": False,
            "error": f"Scan failed: {str(e)}"
        }


def _get_agent_response(test_case: TestCase, context: ToolContext) -> str:
    """
    Get response from the target agent via context.call_provider().
    
    Args:
        test_case: The test case containing the prompt
        context: Tool execution context with agent provider
        
    Returns:
        Agent response string
        
    Raises:
        ValueError: If agent call fails
    """
    result = context.call_provider(test_case.prompt)
    
    if not result.success:
        raise ValueError(f"Agent call failed: {result.message}")
    
    if result.provider_response:
        output = result.provider_response.output
        if output:
            return str(output)
        raw = result.provider_response.raw
        if raw:
            return str(raw)
    
    raise ValueError("Agent returned empty response")
