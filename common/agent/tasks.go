package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
	iputil "github.com/projectdiscovery/utils/ip"

	"github.com/Tencent/AI-Infra-Guard/common/utils"

	"github.com/Tencent/AI-Infra-Guard/common/utils/models"

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
	Timeout int               `json:"timeout,omitempty"`
	Model   struct {
		Model   string `json:"model"`
		Token   string `json:"token"`
		BaseUrl string `json:"base_url"`
	} `json:"model,omitempty"`
}

type AIInfraScanAgent struct {
	Server string
}

func (t *AIInfraScanAgent) GetName() string {
	return TaskTypeAIInfraScan
}
func (t *AIInfraScanAgent) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	var reqScan ScanRequest
	if len(request.Params) > 0 {
		if err := json.Unmarshal(request.Params, &reqScan); err != nil {
			return err
		}
	}

	language := request.Language
	if language == "" {
		language = "zh"
	}

	// 初始化语言文本
	texts := initTexts(language)

	// 处理目标和附件
	targets, err := t.prepareTargets(request, reqScan, texts)
	if err != nil {
		return err
	}
	reqScan.Target = targets

	if reqScan.Timeout == 0 {
		reqScan.Timeout = 30
	}

	// 判断是否使用AI模式
	useAI := reqScan.Model.Token != "" || reqScan.Model.BaseUrl != ""
	var model *models.OpenAI
	if useAI {
		if reqScan.Model.BaseUrl == "" && reqScan.Model.Model == "" {
			return fmt.Errorf("model parameters are required")
		}
		model = &models.OpenAI{
			BaseUrl: reqScan.Model.BaseUrl,
			Model:   reqScan.Model.Model,
			Key:     reqScan.Model.Token,
		}
	}

	return t.executeScan(ctx, request, reqScan, texts, callbacks, model)
}

// scanTexts 包含所有语言相关的文本
type scanTexts struct {
	initEnv, execScan, genReport, aigWorking, aigCompleted, initConfig, portDetection, targetConfig, scanComplete, reportGen                               string
	createTempDir, downloadFile, readFile, portScan, foundPort, portCount, targetCount, foundVuln, noVuln, execError, config, scanResult                   string
	initDescTemplate, portDetectDescTemplate, portCompleteTemplate, targetCountTemplate, webAppTemplate, vulnFoundTemplate, noVulnTemplate, errorTemplate  string
	scanningDesc, execScanDesc, scanCompleteDesc, taskCompleteDesc, reportGenDesc, reportGenToolDesc, scanResultTemplate                                   string
	downloadFileLog, execScanTool, scanTool, generateReportTool, nmapTool, aiScannerTool, reportGeneratorTool, scanOperation, targetSystem, generateReport string
}

// initTexts 初始化语言文本
func initTexts(language string) scanTexts {
	var texts scanTexts
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
		texts.initEnv = "准备扫描环境"
		texts.execScan = "执行深度扫描"
		texts.genReport = "智能分析与报告生成"
		texts.aigWorking = "Agent正在工作"
		texts.aigCompleted = "Agent完成工作"
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
		texts.scanResult = "Agent发现"
		texts.initDescTemplate = "开始初始化AI基础设施扫描环境"
		texts.portDetectDescTemplate = "正在自动识别IP: %s"
		texts.portCompleteTemplate = "%s 端口探测完成"
		texts.targetCountTemplate = "目标数量: %d"
		texts.webAppTemplate = "WEB应用: %s "
		texts.vulnFoundTemplate = "URL:%s %s发现漏洞:%d\n"
		texts.noVulnTemplate = "URL:%s %s扫描完成,未发现漏洞\n"
		texts.errorTemplate = "执行错误: host:%s %s\n"
		texts.scanningDesc = "开始对目标系统进行多维度扫描"
		texts.execScanDesc = "正在执行AI基础设施扫描"
		texts.scanCompleteDesc = "完成扫描"
		texts.taskCompleteDesc = "AI基础设施扫描任务完成"
		texts.reportGenDesc = "我需要提供更有价值的洞察..."
		texts.reportGenToolDesc = "正在生成扫描报告"
		texts.scanResultTemplate = "扫描结果: %d 条"
		texts.downloadFileLog = "开始下载文件: %s"
		texts.execScanTool = "执行扫描"
		texts.scanTool = "扫描"
		texts.generateReportTool = "生成报告"
		texts.nmapTool = "nmap"
		texts.aiScannerTool = "ai_scanner"
		texts.reportGeneratorTool = "report_generator"
		texts.scanOperation = "扫描"
		texts.targetSystem = "目标系统"
		texts.generateReport = "生成结构化扫描报告"
	}
	return texts
}

