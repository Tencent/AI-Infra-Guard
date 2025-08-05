// Package parser 实现了指纹规则的解析和评估功能。
// 该包提供了将YAML格式的指纹规则转换为可执行规则对象的功能，
// 并支持对HTTP请求响应进行指纹匹配评估。
package parser

import (
	"gopkg.in/yaml.v2"
)

// FingerPrintInfo 定义了指纹的基本信息
type FingerPrintInfo struct {
	Name     string            `yaml:"name" json:"name"`
	Author   string            `yaml:"author" json:"author"`
	Example  []string          `yaml:"example,omitempty" json:"example,omitempty"`
	Desc     string            `yaml:"desc,omitempty" json:"desc,omitempty"`
	Severity string            `yaml:"severity" json:"severity"`
	Metadata map[string]string `yaml:"metadata" json:"metadata"`
}

// Extractor 定义了从响应中提取信息的规则
type Extractor struct {
	Part  string `yaml:"part" json:"part"`
	Group string `yaml:"group" json:"group"`
	Regex string `yaml:"regex" json:"regex"`
}

// HttpRule 定义了HTTP请求匹配规则
type HttpRule struct {
	Method    string    `yaml:"method" json:"method"`
	Path      string    `yaml:"path" json:"path"`
	Matchers  []string  `yaml:"matchers" json:"matchers"`
	Data      string    `yaml:"data,omitempty" json:"data,omitempty"`
	dsl       []*Rule   `yaml:"-"`
	Extractor Extractor `yaml:"extractor,omitempty" json:"extractor,omitempty"`
}

// FuzzVersion 定义模糊版本检测规则
type FuzzVersion struct {
	Path         string `yaml:"path" json:"path"`
	Pattern      string `yaml:"pattern,omitempty" json:"pattern,omitempty"`
	Hash         string `yaml:"hash,omitempty" json:"hash,omitempty"`
	VersionRange string `yaml:"version_range" json:"version_range"`
}

// GetDsl 返回解析后的DSL规则列表
func (h *HttpRule) GetDsl() []*Rule {
	return h.dsl
}

// FingerPrint 定义了完整的指纹规则结构
type FingerPrint struct {
	Info        FingerPrintInfo `yaml:"info" json:"info"`
	Http        []HttpRule      `yaml:"http" json:"http"`
	Version     []HttpRule      `yaml:"version,omitempty" json:"version"`
	FuzzVersion []FuzzVersion   `yaml:"fuzzversion,omitempty" json:"fuzzversion"`
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
