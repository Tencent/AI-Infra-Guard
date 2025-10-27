# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v3.4.3] - 2025-10-27
### 新增功能 (Added)
🔧 **API文档支持**：更新并增强了API文档支持，提供更完整的接口文档和Swagger规范。
🤖 **模型调用基础类**：新增模型调用的基础类方法，提升代码复用性和维护性。
📊 **评估数据集扩展**：新增网络攻击(Cyberattack)和CBRN武器相关的测试数据集。

### 修复问题 (Fixed)
🛠️ **CSV编码问题**：修复CSV文件中文乱码问题，改善数据导出体验。

## [v3.4.2] - 2025-09-25
- 优化前端
- 新增漏洞指纹:
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
- 新增漏洞指纹 CVE-2025-23316
- 优化：triton指纹

## [v3.4] - 2025-09-18
### 新增功能 (Added)
🌐 **国际化支持**：实现了前端界面的国际化(i18n)支持，包括多语言文本和英文截图资源。
🐳 **Docker增强**：更新了一键部署脚本，增加Docker拉取错误信息提示，并支持Apple ARM架构部署。
⚡ **任务并发控制**：新增任务并发限制功能，优化系统资源管理。
🔄 **模型重试逻辑**：更新模型调用重试机制，提升服务稳定性。
🤖 **Agent自恢复**：实现Agent进程异常退出后的自动重启功能。
📚 **多数据集兼容**：增强对多数据集格式的兼容性处理。
🔌 **OpenAPI接口更新**：处理thinking模型思考过程过长的问题。

### 修复问题 (Fixed)
🛠️ **前端问题修复**：修复前端界面显示问题，包括窄屏适配和特定UI异常（#74）。
🔧 **MCP问题修复**：修复MCP协议中的已知Bug，包括模型输出处理和连接稳定性。
⚙️ **参数解析错误**：修复参数解析过程中的异常问题。
📊 **评估异常修复**：修复评估模块中的异常行为。
🔄 **任务重置失败**：修复运行中任务重置操作失败的问题。
🛡️ **安全风险修复**：修复IP检查相关的安全风险问题（#78）。
🔗 **循环导入问题**：修复代码中可能的循环导入错误。
📝 **许可证更新**：更新项目许可证文件。

## [v3.3] - 2025-09-03
- 新增docker部署一键脚本 For Linux
- 修复磁盘读写较慢情况下SSE连接失败问题
- 优化AI基础设施扫描探针

## [v3.2] - 2025-08-26

### 新增功能 (Added)

- 📊 **MCP扫描报告优化**：增加了更多维度的检测数据展示，提升了用户体验。
- 📱 **窄屏安全报告适配**：优化了大模型安全体检报告在窄屏下的展示问题。
- ⚙️ **新增模型并发限制**：引入了新的模型并发限制功能。

### 修复问题 (Fixed)

- 🔌 **修复MCP SSE超时问题**：解决了MCP（模型控制协议）中服务器发送事件（SSE）的超时问题。
- ❓ **修复MCP模型输出为空退出问题**：解决了当MCP模型输出为空时系统会退出的问题 (#61)。
- 📋 **更新MCP硬编码模板**：更新了MCP的硬编码（hardcoded）模板。
- 🛡️ **修复AIG提示词IP检查风险**：修复了与AIG提示词中IP检查相关的安全风险。
