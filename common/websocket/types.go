// Package websocket 实现WebSocket服务器功能
package websocket

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

const (
	// WSMsgTypeLog 日志消息类型
	WSMsgTypeLog = "log"
	// WSMsgTypeScanResult 扫描结果消息类型
	WSMsgTypeScanResult = "result"
	// WSMsgTypeProcessInfo 进度消息类型
	WSMsgTypeProcessInfo = "processing"
	// WSMsgTypeReportInfo 报告消息类型
	WSMsgTypeReportInfo = "report"
	// WSMsgTypeScanRet 扫描状态返回
	WSMsgTypeScanRet = "scan_ret"
)

const (
	WSLogLevelInfo  = "info"
	WSLogLevelDebug = "debug"
	WSLogLevelError = "error"
)

// ScanRequest 扫描请求结构
type ScanRequest struct {
	ScanType string            `json:"scan_type"`
	Target   []string          `json:"target,omitempty"`
	Headers  map[string]string `json:"headers,omitempty"`
	Lang     string            `json:"lang,omitempty"`
}

// Response 基础响应结构
type Response struct {
	Status  int         `json:"status"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// WSMessage WebSocket消息结构
type WSMessage struct {
	Type    string      `json:"type"`
	Content interface{} `json:"content"`
}

// ReportInfo 报告信息结构
type ReportInfo struct {
	SecScore   int `json:"sec_score"`
	HighRisk   int `json:"high_risk"`
	MiddleRisk int `json:"middle_risk"`
	LowRisk    int `json:"low_risk"`
}

// ScanRet 扫描状态返回
type ScanRet struct {
	Status int    `json:"status"`
	Msg    string `json:"msg"`
}

// Log 日志信息结构
type Log struct {
	Message string `json:"message"`
	Level   string `json:"level"`
}

func SuccessResponse(c *gin.Context, message interface{}) {
	c.JSON(http.StatusOK, gin.H{"status": 0, "message": message})
}

func ErrorResponse(c *gin.Context, message interface{}) {
	c.JSON(http.StatusOK, gin.H{"status": 1, "message": message})
}

func ErrorResponseWithStatus(c *gin.Context, message interface{}, status int) {
	c.JSON(http.StatusOK, gin.H{"status": status, "message": message})
}
