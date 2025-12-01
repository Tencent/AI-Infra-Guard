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
