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

package agent

import (
	"archive/tar"
	"archive/zip"
	"bytes"
	"compress/gzip"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/Tencent/AI-Infra-Guard/common/redteam"
	"github.com/Tencent/AI-Infra-Guard/common/runner"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"trpc.group/trpc-go/trpc-agent-go/tool"
	"trpc.group/trpc-go/trpc-agent-go/tool/function"
)

const (
	toolBodyLimit = 48 * 1024
	toolTextLimit = 24 * 1024
)

type toolOutcome struct {
	OK     bool   `json:"ok"`
	Detail string `json:"detail"`
}

type modelCreds struct {
	Name    string
	Token   string
	BaseURL string
}

type scenarioToolBox struct {
	target    *url.URL
	headers   map[string]string
	uploadDir string
	model     modelCreds
	agentData string
	language  string
}

func (b *scenarioToolBox) build(names []string) ([]tool.Tool, error) {
	tools := make([]tool.Tool, 0, len(names))
	for _, name := range names {
		switch name {
		case "http_fetch":
			tools = append(tools, function.NewFunctionTool(b.httpFetch,
				function.WithName("http_fetch"),
				function.WithDescription("Fetch one page on the configured target host. Use this for evidence about what the service exposes.")))
		case "fingerprint_scan":
			tools = append(tools, function.NewFunctionTool(b.fingerprintScan,
				function.WithName("fingerprint_scan"),
				function.WithDescription("Match the configured target against local AI component fingerprints and known vulnerability rules.")))
		case "probe_model":
			tools = append(tools, function.NewFunctionTool(b.probeModel,
				function.WithName("probe_model"),
				function.WithDescription("Send one short prompt to the model under test and return its reply. Judge only that reply.")))
		case "list_uploads":
			tools = append(tools, function.NewFunctionTool(b.listUploads,
				function.WithName("list_uploads"),
				function.WithDescription("List uploaded files and text members inside zip or tar.gz packages.")))
		case "read_text_file":
			tools = append(tools, function.NewFunctionTool(b.readTextFile,
				function.WithName("read_text_file"),
				function.WithDescription("Read one uploaded text file. For an archive member, pass archive.zip!path/inside.")))
		case "read_agent_config":
			tools = append(tools, function.NewFunctionTool(b.readAgentConfig,
				function.WithName("read_agent_config"),
				function.WithDescription("Read the saved agent configuration with secrets redacted.")))
		default:
			return nil, fmt.Errorf("unknown tool %s", name)
		}
	}
	return tools, nil
}

type fetchArgs struct {
	URL string `json:"url" description:"Absolute http(s) URL on the configured target host. Empty uses the target itself."`
}

func (b *scenarioToolBox) httpFetch(_ context.Context, args fetchArgs) (toolOutcome, error) {
	if b.target == nil {
		return toolOutcome{Detail: "没有配置在线地址"}, nil
	}
	raw := strings.TrimSpace(args.URL)
	if raw == "" {
		raw = b.target.String()
	}
	parsed, err := url.Parse(raw)
	if err != nil {
		return toolOutcome{Detail: "地址无法解析"}, nil
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return toolOutcome{Detail: "只允许 http 或 https"}, nil
	}
	if !sameHost(parsed, b.target) {
		return toolOutcome{Detail: "只能访问本次任务配置的目标主机"}, nil
	}
	client := &http.Client{
		Timeout: 12 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 3 {
				return fmt.Errorf("redirect limit")
			}
			if !sameHost(req.URL, b.target) {
				return fmt.Errorf("redirect left the target host")
			}
			return nil
		},
	}
	req, err := http.NewRequest(http.MethodGet, parsed.String(), nil)
	if err != nil {
		return toolOutcome{Detail: "无法创建请求"}, nil
	}
	req.Header.Set("User-Agent", "AI-Infra-Guard")
	for key, value := range b.headers {
		if strings.EqualFold(key, "host") || len(key) > 64 || len(value) > 512 {
			continue
		}
		req.Header.Set(key, value)
	}
	resp, err := client.Do(req)
	if err != nil {
		return toolOutcome{Detail: "请求失败: " + err.Error()}, nil
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, toolBodyLimit))
	text := clampText(string(body), 4000)
	return toolOutcome{
		OK:     resp.StatusCode < 500,
		Detail: fmt.Sprintf("status=%d content_type=%s\n%s", resp.StatusCode, resp.Header.Get("Content-Type"), text),
	}, nil
}

