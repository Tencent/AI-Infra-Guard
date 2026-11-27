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

package parser

import (
	"fmt"
	"testing"

	vv "github.com/hashicorp/go-version"
)

func TestTransFormExp(t *testing.T) {
	s := "header=\"realm=\\\"Comtrend Gigabit 802.11n Router\" || body=\"Comtrend Gigabit 802.11n Router\""
	tokens, err := ParseTokens(s)
	if err != nil {
		t.Fatal(err)
	}
	exp, err := TransFormExp(tokens)
	if err != nil {
		t.Fatal(err)
	}

	exp.PrintAST()
}

func TestTransFormExp2(t *testing.T) {
	for _, s := range []string{
		`body="nginx" || header="nginx"`,
		`body="nginx" || header="nginx" && header="Server: nginx"`,
		`body="nginx" && header="nginx" || header="Server: nginx"`,
		`(body="nginx" || header="nginx") && header="Server: nginx"`,
		`body="nginx" || (header="nginx" && header="Server: nginx")`,
	} {
		tokens, err := ParseTokens(s)
		if err != nil {
			t.Fatal(err)
		}

		if exp, err := TransFormExp(tokens); err != nil {
			t.Fatal(err)
		} else {
			exp.PrintAST()
		}
	}
}

func TestEval(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Fatal(r)
		}
	}()

	rules := []struct {
		Rule   string
		Config *Config
		Ret    bool
	}{
		{
			Rule: `header="nginx" || body="nginx"`,
			Config: &Config{
				Header: "nginx123",
			},
			Ret: true,
		},
		{
			Rule: `header="nginx" || body="nginx"`,
			Config: &Config{
				Body: "nginxabc",
			},
			Ret: true,
		},
		{
			Rule: `body="nginx" || header="nginx" && icon="123"`,
			Config: &Config{
				Body:   "nginxabc",
				Header: "server:none",
				Icon:   123,
			},
			Ret: true,
		},
		{
			Rule: `body="nginx" || header="nginx" && icon="123"`,
			Config: &Config{
				Body:   "abc",
				Header: "nginx",
				Icon:   123,
			},
			Ret: true,
		},
		{
			// "&&" 优先于 "||"，故规则等价于 body="nginx" || (header="nginx" && icon="123")。
			// body 已命中，整条规则即为真，icon 不匹配不影响结果。
			// 此前的左折叠把规则读作 (body || header) && icon，命中 body 仍返回 false。
			Rule: `body="nginx" || header="nginx" && icon="123"`,
			Config: &Config{
				Body:   "nginx",
				Header: "nginx",
				Icon:   456,
			},
			Ret: true,
		},
		{
			Rule: `body="nginx" && (icon=="123" || header="nginx")`,
			Config: &Config{
				Body:   "nginx",
				Header: "server:none",
				Icon:   123,
			},
			Ret: true,
		}, {
			Rule: `body="nginx" && (icon=="123" || header="nginx")`,
			Config: &Config{
				Body:   "nginxabc",
				Header: "server:none",
				Icon:   456,
			},
			Ret: false,
		},
		{
			Rule: `body="nginx" || (icon=="123" && header="nginx")`,
			Config: &Config{
				Body:   "none",
				Header: "nginx",
				Icon:   123,
			},
			Ret: true,
		},
	}

	for _, r := range rules {
		tokens, err := ParseTokens(r.Rule)
		if err != nil {
			t.Fatal(err)
		}
		exp, err := TransFormExp(tokens)
		if err != nil {
			t.Fatal(err)
		}
		if ret := exp.Eval(r.Config); ret != r.Ret {
			t.Fatalf("eval: %s ret: %v", r.Rule, ret)
		}
	}
}

