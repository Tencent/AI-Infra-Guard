package agent

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"

	"github.com/Tencent/AI-Infra-Guard/common/runner"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/google/uuid"
)

// ResultCallback 任务结果回调函数类型
type ResultCallback func(result map[string]interface{})

// ActionLogCallback 插件日志回调函数类型
type ActionLogCallback func(actionId, tool, planStepId, actionLog string)

// ToolUsedCallback 插件工作状态回调函数类型
type ToolUsedCallback func(planStepId, statusId, description string, tools []Tool)

// NewPlanStepCallback 新建执行步骤回调函数类型
type NewPlanStepCallback func(stepId, title string)

// StatusUpdateCallback 更新步骤状态回调函数类型
type StatusUpdateCallback func(planStepId, statusId, agentStatus, brief, description string)

// PlanUpdateCallback 更新任务计划回调函数类型
type PlanUpdateCallback func(tasks []SubTask)

// TaskCallbacks 任务回调函数集合
type TaskCallbacks struct {
	ResultCallback           ResultCallback       // 任务结果回调
	ToolUseLogCallback       ActionLogCallback    // 插件日志回调
	ToolUsedCallback         ToolUsedCallback     // 插件状态回调
	NewPlanStepCallback      NewPlanStepCallback  // 新建执行步骤回调
	StepStatusUpdateCallback StatusUpdateCallback // 更新步骤状态回调
	PlanUpdateCallback       PlanUpdateCallback   // 更新任务计划回调
}

type TaskInterface interface {
	GetName() string
	Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error
}

type TestDemoAgent struct{}

func (t *TestDemoAgent) GetName() string {
	return TaskTypeTestDemo
}

func (t *TestDemoAgent) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	//0. 发送初始任务计划
	taskTitles := []string{
		"测试任务",
	}
	var tasks []SubTask
	for _, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0))
	}
	callbacks.PlanUpdateCallback(tasks)

	//1. 创建新的执行步骤
	step01 := uuid.New().String()
	callbacks.NewPlanStepCallback(step01, "环境检测和准备")

	//2. 发送步骤运行状态
	statusId := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step01, statusId, AgentStatusRunning, "A.I.G正在工作", "开始扫描AI基础设施")

	//3. 调用插件
	toolId := uuid.New().String()
	callbacks.ToolUsedCallback(step01, statusId, "开始AI基础设施扫描",
		[]Tool{CreateTool(toolId, "ai_scanner", ToolStatusDoing, "正在启动AI扫描器", "扫描", "目标系统", "")})

	//4. 发送插件执行日志
	callbacks.ToolUseLogCallback(toolId, "ai_scanner", step01, "正在初始化扫描模块... 显示插件日志")

	//5. 发送插件完成状态
	completedTool := CreateTool(toolId, "ai_scanner", ToolStatusDone, "AI扫描器已完成", "扫描", "目标系统", "发现3个高危漏洞")
	callbacks.ToolUsedCallback(step01, statusId, "扫描完成", []Tool{completedTool})

	//6. 发送步骤完成状态
	callbacks.StepStatusUpdateCallback(step01, statusId, AgentStatusCompleted, "A.I.G完成工资", "完成扫描AI基础设施")

	//7. 更新任务计划 - 完成第一个子任务，开始下一个
	tasks[0].Status = SubTaskStatusDone
	callbacks.PlanUpdateCallback(tasks)

	//8. 发送任务最终结果
	result := map[string]any{
		"Brief":       "AI基础设施扫描完成",
		"Description": "扫描发现了3个高危漏洞：CVE-2024-001, CVE-2024-002, CVE-2024-003",
	}
	callbacks.ResultCallback(result)
	return nil
}

// ScanRequest 扫描请求结构
type ScanRequest struct {
	Target  []string          `json:"-"`
	Headers map[string]string `json:"headers"`
	Timeout int               `json:"timeout"`
}

type AIInfraScanAgent struct{}

func (t *AIInfraScanAgent) GetName() string {
	return TaskTypeAIInfraScan
}

