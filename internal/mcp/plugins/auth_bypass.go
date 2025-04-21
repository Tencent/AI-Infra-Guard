package plugins

import (
	"regexp"
	"strconv"
	"strings"
)

// 身份验证绕过插件
type AuthBypassPlugin struct {
	rules []authBypassRule
}

// 身份验证绕过检测规则
type authBypassRule struct {
	Name        string
	Pattern     *regexp.Regexp
	Level       Level
	Description string
	Suggestion  string
}

// 创建新的身份验证绕过插件
func NewAuthBypassPlugin() *AuthBypassPlugin {
	return &AuthBypassPlugin{
		rules: []authBypassRule{
			{
				Name:        "弱密码检测",
				Pattern:     regexp.MustCompile(`(?i)password\s*=\s*['"]?(admin|password|123456|qwerty|default)['"]?`),
				Level:       LevelHigh,
				Description: "发现硬编码的弱密码，可能被攻击者利用",
				Suggestion:  "使用强密码政策并避免在代码中硬编码密码",
			},
			{
				Name:        "未加密令牌传输",
				Pattern:     regexp.MustCompile(`(?i)(token|auth_token|access_token|session_id)\s*=\s*['"][^'"]{5,}['"]`),
				Level:       LevelHigh,
				Description: "发现明文传输的认证令牌",
				Suggestion:  "使用HTTPS或其他加密方式传输认证信息",
			},
			{
				Name:        "不安全的OAuth实现",
				Pattern:     regexp.MustCompile(`(?i)(oauth|oauth2).*?(redirect_uri|client_secret)\s*=\s*['"][^'"]+['"]`),
				Level:       LevelMedium,
				Description: "OAuth实现可能存在缺陷",
				Suggestion:  "确保OAuth流程安全，避免硬编码client_secret",
			},
			{
				Name:        "缺少身份验证检查",
				Pattern:     regexp.MustCompile(`(?i)function\s+handle.*?\{\s*[^{]*?response\s*\(`),
				Level:       LevelCritical,
				Description: "处理函数可能缺少身份验证检查",
				Suggestion:  "在处理请求前增加身份验证检查",
			},
			{
				Name:        "硬编码JWT密钥",
				Pattern:     regexp.MustCompile(`(?i)(secret|key|jwt).*?['"][a-zA-Z0-9+/=]{16,}['"]`),
				Level:       LevelCritical,
				Description: "发现硬编码的JWT密钥",
				Suggestion:  "从环境变量或安全存储中获取JWT密钥",
			},
		},
	}
}

// 获取插件信息
func (p *AuthBypassPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "身份验证绕过检测",
		Desc: "检测MCP代码中可能存在的身份验证绕过漏洞",
	}
}

// 执行检测
func (p *AuthBypassPlugin) Check(inputs []McpInput) ([]Issue, error) {
	var issues []Issue

	// 对每个输入进行检测
	for _, input := range inputs {
		// 只处理代码类型的输入
		if input.Type == MCPTypeCode {
			issues = append(issues, p.checkCode(input)...)
		}
	}
	return issues, nil
}

// 检测代码中的身份验证绕过问题
func (p *AuthBypassPlugin) checkCode(input McpInput) []Issue {
	var issues []Issue

	for _, rule := range p.rules {
		matches := rule.Pattern.FindAllStringIndex(input.Input, -1)
		for _, match := range matches {
			startPos := match[0]
			endPos := match[1]

			// 获取匹配上下文
			start := startPos - 20
			if start < 0 {
				start = 0
			}
			end := endPos + 20
			if end > len(input.Input) {
				end = len(input.Input)
			}

			location := ""
			if strings.Count(input.Input[:startPos], "\n") > 0 {
				line := strings.Count(input.Input[:startPos], "\n") + 1
				location = "第" + strconv.Itoa(line) + "行"
			} else {
				location = "字符位置: " + strconv.Itoa(startPos) + "-" + strconv.Itoa(endPos)
			}

			issue := Issue{
				Title:       rule.Name,
				Description: rule.Description,
				Level:       rule.Level,
				Suggestion:  rule.Suggestion,
				Input:       location,
				Type:        input.Type,
			}

			issues = append(issues, issue)
		}
	}

	return issues
}
