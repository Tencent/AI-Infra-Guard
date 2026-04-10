package utils

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const (
	AgentScanDirEnv      = "AIG_AGENT_SCAN_DIR"
	McpScanDirEnv        = "AIG_MCP_SCAN_DIR"
	PromptSecurityDirEnv = "AIG_PROMPT_SECURITY_DIR"
	UvBinEnv             = "AIG_UV_BIN"
)

func ResolveAgentScanDir() (string, error) {
	return resolveRuntimeDir(AgentScanDirEnv, "/app/agent-scan", "agent-scan")
}

func ResolveMcpScanDir() (string, error) {
	return resolveRuntimeDir(McpScanDirEnv, "/app/mcp-scan", "mcp-scan")
}

func ResolvePromptSecurityDir() (string, error) {
	return resolveRuntimeDir(PromptSecurityDirEnv, "/app/AIG-PromptSecurity", "AIG-PromptSecurity")
}

func ResolveUvBin() (string, error) {
	if override := strings.TrimSpace(os.Getenv(UvBinEnv)); override != "" {
		return override, nil
	}
	if uvPath, err := exec.LookPath("uv"); err == nil {
		return uvPath, nil
	}
	const containerUvPath = "/usr/local/bin/uv"
	if info, err := os.Stat(containerUvPath); err == nil && !info.IsDir() {
		return containerUvPath, nil
	}
	return "", fmt.Errorf("unable to locate uv; set %s to override the path", UvBinEnv)
}

func resolveRuntimeDir(envName, containerPath, relativePath string) (string, error) {
	candidates := collectRuntimeDirCandidates(envName, containerPath, relativePath, runtimeSearchBases()...)
	for _, candidate := range candidates {
		info, err := os.Stat(candidate)
		if err == nil && info.IsDir() {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("unable to locate %s; set %s to override the path", relativePath, envName)
}

func runtimeSearchBases() []string {
	var bases []string
	if wd, err := os.Getwd(); err == nil {
		bases = append(bases, wd)
	}
	if execPath, err := os.Executable(); err == nil {
		bases = append(bases, filepath.Dir(execPath))
	}
	return bases
}

func collectRuntimeDirCandidates(envName, containerPath, relativePath string, bases ...string) []string {
	var candidates []string
	seen := make(map[string]struct{})
	addCandidate := func(path string) {
		path = strings.TrimSpace(path)
		if path == "" {
			return
		}
		path = filepath.Clean(path)
		if !filepath.IsAbs(path) {
			if absPath, err := filepath.Abs(path); err == nil {
				path = absPath
			}
		}
		if _, ok := seen[path]; ok {
			return
		}
		seen[path] = struct{}{}
		candidates = append(candidates, path)
	}

	addCandidate(os.Getenv(envName))
	addCandidate(containerPath)

	for _, base := range bases {
		base = strings.TrimSpace(base)
		if base == "" {
			continue
		}
		current := filepath.Clean(base)
		for i := 0; i < 8; i++ {
			addCandidate(filepath.Join(current, relativePath))
			parent := filepath.Dir(current)
			if parent == current {
				break
			}
			current = parent
		}
	}

	return candidates
}
