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

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

// sseChunk encodes a single streaming delta in OpenAI SSE format.
func sseChunk(content string) string {
	payload, _ := json.Marshal(map[string]any{
		"choices": []map[string]any{
			{"delta": map[string]any{"content": content}},
		},
	})
	return "data: " + string(payload) + "\n\n"
}

// dropConnection closes the underlying TCP connection abruptly so the
// client observes an unexpected EOF instead of a clean SSE terminator.
func dropConnection(w http.ResponseWriter) {
	hj, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "hijack unsupported", http.StatusInternalServerError)
		return
	}
	conn, _, err := hj.Hijack()
	if err != nil {
		return
	}
	_ = conn.Close()
}

// collectStream drains a ChatStream channel into one string, failing the
// test if the channel does not close within the deadline.
func collectStream(t *testing.T, ch <-chan string) string {
	t.Helper()
	done := make(chan string, 1)
	go func() {
		var sb strings.Builder
		for word := range ch {
			sb.WriteString(word)
		}
		done <- sb.String()
	}()
	select {
	case got := <-done:
		return got
	case <-time.After(20 * time.Second):
		t.Fatal("timed out waiting for ChatStream channel to close")
		return ""
	}
}

// TestChatStreamMidStreamFailureDoesNotDuplicate guards #693: once a delta
// has been delivered to the caller, a mid-stream failure must not trigger a
// retry that replays the whole response on top of the partial text the
// consumer already accumulated.
func TestChatStreamMidStreamFailureDoesNotDuplicate(t *testing.T) {
	var requests atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests.Add(1)
		w.Header().Set("Content-Type", "text/event-stream")
		flusher := w.(http.Flusher)
		if requests.Load() == 1 {
			// First request: emit one delta, then hard-drop the connection.
			fmt.Fprint(w, sseChunk("Hello"))
			flusher.Flush()
			dropConnection(w)
			return
		}
		// A retry would return the full response from scratch.
		fmt.Fprint(w, sseChunk("Hello world"))
		fmt.Fprint(w, "data: [DONE]\n\n")
	}))
	t.Cleanup(server.Close)

	model := NewOpenAI("test-key", "gpt-test", server.URL+"/")
	text := collectStream(t, model.ChatStream(context.Background(), []map[string]string{
		{"role": "user", "content": "hi"},
	}))

	if text != "Hello" {
		t.Fatalf("consumer received duplicated/replayed content: %q", text)
	}
	if got := requests.Load(); got != 1 {
		t.Fatalf("expected no retry after partial output, got %d requests", got)
	}
}

// TestChatStreamRetriesWhenNothingEmitted verifies the retry loop still
// fires when the stream fails before any delta reached the caller.
func TestChatStreamRetriesWhenNothingEmitted(t *testing.T) {
	var requests atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests.Add(1)
		w.Header().Set("Content-Type", "text/event-stream")
		if requests.Load() == 1 {
			// Fail before emitting anything.
			dropConnection(w)
			return
		}
		fmt.Fprint(w, sseChunk("Hello world"))
		fmt.Fprint(w, "data: [DONE]\n\n")
	}))
	t.Cleanup(server.Close)

	model := NewOpenAI("test-key", "gpt-test", server.URL+"/")
	text := collectStream(t, model.ChatStream(context.Background(), []map[string]string{
		{"role": "user", "content": "hi"},
	}))

	if text != "Hello world" {
		t.Fatalf("expected the retried stream to deliver the full text once, got %q", text)
	}
	if got := requests.Load(); got != 2 {
		t.Fatalf("expected exactly one retry (2 requests), got %d", got)
	}
}
