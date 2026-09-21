"""Native contract audit for TypeSafe System One (Jev) APIs."""

from __future__ import annotations

from typing import Any

from .relay_audit import (
    Finding,
    ProbeResult,
    _http_json,
    risk_verdict,
)


TYPESAFE_REQUEST_COUNT = 3

_QUESTIONS = {
    "urgent": {
        "type": "noul",
        "instructions": "The customer has an urgent, time-sensitive problem.",
    },
    "department": {
        "type": "choice",
        "instructions": "Which team should handle this request?",
        "criteria": {
            "billing": "Payments, charges, refunds, or payouts",
            "technical": "Software bugs, outages, or integrations",
            "sales": "Pricing, upgrades, or new accounts",
        },
    },
    "severity": {
        "type": "score",
        "instructions": "How severe is the reported problem?",
        "criteria": [
            "No problem; everything is working",
            "A problem exists but a workaround is available",
            "A blocking problem with no workaround",
        ],
    },
}

_POSITIVE_STATE = (
    "Our payouts have failed for three days and sales are blocked. "
    "There is no workaround. Please help immediately."
)
_NEGATIVE_STATE = (
    "Everything is working normally. This is a routine note and no action "
    "is needed."
)


def _probabilities(value: Any, expected_keys: set[str]) -> tuple[dict, str | None]:
    if not isinstance(value, dict) or set(value) != expected_keys:
        return {}, "probability keys do not match criteria"
    if any(
        not isinstance(item, (int, float))
        or isinstance(item, bool)
        or not 0 <= float(item) <= 1
        for item in value.values()
    ):
        return {}, "probabilities must be numbers between 0 and 1"
    result = {str(key): float(item) for key, item in value.items()}
    if abs(sum(result.values()) - 1.0) > 0.02:
        return {}, "probabilities do not sum to 1"
    return result, None


def _validate_response(payload: Any) -> tuple[list[str], dict[str, Any]]:
    errors = []
    summary: dict[str, Any] = {}
    if not isinstance(payload, dict):
        return ["response is not an object"], summary
    model = payload.get("model")
    if not isinstance(model, str) or not model:
        errors.append("missing resolved model")
    else:
        summary["model"] = model
    usage = payload.get("usage")
    if not isinstance(usage, dict) or any(
        not isinstance(usage.get(key), int) or usage[key] <= 0
        for key in ("input_tokens", "output_tokens")
    ):
        errors.append("invalid token usage")
    else:
        summary["usage"] = dict(usage)

    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return errors + ["missing answers object"], summary
    if set(answers) != set(_QUESTIONS):
        errors.append("answer keys do not match question keys")

    urgent = answers.get("urgent") or {}
    noul = urgent.get("noul")
    if (
        urgent.get("type") != "noul"
        or not isinstance(noul, (int, float))
        or isinstance(noul, bool)
        or not 0 <= float(noul) <= 1
    ):
        errors.append("invalid Noul answer")
    else:
        summary["urgent"] = float(noul)

    department = answers.get("department") or {}
    choice_keys = set(_QUESTIONS["department"]["criteria"])
    choice_probabilities, choice_error = _probabilities(
        department.get("probabilities"),
        choice_keys,
    )
    choice = department.get("choice")
    if department.get("type") != "choice" or choice not in choice_keys:
        errors.append("invalid Choice answer")
    elif choice_error:
        errors.append(f"invalid Choice {choice_error}")
    elif choice_probabilities[choice] + 1e-9 < max(choice_probabilities.values()):
        errors.append("Choice is not the maximum-probability option")
    else:
        summary["department"] = choice

    severity = answers.get("severity") or {}
    score_keys = {"0", "1", "2"}
    score_probabilities, score_error = _probabilities(
        severity.get("probabilities"),
        score_keys,
    )
    score = severity.get("score")
    legend = severity.get("legend")
    if (
        severity.get("type") != "score"
        or not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not 0 <= float(score) <= 2
    ):
        errors.append("invalid Score answer")
    elif not isinstance(legend, dict) or set(legend) != score_keys:
        errors.append("Score legend does not match criteria")
    elif score_error:
        errors.append(f"invalid Score {score_error}")
    else:
        weighted = sum(int(key) * value for key, value in score_probabilities.items())
        if abs(weighted - float(score)) > 0.02:
            errors.append("Score does not equal its probability-weighted value")
        else:
            summary["severity"] = float(score)
    return errors, summary


