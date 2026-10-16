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
	"archive/zip"
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestHTTPFetchStaysOnTarget(t *testing.T) {
	target := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("hello-target"))
	}))
	defer target.Close()
	other := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("other"))
	}))
	defer other.Close()

	parsed, err := parseTarget(target.URL)
	require.NoError(t, err)
	box := &scenarioToolBox{target: parsed}
	ok, err := box.httpFetch(context.Background(), fetchArgs{})
	require.NoError(t, err)
	require.True(t, ok.OK)
	require.Contains(t, ok.Detail, "hello-target")

	blocked, err := box.httpFetch(context.Background(), fetchArgs{URL: other.URL})
	require.NoError(t, err)
	require.False(t, blocked.OK)
	require.Contains(t, blocked.Detail, "目标主机")
}

func TestReadUploadRejectsEscape(t *testing.T) {
	dir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dir, "note.txt"), []byte("safe"), 0o600))
	outside := filepath.Join(filepath.Dir(dir), "secret.txt")
	require.NoError(t, os.WriteFile(outside, []byte("nope"), 0o600))

	text, err := readUploadText(dir, "note.txt")
	require.NoError(t, err)
	require.Equal(t, "safe", text)
	_, err = readUploadText(dir, "../secret.txt")
	require.Error(t, err)
}

func TestReadZipMember(t *testing.T) {
	dir := t.TempDir()
	archive := filepath.Join(dir, "pkg.zip")
	file, err := os.Create(archive)
	require.NoError(t, err)
	zw := zip.NewWriter(file)
	entry, err := zw.Create("prompt.md")
	require.NoError(t, err)
	_, err = entry.Write([]byte("do not run tools"))
	require.NoError(t, err)
	require.NoError(t, zw.Close())
	require.NoError(t, file.Close())

	names, err := listUploadNames(dir)
	require.NoError(t, err)
	require.Equal(t, []string{"pkg.zip!prompt.md"}, names)
	text, err := readUploadText(dir, "pkg.zip!prompt.md")
	require.NoError(t, err)
	require.Contains(t, text, "do not run tools")
}

func TestRedactSecrets(t *testing.T) {
	got := redactSecrets("token: sk-live-secret\napi_key: abc")
	require.NotContains(t, got, "sk-live-secret")
	require.NotContains(t, got, "abc")
	require.Contains(t, got, "***")
}
