package utils

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/mcp"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

var ignoreFiles = []string{
	// 系统文件
	".DS_Store", "Thumbs.db",

	// 版本控制相关
	".gitignore", ".gitattributes", ".gitmodules", ".gitkeep", ".git", ".svn",

	// 环境配置文件
	".env", "env", ".env.local", ".env.example", ".env.test", ".env.production",

	// Node.js/npm相关
	"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "uv.lock",
	".npmrc", ".yarnrc", ".yarn-integrity",

	// Python相关
	"Pipfile", "Pipfile.lock", "poetry.lock", "requirements.txt", "setup.py",

	// Java相关
	"pom.xml", "build.gradle", "gradle.properties",

	// Ruby相关
	"Gemfile", "Gemfile.lock",

	// IDE和编辑器配置
	".idea", ".vscode", ".editorconfig", ".project",

	// 构建工具配置
	"webpack.config.js", "rollup.config.js", "gulpfile.js", "gruntfile.js",
	"tsconfig.json", "jsconfig.json", "babel.config.js", ".babelrc",

	// 测试相关
	"jest.config.js", "karma.conf.js", ".mocharc.json",

	// 其他常见配置文件
	"dockerfile", ".dockerignore", "composer.json", "composer.lock",
	"Makefile", "CMakeLists.txt",
}

func WalkFilesInDir(dir string) ([]string, error) {
	files := make([]string, 0)
	if err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if info.IsDir() {
			return nil
		}
		if IsIgnoreFile(path) {
			return nil
		}
		files = append(files, path)
		return nil
	}); err != nil {
		return nil, err
	}
	return files, nil
}

func IsIgnoreFile(path string) bool {
	for _, ignoreFile := range ignoreFiles {
		if ignoreFile == filepath.Base(path) {
			return true
		}
	}
	return false
}

func ReadFile(filepath string) ([]byte, error) {
	return os.ReadFile(filepath)
}

// GetLocation 根据start,end按行获取文件位置，line是间隔行数
func GetLocation(path string, startPos int, endPos int, line int) string {
	content, err := os.ReadFile(path)
	if err != nil {
		return ""
	}

	lines := strings.Split(string(content), "\n")
	var startLine, endLine int
	currentPos := 0

	// 确定起始和结束行号
	for i, l := range lines {
		lineEnd := currentPos + len(l)
		if currentPos <= startPos && startPos <= lineEnd {
			startLine = i
		}
		if currentPos <= endPos && endPos <= lineEnd {
			endLine = i
		}
		currentPos += len(l) + 1 // +1 for newline character
	}

	// 计算上下文范围
	contextStart := startLine - line
	if contextStart < 0 {
		contextStart = 0
	}
	contextEnd := endLine + line
	if contextEnd >= len(lines) {
		contextEnd = len(lines) - 1
	}
	return strings.Join(lines[contextStart:contextEnd], "\n")
}

func GetContentLines(path string, startLine int, endLine int) string {
	content, err := os.ReadFile(path)
	if err != nil {
		return ""
	}

	lines := strings.Split(string(content), "\n")
	var result []string
	for i, l := range lines {
		if i >= startLine && i <= endLine {
			result = append(result, l)
		}
	}
	return strings.Join(result, "\n")
}

// 获取文件行数,快速获取
func GetFileLineCount(file string) int {
	f, err := os.Open(file)
	if err != nil {
		return 0
	}
	defer f.Close()

	buf := make([]byte, 32*1024)
	count := 0
	lineSep := []byte{'\n'}

	for {
		c, err := f.Read(buf)
		count += bytes.Count(buf[:c], lineSep)

		switch {
		case err == io.EOF:
			return count
		case err != nil:
			return count
		}
	}
}

// ListDir 递归列出目录结构并生成树形图
// dir: 要列出的目录路径
// maxLevel: 最大递归深度（0表示不限制）
func ListDir(dir string, maxLevel int) (string, error) {
	var builder strings.Builder
	err := listDirRecursive(dir, 0, true, &builder, []bool{}, maxLevel)
	if err != nil {
		return "", err
	}
	return builder.String(), nil
}