type reasonArgs struct {
	Reason string `json:"reason,omitempty" description:"Why this call is needed."`
}

func (b *scenarioToolBox) fingerprintScan(ctx context.Context, _ reasonArgs) (toolOutcome, error) {
	if b.target == nil {
		return toolOutcome{Detail: "没有配置在线地址"}, nil
	}
	fpDir := findDataDir("fingerprints")
	vulDir := findDataDir("vuln")
	if b.language == "en" {
		if en := findDataDir("vuln_en"); en != "" {
			vulDir = en
		}
	}
	if fpDir == "" || vulDir == "" {
		return toolOutcome{Detail: "本地指纹或漏洞规则目录不存在"}, nil
	}
	var (
		found []string
		errs  []string
	)
	opts := &options.Options{
		TimeOut:      8,
		RateLimit:    20,
		FPTemplates:  fpDir,
		AdvTemplates: vulDir,
		Target:       []string{b.target.String()},
		Language:     b.language,
		Headers:      headerLines(b.headers),
		Callback: func(data interface{}) {
			switch item := data.(type) {
			case runner.CallbackScanResult:
				line := fmt.Sprintf("url=%s status=%d title=%s fingerprint=%s", item.TargetURL, item.StatusCode, item.Title, item.Fingerprint)
				for i, vul := range item.Vulnerabilities {
					if i >= 12 {
						line += "\n...more advisories omitted"
						break
					}
					line += fmt.Sprintf("\n- %s [%s] %s", vul.CVEName, vul.Severity, vul.Summary)
				}
				found = append(found, line)
			case runner.CallbackErrorInfo:
				msg := "unknown error"
				if item.Error != nil {
					msg = item.Error.Error()
				}
				errs = append(errs, item.Target+": "+msg)
			}
		},
	}
	scan, err := runner.New(opts)
	if err != nil {
		return toolOutcome{Detail: "扫描器初始化失败: " + err.Error()}, nil
	}
	defer scan.Close()
	done := make(chan struct{})
	go func() {
		scan.RunEnumeration()
		close(done)
	}()
	select {
	case <-ctx.Done():
		return toolOutcome{Detail: "扫描被取消"}, ctx.Err()
	case <-done:
	}
	if len(found) == 0 && len(errs) == 0 {
		return toolOutcome{OK: true, Detail: "没有返回指纹或漏洞。目标可能不可达。"}, nil
	}
	detail := strings.Join(append(errs, found...), "\n")
	return toolOutcome{OK: len(errs) == 0, Detail: clampText(detail, 6000)}, nil
}

type probeArgs struct {
	Prompt string `json:"prompt" description:"One short prompt to send to the model under test."`
}

