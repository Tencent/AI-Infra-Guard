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
	Timeout int               `json:"timeout"`
	Model   struct {
		Model   string `json:"model"`
		Token   string `json:"token"`
		BaseUrl string `json:"base_url"`
	} `json:"model"`
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
		// 动态描述文本模板
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
		texts.generateReport = "生成结构化扫描报告"
	}
	targets := strings.Split(strings.TrimSpace(request.Content), "\n")
	if len(request.Attachments) > 0 {
		// 创建临时目录用于存储上传的文件
		tempDir := "temp_uploads"
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
	// AI分析部分
	type Item struct {
		Title string `json:"title"`
		Desc  string `json:"desc"`
	}
	model := models.NewOpenAI(reqScan.Model.Token, reqScan.Model.Model, reqScan.Model.BaseUrl)
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
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusRunning, "Thinking", "")
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
	//callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, texts.targetConfig, fmt.Sprintf(texts.targetCountTemplate, len(targets)))
	opts.Target = targets
	// 结果收集
	scanResults := make([]runner.CallbackScanResult, 0)
	mu := sync.Mutex{}
	step02 := tasks[1].StepId
	statustool := uuid.New().String()
	toolId02 := uuid.New().String()

	prompt2 := `
你在执行AI基础设施扫描任务，你正在完成todo:{todo}
然后将以下文本转换为进度任务中的todo,加入你自己的思考，而不是简单罗列:
target count:{target-count}
	 {config}
## 返回格式 example
` + "```json\n" + `
[
{"title":"思考","desc":"在开始扫描前，需要确保所有必要的工具和数据库都已就绪。这就像医生手术前检查器械一样重要。"},
{"title":"执行1","desc":"✓ 目标锁定成功 - 识别到1个待扫描目标 ✓ 指纹库加载完成 - 已装载36种识别模式 ✓ 漏洞数据库就绪 - 涵盖394个已知漏洞特征"},
{"title":"Agent反思","desc":"环境配置符合预期，所有组件状态良好。我现在已经具备了执行任务所需的全部能力。"},
]
` + "\n```\n"
	if language == "en" {
		prompt2 += "## Return in English"
	}
	prompt2 = strings.ReplaceAll(prompt2, "{todo}", texts.initEnv)
	prompt2 = strings.ReplaceAll(prompt2, "{target-count}", fmt.Sprintf(texts.targetCountTemplate, len(targets)))
	var config string

	processFunc := func(data interface{}) {
		mu.Lock()
		defer mu.Unlock()
		switch v := data.(type) {
		case runner.CallbackScanResult:
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
			status := uuid.NewString()
			callbacks.StepStatusUpdateCallback(step02, status, AgentStatusRunning, texts.scanResult, "AI analysis")
			callbacks.ToolUseLogCallback(toolId02, texts.aiScannerTool, step02, log)
			prompt := fmt.Sprintf("这是AI基础设施扫描的扫描结果，请你根据以下文本进行总结和归纳，你最后要补充一句(后面将调用未授权检测工具继续扫描,不需要一模一样的文字，大致意思是这样就可以):'我将进行截图分析,继续探索网页上可能的漏洞点'，扫描结果如下:\n%s\n", log)
			if language == "en" {
				prompt += "## 返回使用全英文"
			}
			response2, _ := model.ChatResponse(context.Background(), prompt)
			callbacks.StepStatusUpdateCallback(step02, status, AgentStatusCompleted, texts.scanResult, response2)
			// AI分析
			newUuid := uuid.New().String()
			func() {
				callbacks.StepStatusUpdateCallback(step02, newUuid, AgentStatusRunning, "A.I.G is Thinking", "")
				defer func() {
					callbacks.StepStatusUpdateCallback(step02, newUuid, AgentStatusCompleted, "A.I.G Finished", "")
				}()
				screenshotData, vulInfo, summary, err := runner.Analysis(v.TargetURL, v.Resp, language, model)
				if err != nil {
					gologger.WithError(err).Errorf("写入回调结果失败: %v", err)
					return
				}
				v.Reason = summary
				if len(screenshotData) > 0 {
					tmpPath := path.Join(os.TempDir(), fmt.Sprintf("%d.jpg", time.Now().UnixMicro()))
					err := os.WriteFile(tmpPath, screenshotData, 0644)
					if err != nil {
						gologger.WithError(err).Errorf("write file failed: %v", err)
						return
					}
					info, err := UploadFile(t.Server, tmpPath)
					if err != nil {
						gologger.WithError(err).Errorf("upload file failed: %v", err)
						return
					}
					v.ScreenShot = "/api/v1/images/" + info.Data.FileUrl
					if vulInfo.Severity == "high" || vulInfo.Severity == "medium" {
						v.Vulnerabilities = append(v.Vulnerabilities, *vulInfo)
					}
				}
				// summary
				vData, _ := json.Marshal(v.Vulnerabilities)
				summaryPrompt := "根据以下我提供的漏洞信息，请总结一下发现x个漏洞，会导致xx业务风险，建议xx修复，几句简短的话概括，若未提供漏洞信息，就说目前暂时无漏洞发现。漏洞信息如下:\n" + string(vData)
				if language == "en" {
					summaryPrompt += "## 返回使用全英文"
				}
				summary2, _ := model.ChatResponse(context.Background(), summaryPrompt)
				v.Summary = summary2
			}()
			scanResults = append(scanResults, v)
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
			config += v.Text + "\n"
		default:
			gologger.Errorf("processFunc unknown type: %T\n", v)
		}
	}
	opts.SetCallback(processFunc)
	r, err := runner.New(opts) // 创建runner
	if err != nil {
		return fmt.Errorf("new runner failed: %v", err)
	}
	defer r.Close() // 关闭runner

	prompt2 = strings.ReplaceAll(prompt2, "{config}", config)
	response2, err := model.ChatResponse(context.Background(), prompt2)
	if err != nil {
		return fmt.Errorf("chat response failed: %v", err)
	}
	var items2 []Item
	data2 := models.GetJsonString(response2)
	_ = json.Unmarshal([]byte(data2), &items2)
	//4. 完成初始化
	callbacks.StepStatusUpdateCallback(step01, statusId01, AgentStatusCompleted, items2[0].Title, items2[0].Desc)
	for _, item := range items2[1 : len(items2)-1] {
		s1 := uuid.NewString()
		callbacks.StepStatusUpdateCallback(step01, s1, AgentStatusRunning, "思考中", "AI思考中")
		time.Sleep(time.Millisecond * 600)
		callbacks.StepStatusUpdateCallback(step01, s1, AgentStatusCompleted, item.Title, item.Desc)
	}

	// 更新任务计划
	tasks[0].Status = SubTaskStatusDone
	tasks[1].Status = SubTaskStatusDoing
	tasks[1].StartedAt = time.Now().Unix()
	callbacks.PlanUpdateCallback(tasks)

	//5. 创建runner并执行扫描
	callbacks.NewPlanStepCallback(step02, texts.execScan)
	statusId02 := uuid.NewString()
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
		[]Tool{CreateTool(toolId03, texts.reportGeneratorTool, ToolStatusDone, texts.reportGenToolDesc, texts.generateReport, "", fmt.Sprintf("%d", len(scanResults)))})

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
