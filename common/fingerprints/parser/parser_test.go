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
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"github.com/projectdiscovery/fastdialer/fastdialer"
	"github.com/stretchr/testify/assert"
	"testing"
	"time"
)

func TestSingleRule(t *testing.T) {
	rule := "body~=\"123123\" && (body == \"title\" || header=\"X-Powered-By: Express\")"
	config := &Config{
		Body:   "1111231232233",
		Header: "Server: nginx\r\nX-Powered-By: Express\r\n",
		Icon:   23333,
	}
	tokens, err := ParseTokens(rule)
	if err != nil {
		t.Fatal(err)
	}
	if err = CheckBalance(tokens); err != nil {
		t.Fatal(err)
	}
	dsl, err := TransFormExp(tokens)
	if err != nil {
		t.Fatal(err)
	}
	assert.True(t, dsl.Eval(config))
}

func TestSingleRuleForParse(t *testing.T) {
	dialer, err := fastdialer.NewDialer(fastdialer.DefaultOptions)
	assert.NoError(t, err)
	httpOptions := &httpx.HTTPOptions{
		Timeout:          time.Duration(30) * time.Second,
		RetryMax:         3,
		FollowRedirects:  false,
		HTTPProxy:        "",
		Unsafe:           false,
		DefaultUserAgent: httpx.GetRandomUserAgent(),
		Dialer:           dialer,
	}
	hp, err := httpx.NewHttpx(httpOptions)
	assert.NoError(t, err)
	resp, err := hp.Get("https://security.tencent.com/index.php", nil)
	config := &Config{
		Body:   resp.DataStr,
		Header: resp.GetHeaderRaw(),
		Icon:   3444,
	}
	rule := "header=\"nginx\" || header=\"X-Powered-By: Express\""
	fp, err := transfromRule(rule)
	assert.NoError(t, err)
	x := fp.Eval(config)
	t.Log(x)
}

func TestParseAdvisorTokens(t *testing.T) {
	tokens, err := ParseAdvisorTokens(`version > "1.2.3" && version < "2.3.dev"`)
	assert.NoError(t, err)
	err = CheckBalance(tokens)
	assert.NoError(t, err)
	dsl, err := TransFormExp(tokens)
	assert.NoError(t, err)
	config := &AdvisoryConfig{
		Version: "1.3",
	}
	b := dsl.AdvisoryEval(config)
	t.Log(b)
	//assert.Equal(t, dsl.AdvisoryEval(config), true)
}

func TestParseAdvisorLatestTokens(t *testing.T) {
	tokens, err := ParseAdvisorTokens(`version > "0" && version < "latest"`)
	assert.NoError(t, err)
	err = CheckBalance(tokens)
	assert.NoError(t, err)
	dsl, err := TransFormExp(tokens)
	assert.NoError(t, err)
	config := &AdvisoryConfig{
		Version: "1.3",
	}
	b := dsl.AdvisoryEval(config)
	t.Log(b)
	//assert.Equal(t, dsl.AdvisoryEval(config), true)
}
