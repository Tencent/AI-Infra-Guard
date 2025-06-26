package utils

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/mcp"
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

func IsIgnoreFile(path string) bool {
	for _, ignoreFile := range ignoreFiles {
		if ignoreFile == filepath.Base(path) {
			return true
		}
	}
	return false
}

type Agent interface {
	GetHistory() []map[string]string
}

// ListDir 递归列出目录结构并生成树形图
// dir: 要列出的目录路径
// maxLevel: 最大递归深度（0表示不限制）
func ListDir(dir string, maxLevel int, exts string) (string, error) {
	var builder strings.Builder
	err := listDirRecursive(dir, 0, &builder, []bool{}, maxLevel, strings.Split(exts, ","))
	if err != nil {
		return "", err
	}
	return builder.String(), nil
}

// formatFileSize 格式化文件大小，返回带单位的字符串
func formatFileSize(size int64) string {
	if size < 1024 {
		return fmt.Sprintf("%dB", size)
	} else if size < 1024*1024 {
		return fmt.Sprintf("%.1fKB", float64(size)/1024)
	} else if size < 1024*1024*1024 {
		return fmt.Sprintf("%.1fMB", float64(size)/(1024*1024))
	} else {
		return fmt.Sprintf("%.1fGB", float64(size)/(1024*1024*1024))
	}
}

