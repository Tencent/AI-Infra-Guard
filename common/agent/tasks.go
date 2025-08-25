package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
	iputil "github.com/projectdiscovery/utils/ip"

	"github.com/Tencent/AI-Infra-Guard/common/utils"

	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"

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

type ErrorCallback func(error string)

// TaskCallbacks 任务回调函数集合
type TaskCallbacks struct {
	ResultCallback           ResultCallback       // 任务结果回调
	ToolUseLogCallback       ActionLogCallback    // 插件日志回调
	ToolUsedCallback         ToolUsedCallback     // 插件状态回调
	NewPlanStepCallback      NewPlanStepCallback  // 新建执行步骤回调
	StepStatusUpdateCallback StatusUpdateCallback // 更新步骤状态回调
	PlanUpdateCallback       PlanUpdateCallback   // 更新任务计划回调
	ErrorCallback            ErrorCallback        // 错误回调
}

type TaskInterface interface {
	GetName() string
	Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error
}

// ScanRequest 扫描请求结构
type ScanRequest struct {
	Target  []string          `json:"-"`
	Headers map[string]string `json:"headers"`
	Timeout int               `json:"timeout"`
}

type AIInfraScanAgent struct {
	Server string
}

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
	if len(request.Attachments) > 0 {
		// 创建临时目录用于存储上传的文件
		tempDir := "temp_uploads"
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			gologger.Errorf("创建临时目录失败: %v", err)
			return err
		}
		// 远程下载
		for _, file := range request.Attachments {
			// 下载文件
			gologger.Infof("开始下载文件: %s", file)
			fileName := filepath.Join(tempDir, fmt.Sprintf("tmp-%d.%s", time.Now().UnixMicro(), filepath.Ext(file)))
			err := DownloadFile(t.Server, request.SessionId, file, fileName)
			if err != nil {
				gologger.WithError(err).Errorln("下载文件失败")
				return err
			}
			lines, err := os.ReadFile(fileName)
			if err != nil {
				gologger.WithError(err).Errorln("读取文件失败")
				return err
			}
			targets = append(targets, strings.Split(string(lines), "\n")...)
		}
	}
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
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, uuid.NewString()))
	}
	callbacks.PlanUpdateCallback(tasks)

	//1. 创建新的执行步骤 - 初始化
	step01 := tasks[0].StepId
	callbacks.NewPlanStepCallback(step01, "初始化扫描环境")

	//2. 发送步骤运行状态
	statusId01 := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusRunning, "A.I.G正在工作", "开始初始化AI基础设施扫描环境")
	// 深拷贝options
	opts := &options.Options{
		TimeOut:      reqScan.Timeout,
		RateLimit:    200,
		FPTemplates:  t.Server,
		AdvTemplates: t.Server,
		WebServer:    false,
		Target:       reqScan.Target,
		LoadRemote:   true,
	}

	// 配置请求头
	headers := make([]string, 0)
	for k, v := range reqScan.Headers {
		headers = append(headers, k+":"+v)
	}
	opts.Headers = headers
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, "初始化配置完成", "")
	// 2. 判断需要扫描端口的target
	targets = []string{}
	var hosts []string
	for _, target := range reqScan.Target {
		if iputil.IsIP(target) {
			hosts = append(hosts, target)
		}
		targets = append(targets, target)
	}
	if len(hosts) > 0 {
		for _, host := range hosts {
			statusNmap := uuid.NewString()
			toolId := uuid.NewString()
			callbacks.StepStatusUpdateCallback(step01, statusNmap, AgentStatusRunning, "正在自动识别端口", fmt.Sprintf("正在自动识别IP: %s", host))
			callbacks.ToolUsedCallback(step01, statusNmap, "nmap", []Tool{
				CreateTool(toolId, "nmap", SubTaskStatusDoing, "端口扫描", "nmap", "-T4 -p 11434,1337,7000-9000", ""),
			})
			portScanResult, err := utils.NmapScan(host, "11434,1337,7000-9000")
			if err != nil {
				return err
			}
			success := 0
			for _, port := range portScanResult.Hosts {
				address := port.Address.Addr
				for _, ported := range port.Ports.PortList {
					if ported.State.State == "open" {
						targets = append(targets, fmt.Sprintf("%s:%d", address, ported.PortID))
						success += 1
						callbacks.ToolUseLogCallback(toolId, "nmap", step01, fmt.Sprintf("发现端口: %s:%d\n", address, ported.PortID))
					}
				}
			}
			callbacks.ToolUsedCallback(step01, statusNmap, "nmap", []Tool{
				CreateTool(toolId, "nmap", SubTaskStatusDone, "端口扫描", "nmap", "-T4", fmt.Sprintf("端口数量: %d", success)),
			})
			callbacks.StepStatusUpdateCallback(step01, statusNmap, AgentStatusCompleted, host+" 端口探测完成", "")
		}
	}
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, "目标配置完成", fmt.Sprintf("目标数量: %d", len(targets)))
	opts.Target = targets
	// 结果收集
	scanResults := make([]runner.CallbackScanResult, 0)
	mu := sync.Mutex{}
	step02 := tasks[1].StepId
	statusId02 := uuid.New().String()
	statustool := uuid.New().String()
	toolId02 := uuid.New().String()

	processFunc := func(data interface{}) {
		mu.Lock()
		defer mu.Unlock()
		switch v := data.(type) {
		case runner.CallbackScanResult:
			scanResults = append(scanResults, v)
			var log string = ""
			var appFinger string
			if v.Fingerprint != "" {
				appFinger = fmt.Sprintf("WEB应用: %s ", v.Fingerprint)
			}
			if len(v.Vulnerabilities) > 0 {
				log = fmt.Sprintf("URL:%s %s发现漏洞:%d\n", v.TargetURL, appFinger, len(v.Vulnerabilities))
			} else {
				log = fmt.Sprintf("URL:%s %s扫描完成,未发现漏洞\n", v.TargetURL, appFinger)
			}
			callbacks.ToolUseLogCallback(toolId02, "ai_scanner", step02, log)
			callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, "发现结果", log)
		//if len(v.Vulnerabilities) > 0 {
		//	for _, vuln := range v.Vulnerabilities {
		//		callbacks.StepStatusUpdateCallback(step02, statusId, AgentStatusCompleted, "发现漏洞", fmt.Sprintf("CVE:%s\n描述:%s\n详情:%s", vuln.CVEName, vuln.Summary, vuln.Details))
		//	}
		//}
		case runner.CallbackErrorInfo:
			callbacks.ToolUseLogCallback(toolId02, "ai_scanner", step02, fmt.Sprintf("执行错误: host:%s %s\n", v.Target, v.Error))
		case runner.CallbackProcessInfo:
		case runner.CallbackReportInfo:
		case runner.Step01:
			callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, "配置", v.Text)
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	opts.SetCallback(processFunc)
	r, err := runner.New(opts) // 创建runner
	if err != nil {
		return err
	}
	defer r.Close() // 关闭runner

	//4. 完成初始化
	callbacks.StepStatusUpdateCallback(step01, uuid.New().String(), AgentStatusCompleted, "A.I.G完成工作", "扫描环境初始化完成")

	// 更新任务计划
	tasks[0].Status = SubTaskStatusDone
	tasks[1].Status = SubTaskStatusDoing
	tasks[1].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//5. 创建runner并执行扫描
	callbacks.NewPlanStepCallback(step02, "执行AI基础设施扫描")
	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusCompleted, "A.I.G正在工作", "正在扫描...")

	//statusId03 := uuid.NewString()
	callbacks.ToolUsedCallback(step02, statusId02, "执行扫描",
		[]Tool{CreateTool(toolId02, "ai_scanner", ToolStatusDoing, "正在执行AI基础设施扫描", "扫描", "目标系统", "")})

	// 执行枚举
	r.RunEnumeration()
	advies := make([]vulstruct.Info, 0)
	for _, item := range scanResults {
		advies = append(advies, item.Vulnerabilities...)
	}
	score := r.CalcSecScore(advies)

	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusCompleted, "A.I.G完成工作", "完成扫描")
	callbacks.ToolUsedCallback(step02, statusId02, "执行扫描",
		[]Tool{CreateTool(toolId02, "ai_scanner", ToolStatusDone, "AI基础设施扫描完成", "扫描", "目标系统", fmt.Sprintf("扫描结果: %d 条", len(scanResults)))})

	//6. 完成扫描
	callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, "A.I.G完成工作", "AI基础设施扫描任务完成")

	// 更新任务计划
	tasks[1].Status = SubTaskStatusDone
	tasks[2].Status = SubTaskStatusDoing
	tasks[2].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//7. 生成最终报告
	step03 := tasks[2].StepId
	callbacks.NewPlanStepCallback(step03, "生成扫描报告")

	callbacks.StepStatusUpdateCallback(step03, statustool, AgentStatusCompleted, "A.I.G正在工作", "生成扫描报告")

	toolId03 := uuid.New().String()
	callbacks.ToolUsedCallback(step03, statustool, "生成报告",
		[]Tool{CreateTool(toolId03, "report_generator", ToolStatusDoing, "正在生成扫描报告", "生成报告", "", fmt.Sprintf("%d", len(scanResults)))})

	//8. 发送任务最终结果
	result := map[string]interface{}{
		"total":   len(advies),
		"score":   score.SecScore,
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
	Language string   `json:"language"`
	Quick    bool     `json:"quick"`
	Plugins  []string `json:"plugins,omitempty"`
}

