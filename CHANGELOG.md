# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
