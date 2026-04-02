// Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Requirement: Any integration or derivative work must explicitly attribute
// Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
// documentation or user interface, as detailed in the NOTICE file.

// Package vulstruct 漏洞扫描结构测试
package vulstruct

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestReadVersionVul_Scanner_ValidYAML 测试合法 YAML 正常解析并填充各字段
func TestReadVersionVul_Scanner_ValidYAML(t *testing.T) {
	yaml := []byte(`
info:
  name: "ScannerTest"
  cve: "CVE-2024-9999"
  summary: "测试漏洞摘要"
  details: "  漏洞详细描述  "
  cvss: "7.5"
  severity: "high"
rule: 'version >= "1.0.0" && version < "2.0.0"'
references:
  - "https://example.com/advisory"
`)
	vul, err := ReadVersionVul(yaml)
	require.NoError(t, err, "合法 YAML 应解析成功")
	require.NotNil(t, vul, "解析结果不应为 nil")

	// 验证基础字段
	assert.Equal(t, "ScannerTest", vul.Info.FingerPrintName, "name 字段应正确解析")
	assert.Equal(t, "CVE-2024-9999", vul.Info.CVEName, "cve 字段应正确解析")
	assert.Equal(t, "high", vul.Info.Severity, "severity 字段应正确解析")

	// details 中的前后空格应被 TrimSpace 去除
	assert.Equal(t, "漏洞详细描述", vul.Info.Details, "details 应被 TrimSpace 处理")

	// rule 字段非空时 RuleCompile 应被编译
	assert.NotEmpty(t, vul.Rule, "rule 字段应非空")
	assert.NotNil(t, vul.RuleCompile, "合法的非空 rule 应被编译为 RuleCompile")
}

// TestReadVersionVul_Scanner_MissingRule 测试缺少 rule 字段时返回错误
func TestReadVersionVul_Scanner_MissingRule(t *testing.T) {
	yaml := []byte(`
info:
  name: "MissingRuleTest"
  cve: "CVE-2024-0003"
  summary: "缺少 rule 字段"
  details: ""
  cvss: "4.0"
  severity: "low"
`)
	_, err := ReadVersionVul(yaml)
	// 缺少 rule 字段应返回错误
	assert.Error(t, err, "缺少 rule 字段时应返回错误")
	assert.Contains(t, err.Error(), "rule", "错误信息应提及 rule 字段")
}

// TestReadVersionVul_Scanner_EmptyRule 测试 rule 字段为空字符串时 RuleCompile 为 nil
func TestReadVersionVul_Scanner_EmptyRule(t *testing.T) {
	yaml := []byte(`
info:
  name: "EmptyRuleTest"
  cve: "CVE-2024-0002"
  summary: "空规则测试"
  details: ""
  cvss: "5.0"
  severity: "medium"
rule: ''
`)
	vul, err := ReadVersionVul(yaml)
	require.NoError(t, err, "空 rule 字段应解析成功，不报错")
	require.NotNil(t, vul, "解析结果不应为 nil")

	// rule 为空字符串时 RuleCompile 应为 nil
	assert.Equal(t, "", vul.Rule, "rule 应为空字符串")
	assert.Nil(t, vul.RuleCompile, "空 rule 时 RuleCompile 应为 nil")
}

// TestReadVersionVul_Scanner_InvalidRuleExpr 测试无效 rule 表达式时返回解析错误
func TestReadVersionVul_Scanner_InvalidRuleExpr(t *testing.T) {
	yaml := []byte(`
info:
  name: "InvalidRuleTest"
  cve: "CVE-2024-0004"
  summary: "非法规则表达式"
  details: ""
  cvss: "3.0"
  severity: "low"
rule: 'INVALID_KEYWORD === "abc"'
`)
	_, err := ReadVersionVul(yaml)
	// 非法 rule 表达式（未知 token）应返回解析错误
	assert.Error(t, err, "非法 rule 表达式应返回错误")
}

// TestReadVersionVul_Scanner_References 测试 references 字段被同步到 Info.References
func TestReadVersionVul_Scanner_References(t *testing.T) {
	yaml := []byte(`
info:
  name: "RefTest"
  cve: "CVE-2024-0005"
  summary: "引用字段同步测试"
  details: ""
  cvss: "6.0"
  severity: "medium"
rule: 'version < "3.0.0"'
references:
  - "https://example.com/advisory"
  - "https://nvd.nist.gov/vuln/detail/CVE-2024-0005"
`)
	vul, err := ReadVersionVul(yaml)
	require.NoError(t, err)

	// 顶层 References 应同步到 Info.References
	assert.Equal(t, vul.References, vul.Info.References, "顶层 References 应被赋值到 Info.References")
	assert.Len(t, vul.References, 2, "应有 2 个引用链接")
}