// TestEvalRegexCaseInsensitive: Eval lowercases the body before matching, so a
// body~= pattern containing uppercase letters must still match.
func TestEvalRegexCaseInsensitive(t *testing.T) {
	tests := []struct {
		name string
		rule string
		body string
		want bool
	}{
		{"uppercase pattern matches", `body~="(OPENAI_API_KEY|ANTHROPIC_API_KEY)=[A-Za-z0-9_-]{16,}"`, "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuv", true},
		{"shipped .env rule shape", `body~="(OPENAI_API_KEY|GEMINI_API_KEY)\\s*=\\s*[A-Za-z0-9_\\-]{16,}"`, "GEMINI_API_KEY=AIzaSyabcdefghijklmnopqrstuv", true},
		{"lowercase pattern still matches", `body~="^\\s*\\{"`, `{"a":1}`, true},
		{"uppercase pattern, no key present", `body~="(OPENAI_API_KEY)=[A-Za-z0-9_-]{16,}"`, "PATH=/usr/bin", false},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			tokens, err := ParseTokens(tc.rule)
			if err != nil {
				t.Fatal(err)
			}
			exp, err := TransFormExp(tokens)
			if err != nil {
				t.Fatal(err)
			}
			if got := exp.Eval(&Config{Body: tc.body}); got != tc.want {
				t.Fatalf("rule %s body %q: got %v want %v", tc.rule, tc.body, got, tc.want)
			}
		})
	}
}

// TestVersionCheckPreRelease 覆盖 PEP 440 风格的预发布版本号。
// 直接删除字母有两种错法：把两侧数字粘连成 "3.11.02"（即 3.11.2），
// 或者丢掉没有尾随数字的标签，让 "3.11.0rc" 等同于正式版 "3.11.0"。
func TestVersionCheckPreRelease(t *testing.T) {
	for _, c := range []struct {
		version string
		want    string
	}{
		// 带数字后缀的标签
		{"3.11.0rc2", "3.11.0-rc2"},
		{"0.6.0rc1", "0.6.0-rc1"},
		{"1.2.3b1", "1.2.3-b1"},
		{"3.11.0a1", "3.11.0-a1"},
		// 不带数字后缀的标签
		{"3.11.0rc", "3.11.0-rc"},
		{"3.11.0alpha", "3.11.0-alpha"},
		{"3.11.0beta", "3.11.0-beta"},
		{"1.2.3b", "1.2.3-b"},
		// 已经带连字符的写法
		{"1.2.3-rc1", "1.2.3-rc1"},
		{"1.2.3-rc", "1.2.3-rc"},
		// 未被字母分隔的数字保持原样
		{"1.2.3", "1.2.3"},
		{"v1.2.3", "1.2.3"},
		{"3.11.0", "3.11.0"},
		// ".RELEASE" 之类表示正式版，不能当作预发布标签
		{"1.2.3.RELEASE", "1.2.3.0"},
		{"latest", "999"},
		{"", "0"},
	} {
		if got := versionCheck(c.version); got != c.want {
			t.Fatalf("versionCheck(%q) = %q, want %q", c.version, got, c.want)
		}
	}
}

// TestVersionCheckPreReleaseOrdering 标准化后的版本号必须能被解析，
// 并且预发布版本要排在同名正式版本之前、标签之间也要保持先后顺序。
func TestVersionCheckPreReleaseOrdering(t *testing.T) {
	for _, c := range []struct {
		lower string
		upper string
	}{
		// 预发布版本排在正式版本之前
		{"3.11.0rc", "3.11.0"},
		{"3.11.0rc2", "3.11.0"},
		{"3.11.0alpha", "3.11.0"},
		{"3.11.0beta", "3.11.0"},
		// 也排在下一个正式版本之前
		{"3.11.0rc", "3.11.1"},
		{"3.11.0", "3.11.1"},
		// 标签之间的顺序：alpha < beta < rc
		{"3.11.0alpha", "3.11.0beta"},
		{"3.11.0beta", "3.11.0rc"},
		{"3.11.0a1", "3.11.0rc1"},
		// 同一标签内按数字递增
		{"3.11.0rc1", "3.11.0rc2"},
	} {
		lower, err := vv.NewVersion(versionCheck(c.lower))
		if err != nil {
			t.Fatalf("versionCheck(%q) = %q, 无法解析: %v", c.lower, versionCheck(c.lower), err)
		}
		upper, err := vv.NewVersion(versionCheck(c.upper))
		if err != nil {
			t.Fatalf("versionCheck(%q) = %q, 无法解析: %v", c.upper, versionCheck(c.upper), err)
		}
		if !lower.LessThan(upper) {
			t.Fatalf("versionCheck(%q)=%q 应小于 versionCheck(%q)=%q",
				c.lower, lower, c.upper, upper)
		}
	}
}

