package monitoring

import (
	"sync"
	"time"

	"git.code.oa.com/trpc-go/trpc-go/metrics"
	_ "git.code.oa.com/trpc-go/trpc-log-zhiyan"
	"git.woa.com/trpc-go/tnet/log"
	_ "git.woa.com/trpc-go/trpc-metrics-zhiyan/v2"
)

// 指标组名称常量
const (
	HTTPRequestMetricGroup = "http_request" // HTTP请求指标组
	TaskMetricGroup        = "task"         // 任务指标组
	BusinessMetricGroup    = "business"     // 业务指标组
	ConnectionMetricGroup  = "connection"   // 连接监控指标组
)

// TaskTimeManager 任务时间管理器，为每个sessionId维护独立的时间记录
type TaskTimeManager struct {
	mu        sync.RWMutex
	taskTimes map[string]time.Time // sessionId -> 开始时间
}

var taskTimeManager = &TaskTimeManager{
	taskTimes: make(map[string]time.Time),
}

// StartTask 记录任务开始时间
func (ttm *TaskTimeManager) StartTask(sessionId string) {
	ttm.mu.Lock()
	defer ttm.mu.Unlock()
	ttm.taskTimes[sessionId] = time.Now()
	log.Debugf("任务开始时间记录: sessionId=%s", sessionId)
}

// GetTaskDuration 获取任务执行时间但不清理记录
func (ttm *TaskTimeManager) GetTaskDuration(sessionId string) time.Duration {
	ttm.mu.RLock()
	defer ttm.mu.RUnlock()

	startTime, exists := ttm.taskTimes[sessionId]
	if !exists {
		log.Warnf("任务开始时间未找到: sessionId=%s", sessionId)
		return 0
	}

	duration := time.Since(startTime)
	log.Debugf("任务执行时间计算: sessionId=%s, duration=%v", sessionId, duration)
	return duration
}

// GetTaskDurationAndCleanup 获取任务执行时间并清理记录
func (ttm *TaskTimeManager) GetTaskDurationAndCleanup(sessionId string) time.Duration {
	ttm.mu.Lock()
	defer ttm.mu.Unlock()

	startTime, exists := ttm.taskTimes[sessionId]
	if !exists {
		log.Warnf("任务开始时间未找到: sessionId=%s", sessionId)
		return 0
	}

	duration := time.Since(startTime)
	delete(ttm.taskTimes, sessionId) // 清理记录
	log.Debugf("任务执行时间计算并清理: sessionId=%s, duration=%v", sessionId, duration)
	return duration
}

// CleanupTask 清理任务时间记录（用于异常情况）
func (ttm *TaskTimeManager) CleanupTask(sessionId string) {
	ttm.mu.Lock()
	defer ttm.mu.Unlock()
	delete(ttm.taskTimes, sessionId)
	log.Debugf("任务时间记录清理: sessionId=%s", sessionId)
}

// HTTPMetrics HTTP请求监控指标
type HTTPMetrics struct {
	Path       string
	Method     string
	StatusCode int
	Duration   time.Duration
	ClientIP   string
}

// ReportHTTPMetrics 上报HTTP请求监控指标
func ReportHTTPMetrics(metric HTTPMetrics) {
	// 创建指标列表
	var metricList []*metrics.Metrics

	// 1. HTTP请求总量 - 每次请求计数为1，通过维度可以按路径、方法等分组
	metricList = append(metricList,
		metrics.NewMetrics("http_request_api", 1, metrics.PolicySUM))

	// 2. 请求响应时间 - 记录响应时间（单位：微秒）
	durationUs := float64(metric.Duration.Microseconds())
	metricList = append(metricList,
		metrics.NewMetrics("http_response_time", durationUs, metrics.PolicyAVG))

	// 3. 慢请求监控 - 响应时间超过阈值的请求（超过1000000微秒 = 1秒）
	if metric.Duration.Microseconds() > 1000000 {
		metricList = append(metricList,
			metrics.NewMetrics("http_request_slow", 1, metrics.PolicySUM))
	}

	// 创建多维度指标
	rec := metrics.NewMultiDimensionMetrics(
		[]*metrics.Dimension{
			{Name: "ip", Value: metric.ClientIP},
			{Name: "path", Value: metric.Path},
			{Name: "method", Value: metric.Method},
		},
		metricList)

	// 设置自定义指标组名称
	rec.Name = HTTPRequestMetricGroup

	// 上报指标
	err := metrics.Report(rec)
	if err != nil {
		log.Errorf("Report HTTP metrics error: %+v", err)
	}
}

