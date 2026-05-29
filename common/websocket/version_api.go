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
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	version "github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/gin-gonic/gin"
)

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const (
	// githubTagsAPI is the GitHub API endpoint for listing repository tags.
	githubTagsAPI = "https://api.github.com/repos/Tencent/AI-Infra-Guard/tags"

	// versionCacheTTL controls how long the latest version result is cached.
	versionCacheTTL = 10 * time.Minute

	// githubRequestTimeout is the HTTP client timeout for GitHub API calls.
	githubRequestTimeout = 10 * time.Second
)

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

// VersionCheckResponse is the JSON payload returned by the version-check endpoint.
type VersionCheckResponse struct {
	CurrentVersion string `json:"current_version" example:"v4.1.10"` // Currently running version
	LatestVersion  string `json:"latest_version" example:"v4.1.11"`  // Latest version from GitHub
	UpdateRequired bool   `json:"update_required"`                   // True if latest > current
	Message        string `json:"message" example:"A new version is available"` // Human-readable message
}

// versionCache stores the last fetched latest version to avoid hammering GitHub.
type versionCache struct {
	mu        sync.RWMutex
	version   string
	fetchedAt time.Time
}

var latestVersionCache = &versionCache{}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------

// HandleVersionCheck godoc
//
//	@Summary		Check for version updates
//	@Description	Returns the current running version, the latest available version from
//	@Description	GitHub releases (tags), and whether an update is required.
//	@Tags			system
//	@Produce		json
//	@Success		200	{object}	APIResponse{data=VersionCheckResponse}
//	@Router			/api/v1/system/version [get]
func HandleVersionCheck(c *gin.Context) {
	current := version.GetVersion()

	latest, err := getLatestVersion()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": fmt.Sprintf("failed to fetch latest version: %v", err),
			"data": VersionCheckResponse{
				CurrentVersion: current,
				LatestVersion:  "",
				UpdateRequired: false,
				Message:        fmt.Sprintf("Unable to check for updates: %v", err),
			},
		})
		return
	}

	needUpdate := compareVersions(current, latest)

	msg := "You are running the latest version"
	if needUpdate {
		msg = fmt.Sprintf("A new version %s is available (current: %s)", latest, current)
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "ok",
		"data": VersionCheckResponse{
			CurrentVersion: current,
			LatestVersion:  latest,
			UpdateRequired: needUpdate,
			Message:        msg,
		},
	})
}

// ---------------------------------------------------------------------------
// GitHub tag fetching (with cache)
// ---------------------------------------------------------------------------

// githubTag represents a single tag from the GitHub API response.
type githubTag struct {
	Name string `json:"name"`
}

// getLatestVersion fetches the latest version tag from GitHub (cached).
func getLatestVersion() (string, error) {
	// Check cache first.
	latestVersionCache.mu.RLock()
	if latestVersionCache.version != "" && time.Since(latestVersionCache.fetchedAt) < versionCacheTTL {
		v := latestVersionCache.version
		latestVersionCache.mu.RUnlock()
		return v, nil
	}
	latestVersionCache.mu.RUnlock()

	// Fetch from GitHub.
	client := &http.Client{Timeout: githubRequestTimeout}
	req, err := http.NewRequest("GET", githubTagsAPI+"?per_page=10", nil)
	if err != nil {
		return "", fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Accept", "application/vnd.github.v3+json")
	req.Header.Set("User-Agent", "AI-Infra-Guard/"+version.GetVersion())

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("request GitHub API: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("GitHub API returned status %d", resp.StatusCode)
	}

	var tags []githubTag
	if err := json.NewDecoder(resp.Body).Decode(&tags); err != nil {
		return "", fmt.Errorf("decode response: %w", err)
	}

	if len(tags) == 0 {
		return "", fmt.Errorf("no tags found in repository")
	}

	// Find the highest semver tag (tags from GitHub are not guaranteed sorted).
	latest := ""
	for _, t := range tags {
		name := t.Name
		if !strings.HasPrefix(name, "v") {
			continue
		}
		if latest == "" || compareVersions(latest, name) {
			latest = name
		}
	}

	if latest == "" {
		return "", fmt.Errorf("no valid version tags found")
	}

	// Update cache.
	latestVersionCache.mu.Lock()
	latestVersionCache.version = latest
	latestVersionCache.fetchedAt = time.Now()
	latestVersionCache.mu.Unlock()

	return latest, nil
}

// ---------------------------------------------------------------------------
// Version comparison helpers
// ---------------------------------------------------------------------------

// compareVersions returns true if b is strictly greater than a (semver-like).
// Expects format "vMAJOR.MINOR.PATCH" (e.g. "v4.1.10").
func compareVersions(a, b string) bool {
	aParts := parseVersion(a)
	bParts := parseVersion(b)

	for i := 0; i < 3; i++ {
		if bParts[i] > aParts[i] {
			return true
		}
		if bParts[i] < aParts[i] {
			return false
		}
	}
	return false
}

// parseVersion extracts [major, minor, patch] from a version string like "v4.1.10".
func parseVersion(v string) [3]int {
	v = strings.TrimPrefix(v, "v")
	parts := strings.SplitN(v, ".", 3)

	var result [3]int
	for i := 0; i < 3 && i < len(parts); i++ {
		n, _ := strconv.Atoi(parts[i])
		result[i] = n
	}
	return result
}
