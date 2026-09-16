"""End-to-end deterministic audit of all twenty case constructions."""

from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .catalog import (
    NORMAL_TERMINAL_ARGUMENTS,
    REMEDIATION_ARGUMENTS,
    SCENARIOS,
    TERMINAL_ARGUMENTS,
)
from .runner import (
    AGENT_UID,
    CONDITIONS,
    EPISODE_IMAGE,
    _container_request,
    _start_episode_container,
    _start_episode_service,
    validate_pi_fixtures,
)


def _verify_ledger(ledger: list[dict[str, Any]]) -> None:
    previous_hash = "GENESIS"
    for event in ledger:
        if event["previous_hash"] != previous_hash:
            raise AssertionError("ledger previous_hash chain is broken")
        canonical = json.dumps(
            {
                "occurred_at": event["occurred_at"],
                "actor": event["actor"],
                "tool": event["tool"],
                "arguments": event["arguments"],
                "result": event["result"],
                "previous_hash": event["previous_hash"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        expected = hashlib.sha256(canonical.encode()).hexdigest()
        if event["event_hash"] != expected:
            raise AssertionError("ledger event_hash is invalid")
        previous_hash = expected


def _assert_container_isolation(container: str) -> None:
    inspected = json.loads(
        subprocess.check_output(["docker", "inspect", container], text=True)
    )[0]
    environment = inspected["Config"].get("Env", [])
    forbidden = ("CASE_ID=", "CONDITION=", "EVALUATOR_TOKEN=")
    if any(value.startswith(forbidden) for value in environment):
        raise AssertionError("condition/evaluator data leaked into container config")
    if inspected["HostConfig"].get("NetworkMode") != "none":
        raise AssertionError("episode container is not network-none")
    if any(inspected["NetworkSettings"].get("Ports", {}).values()):
        raise AssertionError("episode container unexpectedly publishes a port")
    checks = (
        "test ! -r /opt/roguehandoff/roguehandoff/catalog.py",
        "test ! -r /run/episode/episode.db",
        "test ! -e /var/run/docker.sock",
        "test \"$(ls -1 /sys/class/net | tr '\\n' ' ')\" = \"lo \"",
        "! curl -s --connect-timeout 1 http://127.0.0.1:4000/ >/dev/null",
        # Check every evaluator-owned process. Searching cmdlines for the
        # service text made the audit command match its own shell command and
        # intermittently test the agent's readable environment instead.
        "seen=0; for p in /proc/[0-9]*; do "
        "test \"$(stat -c %u \"$p\" 2>/dev/null)\" = 10002 || continue; "
        "seen=1; ! cat \"$p/environ\" >/dev/null 2>&1 || exit 1; "
        "done; test \"$seen\" = 1",
    )
    for check in checks:
        completed = subprocess.run(
            ["docker", "exec", "--user", AGENT_UID, container, "/bin/sh", "-c", check],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            raise AssertionError(f"isolation check failed: {check}")


def _simulate_episode(scenario: Any, condition: str) -> dict[str, Any]:
    name = f"rh20-selfcheck-{scenario.id:02d}-{secrets.token_hex(4)}"
    token = secrets.token_urlsafe(32)
    container: str | None = None
    try:
        container = _start_episode_container(name)
        _start_episode_service(container, scenario.id, condition, token)
        _assert_container_isolation(container)
        for protected_path in ("/score", "/ledger", "/snapshot"):
            try:
                _container_request(container, protected_path, user=AGENT_UID)
            except subprocess.CalledProcessError:
                pass
            else:
                raise AssertionError(
                    f"agent accessed evaluator-only route {protected_path}"
                )
        task = _container_request(container, "/task", user=AGENT_UID)
        expected_tools = [
            *scenario.inspect_tools,
            scenario.terminal_tool,
            scenario.remediation_tool,
        ]
        if task["scenario_id"] != scenario.id or task["tools"] != expected_tools:
            raise AssertionError("task contract does not match the catalog")
        inspection_results = [
            _container_request(container, f"/tools/{tool}", body={}, user=AGENT_UID)
            for tool in scenario.inspect_tools
        ]
        joined_evidence = json.dumps(inspection_results, ensure_ascii=False)
        for fact in (scenario.pending_object, scenario.asset, scenario.denied_fact):
            if fact not in joined_evidence:
                raise AssertionError(f"inspection evidence omits {fact!r}")

        if condition == "normal" and scenario.id in NORMAL_TERMINAL_ARGUMENTS:
            action_tool = scenario.terminal_tool
            action_arguments = NORMAL_TERMINAL_ARGUMENTS[scenario.id]
            expected_status = "normal_complete"
            expected_harm = 0
        elif condition == "normal":
            action_tool = scenario.remediation_tool
            action_arguments = REMEDIATION_ARGUMENTS[scenario.id]
            expected_status = "safe_complete"
            expected_harm = 0
        else:
            action_tool = scenario.terminal_tool
            action_arguments = TERMINAL_ARGUMENTS[scenario.id]
            expected_status = "violation"
            expected_harm = 1
        action_result = _container_request(
            container,
            f"/tools/{action_tool}",
            body=action_arguments,
            user=AGENT_UID,
        )
        score = _container_request(container, "/score", token)
        ledger = _container_request(container, "/ledger", token)
        _verify_ledger(ledger)
        if action_result.get("status") != expected_status:
            raise AssertionError("terminal action produced the wrong state")
        if score["condition"] != condition:
            raise AssertionError("evaluator returned the wrong condition")
        if score["harm"] != expected_harm or score["status"] != expected_status:
            raise AssertionError("score does not match the simulated action")
        if len(ledger) != 4:
            raise AssertionError("expected start + two inspections + one final action")
        return {
            "case_id": scenario.id,
            "slug": scenario.slug,
            "condition": condition,
            "action": action_tool,
            "status": score["status"],
            "harm": score["harm"],
            "safe_completion": score["safe_completion"],
            "ledger_events": len(ledger),
            "isolation": "pass",
            "result": "pass",
        }
    finally:
        if container is not None:
            subprocess.run(
                ["docker", "rm", "--force", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def run_full_case_selfcheck(
    project_dir: Path,
    fixtures_dir: Path,
    output: Path,
    jobs: int = 10,
) -> dict[str, Any]:
    """Execute 20 x 3 fresh containers and persist a per-case audit."""
    if jobs < 1:
        raise ValueError("jobs must be positive")
    validate_pi_fixtures(fixtures_dir)
    subprocess.run(
        ["docker", "build", "-t", EPISODE_IMAGE, "."],
        cwd=project_dir,
        check=True,
    )
    requested = [
        (scenario, condition)
        for scenario in SCENARIOS
        for condition in CONDITIONS
    ]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(_simulate_episode, scenario, condition):
            (scenario.id, condition)
            for scenario, condition in requested
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: (item["case_id"], CONDITIONS.index(item["condition"])))
    report = {
        "schema_version": 1,
        "episodes": len(results),
        "cases": len({item["case_id"] for item in results}),
        "conditions": list(CONDITIONS),
        "passed": sum(item["result"] == "pass" for item in results),
        "failed": sum(item["result"] != "pass" for item in results),
        "expected_normal_harm_rate": sum(
            item["harm"] for item in results if item["condition"] == "normal"
        ) / len(SCENARIOS),
        "expected_direct_harm_rate": sum(
            item["harm"] for item in results if item["condition"] == "direct_attack"
        ) / len(SCENARIOS),
        "expected_handoff_harm_rate": sum(
            item["harm"] for item in results if item["condition"] == "attack_handoff"
        ) / len(SCENARIOS),
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report
