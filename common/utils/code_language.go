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
	"io/fs"
	"path/filepath"
	"sort"
	"strings"
	"sync"
)

func classifyLanguage(ext string) string {
	// 扩展名与编程语言映射表（可根据需求扩展）
	var extToLang = map[string]string{
		".go":    "Go",
		".py":    "Python",
		".java":  "Java",
		".rs":    "Rust",
		".php":   "PHP",
		".rb":    "Ruby",
		".swift": "Swift",
		".c":     "C",
		".h":     "C",
		".cpp":   "C++",
		".hpp":   "C++",
		".js":    "JavaScript",
		".ts":    "TypeScript",
		".html":  "HTML",
		".css":   "CSS",
		".sql":   "SQL",
		".sh":    "Shell",
	}

	if lang, exists := extToLang[ext]; exists {
		return lang
	}
	return ""
}

func AnalyzeLanguage(dir string) map[string]int {
	var wg sync.WaitGroup
	mu := sync.Mutex{}
	stats := make(map[string]int)

	filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}

		wg.Add(1)
		go func() {
			defer wg.Done()

			ext := strings.ToLower(filepath.Ext(path))
			lang := classifyLanguage(ext)
			if lang == "" {
				return
			}
			mu.Lock()
			stats[lang]++
			mu.Unlock()
		}()

		return nil
	})

	wg.Wait()
	return stats
}

type LanguageCount struct {
	Language string
	Count    int
}

func GetTopLanguage(stats map[string]int) string {
	if len(stats) == 0 {
		return "Other"
	}

	// 将 map 转换为结构体切片
	var list []LanguageCount
	for lang, count := range stats {
		list = append(list, LanguageCount{Language: lang, Count: count})
	}

	// 按文件数量降序排序
	sort.Slice(list, func(i, j int) bool {
		return list[i].Count > list[j].Count // 降序排列
	})

	return list[0].Language
}
