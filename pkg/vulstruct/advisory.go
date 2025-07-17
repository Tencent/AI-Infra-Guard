// Package vulstruct 漏洞结构体
package vulstruct

import (
	"encoding/json"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"io"
	"net/http"
	"os"
	"strings"
)

// AdvisoryEngine 漏洞建议引擎结构体，用于管理版本漏洞信息
type AdvisoryEngine struct {
	ads []VersionVul
}

// NewAdvisoryEngine 创建一个新的漏洞建议引擎
// 返回: 漏洞建议引擎实例和可能的错误
func NewAdvisoryEngine() *AdvisoryEngine {
	return &AdvisoryEngine{ads: make([]VersionVul, 0)}
}

func (ae *AdvisoryEngine) LoadFromDirectory(dir string) error {
	var files []string
	var err error
	if utils.IsDir(dir) {
		files, err = utils.ScanDir(dir)
		if err != nil {
			return err
		}
	} else {
		files = []string{dir}
	}
	ads := make([]VersionVul, 0)
	for _, file := range files {
		if !strings.HasSuffix(file, ".yaml") {
			continue
		}
		body, err := os.ReadFile(file)
		if err != nil {
			gologger.WithError(err).Errorln("read directory error", file)
			continue
		}
		ad, err := ReadVersionVul(body)
		if err != nil {
			return nil, fmt.Errorf("read advisory file error %s: %w", file, err)
		}
		ads = append(ads, *ad)
	}
	ae.ads = ads
	return nil
}

func LoadRemoteVulStruct(api string) ([]VersionVul, error) {
	type msg struct {
		Data struct {
			Vuls  []json.RawMessage `json:"items"`
			Total int               `json:"total"`
		} `json:"data"`
		Message string `json:"message"`
	}
	resp, err := http.Get(api)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("http status code: %d", resp.StatusCode)
	}
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var m msg
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	ads := make([]VersionVul, 0)
	for _, raw := range m.Data.Vuls {
		ad, err := ReadVersionVul(raw)
		if err != nil {
			gologger.WithError(err).Errorln("read advisory file error", raw)
			continue
		}
		ads = append(ads, *ad)
	}
	return ads, nil
}

func (ae *AdvisoryEngine) LoadFromHost(host string) error {
	ads, err := LoadRemoteVulStruct(fmt.Sprintf("http://%s/api/v1/knowledge/vulnerabilities?page=1&size=9999", host))
	if err != nil {
		return err
	}
	ae.ads = ads
	return nil
}

// GetAdvisories 根据包名和版本获取相关的漏洞建议
// PackageName: 需要检查的包名
// version: 需要检查的版本号
// 返回: 匹配的漏洞建议列表和可能的错误
func (ae *AdvisoryEngine) GetAdvisories(packageName, version string, isInternal bool) ([]VersionVul, error) {
	ret := make([]VersionVul, 0)
	for _, ad := range ae.ads {
		if ad.Info.FingerPrintName != packageName {
			continue
		}
		if version != "" && ad.Rule != "" {
			if ad.RuleCompile.AdvisoryEval(&parser.AdvisoryConfig{Version: version, IsInternal: isInternal}) {
				ret = append(ret, ad)
			}
		} else {
			ret = append(ret, ad)
		}
	}
	return ret, nil
}

// GetCount 获取当前加载的漏洞建议总数
// 返回: 漏洞建议数量
func (ae *AdvisoryEngine) GetCount() int {
	return len(ae.ads)
}