// TestAdvisoryEvalPreRelease 预发布版本必须落在其正式版本之前，
// 否则受影响的目标会被漏报。
func TestAdvisoryEvalPreRelease(t *testing.T) {
	for _, c := range []struct {
		rule    string
		version string
		want    bool
	}{
		{`version < "3.11.0"`, "3.11.0rc2", true},
		{`version <= "3.11.1"`, "3.11.0rc2", true},
		{`version == "3.11.2"`, "3.11.0rc2", false},
		{`version < "0.6.0"`, "0.6.0rc1", true},
		// 正式版本不受影响
		{`version < "3.11.0"`, "3.10.9", true},
		{`version < "3.11.0"`, "3.11.0", false},
	} {
		tokens, err := ParseAdvisorTokens(c.rule)
		if err != nil {
			t.Fatal(err)
		}
		if err := CheckBalance(tokens); err != nil {
			t.Fatal(err)
		}
		rule, err := TransFormExp(tokens)
		if err != nil {
			t.Fatal(err)
		}
		if got := rule.AdvisoryEval(&AdvisoryConfig{Version: c.version}); got != c.want {
			t.Fatalf("rule %s with version %q = %v, want %v", c.rule, c.version, got, c.want)
		}
	}
}

// compileFpRule 编译指纹规则，便于优先级用例复用。
func compileFpRule(t *testing.T, rule string) *Rule {
	t.Helper()
	tokens, err := ParseTokens(rule)
	if err != nil {
		t.Fatalf("ParseTokens(%q): %v", rule, err)
	}
	if err := CheckBalance(tokens); err != nil {
		t.Fatalf("CheckBalance(%q): %v", rule, err)
	}
	compiled, err := TransFormExp(tokens)
	if err != nil {
		t.Fatalf("TransFormExp(%q): %v", rule, err)
	}
	return compiled
}

// compileAdvisoryRule 编译版本规则，便于优先级用例复用。
func compileAdvisoryRule(t *testing.T, rule string) *Rule {
	t.Helper()
	tokens, err := ParseAdvisorTokens(rule)
	if err != nil {
		t.Fatalf("ParseAdvisorTokens(%q): %v", rule, err)
	}
	if err := CheckBalance(tokens); err != nil {
		t.Fatalf("CheckBalance(%q): %v", rule, err)
	}
	compiled, err := TransFormExp(tokens)
	if err != nil {
		t.Fatalf("TransFormExp(%q): %v", rule, err)
	}
	return compiled
}

// TestAndBindsTighterThanOr 用穷举真值表固定 "&&" 优先于 "||" 的语义。
// 以 body / header / icon 作为三个相互独立的原子条件 A、B、C。
func TestAndBindsTighterThanOr(t *testing.T) {
	const (
		ruleOrAnd = `body="nginx" || header="nginx" && icon="123"`
		ruleAndOr = `body="nginx" && header="nginx" || icon="123"`
	)

	configFor := func(a, b, c bool) *Config {
		cfg := &Config{Body: "none", Header: "none", Icon: 456}
		if a {
			cfg.Body = "nginx"
		}
		if b {
			cfg.Header = "nginx"
		}
		if c {
			cfg.Icon = 123
		}
		return cfg
	}

	orAnd := compileFpRule(t, ruleOrAnd)
	andOr := compileFpRule(t, ruleAndOr)

	for _, a := range []bool{false, true} {
		for _, b := range []bool{false, true} {
			for _, c := range []bool{false, true} {
				cfg := configFor(a, b, c)

				// A || B && C 必须等价于 A || (B && C)
				if got, want := orAnd.Eval(cfg), a || (b && c); got != want {
					t.Errorf("%s with A=%v B=%v C=%v = %v, want %v (A || (B && C))",
						ruleOrAnd, a, b, c, got, want)
				}

				// A && B || C 必须等价于 (A && B) || C
				if got, want := andOr.Eval(cfg), (a && b) || c; got != want {
					t.Errorf("%s with A=%v B=%v C=%v = %v, want %v ((A && B) || C)",
						ruleAndOr, a, b, c, got, want)
				}
			}
		}
	}
}

