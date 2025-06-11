package plugins

import (
	"context"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// CredentialTheftPlugin 凭证盗窃检测插件
type CredentialTheftPlugin struct {
}

// NewCredentialTheftPlugin 创建新的凭证盗窃检测插件
func NewCredentialTheftPlugin() *CredentialTheftPlugin {
	return &CredentialTheftPlugin{}
}

// 获取插件信息
func (p *CredentialTheftPlugin) GetPlugin() Plugin {
	return Plugin{
		Name:   "凭证盗窃检测",
		Desc:   "检测MCP代码中可能存在的凭证盗窃风险",
		ID:     "credential_theft",
		NameEn: "credential theft",
		DescEn: "detect credential theft risk in MCP code",
	}
}

// 正则表达式模式
const (
	// 敏感文件类型
	sensitiveFilesPattern = `(\.env|config\.(ini|json|yml)|\b(secrets|credentials|password|token|\.bashrc|\.profile)\b)`
	// 系统敏感文件
	systemFilesPattern = `(\/etc\/passwd|\/etc\/shadow|\/etc\/httpd\/|\/etc\/.*\.conf(\&|\b)|\/usr\/local\/|\/var\/lib\/|~\/\.ssh)`
	// 凭证关键词
	credentialKeywordsPattern = `\b(id_rsa|\.cursor\/mcp\.json|\.cursor\/|\bmcp\.json|api[ -_]?key|access[ -_]?key|auth[ -_]?token)\b`
)

// 扫描描述中是否存在敏感文件访问指令
func scanAccessSensitiveFiles(description string) bool {
	// 合并所有模式
	pattern := sensitiveFilesPattern + "|" + systemFilesPattern + "|" + credentialKeywordsPattern

	// 编译正则表达式
	re, err := regexp.Compile(pattern)
	if err != nil {
		return false
	}

	// 匹配描述文本
	matches := re.FindStringSubmatch(description)
	return len(matches) > 0
}

// 查找匹配的文件
func findFiles(rootPath string, pattern string) ([]string, error) {
	var files []string

	err := filepath.Walk(rootPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			return nil
		}

		matched, err := filepath.Match(pattern, filepath.Base(path))
		if err != nil {
			return err
		}

		if matched {
			files = append(files, path)
		}

		return nil
	})

	return files, err
}

// 读取文件内容
func readFile(path string) (string, error) {
	content, err := ioutil.ReadFile(path)
	if err != nil {
		return "", err
	}

	return string(content), nil
}

