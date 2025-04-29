package plugins

import (
	"context"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
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
		gologger.WithError(err).Errorln("编译正则表达式失败")
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
你是一个专业的网络安全分析助手，需要严格分析给定的源代码目录结构，检测可能存在的敏感凭证泄露。你的分析必须基于专业知识和确凿证据，**绝对禁止任何猜测性或不确定的输出**。
MCP区分SSE与STDIO的区别，STDIO是标准输入输出，SSE是流式输入输出。如果项目只支持STDIO，会由于利用门槛较高，将漏洞标记为低风险。

## 输入数据
源代码文件夹路径:%s
目录详情:
-------
%s
-------
可能存在的问题:
%s
## 检测目标
识别MCP代码中可能导致敏感凭证泄露的代码模式，包括但不限于：
- 敏感环境变量暴露,可以通过接口暴露环境变量
- 可能导致API密钥、SSH密钥、身份验证令牌、AK/SK或其他敏感凭证泄露

特别关注以下内容：
1. 是否引导读取敏感文件，如 ~/.cursor/mcp.json、.env、config 文件等
2. 是否引导读取环境变量，尤其是包含 API_KEY、TOKEN、PASSWORD 等敏感信息的变量
3. 是否要求将读取到的凭证信息返回或发送至其他位置

## 输出规则
仅当同时满足以下条件时输出：
1. 三级检测标准均触发,路径路径，证据链
2. 可构建完整攻击链
3. 硬编码凭证你应该识别是否是测试配置，如果是测试配置则不报告

## 输出内容
漏洞描述给出证据:文件位置、代码片段、技术分析(专业术语说明漏洞原理及潜在影响)
`

// 执行检测
func (p *CredentialTheftPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	// 使用列出目录内容并查找工具描述
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return nil, err
	}

	// 查找所有可能包含工具描述的文件
	files, err := findFiles(config.CodePath, "*.go")
	if err != nil {
		gologger.WithError(err).Errorln("查找文件失败")
		return nil, err
	}

	// 检查每个文件中的工具描述
	maybePrompt := ""
	for _, file := range files {
		content, err := readFile(file)
		if err != nil {
			gologger.WithError(err).Warningln("读取文件失败: " + file)
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
	}, config.Language)
	_, err = agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
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
