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

package trpc

import (
	"trpc.group/trpc-go/trpc-go"
)

// InitTrpc 初始化trpc-go
func InitTrpc(configPath string) error {
	// 加载全局配置
	err := trpc.LoadGlobalConfig(configPath)
	if err != nil {
		return err
	}

	// 创建trpc server（这会加载插件、启动admin等）
	_ = trpc.NewServer()

	return nil
}

// GetTrpcConfig 获取trpc配置
func GetTrpcConfig() *trpc.Config {
	return trpc.GlobalConfig()
}
