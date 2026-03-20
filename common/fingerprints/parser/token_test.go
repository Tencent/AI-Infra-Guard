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

func TestParseTokens(t *testing.T) {
	for _, s := range []string{
		`body="href=\"http://www.thinkphp.cn\">thinkphp</a>" || body="thinkphp_show_page_trace" || icon="f49c4a4bde1eec6c0b80c2277c76e3dbs"`,
		"body~=\"(<center><strong>EZCMS ([\\d\\.]+) )\"",
	} {
		tokens, err := ParseTokens(s)
		if err != nil {
			t.Fatal(err)
		}
		t.Log(tokens)
	}
}

func TestParseTokensInvalidOperator(t *testing.T) {
	for _, s := range []string{
		`body~~"test operator"`,
		`body~!"test operator"`,
	} {
		tokens, err := ParseTokens(s)
		if err == nil {
			t.Log(tokens)
			t.Fatal("expect error, but got nil")
		} else {
			t.Logf("parse token `%s` error: %s", s, err)
		}
	}
}

func TestParseStrangeTokens(t *testing.T) {
	for _, s := range []string{
		`"\`,
		`"abc\`,
		`"abc\"`,
		`"abc\""`,
	} {
		tokens, err := ParseTokens(s)
		if err == nil {
			t.Log(tokens)
		} else {
			t.Logf("parse token `%s` error: %v", s, err)
		}
	}
}

func TestParseAdvisorTokens2(t *testing.T) {
	s := "version >= \"1.0.0\" || version < \"2.0.0\" || version == \"3.0.0\""
	tokens, err := ParseAdvisorTokens(s)
	if err != nil {
		t.Fatal(err)
	}
	t.Log(tokens)
}
