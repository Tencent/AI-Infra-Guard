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
【角色】您是企业级代码安全专家，负责对漏洞报告进行专业复查和增强处理,你的分析必须基于专业知识和确凿证据，**绝对禁止任何猜测性或不确定的输出**。
【任务】请严格按以下流程处理输入的漏洞数据：
1. 重复性核查 
   • 对比所有<result>条目内容
   • 通过匹配代码路径/漏洞类型/漏洞详情特征识别重复项
   • 保留最完整的条目，合并相似报告的补充信息
2. 漏洞误报核查
	1. 识别漏洞是否真实存在,需识别到用户可控点(source)和触发点(sink)
	2. 绝对禁止任何猜测性的漏洞报告
	4. 未授权访问需发现严重问题或功能上高危问题,若无以上问题则不要报告
	5. 通过环境变量加载敏感信息，除非发现可通过在线接口暴露，否则属于正常功能，不报告
	6. 对于敏感变量硬编码,若为占位符或demo举例，不报告
	7. MCP程序区分SSE、Stream与STDIO的区别，STDIO是标准输入输出，SSE/Stream是网络流式输入输出。识别项目的支持方式,如果项目只支持STDIO，漏洞影响较小,不报告
3. 技术细节增强
   • 检查<desc>字段完整性：
   1.精确的代码路径定位(文件路径+行号范围)
   2.至少3个关键代码段的snippet展示
   3.触发条件分析（执行流、数据流分析）
   4.攻击面的上下文说明（包括依赖组件版本）
   • 添加数据验证建议：
   ① 输入验证缺失点的具体位置
   ② 污点传播路径图示（用graphviz语法描述）
   • 污点分析中检查外部用户是否可控输入,若不可控则降低漏洞等级或不报告
4. 风险等级校准
   • 根据漏洞影响范围和修复成本，评估漏洞等级，critical/high/medium/low
	- critical: 严重漏洞,能够获取服务器权限,命令注入
	- high: 高危漏洞,SQL注入、凭证盗窃检测、硬编码可造成敏感信息泄漏、rug_pull、工具投毒攻击
	- medium: 中危漏洞,身份验证绕过、提示词注入
	- low: 低危漏洞,影响范围小其他漏洞
   • 特殊场景识别：
    1. 涉及身份验证前置条件的降权处理
    2. 暴露在公网的Service自动提级
5. 修复方案优化
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
	}, config.Language, config.CodePath)
	_, err := agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config)
}
