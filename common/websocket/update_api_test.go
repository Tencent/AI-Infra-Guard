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
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// buildFakeClone creates a fake cloned repository directory tree in tmp:
//
//	<tmp>/data/fingerprints/foo.yaml
//	<tmp>/data/vuln/bar/CVE-2024-0001.yaml
//	<tmp>/data/mcp/tool.yaml
//	<tmp>/README.md   <- should NOT be copied
func buildFakeClone(t *testing.T, root string) {
	t.Helper()
	files := map[string]string{
		"data/fingerprints/foo.yaml":       "name: foo\n",
		"data/vuln/bar/CVE-2024-0001.yaml": "cve: CVE-2024-0001\n",
		"data/mcp/tool.yaml":               "rule: test\n",
		"README.md":                        "# readme\n",
	}
	for rel, content := range files {
		path := filepath.Join(root, rel)
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatalf("MkdirAll %s: %v", filepath.Dir(path), err)
		}
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			t.Fatalf("WriteFile %s: %v", path, err)
		}
	}
}

func TestCopyDataDirs_selectiveDirs(t *testing.T) {
	srcRoot := t.TempDir()
	buildFakeClone(t, srcRoot)

	dstRoot := t.TempDir()
	orig, _ := os.Getwd()
	if err := os.Chdir(dstRoot); err != nil {
		t.Fatalf("Chdir: %v", err)
	}
	defer os.Chdir(orig)

	dirs := []string{"fingerprints", "vuln"}
	n, err := copyDataDirs(srcRoot, dirs)
	if err != nil {
		t.Fatalf("copyDataDirs: %v", err)
	}

	// Expect 2 files: foo.yaml and CVE-2024-0001.yaml
	if n != 2 {
		t.Errorf("expected 2 files written, got %d", n)
	}

	// Verify fingerprints file exists with correct content.
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

	// Verify mcp was NOT copied (not in dirs list).
	mcpPath := filepath.Join("data", "mcp", "tool.yaml")
	if _, err := os.Stat(mcpPath); !os.IsNotExist(err) {
		t.Errorf("expected %s to NOT exist", mcpPath)
	}

	// Verify README.md was NOT copied.
	readmePath := filepath.Join(dstRoot, "README.md")
	if _, err := os.Stat(readmePath); !os.IsNotExist(err) {
		t.Errorf("expected README.md to NOT be copied to dst root")
	}
}

func TestCopyDataDirs_allDirs(t *testing.T) {
	srcRoot := t.TempDir()
	buildFakeClone(t, srcRoot)

	dstRoot := t.TempDir()
	orig, _ := os.Getwd()
	if err := os.Chdir(dstRoot); err != nil {
		t.Fatalf("Chdir: %v", err)
	}
	defer os.Chdir(orig)

	dirs := splitDirs(dataDirsDefault)
	n, err := copyDataDirs(srcRoot, dirs)
	if err != nil {
		t.Fatalf("copyDataDirs: %v", err)
	}

	// fake clone has 3 data files: foo.yaml, CVE-2024-0001.yaml, tool.yaml
	if n != 3 {
		t.Errorf("expected 3 files written, got %d", n)
	}
}

func TestCopyDataDirs_missingSubdir(t *testing.T) {
	srcRoot := t.TempDir()
	// Only create fingerprints, not vuln_en
	_ = os.MkdirAll(filepath.Join(srcRoot, "data", "fingerprints"), 0o755)
	_ = os.WriteFile(filepath.Join(srcRoot, "data", "fingerprints", "x.yaml"), []byte("x: 1\n"), 0o644)

	dstRoot := t.TempDir()
	orig, _ := os.Getwd()
	if err := os.Chdir(dstRoot); err != nil {
		t.Fatalf("Chdir: %v", err)
	}
	defer os.Chdir(orig)

	// vuln_en is missing in src — should be silently skipped, no error.
	dirs := []string{"fingerprints", "vuln_en"}
	n, err := copyDataDirs(srcRoot, dirs)
	if err != nil {
		t.Fatalf("expected no error for missing sub-dir, got: %v", err)
	}
	if n != 1 {
		t.Errorf("expected 1 file written, got %d", n)
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
