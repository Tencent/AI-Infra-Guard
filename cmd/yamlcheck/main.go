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

// Package main YAML format validation tool
// Used in CI pipelines to verify the format of YAML files under the data directory.
// Usage: yamlcheck <path1> [path2] ...
// Supports files or directories; directories are scanned recursively for .yaml/.yml files.
package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: yamlcheck <path1> [path2] ...")
		fmt.Println("  path can be a file or directory (directories are scanned recursively)")
		fmt.Println("  Validates YAML files under data/fingerprints, data/vuln, data/vuln_en")
		os.Exit(1)
	}

	// Collect all YAML files to check
	var yamlFiles []string
	for _, arg := range os.Args[1:] {
		info, err := os.Stat(arg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "❌ [path error] %s: %v\n", arg, err)
			continue
		}
		if info.IsDir() {
			files, err := walkYAMLFiles(arg)
			if err != nil {
				fmt.Fprintf(os.Stderr, "❌ [directory walk failed] %s: %v\n", arg, err)
				continue
			}
			yamlFiles = append(yamlFiles, files...)
		} else {
			if isYAML(arg) {
				yamlFiles = append(yamlFiles, arg)
			}
		}
	}

	if collisions := findCaseInsensitivePathCollisions(yamlFiles); len(collisions) > 0 {
		fmt.Fprintln(os.Stderr, "❌ [case-insensitive path collision] conflicting YAML paths found:")
		for _, collision := range collisions {
			fmt.Fprintf(os.Stderr, "  - %s\n", strings.Join(collision, " | "))
		}
		os.Exit(1)
	}

	hasError := false
	checkedCount := 0
	passCount := 0
	failCount := 0

	fmt.Println()
	fmt.Println("╔══════════════════════════════════════════════╗")
	fmt.Println("║          AIG YAML Validation Report          ║")
	fmt.Println("╚══════════════════════════════════════════════╝")
	fmt.Println()

	for _, file := range yamlFiles {
		category := categorizeFile(file)
		if category == "" {
			continue
		}

		checkedCount++
		data, err := os.ReadFile(file)
		if err != nil {
			fmt.Fprintf(os.Stderr, "  ❌  FAIL  [read error]  %s\n      └─ %v\n", file, err)
			hasError = true
			failCount++
			continue
		}

		switch category {
		case "fingerprint":
			fp, err := parser.InitFingerPrintFromData(data)
			if err != nil {
				fmt.Fprintf(os.Stderr, "  ❌  FAIL  [fingerprint]  %s\n      └─ %v\n", file, err)
				hasError = true
				failCount++
			} else if strings.TrimSpace(fp.Info.Name) == "" {
				fmt.Fprintf(os.Stderr, "  ❌  FAIL  [fingerprint]  %s\n      └─ missing required 'name' field\n", file)
				hasError = true
				failCount++
			} else {
				fmt.Printf("  ✅  PASS  [fingerprint]  %s\n", file)
				passCount++
			}
		case "vuln":
			vul, err := vulstruct.ReadVersionVul(data)
			if err != nil {
				fmt.Fprintf(os.Stderr, "  ❌  FAIL  [vuln rule]   %s\n      └─ %v\n", file, err)
				hasError = true
				failCount++
			} else if strings.TrimSpace(vul.Info.FingerPrintName) == "" {
				fmt.Fprintf(os.Stderr, "  ❌  FAIL  [vuln rule]   %s\n      └─ missing required 'name' field\n", file)
				hasError = true
				failCount++
			} else if !isValidSeverity(vul.Info.Severity) {
				fmt.Fprintf(os.Stderr, "  ❌  FAIL  [vuln rule]   %s\n      └─ invalid or missing severity level '%s'\n", file, vul.Info.Severity)
				hasError = true
				failCount++
			} else {
				fmt.Printf("  ✅  PASS  [vuln rule]   %s\n", file)
				passCount++
			}
		}
	}

	fmt.Println()
	fmt.Println("──────────────────────────────────────────────")

	if checkedCount == 0 {
		fmt.Println("⚠️  No YAML files found to validate.")
		os.Exit(0)
	}

	fmt.Printf("  Total checked : %d\n", checkedCount)
	fmt.Printf("  ✅ Passed     : %d\n", passCount)
	fmt.Printf("  ❌ Failed     : %d\n", failCount)
	fmt.Println("──────────────────────────────────────────────")

	if hasError {
		fmt.Println()
		fmt.Fprintln(os.Stderr, "❌ Validation FAILED — please fix the errors listed above.")
		os.Exit(1)
	}

	fmt.Println()
	fmt.Println("✅ All YAML files passed validation!")
}

// isValidSeverity verifies that severity matches standard vulnerability levels.
// Accepts both English (low/medium/high/critical) and Chinese (低/中/高/严重/危急)
// severity labels used across the zh/en rule libraries, plus UNKNOWN/"" for
// rules where no CVSS score is available (e.g. supply-chain advisories).
func isValidSeverity(severity string) bool {
	switch strings.ToLower(strings.TrimSpace(severity)) {
	case "info", "low", "medium", "high", "critical",
		"低", "中", "中等", "高", "中危", "高危", "严重", "危急",
		"unknown", "":
		return true
	default:
		return false
	}
}

// findCaseInsensitivePathCollisions returns distinct paths that become equal
// after normalizing separators and folding case. Duplicate occurrences of the
// exact same normalized path are ignored.
func findCaseInsensitivePathCollisions(paths []string) [][]string {
	grouped := make(map[string]map[string]struct{})
	for _, path := range paths {
		normalized := filepath.ToSlash(filepath.Clean(path))
		folded := strings.ToLower(normalized)
		if grouped[folded] == nil {
			grouped[folded] = make(map[string]struct{})
		}
		grouped[folded][normalized] = struct{}{}
	}

	var foldedPaths []string
	for folded, originals := range grouped {
		if len(originals) > 1 {
			foldedPaths = append(foldedPaths, folded)
		}
	}
	sort.Strings(foldedPaths)

	var collisions [][]string
	for _, folded := range foldedPaths {
		originals := make([]string, 0, len(grouped[folded]))
		for original := range grouped[folded] {
			originals = append(originals, original)
		}
		sort.Strings(originals)
		collisions = append(collisions, originals)
	}

	return collisions
}

// walkYAMLFiles recursively walks a directory and returns all .yaml/.yml file paths.
func walkYAMLFiles(root string) ([]string, error) {
	var files []string
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && isYAML(path) {
			files = append(files, path)
		}
		return nil
	})
	return files, err
}

// isYAML reports whether the file has a .yaml or .yml extension.
func isYAML(file string) bool {
	return strings.HasSuffix(file, ".yaml") || strings.HasSuffix(file, ".yml")
}

// categorizeFile determines the category of a YAML file based on its path.
// Returns "fingerprint", "vuln", or "" (not a file that needs validation).
func categorizeFile(file string) string {
	normalized := filepath.ToSlash(file)

	if strings.Contains(normalized, "data/fingerprints/") || strings.HasPrefix(normalized, "fingerprints/") {
		return "fingerprint"
	}

	if strings.Contains(normalized, "data/vuln/") || strings.Contains(normalized, "data/vuln_en/") ||
		strings.HasPrefix(normalized, "vuln/") || strings.HasPrefix(normalized, "vuln_en/") {
		return "vuln"
	}

	return ""
}