// prepareTargets 处理目标和附件
func (t *AIInfraScanAgent) prepareTargets(request TaskRequest, reqScan ScanRequest, texts scanTexts) ([]string, error) {
	targets := strings.Split(strings.TrimSpace(request.Content), "\n")

	if len(request.Attachments) == 0 {
		return targets, nil
	}

	tempDir := "temp_uploads"
	if err := os.MkdirAll(tempDir, 0755); err != nil {
		gologger.Errorf("%s: %v", texts.createTempDir, err)
		return nil, err
	}

	for _, file := range request.Attachments {
		gologger.Infof(texts.downloadFileLog, file)
		fileName := filepath.Join(tempDir, fmt.Sprintf("tmp-%d.%s", time.Now().UnixMicro(), filepath.Ext(file)))
		if err := utils.DownloadFile(t.Server, request.SessionId, file, fileName); err != nil {
			gologger.WithError(err).Errorln(texts.downloadFile)
			return nil, err
		}
		lines, err := os.ReadFile(fileName)
		if err != nil {
			gologger.WithError(err).Errorln(texts.readFile)
			return nil, err
		}
		targets = append(targets, strings.Split(string(lines), "\n")...)
	}

	return targets, nil
}

// scanPortsAndPrepareTargets 扫描端口并准备最终目标列表
func (t *AIInfraScanAgent) scanPortsAndPrepareTargets(targets []string, step01 string, texts scanTexts, callbacks TaskCallbacks) ([]string, error) {
	finalTargets := []string{}
	var hosts []string

	for _, target := range targets {
		if iputil.IsIP(target) {
			hosts = append(hosts, target)
		}
		finalTargets = append(finalTargets, target)
	}

	for _, host := range hosts {
		statusNmap := uuid.NewString()
		toolId := uuid.NewString()
		callbacks.StepStatusUpdateCallback(step01, statusNmap, AgentStatusRunning, texts.portDetection, fmt.Sprintf(texts.portDetectDescTemplate, host))
		callbacks.ToolUsedCallback(step01, statusNmap, texts.nmapTool, []Tool{
			CreateTool(toolId, texts.nmapTool, SubTaskStatusDoing, texts.portScan, texts.nmapTool, "-T4 -p 11434,1337,7000-9000", ""),
		})

		portScanResult, err := utils.NmapScan(host, "11434,1337,7000-9000")
		if err != nil {
			return nil, err
		}

		success := 0
		for _, port := range portScanResult.Hosts {
			address := port.Address.Addr
			for _, ported := range port.Ports.PortList {
				if ported.State.State == "open" {
					finalTargets = append(finalTargets, fmt.Sprintf("%s:%d", address, ported.PortID))
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

	return finalTargets, nil
}

// executeScan 执行扫描任务的统一入口
func (t *AIInfraScanAgent) executeScan(ctx context.Context, request TaskRequest, reqScan ScanRequest, texts scanTexts, callbacks TaskCallbacks, model *models.OpenAI) error {
	// 创建任务计划
	taskTitles := []string{texts.initEnv, texts.execScan, texts.genReport}
	var tasks []SubTask
	for _, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, uuid.NewString()))
	}
	callbacks.PlanUpdateCallback(tasks)

	// 步骤1: 初始化环境
	step01 := tasks[0].StepId
	callbacks.NewPlanStepCallback(step01, texts.initEnv)
	statusId01 := uuid.NewString()
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusRunning, "Thinking", "")

	// 配置选项
	opts := &options.Options{
		TimeOut:      reqScan.Timeout,
		RateLimit:    200,
		FPTemplates:  t.Server,
		AdvTemplates: t.Server,
		WebServer:    false,
		Target:       reqScan.Target,
		LoadRemote:   true,
	}

	headers := make([]string, 0)
	for k, v := range reqScan.Headers {
		headers = append(headers, k+":"+v)
	}
	opts.Headers = headers

	// 扫描端口并准备目标
	targets, err := t.scanPortsAndPrepareTargets(reqScan.Target, step01, texts, callbacks)
	if err != nil {
		return err
	}
	opts.Target = targets

	// AI模式下的初始化反馈
	if model != nil {
		config := ""
		var configMu sync.Mutex

		// 临时回调收集配置信息
		tempCallback := func(data interface{}) {
			if v, ok := data.(runner.Step01); ok {
				configMu.Lock()
				config += v.Text + "\n"
				configMu.Unlock()
			}
		}
		opts.SetCallback(tempCallback)

		// 创建runner获取配置
		r, err := runner.New(opts)
		if err != nil {
			return fmt.Errorf("new runner failed: %v", err)
		}
		r.Close()

		// AI分析初始化配置
		prompt := fmt.Sprintf(`你在执行AI基础设施扫描任务，你正在完成todo:%s
然后将以下文本转换为进度任务中的todo,加入你自己的思考，而不是简单罗列:
target count:%s
%s
## 返回格式(只返回json格式)
`+"```json\n"+`
[
{"title":"思考","desc":"在开始扫描前，需要确保所有必要的工具和数据库都已就绪。这就像医生手术前检查器械一样重要。"},
{"title":"执行1","desc":"✓ 目标锁定成功 - 识别到1个待扫描目标 ✓ 指纹库加载完成 - 已装载36种识别模式 ✓ 漏洞数据库就绪 - 涵盖394个已知漏洞特征"},
{"title":"Agent反思","desc":"环境配置符合预期，所有组件状态良好。我现在已经具备了执行任务所需的全部能力。"},
]
`+"\n```\n", texts.initEnv, fmt.Sprintf(texts.targetCountTemplate, len(targets)), config)

		if request.Language == "en" {
			prompt += "## Return in English"
		}

		response, err := model.ChatResponse(ctx, prompt)
		gologger.Infof("AI分析初始化配置结果: %s", response)
		if err == nil {
			type Item struct {
				Title string `json:"title"`
				Desc  string `json:"desc"`
			}
			var items []Item
			data := models.GetJsonString(response)
			err = json.Unmarshal([]byte(data), &items)
			if err != nil {
				callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, texts.initConfig, "")
				callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, texts.targetConfig, fmt.Sprintf(texts.targetCountTemplate, len(targets)))
			}
			if len(items) > 0 {
				callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, items[0].Title, items[0].Desc)
				if len(items) >= 2 {
					for _, item := range items[1 : len(items)-1] {
						s1 := uuid.NewString()
						//callbacks.StepStatusUpdateCallback(step01, s1, AgentStatusRunning, "思考中", "AI思考中")
						//time.Sleep(time.Millisecond * 600)
						callbacks.StepStatusUpdateCallback(step01, s1, AgentStatusCompleted, item.Title, item.Desc)
					}
				}
			}
		}
	} else {
		callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, texts.initConfig, "")
		callbacks.StepStatusUpdateCallback(step01, uuid.NewString(), AgentStatusCompleted, texts.targetConfig, fmt.Sprintf(texts.targetCountTemplate, len(targets)))
	}

	// 更新任务计划
	tasks[0].Status = SubTaskStatusDone
	tasks[1].Status = SubTaskStatusDoing
	tasks[1].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	// 步骤2: 执行扫描
	step02 := tasks[1].StepId
	callbacks.NewPlanStepCallback(step02, texts.execScan)
	statusId02 := uuid.NewString()
	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusCompleted, texts.aigWorking, texts.scanningDesc)

	toolId02 := uuid.NewString()
	callbacks.ToolUsedCallback(step02, statusId02, texts.execScanTool,
		[]Tool{CreateTool(toolId02, texts.aiScannerTool, ToolStatusDoing, texts.execScanDesc, texts.scanOperation, texts.targetSystem, "")})

	// 收集扫描结果
	scanResults := make([]runner.CallbackScanResult, 0)
	mu := sync.Mutex{}

	processFunc := func(data interface{}) {
		mu.Lock()
		defer mu.Unlock()

		switch v := data.(type) {
		case runner.CallbackScanResult:
			var log string
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

			// AI模式下的额外分析
			if model != nil {
				status := uuid.NewString()
				callbacks.StepStatusUpdateCallback(step02, status, AgentStatusRunning, texts.scanResult, "AI analysis")

				prompt := fmt.Sprintf("这是AI基础设施扫描的扫描结果，请你根据以下文本进行总结和归纳，你最后要补充一句(后面将调用未授权检测工具继续扫描,不需要一模一样的文字，大致意思是这样就可以):'我将进行截图分析,继续探索网页上可能的漏洞点'，扫描结果如下:\n%s\n", log)
				if request.Language == "en" {
					prompt += "## 返回使用全英文"
				}
				response, _ := model.ChatResponse(context.Background(), prompt)
				callbacks.StepStatusUpdateCallback(step02, status, AgentStatusCompleted, texts.scanResult, response)
			}

			// 截图和AI分析
			newUuid := uuid.NewString()
			func() {
				callbacks.StepStatusUpdateCallback(step02, newUuid, AgentStatusRunning, "A.I.G is Thinking", "")
				defer callbacks.StepStatusUpdateCallback(step02, newUuid, AgentStatusCompleted, "A.I.G Finished", "")

				var screenshotData []byte
				var vulInfo *vulstruct.Info
				var summary string
				var err error

				if model != nil {
					screenshotData, vulInfo, summary, err = runner.Analysis(v.TargetURL, v.Resp, request.Language, model)
					if err != nil {
						gologger.WithError(err).Errorf("AI分析失败: %v", err)
						return
					}
					v.Reason = summary
				} else {
					screenshotData, err = runner.ScreenShot(v.TargetURL)
					if err != nil {
						gologger.WithError(err).Errorf("截图失败: %v", err)
						return
					}
				}

				if len(screenshotData) > 0 {
					tmpPath := path.Join(os.TempDir(), fmt.Sprintf("%d.jpg", time.Now().UnixMicro()))
					if err := os.WriteFile(tmpPath, screenshotData, 0644); err != nil {
						gologger.WithError(err).Errorf("write file failed: %v", err)
						return
					}
					info, err := utils.UploadFile(t.Server, tmpPath)
					if err != nil {
						gologger.WithError(err).Errorf("upload file failed: %v", err)
						return
					}
					v.ScreenShot = "/api/v1/images/" + info.Data.FileUrl

					if model != nil && vulInfo != nil && (vulInfo.Severity == "high" || vulInfo.Severity == "medium") {
						v.Vulnerabilities = append(v.Vulnerabilities, *vulInfo)
					}
				}

				// AI模式生成摘要
				if model != nil {
					vData, _ := json.Marshal(v.Vulnerabilities)
					summaryPrompt := "根据以下我提供的漏洞信息，请总结一下发现x个漏洞，会导致xx业务风险，建议xx修复，几句简短的话概括，若未提供漏洞信息，就说目前暂时无漏洞发现。漏洞信息如下:\n" + string(vData)
					if request.Language == "en" {
						summaryPrompt += "## 返回使用全英文"
					}
					summary2, _ := model.ChatResponse(context.Background(), summaryPrompt)
					v.Summary = summary2
				}
			}()

			scanResults = append(scanResults, v)

		case runner.CallbackErrorInfo:
			callbacks.ToolUseLogCallback(toolId02, texts.aiScannerTool, step02, fmt.Sprintf(texts.errorTemplate, v.Target, v.Error))
		case runner.CallbackProcessInfo, runner.CallbackReportInfo, runner.Step01:
			// 忽略这些类型
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}

	opts.SetCallback(processFunc)
	r, err := runner.New(opts)
	if err != nil {
		return fmt.Errorf("new runner failed: %v", err)
	}
	defer r.Close()

	// 执行扫描
	r.RunEnumeration()

	// 计算安全评分
	advies := make([]vulstruct.Info, 0)
	for _, item := range scanResults {
		advies = append(advies, item.Vulnerabilities...)
	}
	score := r.CalcSecScore(advies)

	callbacks.StepStatusUpdateCallback(step02, statusId02, AgentStatusCompleted, texts.aigCompleted, texts.scanCompleteDesc)
	callbacks.ToolUsedCallback(step02, statusId02, texts.execScanTool,
		[]Tool{CreateTool(toolId02, texts.aiScannerTool, ToolStatusDone, texts.scanComplete, texts.scanOperation, texts.targetSystem, fmt.Sprintf(texts.scanResultTemplate, len(scanResults)))})
	callbacks.StepStatusUpdateCallback(step02, uuid.NewString(), AgentStatusCompleted, texts.aigCompleted, texts.taskCompleteDesc)

	// 更新任务计划
	tasks[1].Status = SubTaskStatusDone
	tasks[2].Status = SubTaskStatusDoing
	tasks[2].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	// 步骤3: 生成报告
	step03 := tasks[2].StepId
	callbacks.NewPlanStepCallback(step03, texts.genReport)
	statustool := uuid.NewString()
	callbacks.StepStatusUpdateCallback(step03, statustool, AgentStatusCompleted, texts.aigWorking, texts.reportGenDesc)

	toolId03 := uuid.NewString()
	callbacks.ToolUsedCallback(step03, statustool, texts.generateReportTool,
		[]Tool{CreateTool(toolId03, texts.reportGeneratorTool, ToolStatusDone, texts.reportGenToolDesc, texts.generateReport, "", fmt.Sprintf("%d", len(scanResults)))})

	// 发送最终结果
	result := map[string]interface{}{
		"total":   len(advies),
		"score":   score.SecScore,
		"results": scanResults,
	}
	tasks[2].Status = SubTaskStatusDone
	callbacks.PlanUpdateCallback(tasks)
	callbacks.ResultCallback(result)

	return nil
}
