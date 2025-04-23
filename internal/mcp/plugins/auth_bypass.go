package plugins

import (
	"context"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// AuthBypassPlugin 身份验证绕过插件
type AuthBypassPlugin struct {
}

// NewAuthBypassPlugin 创建新的身份验证绕过插件
func NewAuthBypassPlugin() *AuthBypassPlugin {
	return &AuthBypassPlugin{}
}

// 获取插件信息
func (p *AuthBypassPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "身份验证绕过检测",
		Desc: "检测MCP代码中可能存在的身份验证绕过漏洞",
	}
}

// AI提示词模板
const authBypassAIPrompt = `
分析源代码文件夹，检测可能存在的身份验证绕过漏洞。
源代码文件夹路径:%s
目录详情:
-------
%s
-------
根据目录内容推测需要检测的文件。

需要重点检查：
1. 弱密码或硬编码凭证
2. 未加密的令牌传输
3. 不安全的OAuth实现
4. 缺失的身份验证检查
5. JWT实现缺陷
6. 会话管理问题

如果存在风险，请按风险解释、问题代码输出markdown描述，你必须要保证检测结果准确无误，不要误报或漏报。
`

const authBypassResultPrompt = `
返回格式如下,结果用<result>包裹，可返回多个。为空则返回空。
<result>
	<title>漏洞名称</title>
	<desc>漏洞详细描述,可以代码代码输出详情等,markdown格式</desc>
	<level>规则等级</level>
	<suggestion>修复建议</suggestion>
</result>
...
`

// 执行检测
func (p *AuthBypassPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath)
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(authBypassAIPrompt, config.CodePath, dirPrompt),
	}, authBypassResultPrompt)
	result, err := agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return issues, err
	}
	issue := ParseIssues(result)
	issues = append(issues, issue...)
	return issues, nil
}
