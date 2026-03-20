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

package utils

import (
	"encoding/xml"
	"fmt"
	"os/exec"
)

// 定义XML解析结构体
type NmapRun struct {
	Hosts []Host `xml:"host"`
}
type Address struct {
	Addr     string `xml:"addr,attr"`
	AddrType string `xml:"addrtype,attr"`
}

type Host struct {
	Ports   Ports   `xml:"ports"`
	Address Address `xml:"address"`
}

type Ports struct {
	PortList []Port `xml:"port"`
}

type Port struct {
	Protocol string `xml:"protocol,attr"`
	PortID   int    `xml:"portid,attr"`
	State    State  `xml:"state"`
}

type State struct {
	State string `xml:"state,attr"`
}

func NmapScan(target string, port string) (*NmapRun, error) {
	// 检测nmap是否可用
	_, err := exec.LookPath("nmap")
	if err != nil {
		return nil, fmt.Errorf("nmap不可用: %v", err)
	}
	// 执行nmap扫描（快速模式，无服务识别）
	cmd := exec.Command("nmap", "-T4", "-p", port, target, "-oX", "-")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("nmap扫描失败: %v\n输出: %s", err, string(output))
	}
	// 解析XML结果
	var result NmapRun
	if err := xml.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("解析nmap结果失败: %v", err)
	}
	return &result, nil
}
