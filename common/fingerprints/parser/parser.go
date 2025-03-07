// Package parser 实现了指纹规则的解析和评估功能。
// 该包提供了将YAML格式的指纹规则转换为可执行规则对象的功能，
// 并支持对HTTP请求响应进行指纹匹配评估。
package parser

import (
	"gopkg.in/yaml.v2"
)

// FingerPrintInfo 定义了指纹的基本信息
type FingerPrintInfo struct {
	Name     string            `yaml:"name"`
	Author   string            `yaml:"author"`
	Example  []string          `yaml:"example,omitempty"`
	Desc     string            `yaml:"desc,omitempty"`
	Severity string            `yaml:"severity"`
	Metadata map[string]string `yaml:"metadata"`
}

// Extractor 定义了从响应中提取信息的规则
type Extractor struct {
	Part  string `yaml:"part"`
	Group string `yaml:"group"`
	Regex string `yaml:"regex"`
}

// HttpRule 定义了HTTP请求匹配规则
type HttpRule struct {
	Method    string    `yaml:"method"`
	Path      string    `yaml:"path"`
	Matchers  []string  `yaml:"matchers"`
	Data      string    `yaml:"data,omitempty"`
	dsl       []*Rule   `yaml:"-"`
	Extractor Extractor `yaml:"extractor,omitempty"`
	Auth      bool      `yaml:"auth,omitempty"`
	Subpart   Subpart   `yaml:"subpart,omitempty"`
}

// GetDsl 返回解析后的DSL规则列表
func (h *HttpRule) GetDsl() []*Rule {
	return h.dsl
}

// FingerPrint 定义了完整的指纹规则结构
type FingerPrint struct {
	Info    FingerPrintInfo `yaml:"info"`
	Http    []HttpRule      `yaml:"http"`
	Version []HttpRule      `yaml:"version,omitempty"`
}

// FingerPrints 表示多个指纹规则的集合
type FingerPrints []FingerPrint

// Config 定义了进行指纹匹配时需要的配置信息
type Config struct {
	Body   string
	Header string
	Icon   int32
}

// AdvisoryConfig 提供漏洞配置信息
type AdvisoryConfig struct {
	Version    string
	IsInternal bool
}

// transfromRule 将规则字符串转换为规则对象
// 参数:
//   - rule: 规则字符串
//
// 返回:
//   - *Rule: 解析后的规则对象
//   - error: 解析过程中的错误
func transfromRule(rule string) (*Rule, error) {
	tokens, err := ParseTokens(rule)
	if err != nil {
		return nil, err
	}
	if err = CheckBalance(tokens); err != nil {
		return nil, err
	}
	return TransFormExp(tokens)
}

// InitFingerPrintFromData 从字节数据初始化指纹配置
// 参数:
//   - reader: 包含YAML格式指纹配置的字节数据
//
// 返回:
//   - *FingerPrint: 解析后的指纹对象
//   - error: 解析过程中的错误
func InitFingerPrintFromData(reader []byte) (*FingerPrint, error) {
	var fp FingerPrint
	err := yaml.Unmarshal(reader, &fp)
	if err != nil {
		return nil, err
	}
	for i, rule := range fp.Http {
		dsls := make([]*Rule, 0)
		for _, matcher := range rule.Matchers {
			dsl, err := transfromRule(matcher)
			if err != nil {
				return nil, err
			}
			dsls = append(dsls, dsl)
		}
		fp.Http[i].dsl = dsls
	}
	return &fp, err
}

// FpResult 指纹结构体
type FpResult struct {
	Name    string `json:"name"`
	Version string `json:"version,omitempty"`
}

// Eval 评估配置是否匹配规则
// 参数:
//   - config: 配置对象，包含请求体、请求头和图标信息
//   - dsl: 要评估的规则对象
//
// 返回:
//   - bool: 是否匹配规则
func Eval(config *Config, dsl *Rule) bool {
	return dsl.Eval(config)
}

// Subpart 定义了子匹配规则
type Subpart struct {
	Regex  string `yaml:"regex"`
	Method string `yaml:"method"`
}
