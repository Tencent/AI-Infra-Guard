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
			Rule: `body="nginx" || header="nginx" && icon="123"`,
			Config: &Config{
				Body:   "nginx",
				Header: "nginx",
				Icon:   456,
			},
			Ret: false,
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
