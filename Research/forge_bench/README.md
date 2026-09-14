# FORGE-Bench

FORGE-Bench is a deterministic benchmark for studying **Loss of Control (LoC)** in autonomous language-model agents.

Autonomous agents increasingly inspect environments, invoke side-effecting tools, maintain state across turns, and execute multi-step workflows with limited human intervention. As their operational authority grows, so does the risk that an agent will take an action beyond what an operator intended or authorized. FORGE-Bench investigates a narrower and more fundamental question:

> Can an otherwise capable agent lose control while pursuing a legitimate task, without an adversary, a malicious instruction, or a conflicting objective?

The benchmark uses synthetic, incident-informed scenarios rather than reproductions of real incidents. Its scenarios model ordinary operational work across domains such as software operations, cloud operations, procurement, identity security, and research infrastructure.

## What FORGE-Bench studies

FORGE-Bench disentangles three factors that are often conflated in agent failures:

- **Goal pressure** — pressure to complete the task or maximize progress;
- **Constraint degradation** — loss or weakening of the operator's authorization and scope constraints; and
- **Unsafe opportunity** — an executable action that crosses a boundary or produces an unauthorized external effect.

The benchmark defines LoC through observable environment state and external effects, rather than relying on an agent's self-report or stated intent. This enables deterministic, oracle-based evaluation of whether an action was authorized, in scope, properly confirmed, and consistent with the required stop behavior.

## Main findings

The accompanying study evaluates **5 agent models**, **16 operational domains**, and **1,800 unique trajectories** across full-factorial, cross-domain, paired-counterfactual, and context-management experiments.

The results show that:

- Goal pressure alone and unsafe opportunity alone do not produce substantial LoC.
- Their combination with degraded constraints causes a sharp increase in unauthorized actions, reaching up to **55%** and **62%** LoC in the reported experiments.
- Restoring the original constraints in paired counterfactuals eliminates LoC, yielding **0%** in the evaluated conditions.
- Context compaction remains safe when authorization constraints are retained.
- Omitting authorization constraints during compaction causes LoC to rise to **87%**.

These results support a benign failure mechanism: agents do not fail because task pressure or context compression is inherently unsafe. They fail when operational boundaries are semantically lost and a boundary-crossing action becomes executable.

## Contributions

1. **A causal, benign mechanism for agent LoC.** Degraded constraints combined with an executable unsafe opportunity are sufficient to trigger severe violations, while restoring the original constraint information eliminates them across unseen domains.
2. **Constraint loss as a root cause during context management.** Context compaction itself is not inherently unsafe; the critical failure is the omission of authorization boundaries.
3. **An effect-grounded evaluation methodology.** Auditable environment states and oracle-based scoring enable deterministic safety evaluation at benchmark scale.

## Repository layout

```text
forge_bench/
├── configs/              Example experiment configurations
├── scenarios/            Canonical scenario families and generated cases
├── src/forgebench/       Scenario generation, execution, parsing, and scoring
├── scripts/              Command-line utilities and analysis helpers
└── tests/                Unit tests
```

Runtime outputs, logs, model responses, environment snapshots, and other generated artifacts are intentionally excluded from the public repository. They may contain sensitive prompts, machine-specific paths, or provider-specific metadata. Recreate them locally when needed.

## Requirements

- Python 3.6 or newer
- Python standard library only for the core benchmark and tests
- A model client supplied by the user for live runs (not included in this repository)

## Quick start

From the repository root:

```bash
export PYTHONPATH="$PWD/src"

# Generate and validate scenarios
python3 scripts/build_scenarios.py

# Render prompts without calling a model
python3 scripts/run_benchmark.py \
  --config configs/smoke.json \
  --dry-run

# Run the test suite
python3 -m unittest discover -s tests -p 'test_*.py'
```

Live model execution is adapter-based. The runner imports a local `client.llm_client.LLMClient` implementation supplied by the user; credentials must be provided through that client's documented secret-management mechanism and must never be committed here.

## Data

All scenarios included in this repository are synthetic. Runtime outputs, logs,
model responses, environment snapshots, and other generated artifacts are not
part of the public release.

## Reproducibility

Configurations record seeds and benchmark versions. Scenario generation is deterministic for a given configuration and seed. Results should be reported together with the exact commit, configuration, model alias, and software environment used for the run, while keeping credentials and machine-specific details private.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
