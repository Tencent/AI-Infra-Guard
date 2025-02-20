package runner

import "github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"

// CallbackScanResult 扫描结果结构
type CallbackScanResult struct {
	TargetURL       string           `json:"target_url"`
	StatusCode      int              `json:"status_code"`
	Title           string           `json:"title"`
	Fingerprint     string           `json:"fingerprint"`
	Vulnerabilities []vulstruct.Info `json:"vulnerabilities,omitempty"`
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

type FpInfos struct {
	FpName string                 `json:"name"`
	Vuls   []vulstruct.VersionVul `json:"vuls"`
}
