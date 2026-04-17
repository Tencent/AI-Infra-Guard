# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v4.1.4] - 2026-04-17

### Security
- **TLS**: Support HTTPS connections with self-signed/private CA certificates for model endpoints; add InsecureSkipVerify option (#306, closes #302)

### Added
- **MCP Scan**: Add multi-turn red team attack module with TAP and Crescendo strategies (#299)
- **System API**: Add data auto-sync API (`POST /api/v1/system/update-data`, `GET /api/v1/system/update-status`) for syncing `data/` directory (#301)
- **Agent Scan API**: Support inline `agent_config` in agent scan API, make verify optional on save (#322)
- **CLI**: Support `--agent-config-file` for inline YAML agent scan config (aig-scanner v1.0.3)
- **Security Policy**: Add SECURITY.md with trust model and vulnerability disclosure policy

### Fixed
- **Vulnerability Rules**: Fill empty rule fields and add new CVE rules
- **API**: Fix mcp_scan content field and add agent_scan API documentation
- **Docs**: Fix HTML block bold rendering in multilingual READMEs
- **Architecture**: Fix runtime path resolution for local deployments

### Changed
- **Codebase**: Convert all Chinese comments and messages to English in api.go and knowledge2_api.go
- **Docs**: Expand Related Papers to 17 entries with 5 new 2026 papers; sync across all multilingual READMEs
- **Docs**: Add architecture evolution document covering v0.1/v2.6/v3.6.0 (#294)
- **Vulnerability Stats**: Update component vulnerability counts, add crewai/kubeai/lobehub entries (#291)

### Contributors
Special thanks to @boyhack, @zhuque, @ac0d3r, @feiyang666, @rocie799, @aig-doc-bot

---

## [v4.1.3] - 2026-04-09

### Fixed
- **Fingerprint**: Add version extractor to OpenClaw fingerprint for accurate version detection (#286)
- **MCP Scan**: Harden agent loop and path validation, clean up config (#282)

### Changed
- **Vulnerability Rules**: Remove duplicate GHSA files already covered by CVE entries (OpenClaw dedup)

### Documentation
- Add quick usage guide with concrete scan target examples (issue #281)
- Sync env.example context window vars, update install and test commands for MCP scan
- Fix README_JA quick guide missing sections and correct OpenClaw vuln count (474→451)
- Restructure and sync What's New sections across EN/ZH/JA READMEs

### Contributors
Special thanks to @boyhack, @zhuque, @zznQ, @feiyang666, @juciepie, @aig-doc-bot

---

## [v4.1.2] - 2026-04-03

### Fixed
- **Task Control**: Added support for stopping running tasks, allowing users to actively terminate scans in progress
- **AI Infra Scan**: Fixed a bug where the "No Model" option could not be selected in AI infrastructure scan task configuration, preventing users from creating model-free scan tasks
- **AI Infra Scan**: Fixed double-dot filename bug in scan file upload that caused certain filenames to be incorrectly rejected
- **AI Infra Scan**: Fixed concurrent goroutine hang in multi-IP scan scenarios, improving scan stability and task completion reliability
- **Agent Scan**: Hardened LLM error handling to prevent scan crashes on unexpected model responses
- **LLM Input**: Fixed inappropriate input text passed to LLM in certain scan scenarios

### Added
- **Vulnerability Rules [2026-03-26]**: Added 15 new CVE rules covering n8n (×11), OpenClaw (×3), llama.cpp (×1)
- **Vulnerability Rules [2026-03-27]**: Added 29 new CVE rules covering BentoML (×1), Langflow (×2), OpenClaw (×26); added BentoML fingerprint
- **Vulnerability Rules [2026-03-30]**: Added 15 new CVE rules covering Langflow (×1), LibreChat (×4), LoLLMs (×1), MLflow (×1), OpenClaw (×8); added Wallos fingerprint
- **Coverage**: AI component vulnerability coverage expanded to **52 components / 1000+ CVEs**

### Changed
- **Fingerprint Accuracy**: Aligned fingerprint `info.name` with vulnerability rule names for consistent detection matching
- **Documentation**: Updated AI infra scan component and CVE statistics in README

### Contributors
Special thanks to @feiyang666, @Yang1k, @aigsec

---

## [v4.1.1] - 2026-03-25

### Added
- **New Vulnerability Rules**: Added AIG rules batch [2026-03-25], expanding AI component vulnerability detection coverage
- **Fingerprint Enhancement**: Added correct new-api fingerprint matcher syntax (FOFA 100%)

### Fixed
- **Security**: Mask token fields in GetTaskDetail response to prevent credential leakage (#226)
- **MCP Scan**: Fix missing imports and mcp_tool alias in mcp_tool module
- **Documentation**: Fix incorrect license name in README.md; fix MIT license reference in README_ZH Features section

### Changed
- **CI**: Optimize yaml-lint workflow with Go cache and failure artifact upload
- **Docs**: Update README What's New section to reflect v4.1 features accurately

### Contributors
Special thanks to @feiyang666, @zhuque, @aigsec

---

## [v4.1] - 2026-03-23

### Added
- **New Scan Port**: Added port 18789 to the default AI infrastructure scan port list for broader AI component coverage
- **New Vulnerability Rules**: Added AIG Rules (2026-03-20 batch), continuously expanding the AI component vulnerability detection rule library
- **OpenClaw Vulnerability Database**: Added 281 new CVE/GHSA entries for OpenClaw components, covering a wide range of AI infrastructure security advisories
- **YAML CI/CD Validation**: Introduced automated YAML format validation pipeline via CSCD; triggered on PR and Push events to ensure rule compliance before merge
- **Task API Enhancement**: Improved taskapi lifecycle management and Agent Scan support
- **edgeone-clawscan Skill**: Added EdgeOne-based ClawScan security scanning Skill powered by Tencent Zhuque Lab AI-Infra-Guard

### Changed
- **License Migration**: Migrated from MIT to Apache 2.0; added NOTICE file with attribution requirements
- **License Headers**: Added Apache 2.0 license headers to all `.go` and `.py` source files

### Fixed
- **CodeQL Hardening**: Completed CodeQL path-injection remediation (Round 2), closing all related security alerts
- **Score Normalization**: Fixed severity case inconsistency in `CalcSecScore` and added support for Chinese severity levels (#178)
- **Agent Config Path Validation**: Fixed path injection risk in `readAgentConfigContent`, added input validation and boundary checks
- **Documentation Fixes**: Fixed ClawScan URL formatting, broken links, and other documentation errors

### Docs
- Added AI coding assistant guideline files: CLAUDE.md, CODEBUDDY.md, AGENTS.md
- Updated README and README_ZH.md with v4.0 feature descriptions and capability overview
- Moved license section to bottom of README_ZH.md; fixed license filename reference to `LICENSE`

### Changed (additional)
- Enforced open-source standards across README, CHANGELOG, NOTICE, and YAML CI configuration

### Contributors
Special thanks to @zhuque, @boyhack, @Nicky, @rocie799, @aigsec

---

## [v4.0] - 2026-03-10

### Added
- **Agent-Scan Framework**: Introduced a brand-new Agent-Scan scanning engine — a complete AI-powered autonomous agent security scanning framework
  - Multi-agent architecture with specialized sub-agents: main agent, SSRF agent, config-scanner agent, vulnerability detector agent, agent security reviewer, and data leakage detection agent
  - Full tool ecosystem including bash, file read/write, edit, grep, glob, ls, batch, thinking, todo, task, skill, MCP tool, dialogue, and finish actions
  - Agent adapter system with support for multiple providers (Dify, Coze, etc.) with streaming response and connectivity testing
  - Skill-based scanning capabilities: OWASP ASI compliance, authorization bypass detection, indirect injection detection, tool abuse detection, data leakage detection (with static & advanced prompt sets and LLM evaluator)
  - Agent security review report generation with structured vulnerability assessment
  - Scan pipeline with dialogue count tracking, tool usage statistics, and async processing
- **Claw-Scan Enhancement**: Improved ClawScan (AIG-PromptSecurity) evaluation framework
- **Component Fingerprints**: Added 4 new AI component fingerprints for improved detection coverage
  - llama.cpp, HuggingFace TGI, NVIDIA NIM, LocalAI

### Changed
- 🐳 **Docker Optimization**: Updated Dockerfile and deployment scripts
  - Use shallow clone and prefer docker compose v2 in `docker.sh`
  - Handle chmod failures gracefully in `start.sh`
  - Updated Dockerfile for Agent-Scan support
- 📝 **Documentation Updates**: Comprehensive README updates
  - Updated README to include Agent Skills in scans
  - Updated README_ZH.md for clarity and accuracy
  - Updated research papers and news sections
- ⚙️ **Configuration Refactoring**: Removed some provider configurations, restructured field hierarchy
  - Removed `idSuffix` field and updated related logic
  - Improved parsing compatibility for config files
  - Updated config JSON files with icon support

### Contributors
Special thanks to @rocie799, @Truman, @test0Emma, @hobostay, @Yang Luo, @mhh

---

## [v3.6.2] - 2026-02-09

### Added
- 🛡️ **Vulnerability Database Expansion**: Added 78 new CVE entries across 15 AI/ML infrastructure components
  - **anythingllm** (1): CVE-2025-63390
  - **comfyui** (2): CVE-2025-67303, CVE-2026-22777
  - **dask** (1): CVE-2026-23528
  - **dify** (4): CVE-2025-56157, CVE-2025-63386, CVE-2025-63387, CVE-2025-63388
  - **feast** (1): CVE-2025-11157
  - **jupyter-notebook** (1): CVE-2025-53000
  - **langchain** (4): CVE-2024-58340, CVE-2025-67644, CVE-2025-68664, CVE-2025-68665
  - **langflow** (9): CVE-2025-34291, CVE-2025-68477, CVE-2025-68478, CVE-2026-0768, CVE-2026-0769, CVE-2026-0770, CVE-2026-0771, CVE-2026-0772, CVE-2026-21445
  - **lobechat** (1): CVE-2026-23835
  - **mlflow** (3): CVE-2025-10279, CVE-2025-14279, CVE-2026-22607
  - **n8n** (33): CVE-2023-27562, CVE-2023-27563, CVE-2023-27564, CVE-2025-46343, CVE-2025-49592, CVE-2025-49595, CVE-2025-52478, CVE-2025-52554, CVE-2025-55526, CVE-2025-57749, CVE-2025-61914, CVE-2025-61917, CVE-2025-62726, CVE-2025-65964, CVE-2025-68613, CVE-2025-68668, CVE-2025-68697, CVE-2025-68949, CVE-2026-0863, CVE-2026-1470, CVE-2026-21858, CVE-2026-21877, CVE-2026-21893, CVE-2026-21894, CVE-2026-25049, CVE-2026-25051, CVE-2026-25052, CVE-2026-25053, CVE-2026-25054, CVE-2026-25055, CVE-2026-25056, CVE-2026-25115, CVE-2026-25631
  - **ollama** (5): CVE-2025-15063, CVE-2025-15514, CVE-2025-63389, CVE-2025-66959, CVE-2025-66960
  - **open-webui** (1): CVE-2025-63391
  - **simstudioai** (8): CVE-2025-7107, CVE-2025-7114, CVE-2025-9800, CVE-2025-9801, CVE-2025-9805, CVE-2025-10096, CVE-2025-10097, CVE-2025-15099
  - **vllm** (4): CVE-2026-22773, CVE-2026-22778, CVE-2026-22807, CVE-2026-24779

### Changed
- 📝 **CVE Updates**: Updated existing vulnerability entries for improved accuracy
  - clickhouse: CVE-2024-23689
  - gradio: CVE-2024-1728
  - langchain: CVE-2025-65106
  - langflow: CVE-2025-57760
  - mlflow: CVE-2025-11201
  - vllm: CVE-2025-62164

---

## [v3.6.1] - 2026-01-27

### Added
- 🆔 **Component Fingerprints**: Added Clawdbot Gateway fingerprint to improve AI component vulnerability detection coverage.

## [v3.6.0] - 2025-01-17

### Added
- 🔐 **System Administration**: Added SYS_ADMIN capability for Chrome sandbox and database indexes for performance enhancement (@zhuque)
- 📊 **Report Enhancement**: Updated feature and pager, resolved text misalignment in PDF report download (@zonashi)
- 📝 **User Guide**: Updated user guide for new features (@zonashi)
- ⏱️ **Scan Metrics**: Added model & scan duration in AI tool protocol scan report (@zonashi)
- 👥 **User Management**: Refactored User struct and enhanced user management methods (@boyhack)

### Changed
- 📚 **Documentation**: Updated API docs, Swagger docs, and model API (@zhuque)
- 🐳 **Docker Config**: Updated docker-compose.yml and docker-compose.images.yml (@zhuque)
- 🔢 **Versioning**: Updated version to v3.6.0 (@zhuque)
- 🧠 **LLM Result**: Added LLM parameter to MCP meta result (@zhuque)
- 🗄️ **Database**: Fixed LLM model database (@zhuque)
- 🔐 **Auth**: Implemented inner API auth controller (@zhuque)
- 🎯 **Score Correction**: Corrected CalcSecScore method in runner.py to handle Chinese risk levels correctly (@mhh)
- ⚖️ **Risk Type**: Corrected item.RiskType to item.Severity in scoring logic (@mhh)

### Fixed
- 🧪 **Testing**: Removed test info (@zhuque)

### Contributors
Special thanks to @mhh, @aaasven

---

## [v3.6.0-rc1] - 2025-01-07

### Changed
- 🎯 **Audit Prompt Optimization**: Reduced false positives by focusing on network-layer vulnerabilities
  - Added input source risk priority rules, ignoring CLI inputs
  - Only report medium+ severity vulnerabilities
  - Command injection detection excludes CLI parameter scenarios
  - Credential theft detection requires network exfiltration path
- 🔍 **Skill Project Audit**: Improved Skill project security analysis
  - Skill projects don't require MCP risk classification
  - Focus on malicious behavior detection (reverse shell, data exfiltration, backdoor, cryptominer)
  - Ignore code quality and development standard issues
- ✅ **Quality Checklist**: Added network reachability verification to vulnerability review

---

## [v3.5.0] - 2025-12-26

### Added
- 📚 **Research & Documentation**: Added AIG Technical Report, Black Hat Europe 2025 slides, and Black Hat Arsenal presentation (@hermitgreen, @Nicky, @LouisHovaldt)
- 🎓 **Academic Collaborations**: Added academic collaboration section with partner institutions (@zonashi)
- 🔍 **Dynamic Analysis Framework**: Complete dynamic analysis workflow with specialized agents for malicious behavior testing and vulnerability testing (@sc, @MoonBirdLin)
- 🛡️ **Security Detection**: Tool poisoning detection and rug pull detection support (@sc)
- 📊 **Evaluation Datasets**: Added comprehensive test datasets (copyright-violation, misinformation, privacy-leakage, unethical-behavior, violent, non-violent-illegal-activity) (@zonashi)
- 🔧 **MCP Tools Enhancement**: Added mcp_tool for remote MCP server tool invocation (@zhuque)
- 📝 **File Operations**: Added write_file tool for file writing operations (@zhuque)
- 🔌 **Version API**: Added version router endpoint (@zhuque)
- 🎯 **Prompt Manager**: Introduced prompt_manager utility for better prompt template management (@zhuque)
- 🔐 **MCP Header Support**: Added custom MCP header support for authentication and protocol configuration (@zhuque)

### Changed
- ♻️ **MCP Architecture Refactoring**: Complete overhaul of MCP agent architecture for better modularity and performance (@zhuque, @MoonBirdLin)
- 🎨 **Agent Optimization**: Significantly improved agent prompts and reduced tool execution overhead (@zhuque)
- 📦 **Tool System Redesign**: Introduced ToolDispatcher, refactored tool registry, and improved tool schema management (@zhuque)
- 🐳 **Docker Optimization**: Further reduced Docker Agent image size and improved Dockerfile structure (@zhuque, @ac0d3r)
- 📝 **Logging Enhancement**: Optimized logging system and status update mechanisms (@zhuque)
- 🔄 **Prompt Updates**: Comprehensive updates to code audit, project summary, and vulnerability review prompts (@zhuque)
- 📦 **Dependencies**: Updated requirements, pinned deepeval to <3.7.6 for compatibility (@zhuque, @Truman)
- 🎯 **Scoring Algorithm**: Improved calc_mcp_score function for better vulnerability assessment (@zhuque)
- 🌐 **README Updates**: Enhanced README with better structure, GIF demos, and recommended security tools (@zonashi)
- 📡 **Backend API Simplification**: Refactored and simplified MCP-scan backend API, reduced code complexity in websocket/api.go (@zhuque)
- 📖 **API Documentation**: Updated Swagger documentation with latest API endpoints and improvements (@zhuque)
- 🎨 **Frontend UI Optimization**: Enhanced LLM security check experience with prompt input detection support (@zonashi)
- 🔧 **Frontend Settings Consolidation**: Merged auxiliary functions (plugin management, model management) into unified settings panel for cleaner interface (@zonashi)
- 📋 **Version Display**: Added version number and changelog display in frontend for easier issue tracking (@zonashi)
- 🔐 **MCP Header Configuration**: Added MCP scan header configuration in frontend to support MCP service authentication (@zonashi)

### Fixed
- 🐛 **MCP Agent Bugs**: Fixed various MCP agent bugs and improved stability (@boy-hack, @zhuque)
- 🔧 **Execute Actions**: Fixed execute_actions timeout handling and parameter type conversion (@zhuque)
- 🎯 **Transport Type**: Fixed server_transport type issue (@sc)
- 📊 **Output Handling**: Fixed error output when testing without function invocation but with mcp_function invocation (@MoonBirdLin)
- 🛠️ **System Robustness**: Multiple bug fixes for improved system stability (@zhuque, @MoonBirdLin)
- 📝 **LLM Integration**: Fixed llm.py parameter handling and retry logic (@zhuque)
- 🔐 **Frontend Header Bug**: Fixed AI infrastructure scan header configuration not taking effect (@zonashi)

### Contributors
Special thanks to @zhuque, @sc, @MoonBirdLin, @zonashi, @Truman, @ac0d3r, @hermitgreen, @Nicky, @LouisHovaldt, @boy-hack

---

## [v3.5-rc3] - 2025-12-10
- fixed mcp-scan not found directory bug
- update frontend

## [v3.5-preview-2] - 2025-12-05
### Changed
- Improved the onboarding guide for frontend newcomers
- Vulnerability database: Added 100+ AI component CVEs, with support for detecting the latest React2Shell vulnerability (CVE-2025-55182), which affects popular AI frameworks such as Dify, NextChat, and LobeChat.

## [v3.5-preview] - 2025-12-04

### Added
- 🔍 **MCP-Scan Framework**: AI-powered security scanning framework for Model Context Protocol with autonomous agent-based code audit and vulnerability review (@zhuque)
- 🎯 **Advanced Attack Methods**: Added 12+ new encoding/obfuscation attack methods (A1Z26, AffineCipher, AsciiSmuggling, Aurebesh, Caesar, Leetspeak, MirrorText, Ogham, Vaporwave, Zalgo, Stego, StrataSword suite) (@Truman)
- 📸 **Screenshot Capabilities**: Chromium-based headless screenshot functionality for web scanning (@zhuque)
- 🔐 **Model API Security**: Token masking, API key preservation, and public model access controls (@n-WN)
- 📊 **Hash-Based Fingerprinting**: Hash matcher and version range support for component identification (@KEXNA, @Cursor Agent)
- 🌐 **Documentation**: Comprehensive English docs, FAQ, MCP-Scan guides, and research paper references (@zonashi, @zhuque)
- 🐳 **Docker Optimization**: Reduced agent image size from ~2.9GB to ~2.3GB, improved deployment scripts (@n-WN, @zhuque)

### Changed
- ♻️ **Backend Refactoring**: Optimized AI infrastructure scan architecture, reduced agent task code by ~65% (@zhuque)
- 🔄 **MCP Plugin**: Streamlined plugin architecture, removed redundant templates (@zhuque)
- 🚀 **Model Compatibility**: Enhanced parameter compatibility and retry logic across providers (@Truman)
- 🎨 **Code Quality**: Translated comments to English, improved formatting and documentation (@zhuque)

### Fixed
- 🐛 Fixed AI Infra Guard path resolution and Chromium sandbox issues (@zhuque)
- 🔧 Fixed Docker deployment errors (issue #105) and build optimizations (@n-WN, @zhuque)
- ⚙️ Fixed fingerprint parser syntax and version detection logic (@Cursor Agent, @KEXNA)
- 📊 Updated UI badges, screenshots, and license file naming (@zonashi, @Zonazzzz)

### Contributors
Special thanks to @zhuque, @Truman, @n-WN, @KEXNA, @zonashi, @Cursor Agent, @copilot-swe-agent[bot], @boy-hack, @Zonazzzz, @robertzyang, @Coursen

---

## [v3.4.4] - 2025-11-05

### Fixed
1. Fixed issue where prompts could be incorrectly split
2. Added generalized model loading logs
3. Added model loading parameter combination attempts
4. Fixed model invocation parameter compatibility issue
5. Optimized log display
6. Fixed https://github.com/Tencent/AI-Infra-Guard/issues/110

## [v3.4.3] - 2025-10-27
### Added
🔧 **API Documentation Support**: Updated and enhanced API documentation support, providing more complete interface documentation and Swagger specifications.
🤖 **Model Invocation Base Class**: Added base class methods for model invocation, improving code reusability and maintainability.
📊 **Evaluation Dataset Expansion**: Added test datasets related to Cyberattack and CBRN weapons.

### Fixed
🛠️ **CSV Encoding Issue**: Fixed Chinese garbled text issue in CSV files, improving data export experience.

## [v3.4.2] - 2025-09-25
- Optimized frontend
- Added new vulnerability fingerprints:
clickhouse
comfyui
dask
gradio
langchain
langflow
langfuse
LiteLLM
ollama
open-webui
pyload-ng
ragflow
ray
triton-inference-server
vllm


## [v3.4.1] - 2025-09-24
- Added vulnerability fingerprint CVE-2025-23316
- Optimized: triton fingerprint

## [v3.4] - 2025-09-18
### Added
🌐 **Internationalization Support**: Implemented frontend interface internationalization (i18n) support, including multi-language text and English screenshot resources.
🐳 **Docker Enhancement**: Updated one-click deployment script, added Docker pull error information prompt, and supported Apple ARM architecture deployment.
⚡ **Task Concurrency Control**: Added task concurrency limit feature, optimized system resource management.
🔄 **Model Retry Logic**: Updated model invocation retry mechanism, improving service stability.
🤖 **Agent Auto-Recovery**: Implemented automatic restart function after Agent process abnormal exit.
📚 **Multi-Dataset Compatibility**: Enhanced compatibility handling for multiple dataset formats.
🔌 **OpenAPI Interface Update**: Handled the issue of thinking model thinking process being too long.

### Fixed
🛠️ **Frontend Issue Fix**: Fixed frontend interface display issues, including narrow screen adaptation and specific UI anomalies (#74).
🔧 **MCP Issue Fix**: Fixed known bugs in MCP protocol, including model output processing and connection stability.
⚙️ **Parameter Parsing Error**: Fixed exception issues in parameter parsing process.
📊 **Evaluation Exception Fix**: Fixed abnormal behavior in evaluation module.
🔄 **Task Reset Failure**: Fixed the issue of task reset operation failure while running.
🛡️ **Security Risk Fix**: Fixed security risk issues related to IP checking (#78).
🔗 **Circular Import Issue**: Fixed possible circular import errors in code.
📝 **License Update**: Updated project license files.

## [v3.3] - 2025-09-03
- Added one-click Docker deployment script for Linux
- Fixed SSE connection failure issue when disk read/write is slow
- Optimized AI infrastructure scanning probe

## [v3.2] - 2025-08-26

### Added

- 📊 **MCP Scan Report Optimization**: Added more dimensions of detection data display, improving user experience.
- 📱 **Narrow Screen Security Report Adaptation**: Optimized the display of large model security check reports on narrow screens.
- ⚙️ **New Model Concurrency Limit**: Introduced new model concurrency limit feature.

### Fixed

- 🔌 **Fixed MCP SSE Timeout Issue**: Resolved the timeout issue of Server-Sent Events (SSE) in MCP (Model Control Protocol).
- ❓ **Fixed MCP Model Empty Output Exit Issue**: Resolved the issue where the system would exit when MCP model output is empty (#61).
- 📋 **Updated MCP Hardcoded Template**: Updated the hardcoded template for MCP.
- 🛡️ **Fixed AIG Prompt IP Check Risk**: Fixed security risks related to IP checking in AIG prompts.
