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

// SkillTask performs security auditing of Agent Skill projects.
// It mirrors the structure of McpTask but is scoped to code-mode scanning only.
type SkillTask struct {
	Server string
}

func (s *SkillTask) GetName() string {
	return TaskTypeSkillScan
}

func (s *SkillTask) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	type ScanSkillRequest struct {
		Content string `json:"-"`
		Model   struct {
			Model   string `json:"model"`
			Token   string `json:"token"`
			BaseUrl string `json:"base_url"`
		} `json:"model"`
	}

	var params ScanSkillRequest
	if err := json.Unmarshal(request.Params, &params); err != nil {
		return err
	}
	params.Content = request.Content
	files := request.Attachments

	// skill-scan only supports code mode: either uploaded files or a github.com URL
	transport := "code"
	if len(files) > 0 || strings.Contains(request.Content, "github.com") {
		transport = "code"
	} else {
		transport = "code"
	}

	language := request.Language
	if language == "" {
		language = "zh"
	}

	var folder string
	if transport == "code" {
		tempDir := "uploads"
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			gologger.Errorf("%s: %v", "createTempDir", err)
			return err
		}
		if len(files) > 0 {
			for _, file := range files {
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
				err := utils.DownloadFile(s.Server, request.SessionId, file, fileName)
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

		if info, err := os.Stat(folder); os.IsNotExist(err) || !info.IsDir() {
			return fmt.Errorf("folder does not exist or is not a directory: %s", folder)
		}
	}

	var argv []string = make([]string, 0)
	argv = append(argv, "run", "--no-project", "main.py")
	argv = append(argv, "--model", params.Model.Model)
	argv = append(argv, "--base_url", params.Model.BaseUrl)
	argv = append(argv, "--api_key", params.Model.Token)
	argv = append(argv, "--prompt", params.Content)
	argv = append(argv, "--debug")
	argv = append(argv, "--language", language)

	argv = append(argv, "--repo", folder)

	var taskTitles []string
	if language == "en" {
		taskTitles = []string{
			"Info Collection",
			"Code Audit",
			"Vulnerability Review",
		}
	} else {
		taskTitles = []string{
			"信息收集",
			"代码审计",
			"漏洞整理",
		}
	}

	var tasks []SubTask
	for i, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, strconv.Itoa(i+1)))
	}
	callbacks.PlanUpdateCallback(tasks)
	config := CmdConfig{StatusId: ""}
	skillScanDir, err := utils.ResolveSkillScanDir()
	if err != nil {
		return fmt.Errorf("resolve skill-scan directory: %v", err)
	}
	uvBin, err := utils.ResolveUvBin()
	if err != nil {
		return fmt.Errorf("resolve uv binary: %v", err)
	}
	err = utils.RunCmdWithContext(ctx, skillScanDir, uvBin, argv, func(line string) {
		ParseStdoutLine(s.Server, skillScanDir, tasks, line, callbacks, &config, false)
	})
	return err
}
