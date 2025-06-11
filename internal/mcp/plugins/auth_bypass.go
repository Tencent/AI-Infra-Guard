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
作为专业的网络安全分析专家，你需要精确检测MCP代码中的身份验证绕过漏洞。此检测要求极高准确性，只有发现确凿的认证绕过风险才能报告。

## 漏洞定义
身份验证绕过是指攻击者能够在不提供有效凭证的情况下，绕过系统的认证机制获得未授权访问。

## 检测标准（必须至少满足一项确凿证据）

### 1. 硬编码凭证漏洞
**必要条件：**
- 发现明文存储的真实凭证（非测试/示例数据）
- 凭证具有实际的系统访问权限
- 能够通过代码直接获取有效的认证信息
- 存在绕过正常认证流程的后门

**代码模式：**
- 硬编码的API密钥、密码、令牌
- 万能密码或后门账户
- 绕过认证的特殊参数或标志位

### 2. JWT安全缺陷
**必要条件：**
- JWT签名验证缺失或可绕过
- 使用弱签名算法（如none、HS256弱密钥）
- JWT密钥泄露或可预测
- 存在JWT重放攻击漏洞

**检测要点：**
- verify=False或跳过签名验证
- 使用固定或弱JWT密钥
- 缺少时间戳验证（exp、iat）
- 允许algorithm=none的JWT

### 3. OAuth认证缺陷
**必要条件：**
- redirect_uri验证缺失或不严格
- state参数缺失导致CSRF攻击
- client_secret泄露或硬编码
- 授权码重用或无时效限制

### 4. 会话管理漏洞
**必要条件：**
- 会话固定攻击（session fixation）
- 会话劫持风险（缺少secure/httponly标志）
- 会话超时机制缺失
- 跨站请求伪造（CSRF）防护缺失

### 5. 认证逻辑绕过
**必要条件：**
- 认证检查逻辑存在条件绕过
- 权限判断存在逻辑错误
- 多步认证流程可跳步骤
- 认证中间件缺失或配置错误

## 技术检测方法

### 代码模式识别
**高风险模式：**
- if user == "admin" and password == "hardcoded_password"
- jwt.decode(token, verify=False)
- session['authenticated'] = True  # 无验证设置
- @app.route('/admin')  # 缺少认证装饰器

### 配置文件分析
- 检查认证相关配置的安全性
- 验证默认凭证是否被修改
- 分析访问控制列表的完整性

### API端点安全性
- 识别缺少认证保护的敏感接口
- 检查认证中间件的正确应用
- 验证权限控制的粒度和完整性

## 排除条件（以下不报告）

### 正常开发场景
- 测试代码中的mock认证
- 开发环境的临时凭证
- 单元测试的固定测试数据
- 示例代码中的占位符凭证

### 安全实践
- 正确实施的OAuth2.0流程
- 安全的JWT实现（强签名、完整验证）
- 完善的会话管理机制
- 适当的RBAC权限控制

### 配置管理
- 通过环境变量管理的凭证
- 使用密钥管理服务的实现
- 正确的配置文件权限设置

## 验证要求
1. **漏洞可利用性**：必须能构造实际的攻击路径
2. **影响评估**：明确绕过认证后的访问权限
3. **技术细节**：提供具体的漏洞原理分析
4. **修复建议**：给出明确的安全加固方案

## 严格判断标准
- **默认配置**：如果是框架的默认配置且有说明文档，不报告
- **测试标识**：包含test、demo、example、mock关键字的不报告  
- **开发环境**：明确用于开发调试的配置不报告
- **正确实现**：符合安全最佳实践的认证实现不报告
- **无权限验证判断项目等级**: 若存在无权限验证,判断项目信息收集信息是否为重要项目，即能够操作本地主机或操作数据库等比较重要的功能。若项目不重要则不报告

## 输入数据
源代码路径: %s
目录结构:
------
%s
------

## 输出要求
仅在发现确凿的身份验证绕过漏洞时输出：
- 具体文件路径和行号
- 完整的漏洞代码片段
- 技术分析：漏洞原理和利用方式
- 影响评估：绕过认证后可获得的权限
- 攻击路径：具体的利用步骤
- 修复建议：详细的安全加固方案

**严格要求：必须提供完整的漏洞利用路径和影响分析，无确凿证据时保持静默。**
`

// Check 执行检测
func (p *AuthBypassPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
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
