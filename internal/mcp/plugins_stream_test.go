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

package mcp

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

type summaryTestAgent struct{}

func (summaryTestAgent) GetHistory() []map[string]string {
	return []map[string]string{{"role": "user", "content": "scan the target"}}
}

func summaryStreamConfig(t *testing.T, chunks []string, fail bool) (*McpPluginConfig, *bytes.Buffer, *atomic.Int32) {
	t.Helper()
	requests := new(atomic.Int32)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests.Add(1)
		w.Header().Set("Content-Type", "text/event-stream")
		for _, text := range chunks {
			payload, err := json.Marshal(map[string]any{
				"choices": []map[string]any{{"delta": map[string]any{"content": text}}},
			})
			if err != nil {
				t.Error(err)
				return
			}
			fmt.Fprintf(w, "data: %s\n\n", payload)
			w.(http.Flusher).Flush()
		}
		if fail {
			// A dropped chunked response fails after the already flushed text.
			conn, _, err := w.(http.Hijacker).Hijack()
			if err != nil {
				t.Error(err)
				return
			}
			_ = conn.Close()
			return
		}
		fmt.Fprint(w, "data: [DONE]\n\n")
	}))
	t.Cleanup(server.Close)
	var logs bytes.Buffer
	logger := gologger.NewLogger()
	logger.Logrus().SetOutput(&logs)
	return &McpPluginConfig{
		AIModel:  models.NewOpenAI("test-key", "test-model", server.URL+"/"),
		Language: "en",
		Logger:   logger,
	}, &logs, requests
}

func TestSummaryChatStreamOutcomes(t *testing.T) {
	for _, test := range []struct {
		name     string
		chunks   []string
		fail     bool
		cancel   bool
		wantErr  error
		requests int32
	}{
		{name: "success", chunks: []string{"summary ", "分析"}, requests: 1},
		{name: "partial failure", chunks: []string{"partial ", "analysis"}, fail: true, wantErr: io.ErrUnexpectedEOF, requests: 1},
		{name: "canceled before text", cancel: true, wantErr: context.Canceled},
	} {
		t.Run(test.name, func(t *testing.T) {
			config, logs, requests := summaryStreamConfig(t, test.chunks, test.fail)
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			if test.cancel {
				cancel()
			}
			got, err := SummaryChat(ctx, summaryTestAgent{}, config, "Summarize the scan. %s")
			if !errors.Is(err, test.wantErr) {
				t.Fatalf("SummaryChat error = %v, want %v", err, test.wantErr)
			}
			want := strings.Join(test.chunks, "")
			if got != want {
				t.Errorf("SummaryChat text = %q, want %q", got, want)
			}
			if !strings.Contains(logs.String(), want) {
				t.Errorf("summary logs did not retain emitted text %q: %q", want, logs.String())
			}
			if got := requests.Load(); got != test.requests {
				t.Errorf("requests = %d, want %d", got, test.requests)
			}
		})
	}
}

func TestSummaryResultStreamOutcomes(t *testing.T) {
	const issue = "<result><title>Unsafe tool</title><desc>Verified evidence</desc><level>high</level><risk_type>injection</risk_type><suggestion>Validate input</suggestion></result>"
	for _, test := range []struct {
		name       string
		chunks     []string
		fail       bool
		cancel     bool
		wantErr    error
		wantIssues int
		requests   int32
	}{
		{name: "success", chunks: []string{"<arg>", issue, "</arg>"}, wantIssues: 1, requests: 1},
		{name: "no vulnerabilities", chunks: []string{"<arg></arg>"}, requests: 1},
		// Even a complete first issue must not be accepted from a failed response.
		{name: "partial failure", chunks: []string{"<arg>", issue, "<result><title>Truncated"}, fail: true, wantErr: io.ErrUnexpectedEOF, requests: 1},
		{name: "canceled before text", cancel: true, wantErr: context.Canceled},
	} {
		t.Run(test.name, func(t *testing.T) {
			config, logs, requests := summaryStreamConfig(t, test.chunks, test.fail)
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			if test.cancel {
				cancel()
			}
			issues, err := SummaryResult(ctx, summaryTestAgent{}, config)
			if !errors.Is(err, test.wantErr) {
				t.Fatalf("SummaryResult error = %v, want %v", err, test.wantErr)
			}
			if len(issues) != test.wantIssues {
				t.Fatalf("SummaryResult issues = %+v, want %d issues", issues, test.wantIssues)
			}
			if test.wantErr != nil && issues != nil {
				t.Errorf("failed summary returned issues: %+v", issues)
			}
			if test.wantIssues > 0 && issues[0] != (Issue{
				Title: "Unsafe tool", Description: "Verified evidence", Level: LevelHigh,
				RiskType: "injection", Suggestion: "Validate input",
			}) {
				t.Errorf("parsed issue = %+v", issues[0])
			}
			if want := strings.Join(test.chunks, ""); !strings.Contains(logs.String(), want) {
				t.Errorf("summary logs did not retain emitted text %q: %q", want, logs.String())
			}
			if got := requests.Load(); got != test.requests {
				t.Errorf("requests = %d, want %d", got, test.requests)
			}
		})
	}
}
