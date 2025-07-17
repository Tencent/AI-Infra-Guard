// Package vulstruct 漏洞扫描
package vulstruct

import (
	"fmt"
	"os"
	"strings"
	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"gopkg.in/yaml.v3"
	"strings"
)

// Info represents vulnerability information structure
// 存储漏洞信息的结构体
type Info struct {
	FingerPrintName string   `yaml:"name" json:"name"`                                 // Name of the fingerprint
	CVEName         string   `yaml:"cve" json:"cve"`                                   // CVE identifier
	Summary         string   `yaml:"summary" json:"summary"`                           // Brief summary of the vulnerability
	Details         string   `yaml:"details" json:"details"`                           // Detailed description
	CVSS            string   `yaml:"cvss" json:"cvss"`                                 // CVSS score
	Severity        string   `yaml:"severity" json:"severity"`                         // Severity level
	SecurityAdvise  string   `yaml:"security_advise,omitempty" json:"security_advise"` // Security advisory
	References      []string `yaml:"references" json:"references"`
}

// VersionVul represents a version-based vulnerability
// 版本相关的漏洞结构体
type VersionVul struct {
	Info        Info         `yaml:"info" json:"info"`             // Basic vulnerability information
	Rule        string       `yaml:"rule" json:"rule"`             // Rule expression in string format
	RuleCompile *parser.Rule `yaml:"-" json:"-"`                   // Compiled rule for evaluation
	References  []string     `yaml:"references" json:"references"` // Reference links
}

// UnmarshalYAML implements the yaml.Unmarshaler interface
func (v *VersionVul) UnmarshalYAML(unmarshal func(interface{}) error) error {
	// 定义临时结构体，Rule字段为指针类型
	type tmpStruct struct {
		Info       Info     `yaml:"info"`
		Rule       *string  `yaml:"rule"`
		References []string `yaml:"references"`
	}

	var tmp tmpStruct
	if err := unmarshal(&tmp); err != nil {
		return err
	}

	// 检查Rule字段是否存在
	if tmp.Rule == nil {
		return fmt.Errorf("missing required field 'rule'")
	}

	// 将临时结构体的值赋给原结构体
	v.Info = tmp.Info
	v.Rule = *tmp.Rule // 即使为空字符串也允许
	v.References = tmp.References

	return nil
}

// ReadVersionVul reads and parses a single vulnerability file
// 读取并解析单个漏洞文件
func ReadVersionVul(body []byte) (*VersionVul, error) {
	// Unmarshal YAML content into VersionVul struct
	// 将YAML内容解析到VersionVul结构体中
	var advisory VersionVul
	err := yaml.Unmarshal(body, &advisory)
	if err != nil {
		return nil, err
	}
	advisory.Info.Details = strings.TrimSpace(advisory.Info.Details)
	advisory.Info.References = advisory.References

	if advisory.Rule == "" {
		advisory.RuleCompile = nil
		return &advisory, nil
	}

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
