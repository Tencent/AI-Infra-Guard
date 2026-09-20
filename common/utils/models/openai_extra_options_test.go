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

package models

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// captureRequest 起一个假的 OpenAI 端点，把收到的请求记录下来。
func captureRequest(t *testing.T, headers *http.Header, body *map[string]any) *httptest.Server {
	t.Helper()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		*headers = r.Header.Clone()
		if err := json.NewDecoder(r.Body).Decode(body); err != nil {
			t.Errorf("failed to decode request body: %v", err)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"choices":[{"message":{"content":"1"}}]}`))
	}))
	t.Cleanup(server.Close)
	return server
}

func TestOpenAISendsExtraHeadersAndBody(t *testing.T) {
	var headers http.Header
	var body map[string]any
	server := captureRequest(t, &headers, &body)

	ai := &OpenAI{
		Key:     "test-key",
		BaseUrl: server.URL + "/",
		Model:   "test-model",
		ExtraHeaders: map[string]string{
			"HTTP-Referer": "https://example.com",
			"X-Title":      "AI-Infra-Guard",
		},
		ExtraBody: map[string]any{
			"provider.order": []string{"anthropic"},
			"temperature":    0.25,
		},
	}

	if err := ai.Vaild(context.Background()); err != nil {
		t.Fatalf("Vaild() returned an error: %v", err)
	}

	if got := headers.Get("HTTP-Referer"); got != "https://example.com" {
		t.Errorf("HTTP-Referer = %q, want %q", got, "https://example.com")
	}
	if got := headers.Get("X-Title"); got != "AI-Infra-Guard" {
		t.Errorf("X-Title = %q, want %q", got, "AI-Infra-Guard")
	}
	if got := body["temperature"]; got != 0.25 {
		t.Errorf("temperature = %v, want 0.25", got)
	}

	// 点号路径要写成嵌套字段，OpenRouter 的 provider 路由就靠它。
	provider, ok := body["provider"].(map[string]any)
	if !ok {
		t.Fatalf("provider is missing from the request body: %v", body)
	}
	order, ok := provider["order"].([]any)
	if !ok || len(order) != 1 || order[0] != "anthropic" {
		t.Errorf("provider.order = %v, want [anthropic]", provider["order"])
	}
}

func TestOpenAISendsNothingExtraByDefault(t *testing.T) {
	var headers http.Header
	var body map[string]any
	server := captureRequest(t, &headers, &body)

	ai := &OpenAI{
		Key:     "test-key",
		BaseUrl: server.URL + "/",
		Model:   "test-model",
	}

	if err := ai.Vaild(context.Background()); err != nil {
		t.Fatalf("Vaild() returned an error: %v", err)
	}

	if _, ok := body["provider"]; ok {
		t.Errorf("provider must not be added when ExtraBody is empty: %v", body)
	}
	if got := headers.Get("X-Title"); got != "" {
		t.Errorf("X-Title = %q, want it to be absent", got)
	}
}