func (t *AIInfraScanAgent) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	// 解析扫描请求
	var reqScan ScanRequest
	if err := json.Unmarshal(request.Params, &reqScan); err != nil {
		return err
	}
	targets := strings.Split(strings.TrimSpace(request.Content), "\n")
	reqScan.Target = targets
	if reqScan.Timeout == 0 {
		reqScan.Timeout = 30
	}

	//0. 发送初始任务计划
	taskTitles := []string{
		"初始化扫描环境",
		"执行AI基础设施扫描",
		"生成扫描报告",
	}
	var tasks []SubTask
	for _, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0))
	}
	callbacks.PlanUpdateCallback(tasks)

	//1. 创建新的执行步骤 - 初始化
	step01 := uuid.New().String()
	callbacks.NewPlanStepCallback(step01, "初始化扫描环境")

	//2. 发送步骤运行状态
	statusId01 := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusRunning, "A.I.G正在工作", "开始初始化AI基础设施扫描环境")

	//3. 初始化扫描器
	toolId01 := uuid.New().String()
	callbacks.ToolUsedCallback(step01, statusId01, "初始化扫描器",
		[]Tool{CreateTool(toolId01, "scanner_init", ToolStatusDoing, "正在初始化扫描器", "初始化", "扫描配置", "")})

	callbacks.ToolUseLogCallback(toolId01, "scanner_init", step01, "正在配置扫描参数...")

	// 深拷贝options
	opts := &options.Options{
		TimeOut:      reqScan.Timeout,
		RateLimit:    200,
		FPTemplates:  "data/fingerprints",
		AdvTemplates: "data/vuln",
		WebServer:    false,
		Target:       reqScan.Target,
	}

	// 配置请求头
	headers := make([]string, 0)
	for k, v := range reqScan.Headers {
		headers = append(headers, k+":"+v)
	}
	opts.Headers = headers

	callbacks.ToolUseLogCallback(toolId01, "scanner_init", step01, "扫描目标配置完成，目标数量: "+strconv.Itoa(len(reqScan.Target)))

	// 结果收集
	scanResults := make([]runner.CallbackScanResult, 0)
	mu := sync.Mutex{}
	step02 := uuid.New().String()
	statusId02 := uuid.New().String()
	processFunc := func(data interface{}) {
		mu.Lock()
		defer mu.Unlock()
		switch v := data.(type) {
		case runner.CallbackScanResult:
			scanResults = append(scanResults, v)
			callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusRunning, "发现结果", fmt.Sprintf("URL:%s 状态码:%d 标题:%s web应用:%s", v.TargetURL, v.StatusCode, v.Title, v.Fingerprint))
			if len(v.Vulnerabilities) > 0 {
				for _, vuln := range v.Vulnerabilities {
					callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusRunning, "发现漏洞", fmt.Sprintf("CVE:%s\n描述:%s\n详情:%s", vuln.CVEName, vuln.Summary, vuln.Details))
				}
			}
		case runner.CallbackProcessInfo:
		case runner.CallbackReportInfo:
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	opts.SetCallback(processFunc)

	//4. 完成初始化
	completedTool01 := CreateTool(toolId01, "scanner_init", ToolStatusDone, "扫描器初始化完成", "初始化", "扫描配置", "配置成功")
	callbacks.ToolUsedCallback(step01, statusId01, "初始化完成", []Tool{completedTool01})
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, "A.I.G完成工作", "扫描环境初始化完成")

	// 更新任务计划
	tasks[0].Status = SubTaskStatusDone
	tasks[1].Status = SubTaskStatusDoing
	tasks[1].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//5. 创建runner并执行扫描
	callbacks.NewPlanStepCallback(step02, "执行AI基础设施扫描")

	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusRunning, "A.I.G正在工作", "正在创建扫描器实例...")

	toolId02 := uuid.New().String()
	callbacks.ToolUsedCallback(step02, statusId02, "执行扫描",
		[]Tool{CreateTool(toolId02, "ai_scanner", ToolStatusDoing, "正在执行AI基础设施扫描", "扫描", "目标系统", "")})
	callbacks.ToolUseLogCallback(toolId02, "ai_scanner", step02, "正在创建扫描器实例...")

	r, err := runner.New(opts) // 创建runner
	if err != nil {
		return err
	}
	defer r.Close() // 关闭runner

	callbacks.ToolUseLogCallback(toolId02, "ai_scanner", step02, "扫描器创建成功，开始执行枚举...")

	// 执行枚举
	r.RunEnumeration()

	callbacks.ToolUseLogCallback(toolId02, "ai_scanner", step02, "扫描执行完成")

	//6. 完成扫描
	completedTool02 := CreateTool(toolId02, "ai_scanner", ToolStatusDone, "AI基础设施扫描完成", "扫描", "目标系统",
		"扫描结果: "+strconv.Itoa(len(scanResults))+"条")
	callbacks.ToolUsedCallback(step02, statusId02, "扫描完成", []Tool{completedTool02})
	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusCompleted, "A.I.G完成工作", "AI基础设施扫描任务完成")

	// 更新任务计划
	tasks[1].Status = SubTaskStatusDone
	tasks[2].Status = SubTaskStatusDoing
	tasks[2].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//7. 生成最终报告
	step03 := uuid.New().String()
	callbacks.NewPlanStepCallback(step03, "生成扫描报告")

	statusId03 := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step03, statusId03, AgentStatusRunning, "A.I.G正在工作", "开始生成扫描报告")

	toolId03 := uuid.New().String()
	callbacks.ToolUsedCallback(step03, statusId03, "生成报告",
		[]Tool{CreateTool(toolId03, "report_generator", ToolStatusDoing, "正在生成扫描报告", "报告", "扫描结果", "")})

	//8. 发送任务最终结果
	result := map[string]interface{}{
		"total":   len(scanResults),
		"results": scanResults,
	}
	// 最终更新任务计划
	tasks[2].Status = SubTaskStatusDone
	callbacks.PlanUpdateCallback(tasks)
	callbacks.ResultCallback(result)
	return nil
}