func (b *scenarioToolBox) probeModel(ctx context.Context, args probeArgs) (toolOutcome, error) {
	prompt := strings.TrimSpace(args.Prompt)
	if prompt == "" {
		return toolOutcome{Detail: "prompt 为空"}, nil
	}
	if utf8.RuneCountInString(prompt) > 800 {
		return toolOutcome{Detail: "prompt 超过 800 字"}, nil
	}
	if b.model.BaseURL == "" || b.model.Token == "" || b.model.Name == "" {
		return toolOutcome{Detail: "被测模型配置不完整"}, nil
	}
	endpoint := strings.TrimRight(b.model.BaseURL, "/") + "/chat/completions"
	payload := fmt.Sprintf(`{"model":%q,"temperature":0,"max_tokens":400,"messages":[{"role":"user","content":%q}]}`, b.model.Name, prompt)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, strings.NewReader(payload))
	if err != nil {
		return toolOutcome{Detail: "无法创建模型请求"}, nil
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+b.model.Token)
	client := &http.Client{Timeout: 45 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return toolOutcome{Detail: "模型请求失败"}, nil
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, toolBodyLimit))
	if resp.StatusCode >= 300 {
		return toolOutcome{Detail: fmt.Sprintf("模型返回 HTTP %d", resp.StatusCode)}, nil
	}
	reply := extractAssistantText(body)
	if reply == "" {
		reply = clampText(string(body), 2000)
	}
	return toolOutcome{OK: true, Detail: clampText(reply, 3000)}, nil
}

func (b *scenarioToolBox) listUploads(_ context.Context, _ reasonArgs) (toolOutcome, error) {
	if b.uploadDir == "" {
		return toolOutcome{Detail: "没有上传文件"}, nil
	}
	names, err := listUploadNames(b.uploadDir)
	if err != nil {
		return toolOutcome{Detail: err.Error()}, nil
	}
	if len(names) == 0 {
		return toolOutcome{Detail: "没有可读的文本文件"}, nil
	}
	return toolOutcome{OK: true, Detail: strings.Join(names, "\n")}, nil
}

type readArgs struct {
	Name string `json:"name" description:"File name from list_uploads. Use archive.zip!inner/path for a member."`
}

func (b *scenarioToolBox) readTextFile(_ context.Context, args readArgs) (toolOutcome, error) {
	if b.uploadDir == "" {
		return toolOutcome{Detail: "没有上传文件"}, nil
	}
	text, err := readUploadText(b.uploadDir, args.Name)
	if err != nil {
		return toolOutcome{Detail: err.Error()}, nil
	}
	return toolOutcome{OK: true, Detail: clampText(text, toolTextLimit)}, nil
}

func (b *scenarioToolBox) collectEvidence(ctx context.Context, plugins []redteam.Plugin) redteam.Evidence {
	need := map[string]bool{}
	for _, plugin := range plugins {
		need[plugin.Kind] = true
	}
	var ev redteam.Evidence
	if need["http"] {
		out, _ := b.httpFetch(ctx, fetchArgs{})
		ev.HTTP = out.Detail
	}
	if need["fingerprint"] {
		out, _ := b.fingerprintScan(ctx, reasonArgs{})
		ev.Fingerprint = out.Detail
	}
	if need["code"] {
		ev.Code = b.codeEvidence()
	}
	if need["agent"] {
		out, _ := b.readAgentConfig(ctx, reasonArgs{})
		ev.Agent = out.Detail
	}
	return ev
}

func (b *scenarioToolBox) codeEvidence() string {
	if b.uploadDir == "" {
		return ""
	}
	names, err := listUploadNames(b.uploadDir)
	if err != nil || len(names) == 0 {
		return ""
	}
	var buf strings.Builder
	n := 0
	for _, name := range names {
		if n >= 4 {
			break
		}
		text, err := readUploadText(b.uploadDir, name)
		if err != nil || strings.TrimSpace(text) == "" {
			continue
		}
		fmt.Fprintf(&buf, "\n# %s\n%s\n", name, clampText(text, 1500))
		n++
	}
	return clampText(buf.String(), 6000)
}

func (b *scenarioToolBox) readAgentConfig(_ context.Context, _ reasonArgs) (toolOutcome, error) {
	if strings.TrimSpace(b.agentData) == "" {
		return toolOutcome{Detail: "没有 Agent 配置"}, nil
	}
	return toolOutcome{OK: true, Detail: clampText(redactSecrets(b.agentData), toolTextLimit)}, nil
}

func sameHost(left, right *url.URL) bool {
	if left == nil || right == nil {
		return false
	}
	return endpoint(left) == endpoint(right)
}

