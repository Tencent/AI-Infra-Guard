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

package main

import (
	"path/filepath"
	"reflect"
	"testing"
)

func TestFindCaseInsensitivePathCollisions(t *testing.T) {
	tests := []struct {
		name  string
		paths []string
		want  [][]string
	}{
		{
			name: "detects directory case difference",
			paths: []string{
				filepath.Join("data", "vuln", "dify", "CVE-2026-41947.yaml"),
				filepath.Join("data", "vuln", "Dify", "CVE-2026-41947.yaml"),
			},
			want: [][]string{{
				"data/vuln/Dify/CVE-2026-41947.yaml",
				"data/vuln/dify/CVE-2026-41947.yaml",
			}},
		},
		{
			name: "sorts groups and variants deterministically",
			paths: []string{
				filepath.Join("data", "vuln", "Zeta", "rule.yaml"),
				filepath.Join("data", "vuln", "LITELLM", "rule.yaml"),
				filepath.Join("data", "vuln", "zeta", "rule.yaml"),
				filepath.Join("data", "vuln", "litellm", "rule.yaml"),
				filepath.Join("data", "vuln", "LiteLLM", "rule.yaml"),
			},
			want: [][]string{
				{
					"data/vuln/LITELLM/rule.yaml",
					"data/vuln/LiteLLM/rule.yaml",
					"data/vuln/litellm/rule.yaml",
				},
				{
					"data/vuln/Zeta/rule.yaml",
					"data/vuln/zeta/rule.yaml",
				},
			},
		},
		{
			name: "ignores duplicate occurrences of an exact path",
			paths: []string{
				filepath.Join("data", "vuln", "dify", "rule.yaml"),
				filepath.Join("data", "vuln", "dify", "rule.yaml"),
			},
		},
		{
			name: "does not combine distinct roots",
			paths: []string{
				filepath.Join("data", "vuln", "dify", "rule.yaml"),
				filepath.Join("data", "vuln_en", "dify", "rule.yaml"),
			},
		},
		{
			name: "does not combine different filenames",
			paths: []string{
				filepath.Join("data", "vuln", "dify", "CVE-2026-41947.yaml"),
				filepath.Join("data", "vuln", "Dify", "CVE-2026-41949.yaml"),
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := findCaseInsensitivePathCollisions(tt.paths)
			if !reflect.DeepEqual(got, tt.want) {
				t.Fatalf("findCaseInsensitivePathCollisions() = %#v, want %#v", got, tt.want)
			}
		})
	}
}