// ReportTaskMetrics 上报任务监控指标
func ReportTaskMetrics(taskType, status string, duration time.Duration, jobID string) {
	var metricList []*metrics.Metrics

	// 1. 任务数量 - 每次调用计数为1，通过维度可以按类型、状态等分组
	metricList = append(metricList,
		metrics.NewMetrics("task_count", 1, metrics.PolicySUM))

	// 2. 根据状态使用不同的时间单位和指标名
	if status == "created" || status == "failed" {
		// 任务创建阶段 - 使用毫秒级
		durationMs := float64(duration.Milliseconds())
		metricList = append(metricList,
			metrics.NewMetrics("task_creation_time", durationMs, metrics.PolicyAVG))

		log.Infof("上报任务创建监控: taskType=%s, status=%s, duration=%v (%.2fms), jobID=%s",
			taskType, status, duration, durationMs, jobID)
	} else {
		// 任务执行阶段 - 使用秒级
		durationSec := duration.Seconds()
		metricList = append(metricList,
			metrics.NewMetrics("task_duration", durationSec, metrics.PolicyAVG))

		log.Infof("上报任务执行监控: taskType=%s, status=%s, duration=%v (%.2fs), jobID=%s",
			taskType, status, duration, durationSec, jobID)
	}

	// 创建多维度指标
	rec := metrics.NewMultiDimensionMetrics(
		[]*metrics.Dimension{
			{Name: "task_type", Value: taskType}, // 任务类型：scan、audit等
			{Name: "task_status", Value: status}, // 任务状态：created、failed、completed、terminated
		},
		metricList)

	// 设置指标组名称
	rec.Name = TaskMetricGroup

	// 上报指标
	err := metrics.Report(rec)
	if err != nil {
		log.Errorf("job_id: [%s]. Report task metrics error: %+v", jobID, err)
	}
}

// StartTaskMonitoring 开始任务监控（记录开始时间）
func StartTaskMonitoring(sessionId string) {
	taskTimeManager.StartTask(sessionId)
}

// EndTaskCreationMonitoring 结束任务创建监控（计算创建时间但不清理记录）
func EndTaskCreationMonitoring(taskType, status, sessionId string) {
	duration := taskTimeManager.GetTaskDuration(sessionId)
	ReportTaskMetrics(taskType, status, duration, sessionId)
}

// EndTaskMonitoring 结束任务监控（计算执行时间并清理记录）
func EndTaskMonitoring(taskType, status, sessionId string) {
	duration := taskTimeManager.GetTaskDurationAndCleanup(sessionId)
	ReportTaskMetrics(taskType, status, duration, sessionId)
}

// CleanupTaskMonitoring 清理任务监控记录（异常情况）
func CleanupTaskMonitoring(sessionId string) {
	taskTimeManager.CleanupTask(sessionId)
}

// ConnectionMetrics 连接监控指标
type ConnectionMetrics struct {
	ConnectionType string  // sse 或 websocket
	ConnectionID   string  // 连接ID
	Quality        float64 // 连接质量 (0-1)
	ClientIP       string  // 客户端IP
}

// ReportConnectionMetrics 上报连接监控指标
func ReportConnectionMetrics(metric ConnectionMetrics) {
	var metricList []*metrics.Metrics

	// 1. SSE连接个数 - 计数连接数量
	if metric.ConnectionType == "sse" {
		metricList = append(metricList,
			metrics.NewMetrics("sse_connection_count", 1, metrics.PolicySUM))
	}

	// 2. SSE连接质量 - 记录连接质量
	if metric.ConnectionType == "sse" {
		metricList = append(metricList,
			metrics.NewMetrics("sse_connection_quality", metric.Quality, metrics.PolicyAVG))
	}

	// 3. WebSocket连接质量 - 记录连接质量
	if metric.ConnectionType == "websocket" {
		metricList = append(metricList,
			metrics.NewMetrics("websocket_connection_quality", metric.Quality, metrics.PolicyAVG))
	}

	// 创建多维度指标
	rec := metrics.NewMultiDimensionMetrics(
		[]*metrics.Dimension{
			{Name: "ip", Value: metric.ClientIP},
			{Name: "connection_type", Value: metric.ConnectionType},
			{Name: "connection_id", Value: metric.ConnectionID},
		},
		metricList)

	// 设置指标组名称
	rec.Name = ConnectionMetricGroup

	// 上报指标
	err := metrics.Report(rec)
	if err != nil {
		log.Errorf("connection_id: [%s]. Report connection metrics error: %+v", metric.ConnectionID, err)
	}
}
