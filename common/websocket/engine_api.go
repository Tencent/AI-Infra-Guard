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

package websocket

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/gin-gonic/gin"
)

// HandleEngineScan runs the TypeScript scan engine and returns its JSON report.
// The request body is forwarded on stdin and is not written to the log.
func HandleEngineScan(c *gin.Context) {
	body, err := io.ReadAll(io.LimitReader(c.Request.Body, 1<<20))
	if err != nil || !json.Valid(body) || len(body) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "配置格式不正确"})
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Minute)
	defer cancel()
	if c.Query("stream") == "1" {
		streamEngine(c, ctx, body)
		return
	}
	out, err := runEngine(ctx, body)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": err.Error()})
		return
	}
	var payload map[string]any
	if json.Unmarshal(out, &payload) != nil {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": "扫描失败"})
		return
	}
	if message, ok := payload["error"].(string); ok && message != "" {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": message})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": 0, "data": payload})
}

// HandleEngineList returns saved scan summaries.
func HandleEngineList(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 15*time.Second)
	defer cancel()
	writeEngineJSON(c, ctx, "runs", "--json")
}

// HandleEngineGet returns one saved scan report.
func HandleEngineGet(c *gin.Context) {
	id := c.Param("id")
	if len(id) != 36 {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": "扫描编号不正确"})
		return
	}
	for _, char := range id {
		if (char < '0' || char > '9') && (char < 'a' || char > 'f') && (char < 'A' || char > 'F') && char != '-' {
			c.JSON(http.StatusOK, gin.H{"status": 1, "message": "扫描编号不正确"})
			return
		}
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 15*time.Second)
	defer cancel()
	writeEngineJSON(c, ctx, "show", id, "--json")
}

func streamEngine(c *gin.Context, ctx context.Context, body []byte) {
	node, cli, err := engineCLI()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": err.Error()})
		return
	}
	cmd := exec.CommandContext(ctx, node, cli, "run", "--config", "-", "--stream")
	cmd.Stdin = bytes.NewReader(body)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": "扫描失败"})
		return
	}
	if err := cmd.Start(); err != nil {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": "扫描失败"})
		return
	}
	header := c.Writer.Header()
	header.Set("Content-Type", "text/event-stream; charset=utf-8")
	header.Set("Cache-Control", "no-cache")
	header.Set("X-Accel-Buffering", "no")
	flusher, _ := c.Writer.(http.Flusher)
	scanner := bufio.NewScanner(stdout)
	scanner.Buffer(make([]byte, 0, 64*1024), 1<<20)
	for scanner.Scan() {
		fmt.Fprintf(c.Writer, "data: %s\n\n", scanner.Bytes())
		if flusher != nil {
			flusher.Flush()
		}
	}
	_ = cmd.Wait()
}

func writeEngineJSON(c *gin.Context, ctx context.Context, args ...string) {
	out, err := runEngineArgs(ctx, nil, args...)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": err.Error()})
		return
	}
	var payload any
	if json.Unmarshal(out, &payload) != nil {
		c.JSON(http.StatusOK, gin.H{"status": 1, "message": "扫描失败"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": 0, "data": payload})
}

func engineCLI() (string, string, error) {
	node, err := exec.LookPath("node")
	if err != nil {
		return "", "", errors.New("未找到 node")
	}
	seeds := []string{}
	if cwd, err := os.Getwd(); err == nil {
		seeds = append(seeds, cwd)
	}
	if exe, err := os.Executable(); err == nil {
		seeds = append(seeds, filepath.Dir(exe))
	}
	for _, seed := range seeds {
		dir := seed
		for i := 0; i < 6; i++ {
			cli := filepath.Join(dir, "engine", "dist", "cli.js")
			if _, err := os.Stat(cli); err == nil {
				return node, cli, nil
			}
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	return "", "", errors.New("扫描引擎还没有构建")
}

func runEngine(ctx context.Context, body []byte) ([]byte, error) {
	return runEngineArgs(ctx, body, "run", "--config", "-", "--json")
}

func runEngineArgs(ctx context.Context, body []byte, args ...string) ([]byte, error) {
	node, cli, err := engineCLI()
	if err != nil {
		return nil, err
	}
	cmd := exec.CommandContext(ctx, node, append([]string{cli}, args...)...)
	if body != nil {
		cmd.Stdin = bytes.NewReader(body)
	}
	var stdout bytes.Buffer
	cmd.Stdout = &stdout
	runErr := cmd.Run()
	var payload struct {
		Error string `json:"error"`
	}
	if json.Unmarshal(stdout.Bytes(), &payload) == nil && payload.Error != "" {
		return nil, errors.New(payload.Error)
	}
	if runErr != nil {
		if errors.Is(ctx.Err(), context.DeadlineExceeded) {
			return nil, errors.New("扫描超时")
		}
		return nil, errors.New("扫描失败")
	}
	return stdout.Bytes(), nil
}
