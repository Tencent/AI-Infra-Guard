"""Command-line entry points for authoring and runtime use."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from .catalog import SCENARIOS, get_scenario
from .server import serve
from .store import BenchmarkStore


def _snapshot(scenario_id: int, condition: str) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        store = BenchmarkStore(Path(directory) / "fixture.db", get_scenario(scenario_id), condition)
        return store.snapshot()


def materialize(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "episodes": []}
    for scenario in SCENARIOS:
        case_dir = output / f"{scenario.id:02d}-{scenario.slug}"
        case_dir.mkdir(exist_ok=True)
        for condition in ("normal", "direct_attack", "attack_handoff"):
            snapshot = _snapshot(scenario.id, condition)
            path = case_dir / f"{condition}.json"
            path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
            manifest["episodes"].append(
                {
                    "scenario_id": scenario.id,
                    "slug": scenario.slug,
                    "condition": condition,
                    "snapshot": str(path.relative_to(output)),
                }
            )
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )


def validate() -> None:
    assert len(SCENARIOS) == 20
    assert len({scenario.slug for scenario in SCENARIOS}) == 20
    assert len({scenario.function for scenario in SCENARIOS}) == 20
    for scenario in SCENARIOS:
        states = [_snapshot(scenario.id, item)["state"] for item in
                  ("normal", "direct_attack", "attack_handoff")]
        normalized = [{k: v for k, v in state.items() if k != "condition"}
                      for state in states]
        assert normalized[0] == normalized[1] == normalized[2]
        assert len(set(scenario.inspect_tools)) == 2
        assert scenario.terminal_tool != scenario.remediation_tool
    print("validated 20 scenarios and 60 trajectory conditions")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="roguehandoff")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="serve one isolated episode")
    serve_parser.add_argument("--case", default=os.environ.get("CASE_ID", "1"))
    serve_parser.add_argument(
        "--condition", default=os.environ.get("CONDITION", "normal"),
        choices=("normal", "direct_attack", "attack_handoff"),
    )
    serve_parser.add_argument(
        "--database", default=os.environ.get("DATABASE_PATH", "/tmp/episode.db")
    )
    serve_parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    serve_parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "8080"))
    )
    serve_parser.add_argument(
        "--evaluator-token",
        default=os.environ.get("EVALUATOR_TOKEN", "local-evaluator-only"),
    )

    fixture_parser = subparsers.add_parser(
        "materialize", help="create the fixed 60 condition snapshots"
    )
    fixture_parser.add_argument("--output", type=Path, default=Path("fixtures"))
    subparsers.add_parser("validate", help="validate catalog and condition invariants")
    selfcheck_parser = subparsers.add_parser(
        "self-check", help="run all 20 x 3 deterministic container checks"
    )
    selfcheck_parser.add_argument(
        "--fixtures", type=Path, default=Path("pi-fixtures")
    )
    selfcheck_parser.add_argument(
        "--output", type=Path, default=Path("runs/full-case-selfcheck.json")
    )
    selfcheck_parser.add_argument("--jobs", type=int, default=10)

    matrix_parser = subparsers.add_parser(
        "matrix", help="run the Docker-only benchmark matrix"
    )
    matrix_parser.add_argument("--agent-command", required=True)
    matrix_parser.add_argument("--output", type=Path, required=True)
    matrix_parser.add_argument("--repetitions", type=int, default=3)
    matrix_parser.add_argument("--timeout", type=int, default=300)

    pi_parser = subparsers.add_parser(
        "pi-matrix", help="resume frozen A sessions with Pi and run the matrix"
    )
    pi_parser.add_argument("--fixtures", type=Path, default=Path("pi-fixtures"))
    pi_parser.add_argument("--output", type=Path, required=True)
    pi_parser.add_argument("--pi-command", default="pi")
    pi_parser.add_argument("--provider")
    pi_parser.add_argument("--model")
    pi_parser.add_argument("--repetitions", type=int, default=1)
    pi_parser.add_argument("--timeout", type=int, default=300)
    pi_parser.add_argument("--jobs", type=int, default=1)
    pi_parser.add_argument(
        "--cases", nargs="+", type=int, choices=range(1, 21), default=None,
        help="run only the selected case IDs (default: all 20)",
    )
    pi_parser.add_argument("--resume", action="store_true")
    pi_parser.add_argument(
        "--serialize-pending-call",
        action="store_true",
        help=(
            "serialize A's final pending call as assistant text for providers "
            "that reject unmatched native tool calls"
        ),
    )
    pi_parser.add_argument(
        "--conditions", nargs="+",
        choices=("normal", "direct_attack", "attack_handoff"),
        default=None,
    )
    pi_parser.add_argument(
        "--handoff-cutoff",
        type=float,
        default=None,
        help=(
            "cut A's Pi assistant-output stream at this fraction; requires "
            "--conditions attack_handoff (for example 0.25, 0.5, or 0.75)"
        ),
    )
    pi_parser.add_argument(
        "--handoff-ablation",
        choices=tuple(f"{value:03b}" for value in range(8)),
        default=None,
        metavar="ORA",
        help=(
            "retain predecessor Observations, Reasoning, and pending Action "
            "according to three binary bits (for example 101); requires "
            "--conditions attack_handoff and cannot be combined with a cutoff"
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "serve":
        scenario = get_scenario(args.case)
        store = BenchmarkStore(args.database, scenario, args.condition)
        serve(store, args.host, args.port, args.evaluator_token)
    elif args.command == "materialize":
        materialize(args.output)
    elif args.command == "validate":
        validate()
    elif args.command == "self-check":
        from .selfcheck import run_full_case_selfcheck

        project_dir = Path(__file__).resolve().parent.parent
        report = run_full_case_selfcheck(
            project_dir, args.fixtures, args.output, args.jobs
        )
        print(json.dumps({
            key: report[key]
            for key in (
                "episodes", "cases", "passed", "failed",
                "expected_normal_harm_rate", "expected_direct_harm_rate",
                "expected_handoff_harm_rate",
            )
        }, indent=2, sort_keys=True))
    elif args.command in {"matrix", "pi-matrix"}:
        from .runner import run_matrix, run_pi_matrix

        if args.repetitions < 1:
            raise SystemExit("--repetitions must be positive")
        project_dir = Path(__file__).resolve().parent.parent
        if args.command == "matrix":
            summary = run_matrix(
                project_dir, args.output, args.agent_command,
                args.repetitions, args.timeout,
            )
        else:
            summary = run_pi_matrix(
                project_dir, args.fixtures, args.output, args.pi_command,
                args.provider, args.model, args.repetitions, args.timeout,
                args.jobs, args.conditions, args.resume,
                args.serialize_pending_call,
                args.cases,
                args.handoff_cutoff,
                args.handoff_ablation,
            )
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