def _model_names(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        return []
    return [
        str(item.get("name"))
        for item in payload["models"]
        if isinstance(item, dict) and item.get("name")
    ]


def run_typesafe_audit(
    base_url: str,
    api_key: str,
    model: str,
    cancel_event=None,
    on_request_progress=None,
) -> dict:
    """Validate TypeSafe models, typed response contracts, and input sensitivity."""
    completed = success = failed = 0

    def request_done(ok: bool) -> None:
        nonlocal completed, success, failed
        completed += 1
        if ok:
            success += 1
        else:
            failed += 1
        if on_request_progress:
            on_request_progress(
                completed,
                TYPESAFE_REQUEST_COUNT,
                success,
                failed,
            )

    def cancelled() -> bool:
        return cancel_event is not None and cancel_event.is_set()

    results: list[ProbeResult] = []
    if cancelled():
        return _result(results, model)
    models_status, models_payload, models_latency = _http_json(
        f"{base_url.rstrip('/')}/models",
        api_key,
        method="GET",
        on_request=request_done,
    )
    names = _model_names(models_payload)
    listed = model in names
    models_probe = ProbeResult(
        "typesafe_models",
        200 <= models_status < 300 and bool(names),
        models_latency,
        data={
            "status": models_status,
            "model_count": len(names),
            "target_model_present": listed,
            "sample_models": names[:20],
        },
    )
    results.append(models_probe)

    responses: list[dict[str, Any]] = []
    for probe_name, state in (
        ("typesafe_contract", _POSITIVE_STATE),
        ("typesafe_contrast", _NEGATIVE_STATE),
    ):
        if cancelled():
            results.append(ProbeResult(
                probe_name,
                False,
                None,
                data={"not_executed": True},
                error="audit cancelled",
            ))
            continue
        status, payload, latency = _http_json(
            f"{base_url.rstrip('/')}/systemone",
            api_key,
            {
                "state": state,
                "model": model,
                "questions": _QUESTIONS,
            },
            on_request=request_done,
        )
        validation_errors, summary = _validate_response(payload)
        responses.append(summary)
        results.append(ProbeResult(
            probe_name,
            200 <= status < 300 and not validation_errors,
            latency,
            data={
                "status": status,
                "resolved_model": summary.get("model"),
                "answer_summary": {
                    key: summary.get(key)
                    for key in ("urgent", "department", "severity")
                },
                "usage": summary.get("usage"),
                "validation_errors": validation_errors,
            },
            error=("; ".join(validation_errors) if validation_errors else None),
        ))

    if len(responses) == 2 and all(responses):
        positive, negative = responses
        contrast_ok = (
            positive.get("urgent", -1) > negative.get("urgent", 2) + 0.2
            and positive.get("severity", -1) > negative.get("severity", 3)
        )
        contrast_probe = results[-1]
        if not contrast_ok:
            contrast_probe.ok = False
            contrast_probe.error = "positive and negative states are insufficiently separated"
            contrast_probe.data["validation_errors"].append(contrast_probe.error)
    resolved = next(
        (
            response.get("model")
            for response in responses
            if response.get("model")
        ),
        model,
    )
    if any(probe.ok for probe in results[1:]):
        models_probe.data["target_model_present"] = True
        models_probe.data["resolved_model"] = resolved
    return _result(results, resolved)


def _result(results: list[ProbeResult], resolved_model: str) -> dict:
    findings = []
    weights = {
        "typesafe_models": 20,
        "typesafe_contract": 50,
        "typesafe_contrast": 25,
    }
    titles = {
        "typesafe_models": "TypeSafe model list check failed",
        "typesafe_contract": "TypeSafe response contract failed",
        "typesafe_contrast": "TypeSafe state sensitivity failed",
    }
    for probe in results:
        if probe.data.get("not_executed") or probe.ok:
            continue
        score = weights.get(probe.name, 20)
        findings.append(Finding(
            probe.name,
            "HIGH" if score >= 50 else "MEDIUM",
            score,
            titles.get(probe.name, "TypeSafe audit failed"),
            str(probe.error or probe.data),
            "Confirm the endpoint implements the TypeSafe System One contract",
        ))
    score = min(100, sum(item.score for item in findings))
    verdict = risk_verdict(score)
    return {
        "score": score,
        "verdict": verdict,
        "findings": findings,
        "probe_results": results,
        "resolved_model": resolved_model,
        "summary": f"TypeSafe System One audit: {verdict} ({score}/100 risk)",
    }
