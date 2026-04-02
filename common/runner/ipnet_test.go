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

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// collectTargets 将 chan string 收集为 []string，便于断言
func collectTargets(ch chan string) []string {
	var result []string
	for s := range ch {
		result = append(result, s)
	}
	return result
}

// TestTargets_WithSpace 测试包含空格的目标返回空 channel
func TestTargets_WithSpace(t *testing.T) {
	ch := Targets("192.168.1.1 192.168.1.2")
	result := collectTargets(ch)
	// 包含空格时应返回空
	assert.Empty(t, result, "包含空格的目标应返回空结果")
}

// TestTargets_WithStar 测试包含星号的目标返回空 channel
func TestTargets_WithStar(t *testing.T) {
	ch := Targets("192.168.1.*")
	result := collectTargets(ch)
	// 包含 * 时应返回空
	assert.Empty(t, result, "包含 * 的目标应返回空结果")
}

// TestTargets_SingleIP 测试单个 IP 直接返回该 IP
func TestTargets_SingleIP(t *testing.T) {
	ch := Targets("192.168.1.1")
	result := collectTargets(ch)
	// 单个 IP 应直接返回
	require.Len(t, result, 1, "单个 IP 应返回一个结果")
	assert.Equal(t, "192.168.1.1", result[0], "返回的 IP 应与输入一致")
}

// TestTargets_Hostname 测试主机名直接返回
func TestTargets_Hostname(t *testing.T) {
	ch := Targets("example.com")
	result := collectTargets(ch)
	// 非 CIDR、无特殊字符时应直接返回
	require.Len(t, result, 1, "主机名应返回一个结果")
	assert.Equal(t, "example.com", result[0], "返回的主机名应与输入一致")
}

// TestTargets_CIDR_Small 测试 /30 CIDR 展开 4 个 IP
func TestTargets_CIDR_Small(t *testing.T) {
	ch := Targets("192.168.1.0/30")
	result := collectTargets(ch)
	// /30 包含 4 个 IP（192.168.1.0 - 192.168.1.3）
	assert.Len(t, result, 4, "/30 CIDR 应展开为 4 个 IP")
	assert.Contains(t, result, "192.168.1.0")
	assert.Contains(t, result, "192.168.1.3")
}

// TestTargets_CIDR_32 测试 /32 CIDR 仅展开单个 IP
func TestTargets_CIDR_32(t *testing.T) {
	ch := Targets("10.0.0.1/32")
	result := collectTargets(ch)
	// /32 应只有 1 个 IP
	require.Len(t, result, 1, "/32 CIDR 应展开为 1 个 IP")
	assert.Equal(t, "10.0.0.1", result[0])
}

// TestIPAddresses_Valid 测试合法 CIDR 返回正确的 IP 列表
func TestIPAddresses_Valid(t *testing.T) {
	ips, err := IPAddresses("192.168.0.0/30")
	require.NoError(t, err, "合法 CIDR 不应报错")
	// /30 应返回 4 个 IP
	assert.Len(t, ips, 4, "/30 应返回 4 个 IP")
	assert.Equal(t, "192.168.0.0", ips[0], "第一个 IP 应为网络地址")
	assert.Equal(t, "192.168.0.3", ips[3], "最后一个 IP 应为广播地址")
}

// TestIPAddresses_Invalid 测试非法 CIDR 返回错误
func TestIPAddresses_Invalid(t *testing.T) {
	_, err := IPAddresses("not-a-cidr")
	// 非法 CIDR 应返回错误
	assert.Error(t, err, "非法 CIDR 应返回错误")
}

// TestIPAddresses_SingleHost 测试 /32 CIDR 返回单个 IP
func TestIPAddresses_SingleHost(t *testing.T) {
	ips, err := IPAddresses("172.16.0.5/32")
	require.NoError(t, err)
	require.Len(t, ips, 1, "/32 应只返回 1 个 IP")
	assert.Equal(t, "172.16.0.5", ips[0])
}

// TestIPAddresses_Slash24 测试 /24 CIDR 返回 256 个 IP
func TestIPAddresses_Slash24(t *testing.T) {
	ips, err := IPAddresses("10.0.0.0/24")
	require.NoError(t, err)
	// /24 包含 256 个 IP（.0 - .255）
	assert.Len(t, ips, 256, "/24 应返回 256 个 IP")
	assert.Equal(t, "10.0.0.0", ips[0])
	assert.Equal(t, "10.0.0.255", ips[255])
}
