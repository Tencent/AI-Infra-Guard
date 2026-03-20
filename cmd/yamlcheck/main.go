// Package main YAML格式检查工具
// 用于CI流水线中验证data目录下的YAML文件格式是否正确
// 用法: yamlcheck <path1> [path2] ...
// 支持传入文件或目录，目录会递归扫描其中的 .yaml/.yml 文件
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
		fmt.Println("用法: yamlcheck <path1> [path2] ...")
		fmt.Println("  path 可以是文件或目录，目录会递归扫描")
		fmt.Println("  验证 data/fingerprints、data/vuln、data/vuln_en 下的YAML文件格式")
		os.Exit(1)
	}

	// 收集所有待检查的 yaml 文件
	var yamlFiles []string
	for _, arg := range os.Args[1:] {
		info, err := os.Stat(arg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "❌ [路径错误] %s: %v\n", arg, err)
			continue
		}
		if info.IsDir() {
			files, err := walkYAMLFiles(arg)
			if err != nil {
				fmt.Fprintf(os.Stderr, "❌ [遍历目录失败] %s: %v\n", arg, err)
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

	for _, file := range yamlFiles {
		category := categorizeFile(file)
		if category == "" {
			continue
		}

		checkedCount++
		data, err := os.ReadFile(file)
		if err != nil {
			fmt.Fprintf(os.Stderr, "❌ [读取失败] %s: %v\n", file, err)
			hasError = true
			continue
		}

		switch category {
		case "fingerprint":
			_, err = parser.InitFingerPrintFromData(data)
			if err != nil {
				fmt.Fprintf(os.Stderr, "❌ [指纹格式错误] %s: %v\n", file, err)
				hasError = true
			} else {
				fmt.Printf("✅ [指纹] %s\n", file)
			}
		case "vuln":
			_, err = vulstruct.ReadVersionVul(data)
			if err != nil {
				fmt.Fprintf(os.Stderr, "❌ [漏洞格式错误] %s: %v\n", file, err)
				hasError = true
			} else {
				fmt.Printf("✅ [漏洞] %s\n", file)
			}
		}
	}

	if checkedCount == 0 {
		fmt.Println("⚠️  没有找到需要检查的YAML文件")
		os.Exit(0)
	}

	fmt.Printf("\n共检查 %d 个文件\n", checkedCount)

	if hasError {
		fmt.Fprintln(os.Stderr, "\n❌ YAML格式检查未通过，请修复上述错误")
		os.Exit(1)
	}

	fmt.Println("\n✅ 所有YAML文件格式检查通过")
}

// walkYAMLFiles 递归遍历目录，返回所有 .yaml/.yml 文件路径
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

// isYAML 判断文件是否为 YAML 文件
func isYAML(file string) bool {
	return strings.HasSuffix(file, ".yaml") || strings.HasSuffix(file, ".yml")
}

// categorizeFile 根据文件路径判断文件类别
// 返回 "fingerprint"、"vuln" 或 ""（不属于需要检查的文件）
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
