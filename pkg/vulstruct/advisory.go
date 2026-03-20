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

// Package vulstruct 漏洞结构体
package vulstruct

import (
	"fmt"
	"os"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
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
			return fmt.Errorf("read advisory file error %s: %w", file, err)
		}
		ads = append(ads, *ad)
	}
	ae.ads = ads
	return nil
}

func (ae *AdvisoryEngine) LoadFromHost(host string) error {
	datas, err := utils.LoadRemoteVulStruct(fmt.Sprintf("http://%s/api/v1/knowledge/vulnerabilities?page=1&size=9999", host))
	if err != nil {
		return err
	}
	ads := make([]VersionVul, 0)
	for _, raw := range datas {
		ad, err := ReadVersionVul(raw)
		if err != nil {
			gologger.WithError(err).Errorln("read advisory file error", raw)
			continue
		}
		ads = append(ads, *ad)
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

// GetAll 获取所有漏洞建议
// 返回: 漏洞建议列表和可能的错误
func (ae *AdvisoryEngine) GetAll() []VersionVul {
	return ae.ads
}
