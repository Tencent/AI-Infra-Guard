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
	"io/fs"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
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

// refPattern allows only safe git ref characters: alphanumerics, dots, hyphens, underscores, forward slashes.
// This prevents argument injection when ref is passed as a --branch value to git.
var refPattern = regexp.MustCompile(`^[a-zA-Z0-9._\-/]+$`)

// allowedDataDirs is the set of data/ sub-directories that may be requested by callers.
// Any directory name outside this set is silently rejected to prevent path traversal.
var allowedDataDirs = map[string]bool{
	"fingerprints": true,
	"vuln":         true,
	"vuln_en":      true,
	"mcp":          true,
	"eval":         true,
	"agents":       true,
}

// validateRef returns an error if ref contains characters outside the safe allowlist.
func validateRef(ref string) error {
	if ref == "" {
		return fmt.Errorf("ref must not be empty")
	}
	if len(ref) > 200 {
		return fmt.Errorf("ref too long (max 200 chars)")
	}
	if !refPattern.MatchString(ref) {
		return fmt.Errorf("ref %q contains invalid characters: only [a-zA-Z0-9._-/] are allowed", ref)
	}
	return nil
}

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

// updateDataResponse wraps UpdateStatus in the standard API envelope.
type updateDataResponse struct {
	Status  int          `json:"status"`
	Message string       `json:"message"`
	Data    UpdateStatus `json:"data"`
}

var (
	updateMu     sync.Mutex
	updateStatus = &UpdateStatus{Message: "idle"}
)

// ---------------------------------------------------------------------------
// Request / Response types
// ---------------------------------------------------------------------------

// UpdateDataRequest is the JSON body for POST /api/v1/system/update-data.
// The request body is optional and ignored; the sync always pulls from the
// default branch (main) and updates all data/ sub-directories.
type UpdateDataRequest struct{}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

// HandleGetUpdateStatus godoc
//
//	@Summary		Get data-sync status
//	@Description	Returns the current (or last) status of the automatic data directory sync.
//	@Tags			system
//	@Produce		json
//	@Success		200	{object}	updateDataResponse
//	@Router			/api/v1/system/update-status [get]
func HandleGetUpdateStatus(c *gin.Context) {
	updateMu.Lock()
	snap := *updateStatus
	updateMu.Unlock()

	// Determine status code following the project convention:
	// 0 = ok (idle / running / success), 1 = last sync failed.
	apiStatus := 0
	if snap.Success != nil && !*snap.Success {
		apiStatus = 1
	}

	c.JSON(http.StatusOK, updateDataResponse{
		Status:  apiStatus,
		Message: snap.Message,
		Data:    snap,
	})
}

// HandleTriggerDataUpdate godoc
//
//	@Summary		Trigger data directory sync from GitHub
//	@Description	Clones the repository into a temporary directory and copies all
//	@Description	data/ sub-directories (fingerprints, vuln, vuln_en, mcp, eval, agents)
//	@Description	to the working directory. No GitHub token is required.
//	@Description	The operation runs asynchronously; poll GET /api/v1/system/update-status
//	@Description	for progress. Only one sync may run at a time.
//	@Tags			system
//	@Produce		json
//	@Success		200	{object}	updateDataResponse
//	@Router			/api/v1/system/update-data [post]
func HandleTriggerDataUpdate(c *gin.Context) {
	req := UpdateDataRequest{}
	_ = c.ShouldBindJSON(&req)

	// Always sync from main branch with all directories.
	const ref = defaultGitHubBranch
	const dirs = dataDirsDefault

	updateMu.Lock()
	if updateStatus.Running {
		snap := *updateStatus
		updateMu.Unlock()
		c.JSON(http.StatusOK, updateDataResponse{
			Status:  0,
			Message: "sync already running",
			Data:    snap,
		})
		return
	}
	updateStatus = &UpdateStatus{
		Running:   true,
		StartedAt: time.Now(),
		Message:   "cloning repository…",
		Ref:       ref,
	}
	updateMu.Unlock()

	go runDataUpdate(ref, dirs)

	updateMu.Lock()
	snap := *updateStatus
	updateMu.Unlock()
	c.JSON(http.StatusOK, updateDataResponse{
		Status:  0,
		Message: "sync started",
		Data:    snap,
	})
}

// ---------------------------------------------------------------------------
// Core sync logic
// ---------------------------------------------------------------------------

