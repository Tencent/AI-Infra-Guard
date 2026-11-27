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

package utils

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// TestLoadRemoteFingerPrintsSkipsUnparseableItem: one bad fingerprint from the
// server must not take the agent down. The old code logged with Fatalf
// (os.Exit) for an unparseable item; after the fix it is skipped. This returns
// normally with zero fingerprints instead of killing the process.
func TestLoadRemoteFingerPrintsSkipsUnparseableItem(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		// 123 cannot unmarshal into a FingerPrint, so InitFingerPrintFromData errors.
		_, _ = w.Write([]byte(`{"data":{"items":[123],"total":1},"message":"ok"}`))
	}))
	defer srv.Close()

	fps, err := LoadRemoteFingerPrints(strings.TrimPrefix(srv.URL, "http://"))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(fps) != 0 {
		t.Fatalf("unparseable fingerprint should be skipped, got %d", len(fps))
	}
}
