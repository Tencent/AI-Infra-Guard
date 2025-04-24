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

[信息收集信息]
1. 读取项目内文档[readme]获取项目概览。
2. 了解项目功能和架构,项目使用的技术栈
3. 了解项目功能点,以及代码逻辑
3. 从功能角度出发,列举需重点关注文件以及功能和业务逻辑

目录详情:
------
%s
------

command finish最终结果格式(required):
最终输出总结为markdown格式大模型提示词,给接下来插件获取项目基本信息提供帮助.
eg:<arg>[信息收集信息]</arg>
`

const summaryCollectionPrompt = `
忘记以上格式要求,现在按照以下要求总结信息:
1. 读取项目内文档[readme]获取项目概览。
2. 了解项目功能和架构,项目使用的技术栈
3. 了解项目功能点,以及代码逻辑
3. 从功能角度出发,列举需重点关注文件以及功能和业务逻辑

直接回复我markdown格式大模型提示词,给接下来插件获取项目基本信息提供帮助.
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
	})
	result, err := agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return issues, err
	}
	if result == "" {
		gologger.Warningln("重新总结信息...")
		history := agent.GetHistory()
		history = append(history, map[string]string{
			"role":    "user",
			"content": summaryCollectionPrompt,
		})
		result = ""
		for word := range config.AIModel.ChatStream(ctx, history) {
			result += word
		}
	}
	return []Issue{
		{
			Title:       "信息收集插件检测结果",
			Description: result,
		},
	}, nil
}
