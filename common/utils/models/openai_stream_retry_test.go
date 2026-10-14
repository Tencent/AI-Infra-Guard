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
	"errors"
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

// collectStream also pins the event contract: at most one error, no text on
// that event, and no events after it.
func collectStream(t *testing.T, ch <-chan ChatStreamEvent) (string, error) {
	t.Helper()
	timer := time.NewTimer(20 * time.Second)
	defer timer.Stop()
	var sb strings.Builder
	var streamErr error
	for {
		select {
		case event, ok := <-ch:
			if !ok {
				return sb.String(), streamErr
			}
			if streamErr != nil {
				t.Fatal("received an event after the terminal error")
			}
			if event.Err != nil {
				if event.Text != "" {
					t.Fatal("terminal error must not carry text")
				}
				streamErr = event.Err
			}
			sb.WriteString(event.Text)
		case <-timer.C:
			t.Fatal("timed out waiting for ChatStream channel to close")
			return "", nil
		}
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
	text, err := collectStream(t, model.ChatStream(context.Background(), []map[string]string{
		{"role": "user", "content": "hi"},
	}))

	if err == nil {
		t.Fatal("expected terminal error after partial output")
	}
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
	text, err := collectStream(t, model.ChatStream(context.Background(), []map[string]string{
		{"role": "user", "content": "hi"},
	}))

	if err != nil {
		t.Fatalf("successful retry reported an error: %v", err)
	}
	if text != "Hello world" {
		t.Fatalf("expected the retried stream to deliver the full text once, got %q", text)
	}
	if got := requests.Load(); got != 2 {
		t.Fatalf("expected exactly one retry (2 requests), got %d", got)
	}
}

func TestChatStreamCleanCompletion(t *testing.T) {
	for _, content := range []string{"", "Hello world"} {
		t.Run(content, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.Header().Set("Content-Type", "text/event-stream")
				fmt.Fprint(w, sseChunk(content), "data: [DONE]\n\n")
			}))
			defer server.Close()
			model := NewOpenAI("test-key", "gpt-test", server.URL+"/")
			text, err := collectStream(t, model.ChatStream(context.Background(), nil))
			if err != nil || text != content {
				t.Fatalf("got (%q, %v), want (%q, nil)", text, err, content)
			}
		})
	}
}

func TestChatStreamRetryExhaustion(t *testing.T) {
	var requests atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests.Add(1)
		// Flush successful headers to exercise our stream retry loop rather than
		// the SDK's HTTP status retry policy.
		w.Header().Set("Content-Type", "text/event-stream")
		w.(http.Flusher).Flush()
		dropConnection(w)
	}))
	defer server.Close()
	model := NewOpenAI("test-key", "gpt-test", server.URL+"/")
	text, err := collectStream(t, model.ChatStream(context.Background(), nil))
	if err == nil || text != "" {
		t.Fatalf("got (%q, %v), want empty text and a terminal error", text, err)
	}
	if got := requests.Load(); got != 3 {
		t.Fatalf("got %d requests, want 3", got)
	}
}

func TestChatStreamCancellation(t *testing.T) {
	for _, afterText := range []bool{false, true} {
		t.Run(fmt.Sprint(afterText), func(t *testing.T) {
			ctx, cancel := context.WithCancel(context.Background())
			defer cancel()
			var requests atomic.Int32
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				requests.Add(1)
				w.Header().Set("Content-Type", "text/event-stream")
				fmt.Fprint(w, sseChunk("partial"))
				w.(http.Flusher).Flush()
				<-r.Context().Done()
			}))
			defer server.Close()
			model := NewOpenAI("test-key", "gpt-test", server.URL+"/")
			if !afterText {
				cancel()
			}
			ch := model.ChatStream(ctx, nil)
			if afterText {
				select {
				case first := <-ch:
					if first.Text != "partial" || first.Err != nil {
						t.Fatalf("unexpected first event: %+v", first)
					}
				case <-time.After(5 * time.Second):
					t.Fatal("timed out waiting for initial text")
				}
				cancel()
			}
			text, err := collectStream(t, ch)
			if text != "" || !errors.Is(err, context.Canceled) {
				t.Fatalf("got (%q, %v), want context.Canceled", text, err)
			}
			if !afterText && requests.Load() != 0 {
				t.Fatal("already canceled stream made an HTTP request")
			}
		})
	}
}

func TestChatStreamCancellationDuringBackoff(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	var requests atomic.Int32
	firstRequest := make(chan struct{}, 1)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests.Add(1)
		select {
		case firstRequest <- struct{}{}:
		default:
		}
		w.Header().Set("Content-Type", "text/event-stream")
		w.(http.Flusher).Flush()
		dropConnection(w)
	}))
	defer server.Close()
	model := NewOpenAI("test-key", "gpt-test", server.URL+"/")
	ch := model.ChatStream(ctx, nil)
	select {
	case <-firstRequest:
	case <-time.After(5 * time.Second):
		t.Fatal("timed out waiting for first request")
	}
	// The first response fails immediately; cancellation interrupts the 2s wait.
	time.AfterFunc(200*time.Millisecond, cancel)
	text, err := collectStream(t, ch)
	if text != "" || !errors.Is(err, context.Canceled) {
		t.Fatalf("got (%q, %v), want context.Canceled", text, err)
	}
	if requests.Load() != 1 {
		t.Fatalf("got %d requests, want 1", requests.Load())
	}
}

func TestChatResponsePreservesPartialTextAndError(t *testing.T) {
	for _, fail := range []bool{false, true} {
		t.Run(fmt.Sprint(fail), func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.Header().Set("Content-Type", "text/event-stream")
				fmt.Fprint(w, sseChunk("partial"))
				w.(http.Flusher).Flush()
				if fail {
					dropConnection(w)
					return
				}
				fmt.Fprint(w, "data: [DONE]\n\n")
			}))
			defer server.Close()
			model := NewOpenAI("test-key", "gpt-test", server.URL+"/")
			text, err := model.ChatResponse(context.Background(), "hi")
			if text != "partial" || (err != nil) != fail {
				t.Fatalf("got (%q, %v), want partial text with failure=%v", text, err, fail)
			}
		})
	}
}

func TestChatStreamPreservesUsageOnAbort(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		fmt.Fprint(w, `data: {"choices":[{"delta":{"content":"partial"}}],"usage":{"total_tokens":7}}`+"\n\n")
		w.(http.Flusher).Flush()
		dropConnection(w)
	}))
	defer server.Close()
	model := NewOpenAI("test-key", "gpt-test", server.URL+"/")
	text, err := model.ChatResponse(context.Background(), "hi")
	if text != "partial" || err == nil {
		t.Fatalf("got (%q, %v), want partial text and error", text, err)
	}
	if got := model.GetTotalToken(); got != 7 {
		t.Fatalf("got %d tokens, want 7 credited before terminal event", got)
	}
}
