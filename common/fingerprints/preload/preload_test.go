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

package preload

import (
	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"github.com/projectdiscovery/fastdialer/fastdialer"
	"github.com/stretchr/testify/assert"
	"os"
	"testing"
	"time"
)

func TestFingerPrint(t *testing.T) {
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
	// mlflow
	m := Mlflow{}
	t.Log(m.Match(hp, "http://127.0.0.1:5000/"))
	t.Log(m.GetVersion(hp, "http://127.0.0.1:5000/"))
}

func TestRunner_RunFpReqs(t *testing.T) {
	dialer, err := fastdialer.NewDialer(fastdialer.DefaultOptions)
	assert.NoError(t, err)
	httpOptions := &httpx.HTTPOptions{
		Timeout:          time.Duration(3) * time.Second,
		RetryMax:         1,
		FollowRedirects:  false,
		HTTPProxy:        "",
		Unsafe:           false,
		DefaultUserAgent: httpx.GetRandomUserAgent(),
		Dialer:           dialer,
	}
	hp, err := httpx.NewHttpx(httpOptions)
	assert.NoError(t, err)

	data, err := os.ReadFile("data/fingerprints/anythingllm.yaml")
	assert.NoError(t, err)
	fp, err := parser.InitFingerPrintFromData(data)
	assert.NoError(t, err)
	instance := New(hp, []parser.FingerPrint{*fp})
	fps := instance.RunFpReqs("http://localhost:8888/", 10, 0)
	for _, fp := range fps {
		t.Logf("%+v", fp)
	}
}