type ScanMcpRequest struct {
	Content string `json:"-"`
	Model   struct {
		Model   string `json:"model"`
		Token   string `json:"token"`
		BaseUrl string `json:"base_url"`
	} `json:"model"`
	Language string `json:"language"`
}

type McpScanAgent struct {
}

func (m *McpScanAgent) GetName() string {
	return TaskTypeMcpScan
}

func (m *McpScanAgent) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
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
	//0. 发送初始任务计划
	taskTitles := []string{
		"初始化MCP扫描环境",
		"执行MCP安全扫描",
	}
	var tasks []SubTask
	for _, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0))
	}
	callbacks.PlanUpdateCallback(tasks)

	//1. 创建新的执行步骤 - 初始化
	step01 := uuid.New().String()
	callbacks.NewPlanStepCallback(step01, "初始化MCP扫描环境")

	//2. 发送步骤运行状态
	statusId01 := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusRunning, "A.I.G正在工作", "开始初始化MCP安全扫描环境")

	//3. 初始化扫描器
	toolId01 := uuid.New().String()
	callbacks.ToolUsedCallback(step01, statusId01, "初始化MCP扫描器",
		[]Tool{CreateTool(toolId01, "mcp_scanner_init", ToolStatusDoing, "正在初始化MCP扫描器", "初始化", "扫描配置", "")})

	callbacks.ToolUseLogCallback(toolId01, "mcp_scanner_init", step01, "正在配置MCP扫描参数...")

	writer1 := bytes.Buffer{}
	logger := gologger.NewLogger()
	logger.Logrus().SetOutput(&writer1)

	// 结果收集
	mu := sync.Mutex{}

	step02 := uuid.New().String()
	statusId02 := uuid.New().String()

	readMe := ""

	var moduleStatusId string
	var moduleToolId string

	processFunc := func(data interface{}) {
		mu.Lock()
		defer mu.Unlock()
		switch v := data.(type) {
		case mcp.McpModuleStart:
			moduleStatusId = uuid.New().String()
			moduleToolId = uuid.New().String()
			callbacks.StepStatusUpdateCallback(step02, moduleStatusId, AgentStatusCompleted, "MCP安全插件扫描", "开始MCP安全扫描:"+v.ModuleName)
			callbacks.ToolUsedCallback(step02, moduleStatusId, "开始扫描MCP安全扫描",
				[]Tool{CreateTool(moduleToolId, v.ModuleName, ToolStatusDoing, "开始扫描MCP安全扫描", "开始扫描", v.ModuleName, "")})
		case mcp.McpModuleEnd:
			callbacks.ToolUsedCallback(step02, moduleStatusId, "MCP安全扫描完成",
				[]Tool{CreateTool(moduleToolId, v.ModuleName, ToolStatusDone, "MCP安全扫描完成", "扫描完成", v.ModuleName, "")})
		case mcp.McpCallbackProcessing:
		case mcp.McpCallbackReadMe:
			readMe = v.Content
		case mcp.Issue:
			callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusCompleted, "发现安全问题",
				fmt.Sprintf("标题:%s\n描述:%s\n严重级别:%s", v.Title, v.Description, string(v.Level)))
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	callbacks.ToolUseLogCallback(toolId01, "mcp_scanner_init", step01, "配置AI模型: "+params.Model.Model)

	modelConfig := models.NewOpenAI(params.Model.Token, params.Model.Model, params.Model.BaseUrl)
	scanner := mcp.NewScanner(modelConfig, logger)
	scanner.SetLanguage(params.Language)
	scanner.SetCallback(processFunc)

	callbacks.ToolUseLogCallback(toolId01, "mcp_scanner_init", step01, "设置扫描语言: "+params.Language)

	//4. 完成初始化
	completedTool01 := CreateTool(toolId01, "mcp_scanner_init", ToolStatusDone, "MCP扫描器初始化完成", "初始化", "扫描配置", "配置成功")
	callbacks.ToolUsedCallback(step01, statusId01, "初始化完成", []Tool{completedTool01})
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, "A.I.G完成工作", "MCP扫描环境初始化完成")

	// 更新任务计划
	tasks[0].Status = SubTaskStatusDone
	tasks[1].Status = SubTaskStatusDoing
	tasks[1].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//5. 开始MCP扫描
	callbacks.NewPlanStepCallback(step02, "执行MCP安全扫描")
	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusRunning, "A.I.G正在工作", "开始执行MCP安全扫描")

	toolId02 := uuid.New().String()
	callbacks.ToolUsedCallback(step02, statusId02, "执行MCP扫描",
		[]Tool{
			CreateTool(toolId02, "mcp_scanner", ToolStatusDoing, "正在执行MCP安全扫描", "扫描", "目标内容", ""),
		})

	var scanResults *mcp.McpResult
	var scanType string

	if transport == "url" {
		scanType = "URL扫描"
		url := params.Content
		callbacks.ToolUseLogCallback(toolId02, "mcp_scanner", step02, "开始URL扫描: "+url)
		r, err := scanner.InputUrl(ctx, url)
		if err != nil {
			return err
		}
		callbacks.ToolUseLogCallback(toolId02, "mcp_scanner", step02, "URL输入成功，开始安全扫描...")
		results, err := scanner.ScanLink(ctx, r, false)
		if err != nil {
			return err
		}
		scanResults = results
		callbacks.ToolUseLogCallback(toolId02, "mcp_scanner", step02, "URL扫描完成")
	} else if transport == "code" {
		scanType = "代码扫描"
		// todo: github下载和zip下载
		// 创建临时目录用于存储上传的文件
		tempDir := "temp_uploads"
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			gologger.Errorf("创建临时目录失败: %v", err)
			return err
		}
		var folder string
		if len(files) > 0 {
			// 远程下载
			for _, file := range files {
				// 下载文件
				gologger.Infof("开始下载文件: %s", file)
				fileName := fmt.Sprintf("tmp-%d.zip", time.Now().UnixMicro())
				err := utils.DownloadFile(file, filepath.Join(tempDir, fileName))
				if err != nil {
					gologger.Errorf("下载文件失败: %v", err)
					return err
				}
				extractPath, _ := filepath.Abs(filepath.Join(tempDir, fmt.Sprintf("tmp-%d", time.Now().UnixMicro())))
				gologger.Infof("文件下载成功: %s", file)
				err = utils.ExtractZipFile(fileName, extractPath)
				if err != nil {
					gologger.Errorf("解压文件失败: %v", err)
					return err
				}
				folder = extractPath
			}
		} else {
			extractPath, _ := filepath.Abs(filepath.Join(tempDir, fmt.Sprintf("tmp-%d", time.Now().UnixMicro())))
			err := utils.GitClone(params.Content, extractPath, 30*time.Second)
			if err != nil {
				gologger.Errorf("克隆代码仓库失败: %v", err)
				return err
			}
			folder = extractPath
		}

		callbacks.ToolUseLogCallback(toolId02, "mcp_scanner", step02, "开始代码路径扫描: "+folder)

		// 判断文件夹是否存在
		if info, err := os.Stat(folder); os.IsNotExist(err) || !info.IsDir() {
			return fmt.Errorf("代码路径不存在或不是目录: %s", folder)
		}
		callbacks.ToolUseLogCallback(toolId02, "mcp_scanner", step02, "代码路径验证成功，开始安全扫描...")
		scanner.InputCodePath(folder)
		results, err := scanner.ScanCode(ctx, false)
		if err != nil {
			return err
		}
		scanResults = results
		callbacks.ToolUseLogCallback(toolId02, "mcp_scanner", step02, "代码扫描完成")
	}
	step03 := uuid.New().String()
	callbacks.NewPlanStepCallback(step03, "生成扫描报告")

	statusId03 := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step03, statusId03, AgentStatusCompleted, "A.I.G正在工作", "开始生成MCP扫描报告")

	toolId03 := uuid.New().String()
	callbacks.ToolUsedCallback(step03, statusId03, "生成报告",
		[]Tool{CreateTool(toolId03, "mcp_report_generator", ToolStatusDone, "正在生成MCP扫描报告", "扫描日志", "日志内容", writer1.String())})

	callbacks.ToolUseLogCallback(toolId03, "mcp_report_generator", step03, "正在分析MCP扫描结果...")

	//8. 发送任务最终结果
	result := map[string]interface{}{
		"readme":   readMe,
		"scanType": scanType,
		"results":  scanResults.Issues,
		"report":   scanResults.Report,
	}
	tasks[1].Status = SubTaskStatusDone
	callbacks.PlanUpdateCallback(tasks)

	callbacks.ResultCallback(result)
	return nil
}