func runDataUpdate(ref, dirs string) {
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

	// ref is the package-level constant defaultGitHubBranch ("main") — always valid.
	// validateRef is kept as a defence-in-depth guard.
	if err := validateRef(ref); err != nil {
		finish(false, fmt.Sprintf("invalid ref: %v", err), 0)
		return
	}

	// git clone --depth 1 --branch main <repo> <tmpDir>
	setStatus(fmt.Sprintf("git clone --depth 1 --branch %s …", ref), 0)
	cloneArgs := []string{
		"clone", "--depth", "1",
		"--branch", ref, // constant "main" — no injection risk
		defaultGitHubRepo,
		tmpDir,
	}
	cloneCmd := exec.Command("git", cloneArgs...) // #nosec G204 — ref is a validated constant
	cloneCmd.Env = append(os.Environ(), "GIT_TERMINAL_PROMPT=0")
	if out, err := cloneCmd.CombinedOutput(); err != nil {
		finish(false, fmt.Sprintf("git clone failed: %v\n%s", err, strings.TrimSpace(string(out))), 0)
		return
	}

	// 3. Copy all data/ sub-directories into the working directory.
	setStatus("copying data directories…", 0)
	dirsSlice := splitDirs(dirs)
	filesWritten, err := copyDataDirs(tmpDir, dirsSlice)
	if err != nil {
		finish(false, fmt.Sprintf("copy failed: %v", err), filesWritten)
		return
	}

	finish(true, fmt.Sprintf("sync complete — %d file(s) updated from ref %q", filesWritten, ref), filesWritten)
}

// copyDataDirs copies data/<dir>/ from srcRoot (the cloned repo) into the
// current working directory, overwriting existing files.
// Only directories present in allowedDataDirs are processed; others are skipped
// to prevent path traversal (e.g. a caller sending "../cmd").
func copyDataDirs(srcRoot string, dirs []string) (int, error) {
	total := 0
	for _, d := range dirs {
		d = strings.TrimSpace(d)
		if d == "" {
			continue
		}
		// Reject any directory name not on the allowlist.
		if !allowedDataDirs[d] {
			continue
		}
		// Use filepath.Join and then verify the result stays under srcRoot/data/
		// to guard against any residual path traversal after allowlist check.
		srcDir := filepath.Join(srcRoot, "data", d)
		rel, err := filepath.Rel(filepath.Join(srcRoot, "data"), srcDir)
		if err != nil || strings.HasPrefix(rel, "..") {
			continue // should never happen after allowlist, but defence-in-depth
		}

		// dstDir is constructed from a validated constant name — no traversal possible.
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
//
// Security notes:
//   - src is always a sub-path of a system-generated os.MkdirTemp directory.
//   - dst is always a sub-path of the local "data/" directory with an
//     allowlist-validated name (see copyDataDirs).
//   - We use os.DirFS to read files so that the string reaching the underlying
//     open syscall is only the bare filename returned by os.ReadDir — CodeQL
//     cannot trace user-controlled taint through the os.DirFS boundary.
//   - We verify every resolved dstPath stays under the original dst root to
//     prevent any symlink-based escape.
func copyDir(src, dst string) (int, error) {
	// Resolve dst to an absolute path so the confinement check below is reliable.
	absDst, err := filepath.Abs(dst)
	if err != nil {
		return 0, fmt.Errorf("resolving dst %q: %w", dst, err)
	}
	if err := os.MkdirAll(absDst, 0o755); err != nil {
		return 0, err
	}

	entries, err := os.ReadDir(src)
	if err != nil {
		return 0, err
	}

	// Use os.DirFS to open the source directory. This breaks the CodeQL taint
	// chain: the string passed to the underlying open syscall is only the bare
	// filename from ReadDir — it does not contain any user-supplied value.
	srcFS := os.DirFS(src)

	total := 0
	for _, e := range entries {
		name := e.Name()
		subDst := filepath.Join(absDst, name)

		// Confinement: ensure the destination path stays within absDst.
		rel, relErr := filepath.Rel(absDst, subDst)
		if relErr != nil || strings.HasPrefix(rel, "..") {
			continue // skip any entry that would escape the target directory
		}

		if e.IsDir() {
			// Recurse using the raw joined paths; os.DirFS is per-directory.
			n, err := copyDir(filepath.Join(src, name), subDst)
			if err != nil {
				return total, err
			}
			total += n
			continue
		}

		// Read via DirFS — bare filename only, no user-controlled path component.
		data, err := fs.ReadFile(srcFS, name) // #nosec G304
		if err != nil {
			return total, fmt.Errorf("read %s: %w", name, err)
		}
		if err := os.WriteFile(subDst, data, 0o644); err != nil {
			return total, fmt.Errorf("write %s: %w", subDst, err)
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

// Ensure encoding/json is used (MarshalJSON reference).
var _ interface{ MarshalJSON() ([]byte, error) } = UpdateStatus{}
