// Package vulstruct 漏洞结构体
package vulstruct

import (
	"fmt"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/common/utils"
)

// AdvisoryEngine 漏洞建议引擎结构体，用于管理版本漏洞信息
type AdvisoryEngine struct {
	ads []VersionVul
}

// NewAdvisoryEngine 创建一个新的漏洞建议引擎
// dir: 包含漏洞建议yaml文件的目录路径
// 返回: 漏洞建议引擎实例和可能的错误
func NewAdvisoryEngine(dir string) (*AdvisoryEngine, error) {
	var files []string
	var err error
	if utils.IsDir(dir) {
		files, err = utils.ScanDir(dir)
		if err != nil {
			return nil, err
		}
	} else {
		files = []string{dir}
	}
	ads := make([]VersionVul, 0)
	for _, file := range files {
		if !strings.HasSuffix(file, ".yaml") {
			continue
		}
		ad, err := ReadVersionVulSingFile(file)
		if err != nil {
			return nil, fmt.Errorf("read advisory file error %s: %w", file, err)
		}
		ads = append(ads, *ad)
	}
	return &AdvisoryEngine{ads: ads}, nil
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
