package plugins

import (
	"context"
	"fmt"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// CollectionInfoPlugin 信息收集插件
type CollectionInfoPlugin struct {
}

func NewCollectionInfoPlugin() *CollectionInfoPlugin {
	return &CollectionInfoPlugin{}
}

// GetPlugin 获取插件信息
func (p *CollectionInfoPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "信息收集插件",
		Desc: "初始化信息收集攻击面分析",
		ID:   "CollectionInfoPlugin",
	}
}

// CollectionInfoPluginPrompt AI提示词模板
const CollectionInfoPluginPrompt = `
作为专业的MCP安全分析专家，你需要对目标MCP项目进行全面的安全信息收集和分析。此阶段为后续安全检测提供基础信息支撑。

## 分析目标
对MCP项目 "%s" 进行系统性的信息收集，为后续安全插件提供准确的项目背景和技术架构信息。

## MCP协议基础
MCP（Model Context Protocol）是连接AI模型与数据源/工具的标准化协议，类似AI应用的USB-C接口。

### 协议类型识别
- **STDIO模式**：标准输入输出，本地进程通信，安全隔离性较好
- **SSE模式**：Server-Sent Events，基于HTTP的流式通信
- **Streaming模式**：基于HTTP的流式通信

## 信息收集范围

### 1. 项目基础信息
**核心分析要点：**
- 项目名称、版本、开发者信息
- 项目定位和主要功能描述
- 目标用户群体和使用场景

### 2. 技术架构分析
**技术栈识别：**
- 编程语言和版本要求
- 依赖框架和第三方库
- 数据库和存储方案
- 网络通信协议和接口设计

**架构模式：**
- MCP服务器实现方式
- 工具注册和发现机制
- 资源管理和访问控制
- 错误处理和日志机制

### 3. 安全关键信息
**权限和访问控制：**
- 文件系统访问权限需求
- 网络访问权限和范围
- 系统资源访问能力
- 用户权限验证机制

**数据处理能力：**
- 输入数据类型和来源
- 数据处理和存储方式
- 输出数据格式和目标
- 敏感信息处理流程

### 4. 功能模块梳理
**工具和资源清单：**
- 提供的MCP工具列表
- 每个工具的功能描述
- 工具间的依赖关系
- 资源访问能力评估

**接口分析：**
- API端点和参数定义
- 认证和授权机制
- 错误响应和状态码
- 接口安全防护措施

### 5. 部署和配置
**环境要求：**
- 操作系统兼容性
- 运行时环境需求
- 网络环境要求
- 配置文件和参数

**安全配置：**
- 默认安全设置
- 可配置的安全选项
- 日志和审计配置
- 备份和恢复机制

## 分析方法

### 文档优先策略
1. **README.md分析**：项目概述、安装配置、使用说明
2. **技术文档**：API文档、架构设计、安全说明
3. **配置文件**：package.json、requirements.txt、Dockerfile等
4. **变更记录**：CHANGELOG、发版说明、安全更新

### 代码结构分析
1. **目录结构**：组织方式和模块划分
2. **核心文件**：主要功能实现和入口点
3. **配置管理**：配置文件和环境变量处理
4. **依赖关系**：外部依赖和内部模块关系

## 输出格式

### 项目概览
- 项目基本信息和定位
- 核心功能和业务价值
- 技术架构和实现方式
- 用户群体和使用场景

### 技术分析
- 编程语言和技术栈
- 框架和依赖库分析
- 数据处理和存储方案
- 网络通信和接口设计

### 安全评估
- 权限需求和访问控制
- 数据处理安全性
- 网络暴露面分析
- 潜在安全关注点

### 功能清单
- MCP工具和资源列表
- 每个功能的详细描述
- 功能间的依赖关系
- 安全敏感操作识别

## 输入数据
代码目录:
------
%s
------

## 输出要求
生成详细的项目信息收集报告，为后续安全检测提供准确的技术背景和风险评估基础。报告应包含完整的技术架构分析、功能模块清单和安全关注点识别。
`

const summaryCollectionPrompt = `
根据上下文生成详细的项目信息收集报告，为后续安全检测提供准确的技术背景和风险评估基础。报告应包含完整的技术架构分析、功能模块清单和安全关注点识别

## 输出格式

### 项目概览
- 项目基本信息和定位
- 核心功能和业务价值
- 技术架构和实现方式
- 用户群体和使用场景

### 技术分析
- 编程语言和技术栈
- 框架和依赖库分析
- 数据处理和存储方案
- 网络通信和接口设计

### 安全评估
- 权限需求和访问控制
- 数据处理安全性
- 网络暴露面分析
- 潜在安全关注点

### 功能清单
- MCP工具和资源列表
- 每个功能的详细描述
- 功能间的依赖关系
- 安全敏感操作识别

直接回复我markdown格式
%s
`

// Check 执行检测
func (p *CollectionInfoPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
	if err != nil {
		config.Logger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(CollectionInfoPluginPrompt, config.CodePath, dirPrompt),
	}, config.Language, config.CodePath)
	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return issues, err
	}
	config.Logger.Infoln("总结信息...")
	history := agent.GetHistory()
	history = append(history, map[string]string{
		"role":    "user",
		"content": fmt.Sprintf(summaryCollectionPrompt, utils.LanguagePrompt(config.Language)),
	})
	var result = ""
	for word := range config.AIModel.ChatStream(ctx, history) {
		result += word
		config.Logger.Print(word)
	}
	return []Issue{
		{
			Title:       "信息收集插件检测结果",
			Description: result,
		},
	}, nil
}