// AI提示词模板
const credentialTheftAIPrompt = `
作为专业的网络安全分析专家，你需要精确检测MCP代码中的凭证窃取风险。此检测要求零误报，只有发现确凿的恶意凭证获取行为才能报告。

## 漏洞定义
凭证窃取是指MCP工具通过恶意手段获取、传输或泄露用户的敏感凭证信息，包括API密钥、密码、令牌等。

## 检测标准（必须同时满足以下条件）

### 1. 敏感凭证访问
**必须识别到以下所有要素：**
- **数据源（Source）**：明确的敏感文件或环境变量访问
  - ~/.ssh/、~/.cursor/mcp.json、.env文件
  - 包含API_KEY、TOKEN、PASSWORD、SECRET的环境变量
  - 系统凭证存储：/etc/passwd、credential stores
- **获取方式**：具体的读取或访问代码
- **恶意意图**：非正常业务需要的凭证访问

### 2. 凭证传输或泄露
**必须存在以下行为之一：**
- 通过网络接口传输凭证到外部服务器
- 将凭证写入不安全的存储位置
- 在日志或错误信息中暴露凭证
- 通过API返回值泄露敏感信息

### 3. 攻击可行性验证
**必须确认：**
- 攻击代码在当前环境可执行
- 存在明确的数据流从凭证获取到泄露
- 能够绕过现有的安全防护措施
- 具备实际的危害能力

## 技术检测模式

### 文件系统访问模式
**高风险模式：**
- open("~/.ssh/id_rsa", "r")
- os.environ.get("API_KEY")
- read_file("~/.cursor/mcp.json")
- 访问系统敏感目录：/etc/、/root/

### 网络传输模式
**恶意传输模式：**
- requests.post(external_url, data=credentials)
- socket.send(api_key_data)
- 向未授权域名发送凭证

### 环境变量枚举
**批量获取模式：**
- os.environ遍历
- 搜索包含key、secret、token的变量
- 批量导出环境变量

## 排除条件（以下情况不报告）

### 正常业务场景
- 应用自身配置文件的正常读取
- 使用官方SDK的标准认证流程
- 合理的配置管理和密钥轮换
- 本地开发环境的调试代码

### 安全实践
- 使用密钥管理服务（如HashiCorp Vault）
- 通过HTTPS/TLS加密传输
- 符合OAuth2.0标准的认证流程
- 实施了适当的访问控制

### 测试和示例代码
- 单元测试中的mock凭证
- 文档示例中的占位符
- 开发环境的测试配置
- 明显的dummy或example数据

## 验证要求
1. **完整攻击链**：从凭证获取到泄露的完整路径
2. **实际危害**：能够证明真实的安全风险
3. **恶意意图**：明确的攻击目的而非正常功能
4. **环境适用性**：在目标环境确实可执行

## 特殊判断规则
- **测试凭证识别**：如果发现"test"、"demo"、"example"、"dummy"关键字，降低风险等级
- **开发环境判断**：本地开发配置不视为高风险
- **加密传输验证**：使用HTTPS且有适当验证的不报告
- **官方API调用**：使用官方SDK的标准流程不报告

## 输入数据
源代码路径: %s
目录结构:
-------
%s
-------
初步检测结果:
%s

## 输出要求
仅在发现确凿的凭证窃取攻击时输出：
- 具体文件路径和行号范围
- 完整的攻击代码片段
- 数据流分析：从source到sink的完整路径
- 技术分析：攻击原理和执行机制
- 危害评估：可能泄露的凭证类型和影响范围
- 证据链：完整的恶意行为证据

**关键要求：必须提供完整的攻击证据链和数据流分析，仅在确认存在真实威胁时输出结果。**
`

// 执行检测
func (p *CredentialTheftPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	// 使用列出目录内容并查找工具描述
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
	if err != nil {
		config.Logger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return nil, err
	}

	// 查找所有可能包含工具描述的文件
	files, err := findFiles(config.CodePath, "*.go")
	if err != nil {
		config.Logger.WithError(err).Errorln("查找文件失败")
		return nil, err
	}

	// 检查每个文件中的工具描述
	maybePrompt := ""
	for _, file := range files {
		content, err := readFile(file)
		if err != nil {
			config.Logger.WithError(err).Warningln("读取文件失败: " + file)
			continue
		}

		// 查找文件中所有的文档字符串或注释
		// 这里简化处理，实际应根据语言特性进行更精确的提取
		docStrings := extractDocStrings(content)
		for _, doc := range docStrings {
			if scanAccessSensitiveFiles(doc) {
				maybePrompt += fmt.Sprintf("在文件 %s 中发现可能的凭证盗窃风险。工具描述中包含读取敏感文件或环境变量的指令，可能导致API密钥、密码或其他凭证泄露。\n\n```\n%s\n```", file, doc)
			}
		}
	}

	// 使用AI进行深度检测
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(credentialTheftAIPrompt, config.CodePath, dirPrompt, maybePrompt),
	}, config.Language, config.CodePath)
	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return nil, err
	}
	return SummaryResult(ctx, agent, config)
}

// 从文件内容中提取可能的文档字符串或注释
func extractDocStrings(content string) []string {
	var docStrings []string

	// 匹配多行字符串，可能包含文档
	reMultilineString := regexp.MustCompile("(`[^`]*`)")
	multilineMatches := reMultilineString.FindAllString(content, -1)
	docStrings = append(docStrings, multilineMatches...)

	// 匹配注释行
	reComment := regexp.MustCompile("(?m)^\\s*//.*$")
	commentMatches := reComment.FindAllString(content, -1)

	// 将连续的注释行合并
	var currentComment string
	for _, comment := range commentMatches {
		comment = strings.TrimSpace(comment)
		comment = strings.TrimPrefix(comment, "//")
		comment = strings.TrimSpace(comment)

		if currentComment == "" {
			currentComment = comment
		} else {
			currentComment += " " + comment
		}
	}

	if currentComment != "" {
		docStrings = append(docStrings, currentComment)
	}

	return docStrings
}
