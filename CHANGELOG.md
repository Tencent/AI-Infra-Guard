# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
