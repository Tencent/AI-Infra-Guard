// Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
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

package models

import "testing"

func TestGetJsonString(t *testing.T) {
	tests := []struct {
		name string
		data string
		want string
	}{
		{
			name: "empty input",
		},
		{
			name: "no fences",
			data: "[]",
			want: "[]",
		},
		{
			name: "no opening fence",
			data: "[]\n```",
			want: "[]\n```",
		},
		{
			name: "complete fences",
			data: "```json\n[]\n```",
			want: "\n[]\n",
		},
		{
			name: "complete fences with surrounding text",
			data: "prefix ```json\n[]\n``` suffix",
			want: "\n[]\n",
		},
		{
			name: "empty fenced content",
			data: "```json```",
			want: "",
		},
		{
			name: "unclosed fence",
			data: "```json\n[]",
			want: "```json\n[]",
		},
		{
			name: "unclosed fence with prefix",
			data: "prefix ```json\n[]",
			want: "prefix ```json\n[]",
		},
		{
			name: "opening fence only with prefix",
			data: "prefix ```json",
			want: "prefix ```json",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := GetJsonString(tt.data); got != tt.want {
				t.Fatalf("GetJsonString(%q) = %q, want %q", tt.data, got, tt.want)
			}
		})
	}
}