func endpoint(raw *url.URL) string {
	host := strings.ToLower(raw.Hostname())
	if ip := net.ParseIP(host); ip != nil {
		host = ip.String()
	}
	port := raw.Port()
	if port == "" {
		if raw.Scheme == "https" {
			port = "443"
		} else {
			port = "80"
		}
	}
	return host + ":" + port
}

func headerLines(headers map[string]string) []string {
	lines := make([]string, 0, len(headers))
	for key, value := range headers {
		if strings.TrimSpace(key) == "" {
			continue
		}
		lines = append(lines, key+":"+value)
	}
	return lines
}

func findDataDir(name string) string {
	candidates := make([]string, 0, 8)
	if env := strings.TrimSpace(os.Getenv("AIG_DATA_DIR")); env != "" {
		candidates = append(candidates, filepath.Join(env, name))
	}
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), "data", name))
	}
	if wd, err := os.Getwd(); err == nil {
		dir := wd
		for i := 0; i < 5; i++ {
			candidates = append(candidates, filepath.Join(dir, "data", name))
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	for _, candidate := range candidates {
		info, err := os.Stat(candidate)
		if err == nil && info.IsDir() {
			return candidate
		}
	}
	return ""
}

func listUploadNames(root string) ([]string, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, err
	}
	names := make([]string, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		path := filepath.Join(root, entry.Name())
		lower := strings.ToLower(entry.Name())
		switch {
		case strings.HasSuffix(lower, ".zip"):
			members, err := zipMembers(path)
			if err != nil {
				names = append(names, entry.Name()+" (unreadable zip)")
				continue
			}
			names = append(names, members...)
		case strings.HasSuffix(lower, ".tar.gz") || strings.HasSuffix(lower, ".tgz"):
			members, err := tarMembers(path)
			if err != nil {
				names = append(names, entry.Name()+" (unreadable archive)")
				continue
			}
			names = append(names, members...)
		default:
			names = append(names, entry.Name())
		}
		if len(names) >= 40 {
			break
		}
	}
	return names, nil
}

func readUploadText(root, name string) (string, error) {
	name = strings.TrimSpace(name)
	if name == "" || strings.Contains(name, "\x00") {
		return "", fmt.Errorf("文件名为空")
	}
	archive, member, packed := strings.Cut(name, "!")
	if packed {
		return readArchiveMember(root, archive, member)
	}
	path, err := safeJoin(root, name)
	if err != nil {
		return "", err
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("读取失败")
	}
	if !utf8.Valid(raw) || bytes.Contains(raw, []byte{0}) {
		return "", fmt.Errorf("不是文本文件")
	}
	return string(raw), nil
}

func readArchiveMember(root, archive, member string) (string, error) {
	path, err := safeJoin(root, archive)
	if err != nil {
		return "", err
	}
	member = strings.TrimPrefix(filepath.ToSlash(member), "/")
	if member == "" || strings.Contains(member, "..") {
		return "", fmt.Errorf("非法文件名")
	}
	lower := strings.ToLower(archive)
	if strings.HasSuffix(lower, ".zip") {
		return readZipMember(path, member)
	}
	if strings.HasSuffix(lower, ".tar.gz") || strings.HasSuffix(lower, ".tgz") {
		return readTarMember(path, member)
	}
	return "", fmt.Errorf("不支持的压缩包")
}

func readZipMember(path, member string) (string, error) {
	reader, err := zip.OpenReader(path)
	if err != nil {
		return "", fmt.Errorf("无法打开 zip")
	}
	defer reader.Close()
	for _, file := range reader.File {
		if filepath.ToSlash(file.Name) != member || file.FileInfo().IsDir() {
			continue
		}
		if file.UncompressedSize64 > toolTextLimit {
			return "", fmt.Errorf("文件过大")
		}
		rc, err := file.Open()
		if err != nil {
			return "", fmt.Errorf("无法读取压缩成员")
		}
		defer rc.Close()
		raw, err := io.ReadAll(io.LimitReader(rc, toolTextLimit))
		if err != nil {
			return "", fmt.Errorf("读取失败")
		}
		if bytes.Contains(raw, []byte{0}) || !utf8.Valid(raw) {
			return "", fmt.Errorf("不是文本文件")
		}
		return string(raw), nil
	}
	return "", fmt.Errorf("压缩包里没有这个文件")
}

