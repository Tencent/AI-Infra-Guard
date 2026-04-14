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
	"archive/zip"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
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
	defaultGitHubRepo   = "Tencent/AI-Infra-Guard"
	defaultGitHubBranch = "main"
	githubZipURLFmt     = "https://codeload.github.com/%s/zip/refs/heads/%s"
	githubTagZipURLFmt  = "https://codeload.github.com/%s/zip/refs/tags/%s"

	// dataDirs lists the sub-directories inside data/ that are synced.
	// Callers may override via UpdateDataRequest.Dirs.
	dataDirsDefault = "fingerprints,vuln,vuln_en,mcp,eval,agents"
)

// UpdateStatus holds the current state of a data-sync operation.
type UpdateStatus struct {
	Running   bool      `json:"running"`
	Success   *bool     `json:"success,omitempty"`
	StartedAt time.Time `json:"started_at,omitempty"`
	FinishedAt *time.Time `json:"finished_at,omitempty"`
	Message   string    `json:"message"`
	// FilesUpdated is the number of files written to disk.
	FilesUpdated int `json:"files_updated"`
	// Ref is the branch or tag that was used.
	Ref string `json:"ref,omitempty"`
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
//	  "ref":          "main",          // branch or tag, default: "main"
//	  "is_tag":       false,           // set true when ref is a tag
//	  "github_token": "",              // optional, avoids GitHub rate-limit (60 req/h anon)
//	  "dirs":         "fingerprints,vuln,vuln_en,mcp,eval,agents"  // optional
//	}
type UpdateDataRequest struct {
	Ref         string `json:"ref"`
	IsTag       bool   `json:"is_tag"`
	GithubToken string `json:"github_token"`
	Dirs        string `json:"dirs"`
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
//	@Description	Downloads the repository archive from GitHub and overwrites the local
//	@Description	data/ sub-directories (fingerprints, vuln, vuln_en, mcp, eval, agents).
//	@Description	The operation runs asynchronously; poll GET /api/v1/system/update-status
//	@Description	for progress.  Only one sync may run at a time.
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
		Message:   "downloading archive from GitHub…",
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

	// 1. Build download URL
	var downloadURL string
	if req.IsTag {
		downloadURL = fmt.Sprintf(githubTagZipURLFmt, defaultGitHubRepo, req.Ref)
	} else {
		downloadURL = fmt.Sprintf(githubZipURLFmt, defaultGitHubRepo, req.Ref)
	}

	// 2. Download archive
	setStatus(fmt.Sprintf("downloading %s …", downloadURL), 0)
	body, err := downloadArchive(downloadURL, req.GithubToken)
	if err != nil {
		finish(false, fmt.Sprintf("download failed: %v", err), 0)
		return
	}

	// 3. Extract & overwrite
	setStatus("extracting archive …", 0)
	dirs := splitDirs(req.Dirs)
	n, err := extractDataDirs(body, dirs)
	if err != nil {
		finish(false, fmt.Sprintf("extraction failed: %v", err), n)
		return
	}

	finish(true, fmt.Sprintf("sync complete — %d file(s) updated from ref %q", n, req.Ref), n)
}

// downloadArchive fetches the zip archive and returns its bytes.
func downloadArchive(url, token string) ([]byte, error) {
	client := &http.Client{Timeout: 5 * time.Minute}
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	if token != "" {
		req.Header.Set("Authorization", "token "+token)
	}
	req.Header.Set("User-Agent", "AI-Infra-Guard/data-updater")

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d from %s", resp.StatusCode, url)
	}

	return io.ReadAll(resp.Body)
}

// extractDataDirs extracts the requested data sub-directories from the zip
// archive and writes them to the local filesystem.
//
// GitHub's archive has a single top-level directory named
// "<repo>-<ref>/", e.g. "AI-Infra-Guard-main/".
// We strip that prefix and write only the files under data/<dir>/.
func extractDataDirs(zipBytes []byte, dirs []string) (int, error) {
	zr, err := zip.NewReader(bytes.NewReader(zipBytes), int64(len(zipBytes)))
	if err != nil {
		return 0, fmt.Errorf("invalid zip: %w", err)
	}

	// Find the top-level prefix (first directory entry).
	prefix := ""
	for _, f := range zr.File {
		if f.FileInfo().IsDir() {
			parts := strings.SplitN(f.Name, "/", 2)
			prefix = parts[0] + "/"
			break
		}
	}

	// Build a quick lookup set for the requested dirs.
	wantDir := make(map[string]bool, len(dirs))
	for _, d := range dirs {
		wantDir[strings.TrimSpace(d)] = true
	}

	filesWritten := 0
	for _, f := range zr.File {
		// Strip the top-level prefix.
		rel := strings.TrimPrefix(f.Name, prefix)
		// We only care about files under data/<wantDir>/
		if !strings.HasPrefix(rel, "data/") {
			continue
		}
		// rel is now like "data/fingerprints/foo.yaml"
		parts := strings.SplitN(rel, "/", 3) // ["data", "subdir", "rest"]
		if len(parts) < 3 {
			continue // skip "data/" itself or "data/subdir/" directory entries
		}
		subDir := parts[1]
		if !wantDir[subDir] {
			continue
		}
		if f.FileInfo().IsDir() {
			if err := os.MkdirAll(rel, 0o755); err != nil {
				return filesWritten, fmt.Errorf("mkdir %s: %w", rel, err)
			}
			continue
		}

		// Ensure parent directory exists.
		if err := os.MkdirAll(filepath.Dir(rel), 0o755); err != nil {
			return filesWritten, fmt.Errorf("mkdir %s: %w", filepath.Dir(rel), err)
		}

		// Write file.
		rc, err := f.Open()
		if err != nil {
			return filesWritten, fmt.Errorf("open zip entry %s: %w", f.Name, err)
		}
		written, writeErr := writeFile(rel, rc)
		rc.Close()
		if writeErr != nil {
			return filesWritten, fmt.Errorf("write %s: %w", rel, writeErr)
		}
		if written {
			filesWritten++
		}
	}

	return filesWritten, nil
}

// writeFile atomically writes the content of rc to path.
// It reports whether the file was actually written (always true on success).
func writeFile(path string, rc io.Reader) (bool, error) {
	data, err := io.ReadAll(rc)
	if err != nil {
		return false, err
	}
	if err := os.WriteFile(path, data, 0o644); err != nil {
		return false, err
	}
	return true, nil
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
	Running    bool       `json:"running"`
	Success    *bool      `json:"success,omitempty"`
	StartedAt  time.Time  `json:"started_at,omitempty"`
	FinishedAt *time.Time `json:"finished_at,omitempty"`
	Message    string     `json:"message"`
	FilesUpdated int      `json:"files_updated"`
	Ref        string     `json:"ref,omitempty"`
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