func listDirRecursive(dir string, depth int, builder *strings.Builder, hasLast []bool, maxLevel int, exts []string) error {
	if maxLevel > 0 && depth >= maxLevel {
		return nil
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return err
	}

	// 过滤忽略文件
	var validEntries []fs.DirEntry
	for _, entry := range entries {
		filename := filepath.Join(dir, entry.Name())
		if IsIgnoreFile(filename) {
			continue
		}
		if entry.IsDir() {
			validEntries = append(validEntries, entry)
			continue
		}
		if len(exts) > 0 {
			isSkip := true
			for _, ext := range exts {
				if strings.HasSuffix(entry.Name(), ext) {
					isSkip = false
					break
				}
			}
			if isSkip {
				continue
			}
		}
		validEntries = append(validEntries, entry)
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

		// 添加条目名称和类型和权限以及文件大小
		var sizeInfo string
		if !entry.IsDir() {
			// 获取文件信息
			entryPath := filepath.Join(dir, entry.Name())
			if fileInfo, err := os.Stat(entryPath); err == nil {
				sizeInfo = fmt.Sprintf(" [%s]", formatFileSize(fileInfo.Size()))
			}
		}
		builder.WriteString(fmt.Sprintf("%s (%s)%s\n", entry.Name(), getSimpleType(dir, entry), sizeInfo))

		// 递归处理子目录（不超过最大深度时）
		if entry.IsDir() && (maxLevel <= 0 || depth < maxLevel) {
			newHasLast := append(hasLast, isLastEntry)
			err = listDirRecursive(
				filepath.Join(dir, entry.Name()),
				depth+1,
				builder,
				newHasLast,
				maxLevel,
				exts,
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
		if IsTextFile(fsPath) {
			return "file"
		} else {
			return "binary"
		}
	}
	return entry.Type().String()
}

func InitMcpClient(ctx context.Context, client *client.Client) (*mcp.InitializeResult, error) {
	err := client.Start(ctx)
	if err != nil {
		return nil, err
	}
	r, err := client.Initialize(context.Background(), mcp.InitializeRequest{})
	if err != nil {
		return nil, err
	}
	return r, err
}

func ListMcpTools(ctx context.Context, client *client.Client) (*mcp.ListToolsResult, error) {
	result, err := client.ListTools(ctx, mcp.ListToolsRequest{})
	if err != nil {
		return nil, err
	}
	client.CallTool(ctx, mcp.CallToolRequest{})
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
func IsTextFile(filename string) bool {
	file, err := os.Open(filename)
	if err != nil {
		return false
	}
	defer file.Close()

	buf := make([]byte, 512)
	n, err := file.Read(buf)
	if err != nil && err != io.EOF {
		return false
	}

	// 检查每个字节是否为非文本字符
	for i := 0; i < n; i++ {
		b := buf[i]
		if b <= 8 || b == 0x0B || b == 0x0C || (b >= 0x0E && b <= 0x1F) || b == 0x7F {
			return false // 发现控制字符或NULL，视为二进制文件
		}
	}

	return true // 未找到非文本字符，视为文本文件
}

// Grep 在文件或目录中搜索特定模式并返回匹配行及其上下文
func Grep(path string, pattern string, contextLines int) (string, error) {
	// 检查路径是文件还是目录
	fileInfo, err := os.Stat(path)
	if err != nil {
		return "", err
	}

	// 支持多个表达式，通过逗号分隔
	patterns := strings.Split(pattern, ",")
	if len(patterns) == 0 {
		return "", fmt.Errorf("未提供搜索模式")
	}

	// 编译所有正则表达式
	regexps := make([]*regexp.Regexp, 0, len(patterns))
	for _, p := range patterns {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		re, err := regexp.Compile(p)
		if err != nil {
			return "", fmt.Errorf("正则表达式无效 '%s': %v", p, err)
		}
		regexps = append(regexps, re)
	}

	if len(regexps) == 0 {
		return "", fmt.Errorf("没有有效的正则表达式")
	}

	var results []string
	if fileInfo.IsDir() {
		// 如果是目录，遍历目录中的所有文件
		patternStr := strings.Join(patterns, "', '")
		results = append(results, fmt.Sprintf("在目录 '%s' 中搜索模式 ['%s']:\n", path, patternStr))
		err = grepDirectoryMulti(path, regexps, contextLines, &results)
		if err != nil {
			return "", err
		}
	} else {
		// 如果是文件，直接搜索文件
		fileResults, err := grepFileMulti(path, regexps, contextLines)
		if err != nil {
			return "", err
		}
		if fileResults != "" {
			results = append(results, fmt.Sprintf("文件: %s\n", path))
			results = append(results, fileResults)
		}
	}

	if len(results) == 0 || (len(results) == 1 && strings.HasPrefix(results[0], "在目录")) {
		patternStr := strings.Join(patterns, "', '")
		return fmt.Sprintf("未找到匹配模式 ['%s'] 的内容", patternStr), nil
	}

	return strings.Join(results, "\n"), nil
}

// grepDirectoryMulti 在目录中搜索多个模式
func grepDirectoryMulti(dirPath string, regexps []*regexp.Regexp, contextLines int, results *[]string) error {
	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return err
	}

	foundMatches := false
	for _, entry := range entries {
		entryPath := fmt.Sprintf("%s/%s", dirPath, entry.Name())

		// 跳过隐藏文件和目录
		if strings.HasPrefix(entry.Name(), ".") {
			continue
		}

		if entry.IsDir() {
			// 递归搜索子目录
			err := grepDirectoryMulti(entryPath, regexps, contextLines, results)
			if err != nil {
				// 只记录错误，继续处理其他文件
				*results = append(*results, fmt.Sprintf("搜索目录 %s 时出错: %v", entryPath, err))
			}
		} else {
			// 只处理常见文本文件类型
			if IsTextFile(entryPath) {
				fileResults, err := grepFileMulti(entryPath, regexps, contextLines)
				if err != nil {
					// 只记录错误，继续处理其他文件
					continue
				}

				if fileResults != "" {
					if !foundMatches {
						foundMatches = true
					}
					*results = append(*results, fmt.Sprintf("\n文件: %s", entryPath))
					*results = append(*results, fileResults)
				}
			}
		}
	}

	return nil
}

// grepFileMulti 在单个文件中搜索多个模式，支持跨行匹配
func grepFileMulti(filename string, regexps []*regexp.Regexp, contextLines int) (string, error) {
	// 读取整个文件内容
	content, err := os.ReadFile(filename)
	if err != nil {
		return "", err
	}

	fileContent := string(content)

	// 将文件内容按行分割，保留行信息用于显示上下文
	lines := strings.Split(fileContent, "\n")

	var results []string
	matchFound := false
	processedRanges := make(map[string]bool) // 记录已处理的匹配范围，避免重复

	// 对每个正则表达式进行匹配
	for _, re := range regexps {
		// 在整个文件内容中查找所有匹配
		matches := re.FindAllStringIndex(fileContent, -1)

		for _, match := range matches {
			startPos := match[0]
			endPos := match[1]

			// 生成唯一标识符避免重复处理相同位置的匹配
			rangeKey := fmt.Sprintf("%d-%d", startPos, endPos)
			if processedRanges[rangeKey] {
				continue
			}
			processedRanges[rangeKey] = true

			matchFound = true

			// 计算匹配开始和结束的行号
			startLineNum := strings.Count(fileContent[:startPos], "\n")
			endLineNum := strings.Count(fileContent[:endPos], "\n")

			// 计算显示上下文的行范围
			contextStart := startLineNum - contextLines
			if contextStart < 0 {
				contextStart = 0
			}
			contextEnd := endLineNum + contextLines
			if contextEnd >= len(lines) {
				contextEnd = len(lines) - 1
			}

			// 添加匹配信息
			matchedContent := fileContent[startPos:endPos]
			// 转义显示特殊字符
			displayContent := strings.ReplaceAll(matchedContent, "\n", "\\n")
			displayContent = strings.ReplaceAll(displayContent, "\t", "\\t")
			if len(displayContent) > 100 {
				displayContent = displayContent[:100] + "..."
			}

			results = append(results, fmt.Sprintf("=== 匹配范围: 行 %d-%d ===", startLineNum+1, endLineNum+1))
			results = append(results, fmt.Sprintf("匹配内容: %s", displayContent))
			results = append(results, "")

			// 显示上下文
			for i := contextStart; i <= contextEnd; i++ {
				if i >= len(lines) {
					break
				}

				prefix := "  "
				// 标记匹配行
				if i >= startLineNum && i <= endLineNum {
					prefix = ">"
				}
				results = append(results, fmt.Sprintf("%s %d: %s", prefix, i+1, lines[i]))
			}
			results = append(results, "")
		}
	}

	if !matchFound {
		return "", nil
	}

	return strings.Join(results, "\n"), nil
}

// ReadFileChunk 读取文件的一部分
// 参数：filename 文件名，startLine 开始行号，endLines 结束行号，maxBytes 最大字节数
// 返回值：string: 文件内容，error: 错误信息
func ReadFileChunk(filename string, startLine int, endLines int, maxBytes int) (string, error) {
	file, err := os.Open(filename)
	if err != nil {
		return "", err
	}
	defer file.Close()

	totalLines := 0
	// 读取指定的行数或字节数
	var sb strings.Builder
	bytesRead := 0
	linesRead := 0
	currentLine := 0

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		currentLine += 1
		totalLines += 1
		if ((startLine <= 1 && endLines <= 1) || (currentLine >= startLine && currentLine <= endLines)) && bytesRead < maxBytes {
			line := scanner.Text()
			sb.WriteString(line + "\n")
			bytesRead += len(line + "\n")
			linesRead = currentLine
		}
	}

	if err := scanner.Err(); err != nil {
		return "", err
	}

	result := sb.String()
	if len(result) > 0 {
		if linesRead < totalLines {
			if startLine == 0 && endLines == 0 {
				startLine = 0
				endLines = linesRead
			}
			result += fmt.Sprintf("\n----\n (文件还有更多内容,共 %d 行,准备读取 %d-%d,行当前已读取到第 %d 行，约 %d 字节) 请自行判断是否读取接下来的行\n",
				totalLines, startLine, endLines, linesRead, bytesRead)
		} else {
			result += fmt.Sprintf("\n----\n (文件已读取完毕，最后一行为第 %d 行)\n", linesRead)
		}
	}
	return result, nil
}
