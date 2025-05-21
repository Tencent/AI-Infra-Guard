package plugins

import (
	"context"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// VulnReview 漏洞评审插件
type VulnReview struct {
	origin string
}

func VulnReviewPlugin(origin string) *VulnReview {
	return &VulnReview{
		origin: origin,
	}
}

// GetPlugin 获取插件信息
func (p *VulnReview) GetPlugin() Plugin {
	return Plugin{
		Name:   "漏洞评审插件",
		Desc:   "对已有代码进行漏洞评审，复核",
		ID:     "vuln_review",
		NameEn: "Vuln Review",
		DescEn: "Vuln Review is a plugin for vuln review",
	}
}

// Check 执行检测
func (p *VulnReview) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	// AI提示词模板
	const prompt = `
【角色】您是企业级代码安全专家，负责对漏洞报告进行专业复查和增强处理
【任务】请严格按以下流程处理输入的漏洞数据：
1. 重复性核查 
   • 对比所有<result>条目内容
   • 通过匹配代码路径/漏洞类型/漏洞详情特征识别重复项
   • 保留最完整的条目，合并相似报告的补充信息
2. 技术细节增强
   • 检查<desc>字段完整性：
   1.精确的代码路径定位(文件路径+行号范围)
   2.至少3个关键代码段的snippet展示
   3.触发条件分析（执行流、数据流分析）
   4.攻击面的上下文说明（包括依赖组件版本）
   • 添加数据验证建议：
   ① 输入验证缺失点的具体位置
   ② 污点传播路径图示（用graphviz语法描述）
3. 风险等级校准
   • 根据CVSS v3.1标准重新评估<level>
   • 结合OWASP TOP 10分类验证<risk_type>
   • 特殊场景识别：
   ① 涉及身份验证前置条件的降权处理
   ② 暴露在公网的Service自动提级
4. 修复方案优化
   • 确保建议包含： 
   ① 短期缓解措施（配置修改/补丁应用）
   ② 长期架构改进方案
   ③ 具体代码修改示例（前后对比diff格式）

【输出要求】
1. 保留原始XML结构但需要：
   • 验证所有标签闭合
   • 按照不同的独立漏洞输出报告，每个漏洞占一个<result>标签
   • 格式类似
	 <arg>
		<result>
			<title>Vulnerability Name</title>
			<desc>Detailed description in Markdown format, including code paths, file locations, code snippets, relevant context, and technical analysis (using professional terminology to explain the vulnerability's principle and potential impact).</desc>
			<risk_type>Vulnerability risk type</risk_type>
			<level>Severity level (critical, high, medium,low)</level>
			<suggestion>Step-by-step remediation guidance</suggestion>
		</result>
		<!-- Additional <result> entries can be added -->
	</arg>

【禁止行为】
• 不得删除原始报告中的技术细节
• 禁止使用模糊表述如"可能"、"或许"
• 不可引入原始数据外的假设条件

代码路径:%s
### 原始报告
%s
`
	var issues []Issue
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(prompt, config.CodePath, p.origin),
	}, config.Language)
	_, err := agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config)
}
