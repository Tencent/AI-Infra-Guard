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

// Package cmd 实现命令行界面
package cmd

import (
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/spf13/cobra"
)

// rootCmd 表示基础命令
var rootCmd = &cobra.Command{
	Use:   "ai-infra-guard",
	Short: "AI基础设施安全检测工具",
	Long:  `AI-Infra-Guard是一个针对AI基础设施的安全检测工具，包含扫描、MCP检测功能,支持webui操作。`,
}

// Execute 添加所有子命令到根命令并设置标志
// 这由main.main()调用，仅调用一次
func Execute() {
	options.ShowBanner()
	if err := rootCmd.Execute(); err != nil {
		gologger.Fatalf("执行命令失败: %s\n", err.Error())
	}
}

func init() {
	// 在这里，您可以定义根命令的标志和配置设置
	// Cobra支持持久性标志，如果在这里定义的话，它们将对所有子命令可用
	// rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.cobra.yaml)")

	// Cobra也支持本地标志，只在直接调用此操作时运行
	// rootCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
}