func readTarMember(path, member string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("无法打开压缩包")
	}
	defer file.Close()
	gz, err := gzip.NewReader(file)
	if err != nil {
		return "", fmt.Errorf("无法解压")
	}
	defer gz.Close()
	tr := tar.NewReader(gz)
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return "", fmt.Errorf("读取压缩包失败")
		}
		if filepath.ToSlash(hdr.Name) != member || hdr.FileInfo().IsDir() {
			continue
		}
		raw, err := io.ReadAll(io.LimitReader(tr, toolTextLimit))
		if err != nil {
			return "", fmt.Errorf("读取失败")
		}
		if bytes.Contains(raw, []byte{0}) || !utf8.Valid(raw) {
			return "", fmt.Errorf("不是文本文件")
		}
		return string(raw), nil
	}
	return "", fmt.Errorf("压缩包里没有这个文件")
}

func zipMembers(path string) ([]string, error) {
	reader, err := zip.OpenReader(path)
	if err != nil {
		return nil, err
	}
	defer reader.Close()
	base := filepath.Base(path)
	names := make([]string, 0, 8)
	for _, file := range reader.File {
		if file.FileInfo().IsDir() || strings.Contains(file.Name, "..") {
			continue
		}
		names = append(names, base+"!"+filepath.ToSlash(file.Name))
		if len(names) >= 30 {
			break
		}
	}
	return names, nil
}

func tarMembers(path string) ([]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	gz, err := gzip.NewReader(file)
	if err != nil {
		return nil, err
	}
	defer gz.Close()
	tr := tar.NewReader(gz)
	base := filepath.Base(path)
	names := make([]string, 0, 8)
	for {
		hdr, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		if hdr.FileInfo().IsDir() || strings.Contains(hdr.Name, "..") {
			continue
		}
		names = append(names, base+"!"+filepath.ToSlash(hdr.Name))
		if len(names) >= 30 {
			break
		}
	}
	return names, nil
}

func safeJoin(root, name string) (string, error) {
	clean := filepath.Clean(name)
	if clean == "." || strings.HasPrefix(clean, "..") || filepath.IsAbs(clean) {
		return "", fmt.Errorf("非法文件名")
	}
	full := filepath.Join(root, clean)
	rel, err := filepath.Rel(root, full)
	if err != nil || strings.HasPrefix(rel, "..") {
		return "", fmt.Errorf("非法文件名")
	}
	return full, nil
}

var secretPattern = regexp.MustCompile(`(?i)(token|password|secret|api[_-]?key|authorization)(\s*[:=]\s*["']?)([^\s"',}]+)`)

func redactSecrets(text string) string {
	return secretPattern.ReplaceAllString(text, `${1}${2}***`)
}

func clampText(text string, limit int) string {
	text = strings.ReplaceAll(text, "\x00", "")
	if utf8.RuneCountInString(text) <= limit {
		return text
	}
	runes := []rune(text)
	return string(runes[:limit]) + "\n...truncated"
}

func extractAssistantText(body []byte) string {
	text := string(body)
	marker := `"content":`
	idx := strings.Index(text, marker)
	if idx < 0 {
		return ""
	}
	rest := strings.TrimSpace(text[idx+len(marker):])
	if !strings.HasPrefix(rest, `"`) {
		return ""
	}
	var out string
	if err := json.NewDecoder(strings.NewReader(rest)).Decode(&out); err != nil {
		return ""
	}
	return out
}
