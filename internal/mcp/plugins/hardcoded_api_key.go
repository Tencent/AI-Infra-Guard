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
)

// HardcodedApiKeyPlugin 硬编码API密钥检测插件
type HardcodedApiKeyPlugin struct {
}

// NewHardcodedApiKeyPlugin 创建新的硬编码API密钥检测插件
func NewHardcodedApiKeyPlugin() *HardcodedApiKeyPlugin {
	return &HardcodedApiKeyPlugin{}
}

// 获取插件信息
func (p *HardcodedApiKeyPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "硬编码API密钥检测",
		Desc: "检测MCP代码中可能存在的硬编码API密钥或敏感凭证",
	}
}

// API密钥匹配正则表达式
const apiKeyPattern = `\b(AKIA[A-Za-z0-9]{16}|GOOG[\w\W]{10,30}|AZ[A-Za-z0-9]{34,40}|IBM[A-Za-z0-9]{10,40}|OCID[A-Za-z0-9]{10,40}|LTAI[A-Za-z0-9]{12,20}|AKID[A-Za-z0-9]{13,20}|QCS[\w\W]{10,30}|SLS[\w\W]{10,30}|S3[A-Za-z0-9]{12,20}|AK[A-Za-z0-9]{10,40}|JDC_[A-Z0-9]{28,32}|AKLT[a-zA-Z0-9-_]{0,252}|UC[A-Za-z0-9]{10,40}|QY[A-Za-z0-9]{10,40}|AKLT[a-zA-Z0-9-_]{16,28}|LTC[A-Za-z0-9]{10,60}|YD[A-Za-z0-9]{10,60}|CTC[A-Za-z0-9]{10,60}|YYT[A-Za-z0-9]{10,60}|YY[A-Za-z0-9]{10,40}|CI[A-Za-z0-9]{10,40}|gcore[A-Za-z0-9]{10,30}|ssh-(rsa|ed25519)\s+[A-Za-z0-9+/]{20,}={0,3}|(ghp|gho|ghu|ghs)_[A-Za-z0-9]{36}|-----BEGIN (RSA|OPENSSH) PRIVATE KEY-----(.*?)-----END (RSA|OPENSSH) PRIVATE KEY-----|sk-proj-[A-Za-z0-9]{9}-[A-Za-z0-9]{42}_[A-Za-z0-9]{39}-[A-Za-z0-9]{49}_[A-Za-z0-9]{13}|sk-ant-api\d{2}-[A-Za-z0-9]{17}-[A-Za-z0-9]{15}_[A-Za-z0-9]{13}-[A-Za-z0-9]{38}-[A-Za-z0-9]{8}|sk-[A-Za-z0-9]{32,48})\b`

// 可能包含API密钥的变量名
const apiKeyVarPattern = `\b(api_?key|app_?key|secret|token|password|credential|auth|access_?key|client_?secret)\s*=\s*(['"])(?!\$\{)([^'"]+)(['"])`

// 常见包含密钥的文件匹配模式
const sensitiveFilePattern = `(\.env|config\.(ini|json|yml)|secrets|credentials|\.key|\.pem|\.ppk)`

// 扫描代码中的硬编码API密钥
func scanHardCodeApiKey(code string) (bool, []string) {
	var matches []string

	// 编译API密钥正则表达式
	reApiKey, err := regexp.Compile(apiKeyPattern)
	if err != nil {
		return false, nil
	}

	// 查找API密钥匹配
	apiKeyMatches := reApiKey.FindAllString(code, -1)
	matches = append(matches, apiKeyMatches...)

	// 编译API密钥变量正则表达式
	reApiKeyVar, err := regexp.Compile(apiKeyVarPattern)
	if err != nil {
		return false, nil
	}

	// 查找API密钥变量匹配
	apiKeyVarMatches := reApiKeyVar.FindAllStringSubmatch(code, -1)
	for _, match := range apiKeyVarMatches {
		if len(match) >= 4 {
			matches = append(matches, fmt.Sprintf("%s = %s", match[1], match[3]))
		}
	}

	return len(matches) > 0, matches
}

// 查找匹配的文件
func findFilesForApiKeyCheck(rootPath string) ([]string, error) {
	var files []string

	err := filepath.Walk(rootPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			// 跳过常见的非源代码目录
			baseName := filepath.Base(path)
			if baseName == "node_modules" || baseName == "vendor" || baseName == ".git" ||
				baseName == "build" || baseName == "dist" || baseName == "__pycache__" {
				return filepath.SkipDir
			}
			return nil
		}

		// 检查文件扩展名，只关注源代码和配置文件
		ext := strings.ToLower(filepath.Ext(path))
		baseName := strings.ToLower(filepath.Base(path))

		// 源代码文件
		if ext == ".go" || ext == ".py" || ext == ".js" || ext == ".ts" ||
			ext == ".java" || ext == ".php" || ext == ".rb" || ext == ".sh" ||
			ext == ".c" || ext == ".cpp" || ext == ".h" || ext == ".cs" {
			files = append(files, path)
			return nil
		}

		// 配置文件
		if ext == ".json" || ext == ".yml" || ext == ".yaml" || ext == ".xml" ||
			ext == ".ini" || ext == ".conf" || ext == ".config" || ext == ".toml" {
			files = append(files, path)
			return nil
		}

		// 特殊敏感文件
		reSpecialFile, _ := regexp.Compile(sensitiveFilePattern)
		if reSpecialFile.MatchString(baseName) {
			files = append(files, path)
			return nil
		}

		return nil
	})

	return files, err
}

// 执行检测
func (p *HardcodedApiKeyPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue

	// 查找所有需要检查的文件
	files, err := findFilesForApiKeyCheck(config.CodePath)
	if err != nil {
		gologger.WithError(err).Errorln("查找文件失败")
		return issues, err
	}

	// 检查每个文件中是否存在硬编码API密钥
	for _, file := range files {
		content, err := ioutil.ReadFile(file)
		if err != nil {
			gologger.WithError(err).Warningln("读取文件失败: " + file)
			continue
		}

		// 扫描文件内容
		found, matches := scanHardCodeApiKey(string(content))
		if found && len(matches) > 0 {
			// 构建问题描述，最多显示3个匹配项
			displayMatches := matches
			if len(matches) > 3 {
				displayMatches = matches[:3]
			}

			matchStr := strings.Join(displayMatches, "\n")
			if len(matches) > 3 {
				matchStr += fmt.Sprintf("\n... 以及 %d 个其他匹配项", len(matches)-3)
			}

			// 相对路径，便于显示
			relPath, err := filepath.Rel(config.CodePath, file)
			if err != nil {
				relPath = file
			}

			issue := Issue{
				Title:       "硬编码API密钥风险",
				Description: fmt.Sprintf("在文件 %s 中发现可能的硬编码API密钥或敏感凭证:\n\n```\n%s\n```", relPath, matchStr),
				Level:       LevelHigh,
				Suggestion:  "避免在代码中硬编码API密钥或敏感凭证。建议使用环境变量、密钥管理服务或安全的配置管理工具来存储和访问敏感凭证。",
			}
			issues = append(issues, issue)
		}
	}

	return issues, nil
}
