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

package agent

import (
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

// TestPrepareTargetsCleansTempFiles: AI-Infra-Scan downloads each attachment
// into temp_uploads/ and, unlike the other task types, never removed it. This
// drives the download through the real HTTP path and asserts the copy is gone
// when prepareTargets returns.
func TestPrepareTargetsCleansTempFiles(t *testing.T) {
	t.Chdir(t.TempDir())

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("10.0.0.1\n10.0.0.2\n"))
	}))
	defer ts.Close()

	scanAgent := &AIInfraScanAgent{Server: strings.TrimPrefix(ts.URL, "http://")}
	request := TaskRequest{SessionId: "sess-1", Attachments: []string{"targets.txt"}}

	if _, err := scanAgent.prepareTargets(request, ScanRequest{}, scanTexts{}); err != nil {
		t.Fatalf("prepareTargets: %v", err)
	}

	entries, err := os.ReadDir("temp_uploads")
	if err != nil {
		t.Fatalf("read temp_uploads: %v", err)
	}
	if len(entries) != 0 {
		names := make([]string, 0, len(entries))
		for _, e := range entries {
			names = append(names, e.Name())
		}
		t.Fatalf("downloaded attachment was not cleaned up: %v", names)
	}
}
