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

import "testing"

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
