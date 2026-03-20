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

package runner

import "github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"

// CallbackScanResult 扫描结果结构
type CallbackScanResult struct {
	TargetURL       string           `json:"target_url"`
	StatusCode      int              `json:"status_code"`
	Title           string           `json:"title"`
	Fingerprint     string           `json:"fingerprint"`
	Vulnerabilities []vulstruct.Info `json:"vulnerabilities,omitempty"`
	Resp            string           `json:"-"`
	ScreenShot      string           `json:"screenshot,omitempty"`
	Reason          string           `json:"reason,omitempty"`
	Summary         string           `json:"summary,omitempty"` // 漏洞总览
}

// CallbackProcessInfo 进度信息结构
type CallbackProcessInfo struct {
	Current int `json:"current"`
	Total   int `json:"total"`
}

// CallbackReportInfo 报告信息结构
type CallbackReportInfo struct {
	SecScore   int `json:"sec_score"`
	HighRisk   int `json:"high_risk"`
	MediumRisk int `json:"medium_risk"`
	LowRisk    int `json:"low_risk"`
}

type CallbackErrorInfo struct {
	Target string
	Error  error
}

type FpInfos struct {
	FpName string                 `json:"name"`
	Vuls   []vulstruct.VersionVul `json:"vuls"`
	Desc   string                 `json:"desc"`
}
