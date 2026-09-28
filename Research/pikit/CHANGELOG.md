# Changelog

All notable changes to pikit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.5.0] - 2026-07-29

### Added

- **External Agent Harnesses** — adapters for LangChain, OpenAI Agents SDK,
  PydanticAI, OpenClaw, and Hermes.
- **Runtime indirect-injection matrix** — OpenClaw/Hermes fixture sources for
  documents, webpages, email, RAG, and skills; safe simulated sink capture.
- **Runtime tooling** — `pikit runtime init`, `doctor`, and
  `install-fixture` for isolated external-runtime profiles.
- **Structured experiment reports** — `pikit report` renders Markdown or
  self-contained HTML from JSON/JSONL results.
- **Outcome metadata** — results distinguish attack success, model
  compliance, runtime policy blocks, and structured judge evidence.
- Bundled runtime fixture source assets under `pikit.runtime_assets`.

### Changed

- Matrix execution now resolves runtime harnesses through a registry.
- Runtime file-mode experiments feed channel-extracted model-visible text to
  safe fixture tools.

## [0.4.0] - 2026-07-08

### Added

- **File-mode indirect injection** — channels now support two delivery modes:
  - **Text mode** (default): operates on plain-text representations, same as
    before.
  - **File mode** (`mode="file"`): operates on real carrier files (`.html`,
    `.eml`, `.pdf`, `.ics`, `.csv`, `.json`, `.yaml`, …) whose format matches
    what a real agent encounters.
- **`pikit.carriers` module** with 14 clean carrier files and management API
  (`carrier_path`, `load_carrier`, `load_carrier_bytes`, `CARRIER_FILES`).
- **`Channel.taint_file()`** method on the base class, with format-specific
  overrides for:
  - `pdf_metadata` — uses `pypdf` to inject into real PDF `/Info` dictionary.
  - `calendar_event` — uses iCalendar standard field names (`SUMMARY`,
    `DESCRIPTION`, `LOCATION`, `NOTE`) on real `.ics` files.
  - `spreadsheet` — supports `.csv` (text) and `.xlsx` (via `openpyxl`).
  - `structured_data` — auto-detects format from file extension.
- **`Channel.extract()` / `extract_file()`** methods for reading tainted
  artifacts back as model-visible text.
- `craft()` gains `mode`, `carrier_path`, and `output_path` parameters.
- `CraftResult.output_path` field for file-mode results.
- `ExperimentConfig.carrier_mode` field for batch experiments.
- CLI `--mode` flag for `pikit run`.
- `pypdf` and `openpyxl` as optional `[file-mode]` and `[dev]` dependencies.
- 41 new tests covering carriers module, text-based file mode, PDF/ICS/CSV
  injection, `craft(mode="file")`, and `extract()`.

### Changed

- `Channel` base class docstring updated with two-mode documentation.
- `pyproject.toml` adds `[tool.setuptools.package-data]` for carrier files.
- Version bump to 0.4.0.

## [0.3.0] - 2026-07-08

### Added

- **Unified tool pool** (`pikit.agent.builtin_tools`): 32 tools across 6
  categories (web, email, file, code, knowledge, communication) with pool
  management API (`all_tools`, `get_tools`, `tools_by_category`,
  `data_source_tools`, `sink_tools`) and category bundles
  (`BROWSER_TOOLS`, `EMAIL_TOOLS`, `CODING_TOOLS`, `RAG_TOOLS`).
- **Dynamic system-prompt builder** (`pikit.agent.system_prompt`):
  `build_system_prompt()` auto-generates the tool list and safety text from
  the agent's actual tool set, ensuring prompts stay in sync with tools.
- 46 new tests covering tool pool structure, pool queries, category bundles,
  dynamic prompts, and expanded attack surface.

### Changed

- Scenario agents (browser, email, coding, rag) now select tools from the
  unified pool via category bundles instead of hard-coding individual tools.
- `Tool` dataclass and `@tool` decorator gain a `category` field.
- Browser agent: 6 tools (was 3), 5 taint points (was 2).
- Email agent: 8 tools (was 3), 5 taint points (was 2), 3 sinks (was 1),
  cross-domain tools (`search_kb`, `post_message`).
- Coding agent: 13 tools (was 5), 7 taint points (was 3), 6 sinks (was 2).
- RAG agent: 6 tools (was 3), 5 taint points (was 2), added `summarize_text`
  and `translate_text`.
- System prompts are now dynamically generated instead of hard-coded.
- Scenario agents accept optional `tools=` parameter for custom tool sets.
- Total attack surface expanded from ~8 to 17 unique taint points, and
  from 4 to 12 unique sink tools.

## [0.2.0] - 2026-07-08

### Added

- **Batch matrix evaluation** (`pikit.matrix`): `MatrixRunner` automates
  attacks × defenses × channels × agents combinatorial experiments with
  `ExperimentResult` persistence to JSON / CSV.
- **Automatic judge** (`pikit.judges`): `RuleJudge` (heuristic: sink-firing,
  keyword matching, refusal detection) and `LLMJudge` (model-based verdict)
  for automated success/failure verdicts on agent traces.
- **Detection defenses** (`pikit.defenses.detection`): `PatternDetector`,
  `LengthDetector`, `RepetitionDetector` with `DetectionHooks` for flagging
  suspicious input at three agent insertion points.
- **Experiment configuration** (`pikit.config`): `ExperimentConfig` dataclass
  with TOML loading for reproducible batch experiments.
- **CLI entry point** (`pikit.cli`): `pikit list`, `pikit show`, `pikit run`,
  `pikit matrix` subcommands available after `pip install`.
- **CI workflow** (`.github/workflows/ci.yml`): runs pytest on Python 3.9 /
  3.11 / 3.12 and verifies CLI entry point.
- **CONTRIBUTING.md**: guide for adding new attacks, defenses, channels,
  agents, and target backends.

### Changed

- Version bumped to `0.2.0`.
- `pikit/__init__.py` now exports `Judge`, `JudgeResult`, `RuleJudge`,
  `LLMJudge`, and `ExperimentConfig`.

### Fixed

- `.gitignore` now includes `site/` (MkDocs build output) to prevent
  accidental commits of generated documentation.

## [0.1.0] - 2026-07-02

### Added

- Core architecture: `Attack`, `Defense`, `Channel` base classes with
  decorator-based registry system.
- 8 attacks: naive, escape, context_ignoring, fake_completion, combined,
  payload_splitting, obfuscation, prefix_injection.
- 6 prevention defenses: delimiters, sandwich, instructional, spotlighting,
  random_sequence_enclosure, retokenization.
- 6 channels: webpage, document, markdown, code_comment, skills,
  unicode_hidden.
- 4 target backends: OpenAI-compatible, Anthropic, HuggingFace, Mock.
- 6 agents: chat, tool, email, rag, browser, coding.
- `craft()` unified entry point for direct and indirect injection.
- `Trace` / `TraceStep` for human-readable agent run inspection.
- `DefenseHooks` for defense insertion at system / tool_result / user.
- Demo runner (`demos/run.py`) with CLI, TOML config, and interactive modes.
- MkDocs Material documentation site deployed to GitHub Pages.
