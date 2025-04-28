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
		ID:   "auth_bypass",
	}
}

// AI提示词模板
const authBypassAIPrompt = `
你是一个专业的网络安全分析助手，需要严格分析给定的源代码目录结构，检测可能存在的身份验证绕过漏洞。你的分析必须基于专业知识和确凿证据，**绝对禁止任何猜测性或不确定的输出**。
MCP区分SSE与STDIO的区别，STDIO是标准输入输出，SSE是流式输入输出。如果项目只支持STDIO，会由于利用门槛较高，将漏洞标记为低风险。
## 输入
源代码文件夹路径:%s
目录详情:
------
%s
------
## 检测要求
1. **准确性第一**：必须确认存在真实风险才可输出结果
2. **无风险不输出**：如果未发现确切漏洞，保持静默不输出任何检测结果
3. **证据充分**：所有发现必须能直接对应到源代码中的问题模式

## 重点检测项
发现以下至少一项确凿证据才可报告：
1. [ ] 弱密码/硬编码凭证：发现明文密码、默认凭证或可预测的凭证生成逻辑
2. [ ] 未加密的令牌传输：检测到HTTP明文传输认证令牌的代码
3. [ ] OAuth缺陷：存在错误的redirect_uri验证或state参数缺失
4. [ ] 缺失身份验证检查：关键接口缺少必要的auth验证中间件
5. [ ] JWT问题：存在不安全的签名验证或过长的有效期设置
6. [ ] 会话管理缺陷：发现会话固定、CSRF防护缺失等问题

## 输出
漏洞描述给出证据:文件位置、代码片段、技术分析(专业术语说明漏洞原理及潜在影响)
`

// Check 执行检测
func (p *AuthBypassPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return nil, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(authBypassAIPrompt, config.CodePath, dirPrompt),
	})
	_, err = agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return nil, err
	}
	return SummaryResult(ctx, agent, config.AIModel)
}
