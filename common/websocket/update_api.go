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

// Package websocket provides the HTTP API handlers for the AIG web server.
package websocket

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// ---------------------------------------------------------------------------
// Constants & package-level state
// ---------------------------------------------------------------------------

const (
	defaultGitHubRepo   = "https://github.com/Tencent/AI-Infra-Guard.git"
	defaultGitHubBranch = "main"

	// dataDirsDefault lists the sub-directories inside data/ that are synced by default.
	dataDirsDefault = "fingerprints,vuln,vuln_en,mcp,eval,agents"
)

// UpdateStatus holds the current state of a data-sync operation.
type UpdateStatus struct {
	Running      bool       `json:"running"`
	Success      *bool      `json:"success,omitempty"`
	StartedAt    time.Time  `json:"started_at,omitempty"`
	FinishedAt   *time.Time `json:"finished_at,omitempty"`
	Message      string     `json:"message"`
	FilesUpdated int        `json:"files_updated"`
	Ref          string     `json:"ref,omitempty"`
}

var (
	updateMu     sync.Mutex
	updateStatus = &UpdateStatus{Message: "idle"}
)

// ---------------------------------------------------------------------------
// Request / Response types
// ---------------------------------------------------------------------------

// UpdateDataRequest is the JSON body for POST /api/v1/system/update-data.
//
//	{
//	  "ref":   "main",        // branch name or tag, default: "main"
//	  "is_tag": false,        // set true when ref is a Git tag (e.g. "v4.1.3")
//	  "dirs":  "fingerprints,vuln,vuln_en,mcp,eval,agents"  // optional
//	}
type UpdateDataRequest struct {
	Ref   string `json:"ref"`
	IsTag bool   `json:"is_tag"`
	Dirs  string `json:"dirs"`
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

// HandleGetUpdateStatus godoc
//
//	@Summary		Get data-sync status
//	@Description	Returns the current (or last) status of the automatic data directory sync.
//	@Tags			system
//	@Produce		json
//	@Success		200	{object}	UpdateStatus
//	@Router			/api/v1/system/update-status [get]
func HandleGetUpdateStatus(c *gin.Context) {
	updateMu.Lock()
	snap := *updateStatus
	updateMu.Unlock()
	c.JSON(http.StatusOK, snap)
}

// HandleTriggerDataUpdate godoc
//
//	@Summary		Trigger data directory sync from GitHub
//	@Description	Clones the repository into a temporary directory and copies the requested
//	@Description	data/ sub-directories (fingerprints, vuln, vuln_en, mcp, eval, agents)
//	@Description	to the working directory. No GitHub token is required.
//	@Description	The operation runs asynchronously; poll GET /api/v1/system/update-status
//	@Description	for progress. Only one sync may run at a time.
//	@Tags			system
//	@Accept			json
//	@Produce		json
//	@Param			body	body		UpdateDataRequest	false	"Sync options"
//	@Success		202	{object}	UpdateStatus		"Sync started"
//	@Success		200	{object}	UpdateStatus		"Already running"
//	@Failure		500	{object}	map[string]string	"Internal error"
//	@Router			/api/v1/system/update-data [post]
func HandleTriggerDataUpdate(c *gin.Context) {
	var req UpdateDataRequest
	// allow empty body
	_ = c.ShouldBindJSON(&req)

	if req.Ref == "" {
		req.Ref = defaultGitHubBranch
	}
	if req.Dirs == "" {
		req.Dirs = dataDirsDefault
	}

	updateMu.Lock()
	if updateStatus.Running {
		snap := *updateStatus
		updateMu.Unlock()
		c.JSON(http.StatusOK, snap)
		return
	}
	updateStatus = &UpdateStatus{
		Running:   true,
		StartedAt: time.Now(),
		Message:   "cloning repository…",
		Ref:       req.Ref,
	}
	updateMu.Unlock()

	go runDataUpdate(req)

	updateMu.Lock()
	snap := *updateStatus
	updateMu.Unlock()
	c.JSON(http.StatusAccepted, snap)
}

// ---------------------------------------------------------------------------
// Core sync logic
// ---------------------------------------------------------------------------

func runDataUpdate(req UpdateDataRequest) {
	setStatus := func(msg string, filesUpdated int) {
		updateMu.Lock()
		updateStatus.Message = msg
		updateStatus.FilesUpdated = filesUpdated
		updateMu.Unlock()
	}

	finish := func(success bool, msg string, filesUpdated int) {
		now := time.Now()
		updateMu.Lock()
		b := success
		updateStatus.Running = false
		updateStatus.Success = &b
		updateStatus.FinishedAt = &now
		updateStatus.Message = msg
		updateStatus.FilesUpdated = filesUpdated
		updateMu.Unlock()
	}

	// 1. Create a temporary directory for the clone.
	tmpDir, err := os.MkdirTemp("", "aig-data-sync-*")
	if err != nil {
		finish(false, fmt.Sprintf("failed to create temp dir: %v", err), 0)
		return
	}
	defer os.RemoveAll(tmpDir)

	// 2. git clone --depth 1 --branch <ref> <repo> <tmpDir>
	setStatus(fmt.Sprintf("git clone --depth 1 --branch %s …", req.Ref), 0)
	cloneArgs := []string{
		"clone", "--depth", "1",
		"--branch", req.Ref,
		defaultGitHubRepo,
		tmpDir,
	}
	cloneCmd := exec.Command("git", cloneArgs...) // #nosec G204 — args are not user-controlled paths
	cloneCmd.Env = append(os.Environ(), "GIT_TERMINAL_PROMPT=0")
	if out, err := cloneCmd.CombinedOutput(); err != nil {
		finish(false, fmt.Sprintf("git clone failed: %v\n%s", err, strings.TrimSpace(string(out))), 0)
		return
	}

	// 3. Copy the requested data/ sub-directories into the working directory.
	setStatus("copying data directories…", 0)
	dirs := splitDirs(req.Dirs)
	filesWritten, err := copyDataDirs(tmpDir, dirs)
	if err != nil {
		finish(false, fmt.Sprintf("copy failed: %v", err), filesWritten)
		return
	}

	finish(true, fmt.Sprintf("sync complete — %d file(s) updated from ref %q", filesWritten, req.Ref), filesWritten)
}

// copyDataDirs copies data/<dir>/ from srcRoot (the cloned repo) into the
// current working directory, overwriting existing files.
func copyDataDirs(srcRoot string, dirs []string) (int, error) {
	total := 0
	for _, d := range dirs {
		d = strings.TrimSpace(d)
		if d == "" {
			continue
		}
		srcDir := filepath.Join(srcRoot, "data", d)
		dstDir := filepath.Join("data", d)

		if _, err := os.Stat(srcDir); os.IsNotExist(err) {
			// sub-directory not present in this ref — skip silently
			continue
		}

		n, err := copyDir(srcDir, dstDir)
		if err != nil {
			return total, fmt.Errorf("copying data/%s: %w", d, err)
		}
		total += n
	}
	return total, nil
}

// copyDir recursively copies all files from src to dst, creating dst if needed.
// Returns the number of files written.
func copyDir(src, dst string) (int, error) {
	if err := os.MkdirAll(dst, 0o755); err != nil {
		return 0, err
	}

	entries, err := os.ReadDir(src)
	if err != nil {
		return 0, err
	}

	total := 0
	for _, e := range entries {
		srcPath := filepath.Join(src, e.Name())
		dstPath := filepath.Join(dst, e.Name())

		if e.IsDir() {
			n, err := copyDir(srcPath, dstPath)
			if err != nil {
				return total, err
			}
			total += n
			continue
		}

		data, err := os.ReadFile(srcPath) // #nosec G304 — srcPath is under tmpDir controlled by us
		if err != nil {
			return total, fmt.Errorf("read %s: %w", srcPath, err)
		}
		if err := os.WriteFile(dstPath, data, 0o644); err != nil {
			return total, fmt.Errorf("write %s: %w", dstPath, err)
		}
		total++
	}
	return total, nil
}

// splitDirs splits a comma-separated list of directory names.
func splitDirs(s string) []string {
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

// ---------------------------------------------------------------------------
// Swagger model helpers (needed by swaggo for the UpdateStatus pointer fields)
// ---------------------------------------------------------------------------

// updateStatusJSON is used only for Swagger doc generation.
type updateStatusJSON struct {
	Running      bool       `json:"running"`
	Success      *bool      `json:"success,omitempty"`
	StartedAt    time.Time  `json:"started_at,omitempty"`
	FinishedAt   *time.Time `json:"finished_at,omitempty"`
	Message      string     `json:"message"`
	FilesUpdated int        `json:"files_updated"`
	Ref          string     `json:"ref,omitempty"`
}

// MarshalJSON implements json.Marshaler so UpdateStatus can be serialised
// without exposing internal mutex state.
func (u UpdateStatus) MarshalJSON() ([]byte, error) {
	return json.Marshal(updateStatusJSON{
		Running:      u.Running,
		Success:      u.Success,
		StartedAt:    u.StartedAt,
		FinishedAt:   u.FinishedAt,
		Message:      u.Message,
		FilesUpdated: u.FilesUpdated,
		Ref:          u.Ref,
	})
}
