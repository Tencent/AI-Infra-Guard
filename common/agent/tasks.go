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
	language := request.Language
	if language == "" {
		language = "zh"
	}

	// 定义语言相关的文本
	var texts struct {
		initEnv, execScan, genReport, aigWorking, aigCompleted, initConfig, portDetection, targetConfig, scanComplete, reportGen             string
		createTempDir, downloadFile, readFile, portScan, foundPort, portCount, targetCount, foundVuln, noVuln, execError, config, scanResult string
		// 动态描述文本模板
		initDescTemplate, portDetectDescTemplate, portCompleteTemplate, targetCountTemplate, webAppTemplate, vulnFoundTemplate, noVulnTemplate, errorTemplate string
		scanningDesc, execScanDesc, scanCompleteDesc, taskCompleteDesc, reportGenDesc, reportGenToolDesc, scanResultTemplate                                  string
		// 工具和操作相关文本
		downloadFileLog, execScanTool, scanTool, generateReportTool, nmapTool, aiScannerTool, reportGeneratorTool, scanOperation, targetSystem, generateReport string
	}

	if language == "en" {
		texts.initEnv = "Initialize scan environment"
		texts.execScan = "Execute AI infrastructure scan"
		texts.genReport = "Generate scan report"
		texts.aigWorking = "A.I.G is working"
		texts.aigCompleted = "A.I.G completed work"
		texts.initConfig = "Initialization configuration completed"
		texts.portDetection = "Auto-detecting ports"
		texts.targetConfig = "Target configuration completed"
		texts.scanComplete = "Scan completed"
		texts.reportGen = "Generating scan report"
		texts.createTempDir = "Failed to create temporary directory"
		texts.downloadFile = "Failed to download file"
		texts.readFile = "Failed to read file"
		texts.portScan = "Port scan"
		texts.foundPort = "Found port"
		texts.portCount = "Port count"
		texts.targetCount = "Target count"
		texts.foundVuln = "Found vulnerabilities"
		texts.noVuln = "Scan completed, no vulnerabilities found"
		texts.execError = "Execution error"
		texts.config = "Configuration"
		texts.scanResult = "Scan result"
		// 动态描述文本模板
		texts.initDescTemplate = "Starting to initialize AI infrastructure scan environment"
		texts.portDetectDescTemplate = "Auto-detecting IP: %s"
		texts.portCompleteTemplate = "%s port detection completed"
		texts.targetCountTemplate = "Target count: %d"
		texts.webAppTemplate = "WEB Application: %s "
		texts.vulnFoundTemplate = "URL:%s %sFound vulnerabilities:%d\n"
		texts.noVulnTemplate = "URL:%s %sScan completed, no vulnerabilities found\n"
		texts.errorTemplate = "Execution error: host:%s %s\n"
		texts.scanningDesc = "Scanning..."
		texts.execScanDesc = "Executing AI infrastructure scan"
		texts.scanCompleteDesc = "Scan completed"
		texts.taskCompleteDesc = "AI infrastructure scan task completed"
		texts.reportGenDesc = "Generating scan report"
		texts.reportGenToolDesc = "Generating scan report"
		texts.scanResultTemplate = "Scan results: %d items"
		// 工具和操作相关文本
		texts.downloadFileLog = "Starting to download file: %s"
		texts.execScanTool = "Execute scan"
		texts.scanTool = "Scan"
		texts.generateReportTool = "Generate report"
		texts.nmapTool = "nmap"
		texts.aiScannerTool = "ai_scanner"
		texts.reportGeneratorTool = "report_generator"
		texts.scanOperation = "Scan"
		texts.targetSystem = "Target system"
		texts.generateReport = "Generate report"
	} else {
		texts.initEnv = "初始化扫描环境"
		texts.execScan = "执行AI基础设施扫描"
		texts.genReport = "生成扫描报告"
		texts.aigWorking = "A.I.G正在工作"
		texts.aigCompleted = "A.I.G完成工作"
		texts.initConfig = "初始化配置完成"
		texts.portDetection = "正在自动识别端口"
		texts.targetConfig = "目标配置完成"
		texts.scanComplete = "扫描完成"
		texts.reportGen = "生成扫描报告"
		texts.createTempDir = "创建临时目录失败"
		texts.downloadFile = "下载文件失败"
		texts.readFile = "读取文件失败"
		texts.portScan = "端口扫描"
		texts.foundPort = "发现端口"
		texts.portCount = "端口数量"
		texts.targetCount = "目标数量"
		texts.foundVuln = "发现漏洞"
		texts.noVuln = "扫描完成,未发现漏洞"
		texts.execError = "执行错误"
		texts.config = "配置"
		texts.scanResult = "扫描结果"
		// 动态描述文本模板
		texts.initDescTemplate = "开始初始化AI基础设施扫描环境"
		texts.portDetectDescTemplate = "正在自动识别IP: %s"
		texts.portCompleteTemplate = "%s 端口探测完成"
		texts.targetCountTemplate = "目标数量: %d"
		texts.webAppTemplate = "WEB应用: %s "
		texts.vulnFoundTemplate = "URL:%s %s发现漏洞:%d\n"
		texts.noVulnTemplate = "URL:%s %s扫描完成,未发现漏洞\n"
		texts.errorTemplate = "执行错误: host:%s %s\n"
		texts.scanningDesc = "正在扫描..."
		texts.execScanDesc = "正在执行AI基础设施扫描"
		texts.scanCompleteDesc = "完成扫描"
		texts.taskCompleteDesc = "AI基础设施扫描任务完成"
		texts.reportGenDesc = "生成扫描报告"
		texts.reportGenToolDesc = "正在生成扫描报告"
		texts.scanResultTemplate = "扫描结果: %d 条"
		// 工具和操作相关文本
		texts.downloadFileLog = "开始下载文件: %s"
		texts.execScanTool = "执行扫描"
		texts.scanTool = "扫描"
		texts.generateReportTool = "生成报告"
		texts.nmapTool = "nmap"
		texts.aiScannerTool = "ai_scanner"
		texts.reportGeneratorTool = "report_generator"
		texts.scanOperation = "扫描"
		texts.targetSystem = "目标系统"
		texts.generateReport = "生成报告"
	}
	targets := strings.Split(strings.TrimSpace(request.Content), "\n")
	if len(request.Attachments) > 0 {
		// 创建临时目录用于存储上传的文件
		tempDir := "uploads"
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			gologger.Errorf("%s: %v", texts.createTempDir, err)
			return err
		}
		// 远程下载
		for _, file := range request.Attachments {
			// 下载文件
			gologger.Infof(texts.downloadFileLog, file)
			fileName := filepath.Join(tempDir, fmt.Sprintf("tmp-%d.%s", time.Now().UnixMicro(), filepath.Ext(file)))
			err := DownloadFile(t.Server, request.SessionId, file, fileName)
			if err != nil {
				gologger.WithError(err).Errorln(texts.downloadFile)
				return err
			}
			lines, err := os.ReadFile(fileName)
			if err != nil {
				gologger.WithError(err).Errorln(texts.readFile)
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
		texts.initEnv,
		texts.execScan,
		texts.genReport,
	}
	var tasks []SubTask
	for _, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, uuid.NewString()))
	}
	callbacks.PlanUpdateCallback(tasks)

	//1. 创建新的执行步骤 - 初始化
	step01 := tasks[0].StepId
	callbacks.NewPlanStepCallback(step01, texts.initEnv)

	//2. 发送步骤运行状态
	statusId01 := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusRunning, texts.aigWorking, texts.initDescTemplate)
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
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, texts.initConfig, "")
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
			callbacks.StepStatusUpdateCallback(step01, statusNmap, AgentStatusRunning, texts.portDetection, fmt.Sprintf(texts.portDetectDescTemplate, host))
			callbacks.ToolUsedCallback(step01, statusNmap, texts.nmapTool, []Tool{
				CreateTool(toolId, texts.nmapTool, SubTaskStatusDoing, texts.portScan, texts.nmapTool, "-T4 -p 11434,1337,7000-9000", ""),
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
						callbacks.ToolUseLogCallback(toolId, texts.nmapTool, step01, fmt.Sprintf("%s: %s:%d\n", texts.foundPort, address, ported.PortID))
					}
				}
			}
			callbacks.ToolUsedCallback(step01, statusNmap, texts.nmapTool, []Tool{
				CreateTool(toolId, texts.nmapTool, SubTaskStatusDone, texts.portScan, texts.nmapTool, "-T4", fmt.Sprintf("%s: %d", texts.portCount, success)),
			})
			callbacks.StepStatusUpdateCallback(step01, statusNmap, AgentStatusCompleted, fmt.Sprintf(texts.portCompleteTemplate, host), "")
		}
	}
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, texts.targetConfig, fmt.Sprintf(texts.targetCountTemplate, len(targets)))
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
				appFinger = fmt.Sprintf(texts.webAppTemplate, v.Fingerprint)
			}
			if len(v.Vulnerabilities) > 0 {
				log = fmt.Sprintf(texts.vulnFoundTemplate, v.TargetURL, appFinger, len(v.Vulnerabilities))
			} else {
				log = fmt.Sprintf(texts.noVulnTemplate, v.TargetURL, appFinger)
			}
			callbacks.ToolUseLogCallback(toolId02, texts.aiScannerTool, step02, log)
			callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, texts.scanResult, log)
		//if len(v.Vulnerabilities) > 0 {
		//	for _, vuln := range v.Vulnerabilities {
		//		callbacks.StepStatusUpdateCallback(step02, statusId, AgentStatusCompleted, "发现漏洞", fmt.Sprintf("CVE:%s\n描述:%s\n详情:%s", vuln.CVEName, vuln.Summary, vuln.Details))
		//	}
		//}
		case runner.CallbackErrorInfo:
			callbacks.ToolUseLogCallback(toolId02, texts.aiScannerTool, step02, fmt.Sprintf(texts.errorTemplate, v.Target, v.Error))
		case runner.CallbackProcessInfo:
		case runner.CallbackReportInfo:
		case runner.Step01:
			callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, texts.config, v.Text)
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
	callbacks.StepStatusUpdateCallback(step01, uuid.New().String(), AgentStatusCompleted, texts.aigCompleted, texts.initDescTemplate)

	// 更新任务计划
	tasks[0].Status = SubTaskStatusDone
	tasks[1].Status = SubTaskStatusDoing
	tasks[1].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//5. 创建runner并执行扫描
	callbacks.NewPlanStepCallback(step02, texts.execScan)
	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusCompleted, texts.aigWorking, texts.scanningDesc)

	//statusId03 := uuid.NewString()
	callbacks.ToolUsedCallback(step02, statusId02, texts.execScanTool,
		[]Tool{CreateTool(toolId02, texts.aiScannerTool, ToolStatusDoing, texts.execScanDesc, texts.scanOperation, texts.targetSystem, "")})

	// 执行枚举
	r.RunEnumeration()
	advies := make([]vulstruct.Info, 0)
	for _, item := range scanResults {
		advies = append(advies, item.Vulnerabilities...)
	}
	score := r.CalcSecScore(advies)

	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusCompleted, texts.aigCompleted, texts.scanCompleteDesc)
	callbacks.ToolUsedCallback(step02, statusId02, texts.execScanTool,
		[]Tool{CreateTool(toolId02, texts.aiScannerTool, ToolStatusDone, texts.scanComplete, texts.scanOperation, texts.targetSystem, fmt.Sprintf(texts.scanResultTemplate, len(scanResults)))})

	//6. 完成扫描
	callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, texts.aigCompleted, texts.taskCompleteDesc)

	// 更新任务计划
	tasks[1].Status = SubTaskStatusDone
	tasks[2].Status = SubTaskStatusDoing
	tasks[2].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//7. 生成最终报告
	step03 := tasks[2].StepId
	callbacks.NewPlanStepCallback(step03, texts.genReport)

	callbacks.StepStatusUpdateCallback(step03, statustool, AgentStatusCompleted, texts.aigWorking, texts.reportGenDesc)

	toolId03 := uuid.New().String()
	callbacks.ToolUsedCallback(step03, statustool, texts.generateReportTool,
		[]Tool{CreateTool(toolId03, texts.reportGeneratorTool, ToolStatusDoing, texts.reportGenToolDesc, texts.generateReport, "", fmt.Sprintf("%d", len(scanResults)))})

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
	Quick   bool     `json:"quick"`
	Plugins []string `json:"plugins,omitempty"`
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
	language := request.Language
	if language == "" {
		language = "zh"
	}

	// 定义语言相关的文本
	var texts struct {
		// 任务标题
		initMcpEnv, execMcpScan, genMcpReport string
		// 状态消息
		aigWorking, aigCompleted, aigStartScan string
		// 初始化相关
		initMcpDesc, configAiModel, configLanguage, mcpInitComplete string
		// 扫描相关
		execMcpScanDesc, mcpScanComplete, mcpScanTaskComplete string
		// 报告生成
		genMcpReportDesc, mcpReportGenStart, mcpReportGenComplete string
		// 工具和操作
		mcpSecurityPluginScan, startMcpScan, mcpInfoCollection, vulnDiscovery string
		startScan, scanComplete, infoCollection, vulnFound, reportGenComplete string
		// 扫描类型
		urlScan, codeScan string
		// 文件操作
		createTempDir, downloadFile, downloadSuccess, unsupportedFileType, extractFile, extractFailed string
		cloneRepo, cloneFailed, codePathNotExist, downloadFileFailed                                  string
		// 错误消息
		urlEmpty, urlInvalid, inputUrlFailed string
		// 其他
		moduleName, wordCount string
		// 扫描描述
		startScanUrl, startCodeScan string
		// 漏洞详情格式
		issueFormat string
		// 工具操作
		generate, scanLog string
	}

	if language == "en" {
		// 任务标题
		texts.initMcpEnv = "Initialize MCP scan environment"
		texts.execMcpScan = "Execute MCP security scan"
		texts.genMcpReport = "Generate scan report"
		// 状态消息
		texts.aigWorking = "A.I.G is working"
		texts.aigCompleted = "A.I.G completed work"
		texts.aigStartScan = "A.I.G start scanning"
		// 初始化相关
		texts.initMcpDesc = "Starting to initialize MCP security scan environment"
		texts.configAiModel = "Configure AI model"
		texts.configLanguage = "Configure language"
		texts.mcpInitComplete = "MCP scan environment initialization completed"
		// 扫描相关
		texts.execMcpScanDesc = "Starting to execute MCP security scan"
		texts.mcpScanComplete = "MCP security scan task completed"
		texts.mcpScanTaskComplete = "MCP security scan task completed"
		// 报告生成
		texts.genMcpReportDesc = "Generating MCP scan report"
		texts.mcpReportGenStart = "Starting to generate MCP scan report"
		texts.mcpReportGenComplete = "MCP scan report generation completed"
		// 工具和操作
		texts.mcpSecurityPluginScan = "MCP security plugin scan"
		texts.startMcpScan = "Start MCP security scan"
		texts.mcpInfoCollection = "MCP information collection"
		texts.vulnDiscovery = "Vulnerability discovery"
		texts.startScan = "Start scan"
		texts.scanComplete = "Scan completed"
		texts.infoCollection = "Information collection"
		texts.vulnFound = "Vulnerability found"
		texts.reportGenComplete = "Report generation completed"
		// 扫描类型
		texts.urlScan = "URL scan"
		texts.codeScan = "Code scan"
		// 文件操作
		texts.createTempDir = "Failed to create temporary directory"
		texts.downloadFile = "Starting to download file: %s"
		texts.downloadSuccess = "File downloaded successfully: %s"
		texts.unsupportedFileType = "Unsupported file type, only supports: "
		texts.extractFile = "Unsupported file type"
		texts.extractFailed = "Failed to extract file: %v"
		texts.cloneRepo = "Clone code repository failed: %v"
		texts.cloneFailed = "Clone code repository failed: %v"
		texts.codePathNotExist = "Code path does not exist or is not a directory: %s"
		texts.downloadFileFailed = "Download file failed: %v"
		// 错误消息
		texts.urlEmpty = "url is empty"
		texts.urlInvalid = "url must start with http"
		texts.inputUrlFailed = "input url failed: %v"
		// 其他
		texts.moduleName = "Module name:"
		texts.wordCount = "words"
		// 扫描描述
		texts.startScanUrl = "Starting to scan URL: %s"
		texts.startCodeScan = "Starting code scan"
		// 漏洞详情格式
		texts.issueFormat = "Title:%s\nDescription:%s\nSeverity Level:%s\nSuggestion:%s\nRisk Type:%s\n"
		// 工具操作
		texts.generate = "Generate"
		texts.scanLog = "Scan log"
	} else {
		// 任务标题
		texts.initMcpEnv = "初始化MCP扫描环境"
		texts.execMcpScan = "执行MCP安全扫描"
		texts.genMcpReport = "生成扫描报告"
		// 状态消息
		texts.aigWorking = "A.I.G正在工作"
		texts.aigCompleted = "A.I.G完成工作"
		texts.aigStartScan = "A.I.G开始扫描"
		// 初始化相关
		texts.initMcpDesc = "开始初始化MCP安全扫描环境"
		texts.configAiModel = "配置AI模型"
		texts.configLanguage = "配置语言"
		texts.mcpInitComplete = "MCP扫描环境初始化完成"
		// 扫描相关
		texts.execMcpScanDesc = "开始执行MCP安全扫描"
		texts.mcpScanComplete = "MCP安全扫描任务完成"
		texts.mcpScanTaskComplete = "MCP安全扫描任务完成"
		// 报告生成
		texts.genMcpReportDesc = "生成MCP扫描报告"
		texts.mcpReportGenStart = "开始生成MCP扫描报告"
		texts.mcpReportGenComplete = "MCP扫描报告生成完成"
		// 工具和操作
		texts.mcpSecurityPluginScan = "MCP安全插件扫描"
		texts.startMcpScan = "开始扫描MCP安全扫描"
		texts.mcpInfoCollection = "MCP信息收集"
		texts.vulnDiscovery = "漏洞发现"
		texts.startScan = "开始扫描"
		texts.scanComplete = "扫描完成"
		texts.infoCollection = "信息收集"
		texts.vulnFound = "漏洞发现"
		texts.reportGenComplete = "报告生成完成"
		// 扫描类型
		texts.urlScan = "URL扫描"
		texts.codeScan = "代码扫描"
		// 文件操作
		texts.createTempDir = "创建临时目录失败"
		texts.downloadFile = "开始下载文件: %s"
		texts.downloadSuccess = "文件下载成功: %s"
		texts.unsupportedFileType = "不支持的文件类型，仅支持: "
		texts.extractFile = "不支持的文件类型"
		texts.extractFailed = "解压文件失败: %v"
		texts.cloneRepo = "克隆代码仓库失败: %v"
		texts.cloneFailed = "克隆代码仓库失败: %v"
		texts.codePathNotExist = "代码路径不存在或不是目录: %s"
		texts.downloadFileFailed = "下载文件失败: %v"
		// 错误消息
		texts.urlEmpty = "url is empty"
		texts.urlInvalid = "url must start with http"
		texts.inputUrlFailed = "input url failed: %v"
		// 其他
		texts.moduleName = "模块名称:"
		texts.wordCount = "字"
		// 扫描描述
		texts.startScanUrl = "开始扫描URL: %s"
		texts.startCodeScan = "开始代码扫描"
		// 漏洞详情格式
		texts.issueFormat = "标题:%s\n描述:%s\n严重级别:%s\n建议:%s\n风险类型:%s\n"
		// 工具操作
		texts.generate = "生成"
		texts.scanLog = "扫描日志"
	}

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
		texts.initMcpEnv,
		texts.execMcpScan,
		texts.genMcpReport,
	}
	var tasks []SubTask
	for _, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, uuid.NewString()))
	}
	callbacks.PlanUpdateCallback(tasks)
	step01 := tasks[0].StepId
	step02 := tasks[1].StepId
	//1. 创建新的执行步骤 - 初始化
	callbacks.NewPlanStepCallback(step01, texts.initMcpEnv)

	//2. 发送步骤运行状态
	callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, texts.aigWorking, texts.initMcpDesc)
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
			callbacks.StepStatusUpdateCallback(step02, moduleStatusId, AgentStatusRunning, texts.mcpSecurityPluginScan, texts.startMcpScan+","+texts.moduleName+v.ModuleName)
			callbacks.ToolUsedCallback(step02, moduleStatusId, texts.startMcpScan,
				[]Tool{CreateTool(moduleToolId, v.ModuleName, ToolStatusDoing, texts.startMcpScan, texts.startScan, v.ModuleName, "")})
			//toolName = v.ModuleName
		case mcp.McpModuleEnd:
			moduleStatusId := moduleStatusIdMap[v.ModuleName]
			moduleToolId := moduleToolIdMap[v.ModuleName]
			callbacks.StepStatusUpdateCallback(step02, moduleStatusId, AgentStatusCompleted, texts.mcpSecurityPluginScan, texts.scanComplete+","+texts.moduleName+v.ModuleName)
			callbacks.ToolUsedCallback(step02, moduleStatusId, texts.scanComplete,
				[]Tool{CreateTool(moduleToolId, v.ModuleName, ToolStatusDone, texts.scanComplete, texts.scanComplete, v.ModuleName, "")})
			//writer1.Finally()
		case mcp.McpCallbackProcessing:
		case mcp.McpCallbackReadMe:
			readMe = v.Content
			toolId := uuid.NewString()
			statusId := uuid.NewString()
			callbacks.StepStatusUpdateCallback(step02, statusId, AgentStatusCompleted, texts.mcpInfoCollection, texts.mcpInfoCollection)
			callbacks.ToolUsedCallback(step02, statusId, texts.mcpInfoCollection,
				[]Tool{CreateTool(toolId, "info_collection", ToolStatusDone, texts.mcpInfoCollection, texts.infoCollection, texts.mcpInfoCollection, fmt.Sprintf("%d%s", len(readMe), texts.wordCount))})
			callbacks.ToolUseLogCallback(toolId, "info_collection", step02, readMe)
		case mcp.Issue:
			toolId := uuid.NewString()
			moduleStatusId := uuid.NewString()
			callbacks.ToolUsedCallback(step02, moduleStatusId, texts.vulnDiscovery,
				[]Tool{CreateTool(toolId, toolId, ToolStatusDone, texts.vulnDiscovery, texts.vulnFound, texts.moduleName+v.Title, "")})
			issue := fmt.Sprintf(texts.issueFormat, v.Title, v.Description, string(v.Level), v.Suggestion, v.RiskType)
			callbacks.ToolUseLogCallback(toolId, toolId, step02, issue)
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, texts.configAiModel, fmt.Sprintf("%s: %s", texts.configAiModel, params.Model.Model))
	logger := gologger.NewLogger()
	startTime := time.Now().Unix()
	modelConfig := models.NewOpenAI(params.Model.Token, params.Model.Model, params.Model.BaseUrl)
	scanner := mcp.NewScanner(modelConfig, logger)
	scanner.SetLanguage(language)
	callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, texts.configLanguage, language)

	plugins := params.Plugins
	defaultPlugins := []string{"vuln_review", "code_info_collection", "mcp_info_collection"}
	for _, plugin := range defaultPlugins {
		if !utils.StrInSlice(plugin, plugins) {
			plugins = append(plugins, plugin)
		}
	}
	err := scanner.RegisterPlugin(plugins)
	if err != nil {
		return err
	}
	scanner.SetCallback(processFunc)

	//4. 完成初始化
	callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, texts.aigCompleted, texts.mcpInitComplete)

	// 更新任务计划
	tasks[0].Status = SubTaskStatusDone
	tasks[1].Status = SubTaskStatusDoing
	tasks[1].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//5. 开始MCP扫描
	callbacks.NewPlanStepCallback(step02, texts.execMcpScan)
	callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, texts.aigWorking, texts.execMcpScanDesc)

	var scanResults *mcp.McpResult
	var scanType string
	var CodeLanguage string

	if transport == "url" {
		scanType = texts.urlScan
		url := params.Content
		if url == "" {
			return fmt.Errorf(texts.urlEmpty)
		}
		if !strings.HasPrefix(url, "http") {
			return fmt.Errorf(texts.urlInvalid)
		}
		callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, texts.aigStartScan, fmt.Sprintf(texts.startScanUrl, url))
		target = url
		r, err := scanner.InputUrl(ctx, url)
		if err != nil || r == nil {
			return fmt.Errorf(texts.inputUrlFailed, err)
		}
		results, err := scanner.ScanLink(ctx, r, quickMode)
		if err != nil {
			return err
		}
		scanResults = results
	} else if transport == "code" {
		scanType = texts.codeScan
		// 创建临时目录用于存储上传的文件
		tempDir := "uploads"
		if err := os.MkdirAll(tempDir, 0755); err != nil {
			gologger.Errorf("%s: %v", texts.createTempDir, err)
			return err
		}
		callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, texts.aigStartScan, texts.startCodeScan)
		var folder string
		if len(files) > 0 {
			// 远程下载
			for _, file := range files {
				// 下载文件
				gologger.Infof(texts.downloadFile, file)
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
					gologger.Errorln(texts.unsupportedFileType, strings.Join(supports, ","))
					continue
				}

				fileName := filepath.Join(tempDir, fmt.Sprintf("tmp-%d%s", time.Now().UnixMicro(), ext))
				err := DownloadFile(m.Server, request.SessionId, file, fileName)
				if err != nil {
					return fmt.Errorf(texts.downloadFileFailed, err)
				}
				gologger.Infof(texts.downloadSuccess, file)
				extractPath, _ := filepath.Abs(filepath.Join(tempDir, fmt.Sprintf("tmp-%d", time.Now().UnixMicro())))
				switch ext {
				case ".zip", ".whl":
					err = utils.ExtractZipFile(fileName, extractPath)
				case ".tgz", ".tar.gz":
					err = utils.ExtractTGZ(fileName, extractPath)
				default:
					return errors.New(texts.extractFile)
				}
				if err != nil {
					return errors.New(fmt.Sprintf(texts.extractFailed, err))
				}
				folder = extractPath
			}
		} else {
			target = params.Content
			extractPath, _ := filepath.Abs(filepath.Join(tempDir, fmt.Sprintf("tmp-%d", time.Now().UnixMicro())))
			err := utils.GitClone(params.Content, extractPath, 10*time.Minute)
			if err != nil {
				return fmt.Errorf(texts.cloneFailed, err)
			}
			folder = extractPath
		}

		// 判断文件夹是否存在
		if info, err := os.Stat(folder); os.IsNotExist(err) || !info.IsDir() {
			return fmt.Errorf(texts.codePathNotExist, folder)
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
	callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, texts.aigCompleted, texts.mcpScanTaskComplete)

	// 更新任务计划
	tasks[1].Status = SubTaskStatusDone
	tasks[2].Status = SubTaskStatusDoing
	tasks[2].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//6. 生成最终报告
	step03 := tasks[2].StepId
	callbacks.NewPlanStepCallback(step03, texts.genMcpReport)

	statusId03 := uuid.New().String()
	callbacks.StepStatusUpdateCallback(step03, statusId03, AgentStatusCompleted, texts.aigWorking, texts.mcpReportGenStart)
	toolId03 := uuid.New().String()

	// 完成报告生成
	completedTool03 := CreateTool(toolId03, "mcp_report_generator", ToolStatusDone, texts.mcpReportGenComplete, texts.generate, texts.scanLog, "")
	callbacks.ToolUsedCallback(step03, statusId03, texts.reportGenComplete, []Tool{completedTool03})
	callbacks.StepStatusUpdateCallback(step03, statusId03, AgentStatusCompleted, texts.aigCompleted, texts.mcpReportGenComplete)
	endTime := time.Now().Unix()
	//7. 发送任务最终结果
	result := map[string]interface{}{
		"readme":     readMe,
		"score":      CalcMcpScore(scanResults.Issues),
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
