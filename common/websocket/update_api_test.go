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

package websocket

import (
	"archive/zip"
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// buildTestZip creates an in-memory zip that mimics the GitHub archive layout:
//
//	AI-Infra-Guard-main/
//	AI-Infra-Guard-main/data/fingerprints/foo.yaml
//	AI-Infra-Guard-main/data/vuln/bar/CVE-2024-0001.yaml
//	AI-Infra-Guard-main/data/mcp/tool.yaml
//	AI-Infra-Guard-main/README.md   <- should NOT be extracted
func buildTestZip(t *testing.T) []byte {
	t.Helper()
	buf := new(bytes.Buffer)
	w := zip.NewWriter(buf)

	entries := []struct {
		name    string
		content string
		isDir   bool
	}{
		{"AI-Infra-Guard-main/", "", true},
		{"AI-Infra-Guard-main/data/", "", true},
		{"AI-Infra-Guard-main/data/fingerprints/", "", true},
		{"AI-Infra-Guard-main/data/fingerprints/foo.yaml", "name: foo\n", false},
		{"AI-Infra-Guard-main/data/vuln/", "", true},
		{"AI-Infra-Guard-main/data/vuln/bar/", "", true},
		{"AI-Infra-Guard-main/data/vuln/bar/CVE-2024-0001.yaml", "cve: CVE-2024-0001\n", false},
		{"AI-Infra-Guard-main/data/mcp/", "", true},
		{"AI-Infra-Guard-main/data/mcp/tool.yaml", "rule: test\n", false},
		// files that should be ignored
		{"AI-Infra-Guard-main/README.md", "# readme\n", false},
		{"AI-Infra-Guard-main/cmd/main.go", "package main\n", false},
	}

	for _, e := range entries {
		if e.isDir {
			fh := &zip.FileHeader{Name: e.name, Method: zip.Deflate}
			fh.SetMode(0o755 | os.ModeDir)
			_, err := w.CreateHeader(fh)
			if err != nil {
				t.Fatalf("zip CreateHeader dir %s: %v", e.name, err)
			}
		} else {
			f, err := w.Create(e.name)
			if err != nil {
				t.Fatalf("zip Create %s: %v", e.name, err)
			}
			_, _ = f.Write([]byte(e.content))
		}
	}
	if err := w.Close(); err != nil {
		t.Fatalf("zip Close: %v", err)
	}
	return buf.Bytes()
}

func TestExtractDataDirs_selectiveDirs(t *testing.T) {
	zipBytes := buildTestZip(t)
	tmp := t.TempDir()

	// Change working directory to tmp so relative paths resolve correctly.
	orig, _ := os.Getwd()
	if err := os.Chdir(tmp); err != nil {
		t.Fatalf("Chdir: %v", err)
	}
	defer os.Chdir(orig)

	dirs := []string{"fingerprints", "vuln"}
	n, err := extractDataDirs(zipBytes, dirs)
	if err != nil {
		t.Fatalf("extractDataDirs: %v", err)
	}

	// Expect 2 files: foo.yaml and CVE-2024-0001.yaml
	if n != 2 {
		t.Errorf("expected 2 files written, got %d", n)
	}

	// Verify fingerprints file exists and has correct content.
	fpPath := filepath.Join("data", "fingerprints", "foo.yaml")
	data, err := os.ReadFile(fpPath)
	if err != nil {
		t.Fatalf("ReadFile %s: %v", fpPath, err)
	}
	if strings.TrimSpace(string(data)) != "name: foo" {
		t.Errorf("unexpected content in %s: %q", fpPath, string(data))
	}

	// Verify vuln sub-directory file exists.
	vulnPath := filepath.Join("data", "vuln", "bar", "CVE-2024-0001.yaml")
	if _, err := os.Stat(vulnPath); err != nil {
		t.Errorf("expected %s to exist: %v", vulnPath, err)
	}

	// Verify mcp was NOT extracted (not in dirs list).
	mcpPath := filepath.Join("data", "mcp", "tool.yaml")
	if _, err := os.Stat(mcpPath); !os.IsNotExist(err) {
		t.Errorf("expected %s to NOT exist", mcpPath)
	}

	// Verify README.md was NOT extracted.
	readmePath := "README.md"
	if _, err := os.Stat(readmePath); !os.IsNotExist(err) {
		t.Errorf("expected %s to NOT exist", readmePath)
	}
}

func TestExtractDataDirs_allDirs(t *testing.T) {
	zipBytes := buildTestZip(t)
	tmp := t.TempDir()

	orig, _ := os.Getwd()
	if err := os.Chdir(tmp); err != nil {
		t.Fatalf("Chdir: %v", err)
	}
	defer os.Chdir(orig)

	dirs := splitDirs(dataDirsDefault)
	n, err := extractDataDirs(zipBytes, dirs)
	if err != nil {
		t.Fatalf("extractDataDirs: %v", err)
	}

	// Test zip has 3 data files (foo.yaml, CVE-2024-0001.yaml, tool.yaml).
	if n != 3 {
		t.Errorf("expected 3 files written, got %d", n)
	}
}

func TestExtractDataDirs_invalidZip(t *testing.T) {
	_, err := extractDataDirs([]byte("this is not a zip"), []string{"fingerprints"})
	if err == nil {
		t.Error("expected error for invalid zip, got nil")
	}
}

func TestSplitDirs(t *testing.T) {
	cases := []struct {
		input string
		want  []string
	}{
		{"fingerprints,vuln", []string{"fingerprints", "vuln"}},
		{" fingerprints , vuln_en ", []string{"fingerprints", "vuln_en"}},
		{"", []string{}},
		{"mcp", []string{"mcp"}},
	}
	for _, tc := range cases {
		got := splitDirs(tc.input)
		if len(got) != len(tc.want) {
			t.Errorf("splitDirs(%q): got %v, want %v", tc.input, got, tc.want)
			continue
		}
		for i := range got {
			if got[i] != tc.want[i] {
				t.Errorf("splitDirs(%q)[%d]: got %q, want %q", tc.input, i, got[i], tc.want[i])
			}
		}
	}
}
