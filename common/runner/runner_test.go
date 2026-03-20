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

package runner

import (
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"testing"
)

func TestRunner_RunEnumeration(t *testing.T) {
	targets := []string{
		"http://127.0.0.1:5000",
	}
	parseOptions := &options.Options{
		Target:       targets,
		Output:       "",
		ProxyURL:     "",
		TimeOut:      10,
		JSON:         false,
		RateLimit:    10,
		FPTemplates:  "data/fingerprints",
		AdvTemplates: "data/advisories",
	}
	r, err := New(parseOptions)
	if err != nil {
		gologger.Fatalf("Could not create runner: %s\n", err)
	}
	defer r.Close()
	r.RunEnumeration()
}
