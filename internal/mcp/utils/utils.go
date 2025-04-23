package utils

import (
	"bytes"
	"context"
	"fmt"
	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/mcp"
	"io"
	"os"
	"path/filepath"
	"strings"
)

var ignoreFiles = []string{
	// 系统文件
	".DS_Store", "Thumbs.db",

	// 版本控制相关
	".gitignore", ".gitattributes", ".gitmodules", ".gitkeep",

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

func ListDir(dir string) (string, error) {
	files, err := os.ReadDir(dir)
	if err != nil {
		return "", err
	}
	var userPrompt string
	for _, file := range files {
		userPrompt += fmt.Sprintf("- %s (%s)\n", file.Name(), file.Type())
	}
	return userPrompt, nil
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
