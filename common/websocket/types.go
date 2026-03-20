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