// TestBracketsOverrideDefaultPrecedence 验证文档 "() 分组改变优先级" 的说明：
// 加括号后的规则必须与不加括号的默认结合方式真正不同。
func TestBracketsOverrideDefaultPrecedence(t *testing.T) {
	// 文档中的示例规则。
	bracketed := compileFpRule(t, `(body="gradio" || body="Gradio") && header="X-Gradio-Version"`)
	bare := compileFpRule(t, `body="gradio" || body="Gradio" && header="X-Gradio-Version"`)

	// body 命中但缺少版本头：括号版要求该头部，故为假；默认结合方式下 body 命中即为真。
	cfg := &Config{Body: "a gradio app", Header: "server: none"}
	if got := bracketed.Eval(cfg); got != false {
		t.Errorf("bracketed rule = %v, want false (header required)", got)
	}
	if got := bare.Eval(cfg); got != true {
		t.Errorf("bare rule = %v, want true (body alone satisfies the leading ||)", got)
	}
}

// TestOrChainTopLevelOperator 固定 AST 形状：以 "||" 连接的规则，其根节点必须是 "||"，
// 不能被末尾不带括号的 "&&" 夺走整条规则。
func TestOrChainTopLevelOperator(t *testing.T) {
	rule := compileAdvisoryRule(t, `version < "1.0.0" || version >= "2.0.0" && version < "2.1.0"`)
	root, ok := rule.root.(*logicExp)
	if !ok {
		t.Fatalf("root is %T, want *logicExp", rule.root)
	}
	if root.op != tokenOr {
		t.Fatalf("root operator = %q, want %q", root.op, tokenOr)
	}
	right, ok := root.right.(*logicExp)
	if !ok {
		t.Fatalf("right operand is %T, want *logicExp", root.right)
	}
	if right.op != tokenAnd {
		t.Fatalf("right operand operator = %q, want %q", right.op, tokenAnd)
	}
}

// TestShippedMixedOperatorRulesMatchExplicitGrouping 对仓库中实际发布的、
// 同时在顶层使用 "&&" 与 "||" 的 CVE 规则做差分测试：按书写方式解析的结果，
// 必须与按标准优先级显式加括号的等价规则一致。
func TestShippedMixedOperatorRulesMatchExplicitGrouping(t *testing.T) {
	cases := []struct {
		name      string
		asWritten string
		explicit  string
	}{
		{
			// data/vuln/jupyterlab/CVE-2021-41134.yaml
			name:      "jupyterlab CVE-2021-41134",
			asWritten: `version < "1.1.1" || (version >= "2.0.0" && version < "2.1.1") || (version >= "3.0.0" && version < "3.1.1") || version < "5.0.2" || version >= "6.0.0" && version < "6.1.2" || version < "1.0.1" || version >= "2.0.0" && version < "2.1.1"`,
			explicit:  `version < "1.1.1" || (version >= "2.0.0" && version < "2.1.1") || (version >= "3.0.0" && version < "3.1.1") || version < "5.0.2" || (version >= "6.0.0" && version < "6.1.2") || version < "1.0.1" || (version >= "2.0.0" && version < "2.1.1")`,
		},
		{
			// data/vuln/n8n/CVE-2025-68613.yaml
			name:      "n8n CVE-2025-68613",
			asWritten: `version >= "0.211.0" && version < "1.120.4" || version >= "1.121.0" && version < "1.121.1"`,
			explicit:  `(version >= "0.211.0" && version < "1.120.4") || (version >= "1.121.0" && version < "1.121.1")`,
		},
		{
			// data/vuln/langchain/CVE-2026-44843.yaml
			name:      "langchain CVE-2026-44843",
			asWritten: `version < "0.3.85" || version >= "1.0.0" && version < "1.3.3"`,
			explicit:  `version < "0.3.85" || (version >= "1.0.0" && version < "1.3.3")`,
		},
	}

	versions := make([]string, 0, 512)
	for _, major := range []int{0, 1, 2, 3, 4, 5, 6, 7} {
		for _, minor := range []int{0, 1, 2, 3, 100, 120, 121, 211} {
			for _, patch := range []int{0, 1, 2, 3, 4, 5, 9, 85} {
				versions = append(versions, fmt.Sprintf("%d.%d.%d", major, minor, patch))
			}
		}
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			asWritten := compileAdvisoryRule(t, c.asWritten)
			explicit := compileAdvisoryRule(t, c.explicit)
			for _, version := range versions {
				cfg := &AdvisoryConfig{Version: version}
				got := asWritten.AdvisoryEval(cfg)
				want := explicit.AdvisoryEval(cfg)
				if got != want {
					t.Fatalf("version %q: rule as written = %v, explicit grouping = %v", version, got, want)
				}
			}
		})
	}
}
