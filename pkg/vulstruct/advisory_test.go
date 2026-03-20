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

package vulstruct

import (
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestAdvisoryEngine(t *testing.T) {
	dir := "data/vuln"
	ad := NewAdvisoryEngine()
	err := ad.LoadFromDirectory(dir)
	assert.NoError(t, err)
	results, err := ad.GetAdvisories("mlflow", "2.13", true)
	assert.NoError(t, err)
	for _, result := range results {
		t.Log(result)
	}
}

func TestNewRemoteAdvisoryEngine(t *testing.T) {
	ad := NewAdvisoryEngine()
	assert.NotNil(t, ad)
	hostname := "xx"
	err := ad.LoadFromHost(hostname)
	assert.NoError(t, err)
	results, err := ad.GetAdvisories("mlflow", "2.13", true)
	assert.NoError(t, err)
	for _, result := range results {
		t.Log(result)
	}
}
