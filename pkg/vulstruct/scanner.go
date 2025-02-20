// Package vulstruct 漏洞扫描
package vulstruct

import (
	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"os"
	"strings"

	"gopkg.in/yaml.v3"
)

// Info represents vulnerability information structure
// 存储漏洞信息的结构体
type Info struct {
	FingerPrintName string `yaml:"name" json:"-"`                                    // Name of the fingerprint
	CVEName         string `yaml:"cve" json:"cve"`                                   // CVE identifier
	Summary         string `yaml:"summary" json:"summary"`                           // Brief summary of the vulnerability
	Details         string `yaml:"details" json:"details"`                           // Detailed description
	CVSS            string `yaml:"cvss" json:"cvss"`                                 // CVSS score
	Severity        string `yaml:"severity" json:"severity"`                         // Severity level
	SecurityAdvise  string `yaml:"security_advise,omitempty" json:"security_advise"` // Security advisory
}

// VersionVul represents a version-based vulnerability
// 版本相关的漏洞结构体
type VersionVul struct {
	Info        Info         `yaml:"info" json:"info"`             // Basic vulnerability information
	Rule        string       `yaml:"rule" json:"-"`                // Rule expression in string format
	RuleCompile *parser.Rule `yaml:"-" json:"-"`                   // Compiled rule for evaluation
	References  []string     `yaml:"references" json:"references"` // Reference links
}

// ReadVersionVulSingFile reads and parses a single vulnerability file
// 读取并解析单个漏洞文件
func ReadVersionVulSingFile(filename string) (*VersionVul, error) {
	// Read file content
	// 读取文件内容
	body, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}

	// Unmarshal YAML content into VersionVul struct
	// 将YAML内容解析到VersionVul结构体中
	var advisory VersionVul
	err = yaml.Unmarshal(body, &advisory)
	if err != nil {
		return nil, err
	}
	advisory.Info.Details = strings.TrimSpace(advisory.Info.Details)

	// Parse rule string into tokens
	// 将规则字符串解析为词法单元
	tokens, err := parser.ParseAdvisorTokens(advisory.Rule)
	if err != nil {
		return nil, err
	}

	// Verify token balance
	// 验证词法单元的平衡性
	err = parser.CheckBalance(tokens)
	if err != nil {
		return nil, err
	}

	// Transform tokens into DSL rule
	// 将词法单元转换为DSL规则
	dsl, err := parser.TransFormExp(tokens)
	if err != nil {
		return nil, err
	}

	advisory.RuleCompile = dsl
	return &advisory, nil
}
