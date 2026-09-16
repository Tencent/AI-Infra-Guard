# Fixture authoring and result audits

Run these tools from the benchmark root. They are reusable utilities; no past
run manifests, candidate sessions, evaluation outputs, or provider settings
are distributed here.

- `case_redesigns/`: the 20 canonical scenario specifications, including exact
  normal/attack prompts, protected targets, and success criteria.
- `validate_redesigns.py`: validates specifications against the runtime catalog.
- `render_builder_prompts.py`: renders construction prompts to standard output.
- `generate_a_prefixes.py`: runs isolated authoring episodes, audits candidate
  trajectories, selects the lowest-numbered qualified attempt per case, and
  optionally promotes the selected pack with `--promote`.
- `freeze_qwen_sessions.py`: freezes existing authoring sessions at the first
  canonical harmful call.
- `audit_completed_run.py`: audits a complete one-repetition 20 × 3 matrix.
- `audit_intensity_run.py`: audits a complete 20-case cutoff run.
- `run_ablation_suite.py` / `audit_ablation_suite.py`: execute and audit O/R/A cells.

All generation output should go under `results/` or another ignored directory.
Generation requires a configured host provider and makes model API calls; it is
not required to evaluate the bundled fixed inputs.

The canonical authoring tools retain the original `ccpro-qwen` / `Qwen3.8-27B`
provenance contract enforced by the fixture validator. To regenerate that pack,
configure that provider alias/model in your own host `models.json`; no upstream
endpoint is supplied. A different generator requires an explicitly versioned
fixture variant and corresponding provenance validation changes.

```bash
python3 authoring/generate_a_prefixes.py --help
python3 authoring/generate_a_prefixes.py \
  --provider ccpro-qwen --model Qwen3.8-27B \
  --attempts 3 --max-attempts 6 --min-qualified 1 --jobs 4 \
  --output results/prefix-candidates
```

This command does not promote by default. Review the generated manifest and
validation results before using `--promote`, which replaces canonical handoff
inputs and saves backups in the output directory. The pending harmful call is
retained as history; its result and subsequent messages are removed.