type ModelRedteamReport struct{}

func (m *ModelRedteamReport) GetName() string {
	return TaskTypeModelRedteamReport
}

func (m *ModelRedteamReport) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	type params struct {
		Model struct {
			BaseUrl string `json:"base_url"`
			Token   string `json:"token"`
			Model   string `json:"model"`
		} `json:"model"`
		Datasets struct {
			NumPrompts int `json:"numPrompts"`
			RandomSeed int `json:"randomSeed"`
		} `json:"datasets"`
	}
	var param params
	if err := json.Unmarshal(request.Params, &param); err != nil {
		return err
	}

	planId := uuid.New().String()
	err := utils.RunCmd("python", []string{
		"cli_run.py",
		"--model", param.Model.Model,
		"--base_url", param.Model.BaseUrl,
		"--api_key", param.Model.Token,
		"--scenarios", fmt.Sprintf("MultiDataset:num_prompts=%d,random_seed=%d", param.Datasets.NumPrompts, param.Datasets.RandomSeed),
		"--techniques", "ICRTRedteam",
		"--metric", "JailbreakMetric",
		"--choice", "serial",
	}, func(line string) {
		ParseStdoutLine(planId, line, callbacks)
	})
	return err
}

type ModelJailbreak struct{}

func (m *ModelJailbreak) GetName() string {
	return TaskTypeModelJailbreak
}

func (m *ModelJailbreak) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	type params struct {
		Model struct {
			BaseUrl string `json:"base_url"`
			Token   string `json:"token"`
			Model   string `json:"model"`
		} `json:"model"`
		Prompt string `json:"prompt"`
	}
	var param params
	if err := json.Unmarshal(request.Params, &param); err != nil {
		return err
	}
	planId := uuid.New().String()

	err := utils.RunCmd("python", []string{
		"cli_run.py",
		"--model", param.Model.Model,
		"--base_url", param.Model.BaseUrl,
		"--api_key", param.Model.Token,
		"--scenarios", fmt.Sprintf("Custom:prompt=%s", param.Prompt),
		"--techniques", "ICRTJailbreak",
		"--metric", "JailbreakMetric",
		"--choice", "serial",
	}, func(line string) {
		ParseStdoutLine(planId, line, callbacks)
	})
	return err
}
