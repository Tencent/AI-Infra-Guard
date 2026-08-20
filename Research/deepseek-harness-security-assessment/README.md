# DeepSeek Harness indirect prompt-injection assessment

This repository contains the sanitized experiment artifacts for an authorized,
controlled security assessment of [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), performed with A.I.G (AI-Infra-Guard).

The assessment exercises the real DSH runtime with controlled content-reading
source tools and simulated sensitive sinks. It does not send mail, execute shell
commands, submit external forms, or transfer funds.

## What is included

- `assessment/adapter/`: a Python harness bridge that launches the real DSH
  TypeScript driver and converts DSH session events into an evaluation trace.
- `assessment/dsh_plugin/`: a DSH test plugin with controlled source tools and
  tracked simulated sink tools.
- `dataset/`: sanitized 1,120-case matrix: 16 channels × text/file modes × 35
  payload objectives.
- `results/`: aggregate statistics and a small sanitized trace sample.
- `analysis/`: reproducible aggregation and plotting scripts.

## Evaluation design

The published summary covers 14,560 agent runs: 1,120 base cases, each paired
with `naive` plus 12 attack methods. `naive` is the unmodified baseline. The
remaining methods alter the same objective through priority framing, structural
or format manipulation, and concealment/context strategies.

### Text mode and file mode

The `carrier_mode` field in `dataset/full_channel_mode_sanitized.toml` selects
the delivery path used by the external A.I.G evaluator:

- **Text mode** injects the payload into a textual representation of the
  carrier. It evaluates how the model responds to the resulting content string.
- **File mode** generates or modifies a carrier file in its native format, then
  invokes the format-specific parsing or extraction path to obtain the content
  visible to the model. It therefore evaluates representation-level behavior
  that a plain-text approximation can miss.

Examples of file-mode carrier handling include:

| Channel | File-mode operation |
|---|---|
| `pdf_metadata` | Modify metadata in a real PDF, then extract model-visible content. |
| `spreadsheet` | Modify cells in a real XLSX spreadsheet, then extract content. |
| `calendar_event` | Generate or modify an `.ics` calendar file. |
| `webpage` | Construct a real HTML carrier file. |
| `email_headers` | Construct an email-format carrier with injected header fields. |

The public dataset records the intended mode for every case. The
format-specific `taint_file()` and `extract_file()` implementations belong to
the external A.I.G evaluation dependency and are not vendored in this
repository. This separation is intentional: a `file` case is not equivalent to
renaming a text artifact with a file extension.

Each trace is evaluated by:

- `J_R`: a deterministic rule-based evaluator that checks taint delivery, sink
  calls, argument matches, canaries, and refusals;
- `J_L`: a semantic LLM-based evaluator applied offline to saved traces.

## Safe reproduction outline

1. Clone DeepSeek Harness and configure a model provider in your own environment.
2. Install the external A.I.G prompt-injection evaluation dependency. 
3. Copy `.env.example` to `.env` and set local paths. Do not commit `.env`.
4. Start from a small subset of the sanitized dataset.
5. Run only against systems you own or are explicitly authorized to test.

The driver uses the model ID `deepseek-v4-flash`. API credentials and API-call
code are deliberately outside this repository.

## Results at a glance

| Finding | Evidence |
|---|---|
| Stateful framing increases measured risk | Fake completion reaches 17.0% `J_L` attack success in text mode, compared with 5.7% for the unmodified baseline. |
| File representation changes the attack surface | Hidden Unicode is 0.0% in text mode but 25.5% `J_R` attack success in file mode. |
| Skills deserve supply-chain controls | The skills channel reaches 14.3% / 16.0% `J_R` attack success in text/file modes. |
| Exact and semantic evaluation differ | `J_L` assigns 7.3% partial compliance overall, compared with 2.0% under `J_R`. |
| Output compliance and action completion should be separated | Output-only tasks show higher success rates than sink-required tasks; their criteria differ and should not be treated as the same operational risk. |
