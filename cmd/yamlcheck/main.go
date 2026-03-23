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

	hasError := false
	checkedCount := 0
	passCount := 0
	failCount := 0

	fmt.Println()
	fmt.Println("╔══════════════════════════════════════════════╗")
	fmt.Println("║         AIG YAML Validation Report          ║")
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
			_, err = parser.InitFingerPrintFromData(data)
			if err != nil {
				fmt.Fprintf(os.Stderr, "  ❌  FAIL  [fingerprint]  %s\n      └─ %v\n", file, err)
				hasError = true
				failCount++
			} else {
				fmt.Printf("  ✅  PASS  [fingerprint]  %s\n", file)
				passCount++
			}
		case "vuln":
			_, err = vulstruct.ReadVersionVul(data)
			if err != nil {
				fmt.Fprintf(os.Stderr, "  ❌  FAIL  [vuln rule]   %s\n      └─ %v\n", file, err)
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
