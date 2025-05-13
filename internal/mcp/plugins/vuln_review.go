package plugins

import (
	"context"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// VulnReview 漏洞评审插件
type VulnReview struct {
}

func VulnReviewPlugin() *VulnReview {
	return &VulnReview{}
}

// 获取插件信息
func (p *VulnReview) GetPlugin() Plugin {
	return Plugin{
		Name:   "漏洞评审插件",
		Desc:   "对已有代码进行漏洞评审，复核",
		ID:     "vuln_review",
		NameEn: "Vuln Review",
		DescEn: "Vuln Review is a plugin for vuln review",
	}
}

// 执行检测
func (p *VulnReview) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	// AI提示词模板
	const prompt = `
`
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(prompt, config.CodePath, dirPrompt),
	}, config.Language)
	_, err = agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config)
}
