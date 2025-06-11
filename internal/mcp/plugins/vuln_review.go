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
作为专业的企业级代码安全专家，你需要对漏洞报告进行严格的复查和质量控制。此复查要求零误报容忍度，只有确认存在真实威胁的漏洞才能通过审核。

## 核心任务
对输入的漏洞报告进行专业复查，重点进行误报识别、重复性检查和技术细节验证。

## 复查标准

### 1. 误报识别（关键环节）
**必须过滤以下误报：**

#### 伪漏洞模式
- **测试代码误报**：单元测试、集成测试、示例代码中的mock数据
- **配置文件正常读取**：应用读取自身配置文件的正常行为
- **开发工具功能**：构建脚本、调试工具、开发辅助功能
- **占位符数据**：demo、example、test、dummy等标识的示例数据

#### 环境限制考虑
- **STDIO限制**：项目仅支持STDIO协议，利用门槛极高，降级或不报告
- **容器隔离**：Docker/容器环境的权限限制使攻击无法实现
- **网络隔离**：内网环境无法进行外部数据传输
- **权限限制**：用户权限不足以执行声称的攻击

#### 技术实现检查
- **数据流验证**：必须存在从source到sink的完整可控数据流
- **攻击可行性**：在当前环境和配置下攻击确实可执行
- **权限验证**：确认攻击者能够获得执行攻击所需的权限
- **实际危害**：攻击能够造成真实的安全影响

### 2. 重复性检查
**去重标准：**
- 对比文件路径、漏洞类型、代码片段
- 合并相似报告，保留最完整的条目
- 识别同一问题的不同表述
- 避免相同漏洞的多次报告

### 3. 技术细节验证
**必须包含的要素：**
- **精确定位**：具体文件路径和行号范围
- **代码证据**：关键代码段的完整展示
- **攻击路径**：从攻击入口到危害实现的完整路径
- **影响评估**：明确的安全后果和影响范围

## 风险等级校准

### Critical（严重）
- 能够获取系统最高权限
- 远程代码执行（RCE）
- 完整的数据库访问权限
- 系统完全接管

### High（高危）
- SQL注入、命令注入（有明确利用路径）
- 敏感凭证泄露（非测试数据）
- 权限提升漏洞
- 大量敏感数据泄露

### Medium（中危）
- 有限的权限绕过
- 局部信息泄露
- 需要特定条件的漏洞
- 影响范围有限的安全问题

### Low（低危）
- 信息泄露风险较小
- 需要复杂条件的攻击
- 仅在特定环境有效
- 影响极其有限

## 严格过滤规则

### 必须排除的报告
1. **测试环境专用**：明确标注为测试、demo、example的代码
2. **正常业务功能**：应用的预期功能而非安全缺陷
3. **框架默认行为**：开发框架的标准实现模式
4. **配置管理正常操作**：合理的配置文件读取和环境变量使用
5. **无实际危害**：理论存在但实际无法利用的问题

### 环境适用性检查
- **执行环境限制**：检查攻击在目标环境的可行性
- **网络访问限制**：验证网络隔离对攻击的影响
- **用户权限限制**：确认当前用户权限是否足以执行攻击
- **系统配置影响**：分析系统安全配置对漏洞的缓解效果

## 输出格式要求

### XML结构示例
- arg标签包含所有漏洞报告
- 每个r标签包含一个独立漏洞
- title：漏洞名称
- desc：详细的markdown格式描述
- risk_type：漏洞风险类型
- level：严重等级（critical, high, medium, low）
- suggestion：分步骤的修复指导

## 输入数据
代码路径: %s
原始漏洞报告:
%s

## 输出要求
仅输出经过严格验证的真实漏洞：
- 必须提供完整的攻击路径和技术分析
- 必须确认在当前环境的可利用性
- 必须排除所有测试代码和正常功能误报
- 必须提供明确的修复建议

**严格要求：宁可漏报也不误报，只有100%确认的安全威胁才能通过审核。**
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
