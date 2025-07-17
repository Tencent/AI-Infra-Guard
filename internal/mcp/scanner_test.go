package mcp

import (
	"context"
	"encoding/json"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/mcp"
	fileutil "github.com/projectdiscovery/utils/file"
	"github.com/remeh/sizedwaitgroup"
	"github.com/stretchr/testify/assert"
	"os"
	"path/filepath"
	"testing"
)

func TestScanner(t *testing.T) {

	aiModel := models.NewOpenAI(token, model, baseUrl)
	// 创建扫描器
	scanner := NewScanner(aiModel, gologger.NewLogger())
	// 注册插件
	ctx := context.Background()
	scanner.SetLanguage("zh")
	scanner.InputCodePath("/Users/python/Downloads/core_mcp_server-0.1.63/src/")
	results, err := scanner.ScanCode(ctx, false)
	assert.NoError(t, err)
	assert.NotEmpty(t, results)
	for _, issue := range results.Issues {
		t.Logf("issue: %v", issue)
	}
	for _, issue := range results.Report {
		t.Logf("report: %v", issue)
	}
}

func TestBatchScanner(t *testing.T) {

	scan := func(dir string, logFile string) (*McpResult, error) {
		aiModel := models.NewOpenAI(token, model, baseUrl)
		// 创建扫描器
		logger := gologger.NewLogger()
		writer2, err := os.OpenFile(logFile, os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0644)
		if err != nil {
			return nil, err
		}
		defer writer2.Close()
		logger.Logrus().SetOutput(writer2)
		scanner := NewScanner(aiModel, logger)
		// 注册插件
		ctx := context.Background()
		scanner.SetLanguage("zh")
		scanner.InputCodePath(dir)
		results, err := scanner.ScanCode(ctx, false)
		if err != nil {
			return nil, err
		}
		return results, nil
	}
	rootDir := "./test_data"
	entries, err := os.ReadDir(rootDir)
	assert.NoError(t, err)
	total := len(entries)
	gologger.Infof("scan %d targets", total)
	index := 0
	wg := sizedwaitgroup.New(10)
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		logFile := filepath.Join(rootDir, entry.Name()+".log")
		// 判断文件是否存在
		if fileutil.FileExists(logFile) {
			continue
		}
		wg.Add()
		index += 1
		gologger.Infof("scan %d/%d %s", index, total, entry.Name())
		go func(entry os.DirEntry) {
			defer wg.Done()
			filename := filepath.Join(rootDir, entry.Name())
			resultFile := filepath.Join(rootDir, entry.Name()+"_result.json")
			results, err := scan(filename, logFile)
			assert.NoError(t, err)
			if len(results.Issues) > 0 {
				data, err := json.Marshal(results)
				if err != nil {
					gologger.WithError(err).Errorf("json.Marshal failed")
					return
				}
				err = os.WriteFile(resultFile, data, 0644)
				assert.NoError(t, err)
			}
		}(entry)
	}
	wg.Wait()
}

func TestMcpTools(t *testing.T) {
	aiModel := models.NewOpenAI(token, model, baseUrl)
	// 创建扫描器
	scanner := NewScanner(aiModel, gologger.NewLogger())
	ctx := context.Background()
	r, err := scanner.InputSSELink(ctx, ".")
	assert.NoError(t, err)
	issues, err := scanner.ScanLink(ctx, r, false)
	assert.NoError(t, err)
	t.Log(issues)
}

func TestMcpTools2(t *testing.T) {
	aiModel := models.NewOpenAI(token, model, baseUrl)
	// 创建扫描器
	scanner := NewScanner(aiModel, gologger.NewLogger())
	ctx := context.Background()
	r, err := scanner.InputStreamLink(ctx, ".")
	assert.NoError(t, err)
	t.Log(r)
	tools, err := utils.ListMcpTools(ctx, scanner.client)
	assert.NoError(t, err)
	t.Log(tools)
	args := make(map[string]interface{})
	args["query"] = "abc"
	result, err := scanner.client.CallTool(ctx, mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Name:      "search",
			Arguments: args,
		},
	})
	assert.NoError(t, err)
	t.Log(result.Content[0])
}
