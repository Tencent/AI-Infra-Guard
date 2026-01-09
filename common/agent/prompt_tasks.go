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

const (
	DIR  = "/app/AIG-PromptSecurity"
	NAME = "/usr/local/bin/uv"
)

type ModelRedteamReport struct {
	Server string
}

type ModelParams struct {
	BaseUrl string `json:"base_url"`
	Token   string `json:"token"`
	Model   string `json:"model"`
	Limit   int    `json:"limit"`
}

func getDefaultEvalModel() (*ModelParams, error) {
	baseUrl := os.Getenv("eval_base_url")
	token := os.Getenv("eval_api_key")
	model := os.Getenv("eval_model")
	if baseUrl == "" || token == "" || model == "" {
		return nil, fmt.Errorf("env not set")
	}
	return &ModelParams{
		BaseUrl: baseUrl,
		Token:   token,
		Model:   model,
		Limit:   1000,
	}, nil
}

func (m *ModelRedteamReport) GetName() string {
	return TaskTypeModelRedteamReport
}

func (m *ModelRedteamReport) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	type params struct {
		Model     []ModelParams `json:"model"`
		EvalModel ModelParams   `json:"eval_model"`
		Datasets  struct {
			DataFile     []string `json:"dataFile"`
			NumPrompts   int      `json:"numPrompts"`
			RandomSeed   int      `json:"randomSeed"`
			PromptColumn string   `json:"promptColumn"`
		} `json:"dataset"`
		Prompt     string   `json:"prompt"`
		Techniques []string `json:"techniques"`
	}
	var param params
	if err := json.Unmarshal(request.Params, &param); err != nil {
		return err
	}
	param.Prompt = request.Content
	if param.Datasets.RandomSeed == 0 {
		param.Datasets.RandomSeed = 42
	}
	if param.Datasets.NumPrompts == 0 {
		param.Datasets.NumPrompts = -1
	}
	if request.Language == "" {
		request.Language = "zh"
	}
	var argv []string = make([]string, 0)
	argv = append(argv, "run", "cli_run.py")
	argv = append(argv, "--async_mode")

	for _, model := range param.Model {
		if model.Limit == 0 {
			model.Limit = 1000
		}
		argv = append(argv, "--model", model.Model)
		argv = append(argv, "--base_url", model.BaseUrl)
		argv = append(argv, "--api_key", model.Token)
		argv = append(argv, "--max_concurrent", fmt.Sprintf("%d", model.Limit))
	}

	evalParams, err := getDefaultEvalModel()
	if err == nil {
		argv = append(argv, "--evaluate_model", evalParams.Model)
		argv = append(argv, "--eval_base_url", evalParams.BaseUrl)
		argv = append(argv, "--eval_api_key", evalParams.Token)
	} else {
		argv = append(argv, "--evaluate_model", param.EvalModel.Model)
		argv = append(argv, "--eval_base_url", param.EvalModel.BaseUrl)
		argv = append(argv, "--eval_api_key", param.EvalModel.Token)
	}

	argv = append(argv, "--techniques", "Raw")
	argv = append(argv, "--choice", "serial")
	argv = append(argv, "--lang", request.Language)

	if (len(param.Datasets.DataFile) > 0 || len(request.Attachments) > 0) && param.Prompt != "" {
		return errors.New("prompt 和 data 不能同时使用")
	}

	if len(param.Datasets.DataFile) == 0 && len(request.Attachments) == 0 && param.Prompt == "" {
		return errors.New("prompt 和 data 不能同时为空")
	}

	argv = append(argv, "--scenarios")
	if len(param.Prompt) > 0 {
		argv = append(argv, fmt.Sprintf("Custom:prompt=%s", param.Prompt))
	}
	if len(request.Attachments) > 0 {
		tempDir := "uploads"
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			gologger.Errorf("创建临时目录失败: %v", err)
			return err
		}
		fileName := request.Attachments[0]
		gologger.Infof("开始下载文件: %s", fileName)
		fileName2 := filepath.Join(tempDir, fmt.Sprintf("tmp-%d%s", time.Now().UnixMicro(), filepath.Ext(fileName)))
		fileName2, _ = filepath.Abs(fileName2)
		scenarios := fmt.Sprintf("MultiDataset:dataset_file=%s,num_prompts=%d,random_seed=%d", fileName2, param.Datasets.NumPrompts, param.Datasets.RandomSeed)
		if param.Datasets.PromptColumn != "" {
			scenarios += fmt.Sprintf(",prompt_column=%s", param.Datasets.PromptColumn)
		}
		err := utils.DownloadFile(m.Server, request.SessionId, fileName, fileName2)
		if err != nil {
			gologger.Errorf("下载文件失败: %v", err)
			return err
		}
		gologger.Infof("文件下载成功: %s", fileName2)
		argv = append(argv, scenarios)
	}

	for _, dataName := range param.Datasets.DataFile {
		tempDir := os.TempDir()
		fileName := filepath.Join(tempDir, fmt.Sprintf("%s-%d.json", dataName, time.Now().UnixMicro()))
		fileName = strings.Replace(fileName, " ", "_", -1)
		data, err := utils.GetEvaluationsDetail(m.Server, dataName)
		if err != nil {
			gologger.Errorf("获取评测数据失败: %v", err)
			return err
		}
		err = os.WriteFile(fileName, data, 0644)
		if err != nil {
			gologger.Errorf("写入文件失败: %v", err)
			return err
		}
		scenarios := fmt.Sprintf("MultiDataset:dataset_file=%s,num_prompts=%d,random_seed=%d", fileName, param.Datasets.NumPrompts, param.Datasets.RandomSeed)
		argv = append(argv, scenarios)
	}
	argv = append(argv, "--choice", "parallel")

	argv = append(argv, "--techniques")
	if len(param.Techniques) > 0 {
		argv = append(argv, param.Techniques...)
	} else {
		argv = append(argv, "Raw")
	}

	taskTitles := []string{
		"初始化越狱环境",
		"执行模型安全评估",
		"生成模型安全报告",
	}
	taskTitlesEn := []string{
		"Pre-Jailbreak Parameter Parsing",
		"Jailbreaking",
		"Generating report",
	}

	if strings.ToLower(request.Language) == "zh" || strings.ToLower(request.Language) == "zh_CN" {
	} else {
		// 英文
		taskTitles = taskTitlesEn
	}
	var tasks []SubTask
	for i, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, strconv.Itoa(i+1)))
	}
	callbacks.PlanUpdateCallback(tasks)
	config := CmdConfig{StatusId: ""}
	err = utils.RunCmd(DIR, NAME, argv, func(line string) {
		ParseStdoutLine(m.Server, DIR, tasks, line, callbacks, &config, true)
	})
	return err
}
