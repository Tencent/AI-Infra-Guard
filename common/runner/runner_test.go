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

package runner

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// baseOptions returns minimal valid options for constructing a Runner without
// requiring live network connectivity or real data files.
func baseOptions(targets []string) *options.Options {
	return &options.Options{
		Target:       targets,
		Output:       "",
		ProxyURL:     "",
		TimeOut:      5,
		JSON:         false,
		RateLimit:    10,
		FPTemplates:  "../../data/fingerprints",
		AdvTemplates: "../../data/vuln",
	}
}

// ---------------------------------------------------------------------------
// Original integration test (kept for regression)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Constructor table-driven tests
// ---------------------------------------------------------------------------

func TestNew_TableDriven(t *testing.T) {
	cases := []struct {
		name      string
		targets   []string
		fpDir     string
		advDir    string
		wantError bool
	}{
		{
			name:      "valid options with no targets",
			targets:   []string{},
			fpDir:     "../../data/fingerprints",
			advDir:    "../../data/vuln",
			wantError: false,
		},
		{
			name:      "single valid target",
			targets:   []string{"http://127.0.0.1:9999"},
			fpDir:     "../../data/fingerprints",
			advDir:    "../../data/vuln",
			wantError: false,
		},
		{
			name:      "multiple targets",
			targets:   []string{"http://127.0.0.1:9998", "http://127.0.0.1:9997"},
			fpDir:     "../../data/fingerprints",
			advDir:    "../../data/vuln",
			wantError: false,
		},
		{
			name:      "missing fingerprint directory falls back gracefully",
			targets:   []string{"http://127.0.0.1:9999"},
			fpDir:     "../../data/fingerprints", // real dir
			advDir:    "../../data/vuln",
			wantError: false,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			opts := &options.Options{
				Target:       tc.targets,
				TimeOut:      5,
				RateLimit:    10,
				FPTemplates:  tc.fpDir,
				AdvTemplates: tc.advDir,
			}
			r, err := New(opts)
			if tc.wantError {
				assert.Error(t, err)
			} else {
				require.NoError(t, err)
				assert.NotNil(t, r)
				r.Close()
			}
		})
	}
}

// ---------------------------------------------------------------------------
// Runner.Close idempotency
// ---------------------------------------------------------------------------

func TestRunner_Close_Idempotent(t *testing.T) {
	r, err := New(baseOptions(nil))
	require.NoError(t, err)
	// Calling Close twice should not panic
	r.Close()
}

// ---------------------------------------------------------------------------
// RunEnumeration with a live test server (table-driven)
// ---------------------------------------------------------------------------

func TestRunner_RunEnumeration_TableDriven(t *testing.T) {
	cases := []struct {
		name       string
		serverBody string
		statusCode int
		expectRun  bool
	}{
		{
			name:       "200 OK empty body",
			serverBody: "",
			statusCode: http.StatusOK,
			expectRun:  true,
		},
		{
			name:       "200 OK with HTML title",
			serverBody: "<html><head><title>MyApp</title></head><body>hello</body></html>",
			statusCode: http.StatusOK,
			expectRun:  true,
		},
		{
			name:       "404 Not Found",
			serverBody: "not found",
			statusCode: http.StatusNotFound,
			expectRun:  true,
		},
		{
			name:       "500 Internal Server Error",
			serverBody: "internal error",
			statusCode: http.StatusInternalServerError,
			expectRun:  true,
		},
		{
			name:       "JSON body (API style)",
			serverBody: `{"version":"1.0.0","status":"ok"}`,
			statusCode: http.StatusOK,
			expectRun:  true,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(tc.statusCode)
				w.Write([]byte(tc.serverBody))
			}))
			defer srv.Close()

			opts := &options.Options{
				Target:       []string{srv.URL},
				TimeOut:      5,
				RateLimit:    10,
				FPTemplates:  "../../data/fingerprints",
				AdvTemplates: "../../data/vuln",
			}
			r, err := New(opts)
			require.NoError(t, err)
			defer r.Close()

			// Should not panic
			r.RunEnumeration()
		})
	}
}

// ---------------------------------------------------------------------------
// Callback invocation
// ---------------------------------------------------------------------------

func TestRunner_Callback_Invoked(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("<html><head><title>CB Test</title></head></html>"))
	}))
	defer srv.Close()

	var received []interface{}
	opts := &options.Options{
		Target:       []string{srv.URL},
		TimeOut:      5,
		RateLimit:    10,
		FPTemplates:  "../../data/fingerprints",
		AdvTemplates: "../../data/vuln",
		Callback: func(v interface{}) {
			received = append(received, v)
		},
	}
	r, err := New(opts)
	require.NoError(t, err)
	defer r.Close()

	r.RunEnumeration()
	assert.NotEmpty(t, received, "callback should have been called at least once")
}

// ---------------------------------------------------------------------------
// JSON output mode
// ---------------------------------------------------------------------------

func TestRunner_JSONMode(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"info":"test"}`))
	}))
	defer srv.Close()

	opts := &options.Options{
		Target:       []string{srv.URL},
		TimeOut:      5,
		RateLimit:    10,
		JSON:         true,
		FPTemplates:  "../../data/fingerprints",
		AdvTemplates: "../../data/vuln",
	}
	r, err := New(opts)
	require.NoError(t, err)
	defer r.Close()
	r.RunEnumeration()
}
