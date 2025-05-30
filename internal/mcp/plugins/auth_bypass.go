package plugins

import (
	"context"
	"fmt"
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
		Name:   "身份验证绕过检测",
		NameEn: "Auth Bypass",
		Desc:   "检测MCP代码中可能存在的身份验证绕过漏洞",
		DescEn: "Detect possible authentication bypass vulnerabilities in MCP code.",
		ID:     "auth_bypass",
	}
}

// AI提示词模板
const authBypassAIPrompt = `
你是一个专业的网络安全分析助手，需要严格分析给定的源代码目录结构，检测可能存在的身份验证绕过漏洞。你的分析必须基于专业知识和确凿证据，**绝对禁止任何猜测性或不确定的输出**。
## 检测要求
1. **准确性第一**：必须确认存在真实风险才可输出结果
2. **无风险不输出**：如果未发现确切漏洞，保持静默不输出任何检测结果
3. **证据充分**：所有发现必须能直接对应到源代码中的问题模式

## 重点检测项
发现以下至少一项确凿证据才可报告：
- 弱密码/硬编码凭证：发现明文密码、APIKEY、可预测的凭证生成逻辑，但是对于项目中配置的默认密码不报告
- OAuth缺陷：存在错误的redirect_uri验证或state参数缺失
- 缺失身份验证检查：关键接口缺少必要的auth验证中间件
- JWT问题：存在不安全的签名验证绕过、jwt token泄露、jwt token重放等
- 会话管理缺陷：发现会话固定、CSRF防护缺失等问题

## 输出
漏洞描述给出证据:文件位置、代码片段、技术分析(专业术语说明漏洞原理及潜在影响)

## 输入
源代码文件夹路径:%s
目录详情:
------
%s
------
`

// Check 执行检测
func (p *AuthBypassPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		config.Logger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return nil, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(authBypassAIPrompt, config.CodePath, dirPrompt),
	}, config.Language, config.CodePath)
	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return nil, err
	}
	return SummaryResult(ctx, agent, config)
}
