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
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestClassifyLanguage 测试扩展名到语言的映射
func TestClassifyLanguage(t *testing.T) {
	cases := []struct {
		ext      string
		expected string
	}{
		{".go", "Go"},
		{".py", "Python"},
		{".java", "Java"},
		{".rs", "Rust"},
		{".php", "PHP"},
		{".rb", "Ruby"},
		{".swift", "Swift"},
		{".c", "C"},
		{".h", "C"},
		{".cpp", "C++"},
		{".hpp", "C++"},
		{".js", "JavaScript"},
		{".ts", "TypeScript"},
		{".html", "HTML"},
		{".css", "CSS"},
		{".sql", "SQL"},
		{".sh", "Shell"},
		// 未知扩展名应返回空字符串
		{".unknown", ""},
		{"", ""},
		{".md", ""},
		{".txt", ""},
	}

	for _, tc := range cases {
		t.Run("ext="+tc.ext, func(t *testing.T) {
			result := classifyLanguage(tc.ext)
			assert.Equal(t, tc.expected, result, "扩展名 %q 应映射到语言 %q", tc.ext, tc.expected)
		})
	}
}

// TestGetTopLanguage_Empty 测试空 map 返回 "Other"
func TestGetTopLanguage_Empty(t *testing.T) {
	result := GetTopLanguage(map[string]int{})
	// 空 map 应返回 "Other"
	assert.Equal(t, "Other", result, "空 map 应返回 'Other'")
}

// TestGetTopLanguage_SingleEntry 测试单个语言返回该语言
func TestGetTopLanguage_SingleEntry(t *testing.T) {
	stats := map[string]int{"Go": 10}
	result := GetTopLanguage(stats)
	assert.Equal(t, "Go", result, "单个语言时应返回该语言")
}

// TestGetTopLanguage_MultipleEntries 测试多语言返回文件数最多的语言
func TestGetTopLanguage_MultipleEntries(t *testing.T) {
	stats := map[string]int{
		"Go":     50,
		"Python": 30,
		"Java":   10,
	}
	result := GetTopLanguage(stats)
	// Go 文件最多，应返回 Go
	assert.Equal(t, "Go", result, "文件数最多的语言应排第一")
}

// TestGetTopLanguage_TieBreak 测试相同数量时不 panic（仅验证返回非空）
func TestGetTopLanguage_TieBreak(t *testing.T) {
	stats := map[string]int{
		"Go":     5,
		"Python": 5,
	}
	result := GetTopLanguage(stats)
	// 相同数量时应返回其中一个（具体结果取决于排序稳定性，只验证不为空）
	assert.NotEmpty(t, result, "相同数量时应返回非空语言")
}

// TestAnalyzeLanguage_EmptyDir 测试空目录返回空 map
func TestAnalyzeLanguage_EmptyDir(t *testing.T) {
	// 创建临时空目录
	dir := t.TempDir()
	stats := AnalyzeLanguage(dir)
	assert.Empty(t, stats, "空目录应返回空 map")
}

// TestAnalyzeLanguage_WithFiles 测试含有源文件的目录
func TestAnalyzeLanguage_WithFiles(t *testing.T) {
	// 创建临时目录并写入测试文件
	dir := t.TempDir()

	// 创建 2 个 Go 文件和 1 个 Python 文件
	require.NoError(t, os.WriteFile(filepath.Join(dir, "main.go"), []byte("package main"), 0644))
	require.NoError(t, os.WriteFile(filepath.Join(dir, "util.go"), []byte("package util"), 0644))
	require.NoError(t, os.WriteFile(filepath.Join(dir, "script.py"), []byte("print('hello')"), 0644))

	stats := AnalyzeLanguage(dir)

	// Go 应统计为 2，Python 应统计为 1
	assert.Equal(t, 2, stats["Go"], "Go 文件数应为 2")
	assert.Equal(t, 1, stats["Python"], "Python 文件数应为 1")
}

// TestAnalyzeLanguage_UnknownExtensions 测试未知扩展名不计入统计
func TestAnalyzeLanguage_UnknownExtensions(t *testing.T) {
	dir := t.TempDir()

	// 创建未知扩展名文件
	require.NoError(t, os.WriteFile(filepath.Join(dir, "README.md"), []byte("# docs"), 0644))
	require.NoError(t, os.WriteFile(filepath.Join(dir, "config.yaml"), []byte("key: val"), 0644))
	// 一个已知语言文件
	require.NoError(t, os.WriteFile(filepath.Join(dir, "app.js"), []byte("console.log()"), 0644))

	stats := AnalyzeLanguage(dir)

	// 未知扩展名不计入，JavaScript 应统计为 1
	assert.Equal(t, 1, stats["JavaScript"], "JavaScript 文件数应为 1")
	assert.Len(t, stats, 1, "只有一种已知语言")
}

// TestAnalyzeLanguage_SubDir 测试子目录也被递归统计
func TestAnalyzeLanguage_SubDir(t *testing.T) {
	dir := t.TempDir()
	subDir := filepath.Join(dir, "sub")
	require.NoError(t, os.Mkdir(subDir, 0755))

	// 在根目录和子目录各放一个 Go 文件
	require.NoError(t, os.WriteFile(filepath.Join(dir, "root.go"), []byte(""), 0644))
	require.NoError(t, os.WriteFile(filepath.Join(subDir, "sub.go"), []byte(""), 0644))

	stats := AnalyzeLanguage(dir)
	// 递归遍历后 Go 总数应为 2
	assert.Equal(t, 2, stats["Go"], "子目录中的 Go 文件也应被统计")
}

// TestAnalyzeLanguage_GetTopLanguage_Integration 集成测试：AnalyzeLanguage + GetTopLanguage
func TestAnalyzeLanguage_GetTopLanguage_Integration(t *testing.T) {
	dir := t.TempDir()

	// 创建更多 Rust 文件，让 Rust 成为最多语言
	for _, name := range []string{"a.rs", "b.rs", "c.rs"} {
		require.NoError(t, os.WriteFile(filepath.Join(dir, name), []byte("fn main(){}"), 0644))
	}
	require.NoError(t, os.WriteFile(filepath.Join(dir, "main.py"), []byte(""), 0644))

	stats := AnalyzeLanguage(dir)
	top := GetTopLanguage(stats)
	// Rust 文件最多，应为 top language
	assert.Equal(t, "Rust", top, "Rust 文件最多时应为 top language")
}
