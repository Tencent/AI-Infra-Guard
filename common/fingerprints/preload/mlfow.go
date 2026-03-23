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

// Package preload mlflow漏洞go语言写法
package preload

import (
	"errors"
	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"net/url"
	"regexp"
	"strings"
)

// Mlflow struct implements fingerprint detection for MLflow services
type Mlflow struct {
}

// Match checks if the given URI points to an MLflow service
// 通过检查页面标题来判断是否为 MLflow 服务
func (m Mlflow) Match(httpx *httpx.HTTPX, uri string) bool {
	headers := map[string]string{
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66",
	}
	resp, err := httpx.Get(uri+"/", headers)
	if err != nil {
		return false
	}
	if resp.StatusCode == 200 && strings.Contains(resp.DataStr, "<title>MLflow</title>") {
		return true
	}
	return false
}

// GetVersion attempts to extract the MLflow version from the service
// 通过以下步骤获取 MLflow 版本：
// 1. 获取主页面
// 2. 提取 JS 文件路径
// 3. 请求 JS 文件
// 4. 通过正则表达式匹配版本号
func (m Mlflow) GetVersion(httpx *httpx.HTTPX, uri string) (string, error) {
	flag := `{INTERNAL_ERROR:"INTERNAL_ERROR",INVALID_PARAMETER_VALUE:"INVALID_PARAMETER_VALUE",RESOURCE_DOES_NOT_EXIST:"RESOURCE_DOES_NOT_EXIST",PERMISSION_DENIED:"PERMISSION_DENIED",RESOURCE_CONFLICT:"RESOURCE_CONFLICT"}`
	headers := map[string]string{
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66",
	}
	resp, err := httpx.Get(uri+"/", headers)
	if err != nil {
		return "", err
	}
	if resp.StatusCode != 200 {
		return "", errors.New("request code != 200")
	}
	jsPath := utils.GetMiddleText(`script defer="defer" src="`, `">`, resp.DataStr)
	if jsPath == "" {
		return "", errors.New("not found js path")
	}
	newURL, err := url.JoinPath(uri, jsPath)
	if err != nil {
		return "", err
	}
	resp2, err := httpx.Get(newURL, headers)
	if err != nil {
		return "", err
	}
	index := strings.Index(resp2.DataStr, flag)
	if index == -1 {
		return "", errors.New("not found flag")
	}
	parrern := `\d+\.\d+\.\d+`
	regex := regexp.MustCompile(parrern)
	match := regex.FindString(resp2.DataStr[index+len(flag):])
	return match, nil
}

// Name returns the identifier for this fingerprint detector
func (m Mlflow) Name() string {
	return "mlflow"
}
