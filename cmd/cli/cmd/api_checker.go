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

package cmd

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/spf13/cobra"
)

const (
	apiCheckerDirEnv    = "AIG_API_CHECKER_DIR"
	apiCheckerPythonEnv = "AIG_API_CHECKER_PYTHON"
)

var apiCheckerCmd = &cobra.Command{
	Use:                "api-checker [serve|calibrate|test|detect|audit|pamela|qtest|list] [参数...]",
	Aliases:            []string{"relay-checker"},
	Short:              "运行 AI 模型指纹与 API 中转检测",
	DisableFlagParsing: true,
	Long: `运行随 AIG 发布的 Python API Checker。

不带参数时进入交互菜单；serve 启动 HTTP/SSE 服务（监听地址由 HOST、PORT 控制）；
其余参数原样传给 checker CLI。Python 解释器和服务目录可分别通过
AIG_API_CHECKER_PYTHON、AIG_API_CHECKER_DIR 覆盖。`,
	RunE: runAPIChecker,
}

func init() {
	rootCmd.AddCommand(apiCheckerCmd)
}

func runAPIChecker(command *cobra.Command, args []string) error {
	checkerDir, err := findAPICheckerDir()
	if err != nil {
		return err
	}
	python, err := findAPICheckerPython()
	if err != nil {
		return err
	}

	script := "main.py"
	scriptArgs := args
	if len(args) > 0 && (args[0] == "serve" || args[0] == "server") {
		script = "server.py"
		scriptArgs = args[1:]
		if len(scriptArgs) > 0 {
			return errors.New("api-checker serve 不接收命令行参数；请使用 HOST、PORT 环境变量")
		}
	}

	childArgs := append([]string{filepath.Join(checkerDir, script)}, scriptArgs...)
	child := exec.CommandContext(command.Context(), python, childArgs...)
	child.Dir = checkerDir
	child.Env = os.Environ()
	if script == "server.py" {
		if _, configured := os.LookupEnv("AIG_API_CHECKER_ROOT_PATH"); !configured {
			child.Env = append(child.Env, "AIG_API_CHECKER_ROOT_PATH=/api-checker")
		}
	}
	child.Stdin = os.Stdin
	child.Stdout = os.Stdout
	child.Stderr = os.Stderr
	if err := child.Run(); err != nil {
		return fmt.Errorf("api-checker 执行失败: %w", err)
	}
	return nil
}

func findAPICheckerPython() (string, error) {
	if configured := os.Getenv(apiCheckerPythonEnv); configured != "" {
		path, err := exec.LookPath(configured)
		if err != nil {
			return "", fmt.Errorf("%s 指定的 Python 不可用: %w", apiCheckerPythonEnv, err)
		}
		if !filepath.IsAbs(path) {
			path, err = filepath.Abs(path)
			if err != nil {
				return "", fmt.Errorf("解析 %s 指定的 Python 路径: %w", apiCheckerPythonEnv, err)
			}
		}
		return path, nil
	}
	for _, name := range []string{"python3", "python"} {
		if path, err := exec.LookPath(name); err == nil {
			return path, nil
		}
	}
	return "", errors.New("未找到 Python 解释器，请安装 Python 3.10+ 或设置 AIG_API_CHECKER_PYTHON")
}

func findAPICheckerDir() (string, error) {
	if configured := os.Getenv(apiCheckerDirEnv); configured != "" {
		if isAPICheckerDir(configured) {
			return filepath.Abs(configured)
		}
		return "", fmt.Errorf("%s 不是有效的 checker 目录: %s", apiCheckerDirEnv, configured)
	}

	var roots []string
	if cwd, err := os.Getwd(); err == nil {
		roots = append(roots, cwd)
	}
	if executable, err := os.Executable(); err == nil {
		roots = append(roots, filepath.Dir(executable))
	}

	seen := make(map[string]struct{})
	for _, root := range roots {
		for current := root; ; current = filepath.Dir(current) {
			for _, relative := range []string{
				filepath.Join("services", "api_checker"),
				"api_checker",
			} {
				candidate := filepath.Join(current, relative)
				if _, ok := seen[candidate]; !ok {
					seen[candidate] = struct{}{}
					if isAPICheckerDir(candidate) {
						return filepath.Abs(candidate)
					}
				}
			}
			parent := filepath.Dir(current)
			if parent == current {
				break
			}
		}
	}
	return "", fmt.Errorf(
		"未找到 API checker 服务目录；请将 services/api_checker 与 AIG 一起发布，或设置 %s",
		apiCheckerDirEnv,
	)
}

func isAPICheckerDir(path string) bool {
	for _, name := range []string{"main.py", "server.py", "requirements.txt"} {
		info, err := os.Stat(filepath.Join(path, name))
		if err != nil || info.IsDir() {
			return false
		}
	}
	return true
}
