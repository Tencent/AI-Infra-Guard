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

// Package runner 结果结构体
package runner

import (
	"encoding/json"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/preload"
	"github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
)

// Result defines an interface for result output
// 定义了结果输出的接口
type Result interface {
	STR() string  // Returns result as string format
	JSON() string // Returns result as JSON format
}

// HttpResult represents the HTTP scanning result structure
// HTTP扫描结果的结构体，包含了请求的详细信息和检测结果
type HttpResult struct {
	URL           string                 `json:"url"`            // Target URL
	Title         string                 `json:"title"`          // Page title
	ContentLength int                    `json:"content-length"` // Response content length
	StatusCode    int                    `json:"status-code"`    // HTTP status code
	ResponseTime  string                 `json:"response-time"`  // Request response time
	Fingers       []preload.FpResult     `json:"fingerprints"`   // Fingerprint detection results
	Advisories    []vulstruct.VersionVul `json:"advisories"`     // Vulnerability advisory information
	Resp          string
	s             string // Internal string representation
}

// JSON converts HttpResult to JSON string
// 将HttpResult转换为JSON字符串格式
func (r *HttpResult) JSON() string {
	if js, err := json.Marshal(r); err == nil {
		return string(js)
	}
	return ""
}
