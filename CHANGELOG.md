# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v3.4] - 2025-09-18
- 优化:Docker相关:支持Apple ARM架构部署，Agent自动重启,WEB重启后重置任务状态
- 优化:大模型体检部分功能
- 优化:国际化支持
- 优化:MCP扫描 分数计算

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
