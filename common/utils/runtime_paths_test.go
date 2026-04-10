package utils

import (
	"os"
	"path/filepath"
	"testing"
)

func TestResolveRuntimeDirUsesEnvOverride(t *testing.T) {
	overrideDir := t.TempDir()
	t.Setenv(AgentScanDirEnv, overrideDir)

	resolved, err := resolveRuntimeDir(AgentScanDirEnv, "/app/agent-scan", "agent-scan")
	if err != nil {
		t.Fatalf("resolveRuntimeDir returned error: %v", err)
	}

	expected, err := filepath.Abs(overrideDir)
	if err != nil {
		t.Fatalf("filepath.Abs returned error: %v", err)
	}
	if resolved != expected {
		t.Fatalf("expected %q, got %q", expected, resolved)
	}
}

func TestCollectRuntimeDirCandidatesSearchesParentDirectories(t *testing.T) {
	rootDir := t.TempDir()
	nestedDir := filepath.Join(rootDir, "cmd", "cli")
	targetDir := filepath.Join(rootDir, "agent-scan")

	t.Setenv(AgentScanDirEnv, "")
	if err := os.MkdirAll(nestedDir, 0755); err != nil {
		t.Fatalf("failed to create nested dir: %v", err)
	}
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		t.Fatalf("failed to create target dir: %v", err)
	}

	candidates := collectRuntimeDirCandidates(AgentScanDirEnv, "/app/agent-scan", "agent-scan", nestedDir)
	expected, err := filepath.Abs(targetDir)
	if err != nil {
		t.Fatalf("filepath.Abs returned error: %v", err)
	}

	for _, candidate := range candidates {
		if candidate == expected {
			return
		}
	}
	t.Fatalf("expected candidates to include %q, got %v", expected, candidates)
}

func TestResolveUvBinUsesEnvOverride(t *testing.T) {
	overridePath := filepath.Join(t.TempDir(), "uv")
	if err := os.WriteFile(overridePath, []byte("#!/bin/sh\n"), 0755); err != nil {
		t.Fatalf("failed to create uv override: %v", err)
	}
	t.Setenv(UvBinEnv, overridePath)

	resolved, err := ResolveUvBin()
	if err != nil {
		t.Fatalf("ResolveUvBin returned error: %v", err)
	}

	expected, err := filepath.Abs(overridePath)
	if err != nil {
		t.Fatalf("filepath.Abs returned error: %v", err)
	}
	if resolved != expected {
		t.Fatalf("expected %q, got %q", expected, resolved)
	}
}
