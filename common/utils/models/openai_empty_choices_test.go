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
	"net/http"
	"net/http/httptest"
	"testing"
)

// emptyChoicesServer 模拟一类真实存在的 OpenAI 兼容网关行为：
// HTTP 200，但 choices 是空数组（内容过滤命中、上游错误被包装成 200 等）。
func emptyChoicesServer(t *testing.T) *httptest.Server {
	t.Helper()
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"chatcmpl-empty","object":"chat.completion","created":1,"model":"test-model","choices":[]}`))
	}))
	t.Cleanup(server.Close)
	return server
}

// 空 choices 必须是错误，不能是 panic。
// ChatWithImageByte 跑在扫描任务的 goroutine 里，panic 会带走整个进程。
func TestChatWithImageByteEmptyChoices(t *testing.T) {
	ai := &OpenAI{Key: "test-key", BaseUrl: emptyChoicesServer(t).URL + "/", Model: "test-model"}

	got, err := ai.ChatWithImageByte(context.Background(), "describe this page", []byte("fake-image"))
	if err == nil {
		t.Fatalf("expected an error for an empty choices array, got content %q", got)
	}
}

func TestChatWithImageEmptyChoices(t *testing.T) {
	ai := &OpenAI{Key: "test-key", BaseUrl: emptyChoicesServer(t).URL + "/", Model: "test-model"}

	got, err := ai.ChatWithImage(context.Background(), "describe this page", "")
	if err == nil {
		t.Fatalf("expected an error for an empty choices array, got content %q", got)
	}
}
