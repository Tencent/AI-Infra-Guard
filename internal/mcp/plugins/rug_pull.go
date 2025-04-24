package plugins

import (
	"context"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// RugPullPlugin Rug Pull攻击检测插件
type RugPullPlugin struct {
}

// NewRugPullPlugin 创建新的Rug Pull攻击检测插件
func NewRugPullPlugin() *RugPullPlugin {
	return &RugPullPlugin{}
}

// 获取插件信息
func (p *RugPullPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "Rug Pull攻击检测",
		Desc: "检测MCP代码中可能存在的Rug Pull攻击风险",
	}
}

// AI提示词模板
const rugPullAIPrompt = `
请分析以下 MCP 服务器代码，判断是否存在 Rug Pull Attack 风险。
Rug Pull Attack 指的是一个MCP工具在初始安装和批准时看起来是安全的，但在后续使用中会改变其行为或描述，以执行恶意操作或诱导用户/LLM 执行危险行为（例如，访问敏感数据）。

请检查代码中是否有工具同时满足以下特征：
1.  其行为或功能会根据调用次数或其他条件发生变化。
2.  其注释中的工具描述 (类似python __doc__ 字符串) 会动态改变，特别是如果改变后的描述包含误导性或危险的指令。
3.  改变后的行为或描述试图访问敏感资源或诱导执行非预期操作。

源代码文件夹路径:%s
目录详情:
-------
%s
-------
根据目录内容推测需要检测的文件。
`

// 执行检测
func (p *RugPullPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(rugPullAIPrompt, config.CodePath, dirPrompt),
	})
	result, err := agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return issues, err
	}
	if result == "" {
		gologger.Warningln("检测结果为空")
		return issues, nil
	}
	var issue []Issue
	issue = ParseIssues(result)
	issues = append(issues, issue...)
	return issues, nil
}
