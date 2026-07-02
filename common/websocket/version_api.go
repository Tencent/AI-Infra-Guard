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
	// githubReleasesLatestURL is the GitHub releases page that 302-redirects to the latest tag.
	// Using the HTML page avoids the GitHub REST API rate limit (60 req/h for unauthenticated requests).
	githubReleasesLatestURL = "https://github.com/Tencent/AI-Infra-Guard/releases/latest"

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

// getLatestVersion fetches the latest version tag from GitHub (cached).
//
// Instead of calling the GitHub REST API (which is rate-limited to 60 req/h
// for unauthenticated requests and frequently returns 403), it requests the
// GitHub releases "latest" page. GitHub responds with a 302 redirect whose
// Location header contains the tag name (e.g. .../releases/tag/v4.1.11).
//
// On any failure (network error, unexpected status, parse error) the function
// degrades gracefully by returning the currently running version and nil error,
// so HandleVersionCheck treats it as "already up to date" without surfacing
// an error to the user.
func getLatestVersion() (string, error) {
	// Check cache first.
	latestVersionCache.mu.RLock()
	if latestVersionCache.version != "" && time.Since(latestVersionCache.fetchedAt) < versionCacheTTL {
		v := latestVersionCache.version
		latestVersionCache.mu.RUnlock()
		return v, nil
	}
	latestVersionCache.mu.RUnlock()

	// Request the releases/latest page. GitHub will 302-redirect to
	// /releases/tag/vX.Y.Z. We disable automatic redirect-following so we
	// can read the tag name directly from the Location header.
	client := &http.Client{
		Timeout: githubRequestTimeout,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse // do not follow redirects automatically
		},
	}

	req, err := http.NewRequest(http.MethodGet, githubReleasesLatestURL, nil)
	if err != nil {
		// Degrade: return the current version without error.
		return version.GetVersion(), nil
	}
	req.Header.Set("Accept", "text/html,application/xhtml+xml")
	req.Header.Set("User-Agent", "AI-Infra-Guard/"+version.GetVersion())

	resp, err := client.Do(req)
	if err != nil {
		// Degrade: return the current version without error.
		return version.GetVersion(), nil
	}
	defer resp.Body.Close()

	// Expect a 301/302 redirect. Parse the tag from the Location header.
	// e.g. Location: https://github.com/Tencent/AI-Infra-Guard/releases/tag/v4.1.11
	if resp.StatusCode == http.StatusMovedPermanently || resp.StatusCode == http.StatusFound {
		location := resp.Header.Get("Location")
		if location != "" {
			idx := strings.LastIndex(location, "/")
			if idx >= 0 && idx < len(location)-1 {
				tag := location[idx+1:]
				if strings.HasPrefix(tag, "v") {
					// Update cache.
					latestVersionCache.mu.Lock()
					latestVersionCache.version = tag
					latestVersionCache.fetchedAt = time.Now()
					latestVersionCache.mu.Unlock()
					return tag, nil
				}
			}
		}
	}

	// Degrade: any unexpected situation returns the current version without error.
	return version.GetVersion(), nil
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