// listDirRecursive 递归生成目录树
// dir: 当前目录路径
// depth: 当前递归深度
// isLast: 是否是父目录的最后一项
// builder: 字符串构建器
// hasLast: 记录父目录的层级状态
// maxLevel: 允许的最大递归深度
func listDirRecursive(dir string, depth int, isLast bool, builder *strings.Builder, hasLast []bool, maxLevel int) error {
	if maxLevel != 0 && depth >= maxLevel {
		return nil
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}

	// 过滤忽略文件
	var validEntries []fs.DirEntry
	for _, entry := range entries {
		if !IsIgnoreFile(filepath.Join(dir, entry.Name())) {
			validEntries = append(validEntries, entry)
		}
	}

	for i, entry := range validEntries {
		// 绘制树形结构线
		for d := 0; d < depth; d++ {
			if hasLast[d] {
				builder.WriteString("    ")
			} else {
				builder.WriteString("│   ")
			}
		}

		// 判断是否是最后一项
		isLastEntry := i == len(validEntries)-1
		if isLastEntry {
			builder.WriteString("└── ")
		} else {
			builder.WriteString("├── ")
		}

		// 添加条目名称和类型和权限
		builder.WriteString(fmt.Sprintf("%s (%s)\n", entry.Name(), getSimpleType(dir, entry)))
		// 递归处理子目录（不超过最大深度时）
		if entry.IsDir() && (maxLevel <= 0 || depth < maxLevel) {
			newHasLast := append(hasLast, isLastEntry)
			err = listDirRecursive(
				filepath.Join(dir, entry.Name()),
				depth+1,
				isLastEntry,
				builder,
				newHasLast,
				maxLevel,
			)
			if err != nil {
				return err
			}
		}
	}
	return nil
}

// getSimpleType 简化文件类型显示
func getSimpleType(dir string, entry fs.DirEntry) string {
	if entry.IsDir() {
		return "dir"
	}
	fsPath := filepath.Join(dir, entry.Name())
	if entry.Type().IsRegular() {
		if isTextFile(fsPath) {
			return "file"
		} else {
			return "binary"
		}
	}
	return entry.Type().String()
}

func InitMcpClient(ctx context.Context, client *client.Client) error {
	err := client.Start(ctx)
	if err != nil {
		return err
	}
	_, err = client.Initialize(context.Background(), mcp.InitializeRequest{})
	if err != nil {
		return err
	}
	return err
}

func ListMcpTools(ctx context.Context, client *client.Client) (*mcp.ListToolsResult, error) {
	result, err := client.ListTools(ctx, mcp.ListToolsRequest{})
	if err != nil {
		return nil, err
	}
	return result, nil
}

func SaveHistory(history []map[string]string) error {
	// 转换为json再追加写入
	jsonBytes, err := json.Marshal(history)
	if err != nil {
		return err
	}
	// 追加写入文件
	filename := "history.jsonl"
	jsonBytes = append(jsonBytes, '\n')
	if _, err := os.Stat(filename); os.IsNotExist(err) {
		// 创建文件
		file, err := os.Create(filename)
		if err != nil {
			return err
		}
		defer file.Close()
		// 写入文件
		_, err = file.Write(jsonBytes)
		if err != nil {
			return err
		}
	} else {
		// 追加写入文件
		file, err := os.OpenFile(filename, os.O_APPEND|os.O_WRONLY, 0600)
		if err != nil {
			return err
		}
		defer file.Close()
		_, err = file.Write(jsonBytes)
		if err != nil {
			return err
		}
	}
	return nil
}

func LanguagePrompt(language string) string {
	var languagePrompt string
	if language == "zh" {
		languagePrompt = "Response in Chinese."
	} else {
		languagePrompt = "Response in English."
	}
	return languagePrompt
}

// IsTextFile 检查文件是否为文本文件
func IsTextFile(filename string) (bool, error) {
	file, err := os.Open(filename)
	if err != nil {
		return false, err
	}
	defer file.Close()

	buf := make([]byte, 512)
	n, err := file.Read(buf)
	if err != nil && err != io.EOF {
		return false, err
	}

	// 检查每个字节是否为非文本字符
	for i := 0; i < n; i++ {
		b := buf[i]
		if b <= 8 || b == 0x0B || b == 0x0C || (b >= 0x0E && b <= 0x1F) || b == 0x7F {
			return false, nil // 发现控制字符或NULL，视为二进制文件
		}
	}

	return true, nil // 未找到非文本字符，视为文本文件
}
