package plugins

import (
	"context"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
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
你所做的工作是以资深程序员视角对本地mcp代码 "%s" 进行前期[代码信息收集],方便后面插件更迅速了解项目的信息。
MCP 是一个开放协议，它规范了应用程序向 LLM 提供上下文的方式。MCP 就像 AI 应用程序的 USB-C 端口一样。正如 USB-C 提供了一种标准化的方式将您的设备连接到各种外围设备和配件一样，MCP 也提供了一种标准化的方式将 AI 模型连接到不同的数据源和工具。
MCP区分SSE与STDIO的区别，STDIO是标准输入输出，SSE是流式输入输出。如果项目只支持STDIO，会由于利用门槛较高，将漏洞标记为低风险。
[信息收集信息]
- 读取项目内文档[readme]获取项目概览。
- 技术栈识别
	- 识别前后端框架、通信协议、持久层技术
	- 标记非常规依赖（如自定义SDK）
- 接口
	- 识别http端点和其功能
- 从功能角度出发,列举需重点关注文件以及功能和业务逻辑
- 文档解析优先
	- 扫描所有.md/.rst文件，提取项目定位、核心功能、架构图信息
	- 特别关注API_GUIDELINES/SECURITY.md中的接口规范
	- 从CHANGELOG提取近3个版本的关键变更
- 通过提供的代码目录分析,识别每个目录的功能和业务逻辑
报告名称: 项目信息收集报告
代码目录:
------
%s
------
`

const summaryCollectionPrompt = `
根据上下文生成该项目信息收集报告:
- 获取项目概览
  - 核心业务目标与系统边界  
  - 关键模块组成与交互关系
- 技术栈识别
  - 识别前后端框架、通信协议、持久层技术
  - 标记非常规依赖（如自定义SDK）
- 接口功能识别
  - 识别http端点,接口功能及描述
- 从功能角度出发,列举需重点关注文件以及功能和业务逻辑
  - 核心业务逻辑文件
  - 权限控制相关代码
  - 第三方服务集成点
- 提取项目定位、核心功能、架构图信息
- 通过提供的代码目录分析,识别每个目录的功能和业务逻辑，返回新的目录树并标注

直接回复我markdown格式
%s
`

// Check 执行检测
func (p *CollectionInfoPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(CollectionInfoPluginPrompt, config.CodePath, dirPrompt),
	}, config.Language)
	_, err = agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return issues, err
	}
	gologger.Infoln("总结信息...")
	history := agent.GetHistory()
	history = append(history, map[string]string{
		"role":    "user",
		"content": fmt.Sprintf(summaryCollectionPrompt, utils.LanguagePrompt(config.Language)),
	})
	var result = ""
	for word := range config.AIModel.ChatStream(ctx, history) {
		result += word
		gologger.Print(word)
	}
	return []Issue{
		{
			Title:       "信息收集插件检测结果",
			Description: result,
		},
	}, nil
}