type McpScanAgent struct {
	Server string
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
	quickMode := params.Quick
	var target string

	// 新增：如果没有模型配置，使用默认模型
	if params.Model.Model == "" || params.Model.Token == "" || params.Model.BaseUrl == "" {
		defaultModel := getDefaultModel()
		if defaultModel != nil {
			params.Model = *defaultModel
			gologger.Infof("使用默认模型: %s", defaultModel.Model)
		} else {
			return fmt.Errorf("没有可用的模型配置，请检查环境变量或任务参数")
		}
	}

	//0. 发送初始任务计划
	taskTitles := []string{
		"初始化MCP扫描环境",
		"执行MCP安全扫描",
		"生成扫描报告",
	}
	var tasks []SubTask
	for _, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, uuid.NewString()))
	}
	callbacks.PlanUpdateCallback(tasks)
	step01 := tasks[0].StepId
	step02 := tasks[1].StepId
	//1. 创建新的执行步骤 - 初始化
	callbacks.NewPlanStepCallback(step01, "初始化MCP扫描环境")

	//2. 发送步骤运行状态
	callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, "A.I.G正在工作", "开始初始化MCP安全扫描环境")
	mu := sync.Mutex{}

	// 结果收集
	readMe := ""

	var moduleStatusIdMap map[string]string = map[string]string{}
	var moduleToolIdMap map[string]string = map[string]string{}
	//var toolName string

	processFunc := func(data interface{}) {
		mu.Lock()
		defer mu.Unlock()
		switch v := data.(type) {
		case mcp.CallbackWriteLog:
			moduleName := v.ModuleName
			moduleToolId := moduleToolIdMap[v.ModuleName]
			callbacks.ToolUseLogCallback(moduleToolId, moduleName, step02, string(v.Text))
		case mcp.McpModuleStart:
			moduleStatusId := uuid.New().String()
			moduleToolId := uuid.New().String()
			moduleStatusIdMap[v.ModuleName] = moduleStatusId
			moduleToolIdMap[v.ModuleName] = moduleToolId
			callbacks.StepStatusUpdateCallback(step02, moduleStatusId, AgentStatusRunning, "MCP安全插件扫描", "开始MCP安全扫描,模块名:"+v.ModuleName)
			callbacks.ToolUsedCallback(step02, moduleStatusId, "开始扫描MCP安全扫描",
				[]Tool{CreateTool(moduleToolId, v.ModuleName, ToolStatusDoing, "开始扫描MCP安全扫描", "开始扫描", v.ModuleName, "")})
			//toolName = v.ModuleName
		case mcp.McpModuleEnd:
			moduleStatusId := moduleStatusIdMap[v.ModuleName]
			moduleToolId := moduleToolIdMap[v.ModuleName]
			callbacks.StepStatusUpdateCallback(step02, moduleStatusId, AgentStatusCompleted, "MCP安全插件扫描", "结束MCP安全扫描,模块名:"+v.ModuleName)
			callbacks.ToolUsedCallback(step02, moduleStatusId, "MCP安全扫描完成",
				[]Tool{CreateTool(moduleToolId, v.ModuleName, ToolStatusDone, "MCP安全扫描完成", "扫描完成", v.ModuleName, "")})
			//writer1.Finally()
		case mcp.McpCallbackProcessing:
		case mcp.McpCallbackReadMe:
			readMe = v.Content
			toolId := uuid.NewString()
			statusId := uuid.NewString()
			callbacks.StepStatusUpdateCallback(step02, statusId, AgentStatusCompleted, "MCP信息收集", "收集MCP信息")
			callbacks.ToolUsedCallback(step02, statusId, "收集MCP信息",
				[]Tool{CreateTool(toolId, "info_collection", ToolStatusDone, "收集MCP信息", "信息收集", "MCP信息收集", fmt.Sprintf("%d字", len(readMe)))})
			callbacks.ToolUseLogCallback(toolId, "info_collection", step02, readMe)
		case mcp.Issue:
			toolId := uuid.NewString()
			moduleStatusId := uuid.NewString()
			callbacks.ToolUsedCallback(step02, moduleStatusId, "漏洞发现",
				[]Tool{CreateTool(toolId, toolId, ToolStatusDone, "漏洞发现", "漏洞发现", "模块名称:"+v.Title, "")})
			issue := fmt.Sprintf("标题:%s\n描述:%s\n严重级别:%s\n建议:%s\n风险类型:%s\n", v.Title, v.Description, string(v.Level), v.Suggestion, v.RiskType)
			callbacks.ToolUseLogCallback(toolId, toolId, step02, issue)
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, "配置AI模型", fmt.Sprintf("配置AI模型: %s", params.Model.Model))
	logger := gologger.NewLogger()
	startTime := time.Now().Unix()
	modelConfig := models.NewOpenAI(params.Model.Token, params.Model.Model, params.Model.BaseUrl)
	scanner := mcp.NewScanner(modelConfig, logger)
	if params.Language == "" {
		params.Language = "zh"
	}
	scanner.SetLanguage(params.Language)
	callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, "配置语言", params.Language)
	err := scanner.RegisterPlugin(params.Plugins)
	if err != nil {
		return err
	}
	scanner.SetCallback(processFunc)

	//4. 完成初始化
	callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, "A.I.G完成工作", "MCP扫描环境初始化完成")

	// 更新任务计划
	tasks[0].Status = SubTaskStatusDone
	tasks[1].Status = SubTaskStatusDoing
	tasks[1].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//5. 开始MCP扫描
	callbacks.NewPlanStepCallback(step02, "执行MCP安全扫描")
	callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, "A.I.G正在工作", "开始执行MCP安全扫描")

	var scanResults *mcp.McpResult
	var scanType string
	var CodeLanguage string

	if transport == "url" {
		scanType = "URL扫描"
		url := params.Content
		if url == "" {
			return fmt.Errorf("url is empty")
		}
		if !strings.HasPrefix(url, "http") {
			return fmt.Errorf("url must start with http")
		}
		callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, "A.I.G开始扫描", fmt.Sprintf("开始扫描URL: %s", url))
		target = url
		r, err := scanner.InputUrl(ctx, url)
		if err != nil || r == nil {
			return err
		}
		results, err := scanner.ScanLink(ctx, r, quickMode)
		if err != nil {
			return err
		}
		scanResults = results
	} else if transport == "code" {
		scanType = "代码扫描"
		// 创建临时目录用于存储上传的文件
		tempDir := "temp_uploads"
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			gologger.Errorf("创建临时目录失败: %v", err)
			return err
		}
		callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, "A.I.G开始扫描", "开始代码扫描")
		var folder string
		if len(files) > 0 {
			// 远程下载
			for _, file := range files {
				// 下载文件
				gologger.Infof("开始下载文件: %s", file)
				target = file
				ext := ""
				supports := []string{".zip", ".tar.gz", ".tgz", ".whl"}
				for _, support := range supports {
					if strings.HasSuffix(file, support) {
						ext = support
						break
					}
				}
				if ext == "" {
					gologger.Errorln("不支持的文件类型，仅支持: ", strings.Join(supports, ","))
					continue
				}

				fileName := filepath.Join(tempDir, fmt.Sprintf("tmp-%d%s", time.Now().UnixMicro(), ext))
				err := DownloadFile(m.Server, request.SessionId, file, fileName)
				if err != nil {
					return fmt.Errorf("下载文件失败: %v", err)
				}
				gologger.Infof("文件下载成功: %s", file)
				extractPath, _ := filepath.Abs(filepath.Join(tempDir, fmt.Sprintf("tmp-%d", time.Now().UnixMicro())))
				switch ext {
				case ".zip", ".whl":
					err = utils.ExtractZipFile(fileName, extractPath)
				case ".tgz", ".tar.gz":
					err = utils.ExtractTGZ(fileName, extractPath)
				default:
					return errors.New("不支持的文件类型")
				}
				if err != nil {
					return errors.New(fmt.Sprintf("解压文件失败: %v", err))
				}
				folder = extractPath
			}
		} else {
			target = params.Content
			extractPath, _ := filepath.Abs(filepath.Join(tempDir, fmt.Sprintf("tmp-%d", time.Now().UnixMicro())))
			err := utils.GitClone(params.Content, extractPath, 30*time.Second)
			if err != nil {
				return fmt.Errorf("克隆代码仓库失败: %v", err)
			}
			folder = extractPath
		}

		// 判断文件夹是否存在
		if info, err := os.Stat(folder); os.IsNotExist(err) || !info.IsDir() {
			return fmt.Errorf("代码路径不存在或不是目录: %s", folder)
		}
		scanner.InputCodePath(folder)
		results, err := scanner.ScanCode(ctx, quickMode)
		if err != nil {
			return err
		}
		scanResults = results
		// 脚本语言GetTop
		CodeLanguage = utils.GetTopLanguage(utils.AnalyzeLanguage(folder))
	}
	callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, "A.I.G完成工作", "MCP安全扫描任务完成")

	// 更新任务计划
	tasks[1].Status = SubTaskStatusDone
	tasks[2].Status = SubTaskStatusDoing
	tasks[2].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//6. 生成最终报告
	step03 := tasks[2].StepId
	callbacks.NewPlanStepCallback(step03, "生成扫描报告")

	statusId03 := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step03, statusId03, AgentStatusCompleted, "A.I.G正在工作", "开始生成MCP扫描报告")
	toolId03 := uuid.New().String()

	// 完成报告生成
	completedTool03 := CreateTool(toolId03, "mcp_report_generator", ToolStatusDone, "MCP扫描报告生成完成", "生成", "扫描日志", "")
	callbacks.ToolUsedCallback(step03, statusId03, "报告生成完成", []Tool{completedTool03})
	callbacks.StepStatusUpdateCallback(step03, statusId03, AgentStatusCompleted, "A.I.G完成工作", "MCP扫描报告生成完成")
	endTime := time.Now().Unix()
	//7. 发送任务最终结果
	result := map[string]interface{}{
		"readme":     readMe,
		"score":      100,
		"language":   CodeLanguage,
		"target":     target,
		"plugins":    params.Plugins,
		"start_time": startTime,
		"end_time":   endTime,
		"scanType":   scanType,
		"results":    scanResults.Issues,
		"report":     scanResults.Report,
	}

	// 最终更新任务计划
	tasks[2].Status = SubTaskStatusDone
	callbacks.PlanUpdateCallback(tasks)
	callbacks.ResultCallback(result)
	return nil
}

// 新增：获取默认模型信息
func getDefaultModel() *struct {
	Model   string `json:"model"`
	Token   string `json:"token"`
	BaseUrl string `json:"base_url"`
} {
	model := os.Getenv("DEFAULT_MODEL_NAME")
	token := os.Getenv("DEFAULT_MODEL_TOKEN")
	baseUrl := os.Getenv("DEFAULT_MODEL_BASE_URL")

	if model != "" && token != "" && baseUrl != "" {
		return &struct {
			Model   string `json:"model"`
			Token   string `json:"token"`
			BaseUrl string `json:"base_url"`
		}{
			Model:   model,
			Token:   token,
			BaseUrl: baseUrl,
		}
	}
	return nil
}
