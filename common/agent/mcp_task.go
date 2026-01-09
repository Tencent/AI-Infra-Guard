package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

const McpDir = "/app/mcp-scan"

type McpTask struct {
	Server string
}

func (m *McpTask) GetName() string {
	return TaskTypeMcpScan
}

func (m *McpTask) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	type ScanMcpRequest struct {
		Content string `json:"-"`
		Model   struct {
			Model   string `json:"model"`
			Token   string `json:"token"`
			BaseUrl string `json:"base_url"`
		} `json:"model"`
		Headers map[string]string `json:"headers"`
	}

	var params ScanMcpRequest
	if err := json.Unmarshal(request.Params, &params); err != nil {
		return err
	}
	params.Content = request.Content
	files := request.Attachments
	transport := "code" // code or url
	if len(files) > 0 || strings.Contains(request.Content, "github.com") {
		transport = "code"
	} else {
		transport = "url"
	}
	language := request.Language
	if language == "" {
		language = "zh"
	}

	var folder string
	var serverUrl string
	if transport == "code" {
		// 创建临时目录用于存储上传的文件
		tempDir := "uploads"
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			gologger.Errorf("%s: %v", "createTempDir", err)
			return err
		}
		if len(files) > 0 {
			// 远程下载
			for _, file := range files {
				// 下载文件
				ext := ""
				supports := []string{".zip", ".tar.gz", ".tgz", ".whl"}
				for _, support := range supports {
					if strings.HasSuffix(file, support) {
						ext = support
						break
					}
				}
				if ext == "" {
					gologger.Errorln("Unsupported file type", strings.Join(supports, ","))
					continue
				}

				fileName := filepath.Join(tempDir, fmt.Sprintf("tmp-%d%s", time.Now().UnixMicro(), ext))
				err := utils.DownloadFile(m.Server, request.SessionId, file, fileName)
				if err != nil {
					return fmt.Errorf("download failed: %v", err)
				}
				extractPath, _ := filepath.Abs(filepath.Join(tempDir, fmt.Sprintf("tmp-%d", time.Now().UnixMicro())))
				switch ext {
				case ".zip", ".whl":
					err = utils.ExtractZipFile(fileName, extractPath)
				case ".tgz", ".tar.gz":
					err = utils.ExtractTGZ(fileName, extractPath)
				default:
					return errors.New("Unsupported file type: " + strings.Join(supports, ","))
				}
				if err != nil {
					return errors.New(fmt.Sprintf("extract failed: %v", err))
				}
				folder = extractPath
			}
		} else {
			extractPath, _ := filepath.Abs(filepath.Join(tempDir, fmt.Sprintf("tmp-%d", time.Now().UnixMicro())))
			err := utils.GitClone(params.Content, extractPath, 10*time.Minute)
			if err != nil {
				return fmt.Errorf("clone failed: %v", err)
			}
			folder = extractPath
		}

		// 判断文件夹是否存在
		if info, err := os.Stat(folder); os.IsNotExist(err) || !info.IsDir() {
			return fmt.Errorf("folder does not exist or is not a directory: %s", folder)
		}
	} else if transport == "url" {
		serverUrl = params.Content
	}

	var argv []string = make([]string, 0)
	argv = append(argv, "run", "main.py")
	argv = append(argv, "--model", params.Model.Model)
	argv = append(argv, "--base_url", params.Model.BaseUrl)
	argv = append(argv, "--api_key", params.Model.Token)
	argv = append(argv, "--prompt", params.Content)
	argv = append(argv, "--debug")
	argv = append(argv, "--language", language)
	if params.Headers != nil {
		for k, v := range params.Headers {
			argv = append(argv, "--header", fmt.Sprintf("%s:%s", k, v))
		}
	}

	var taskTitles []string
	if transport == "code" {
		argv = append(argv, "--repo", folder)
		taskTitles = []string{
			"Info Collection",
			"Code Audit",
			"Vulnerability Review",
		}
	} else if transport == "url" {
		argv = append(argv, "--server_url", serverUrl)
		taskTitles = []string{
			"Info Collection",
			"Malicious Testing",
			"Vulnerability Testing",
			"Vulnerability Review",
		}
	}

	var tasks []SubTask
	//taskTitles := []string{
	//	"信息收集",
	//	"代码审计",
	//	"漏洞整理",
	//}

	for i, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, strconv.Itoa(i+1)))
	}
	callbacks.PlanUpdateCallback(tasks)
	config := CmdConfig{StatusId: ""}

	err := utils.RunCmd(McpDir, NAME, argv, func(line string) {
		ParseStdoutLine(m.Server, McpDir, tasks, line, callbacks, &config, false)
	})
	return err
}
