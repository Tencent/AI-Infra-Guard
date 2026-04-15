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
	"errors"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/gin-gonic/gin"
	"gopkg.in/yaml.v3"
)

func HandleList(root string, loadFile func(filePath string) (interface{}, error)) gin.HandlerFunc {
	return func(c *gin.Context) {
		var allItems []interface{}
		err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
			if err != nil {
				return nil // skip entry on error
			}
			if !d.IsDir() {
				item, err := loadFile(path)
				if err != nil {
					return err
				}
				allItems = append(allItems, item)
			}
			return nil
		})
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"status":  1,
				"message": err.Error(),
			})
			return
		}
		c.JSON(http.StatusOK, gin.H{
			"status":  0,
			"message": "success",
			"data": gin.H{
				"total": len(allItems),
				"items": allItems,
			},
		})
	}
}
func HandleCreate(readAndSave func(content string) error) gin.HandlerFunc {
	return func(c *gin.Context) {
		var request struct {
			Content string `json:"content" binding:"required"`
		}
		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "content parameter is required"})
			return
		}
		if err := readAndSave(request.Content); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "failed to save config: " + err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"status": 0, "message": "created"})
	}
}

// HandleEdit returns a HandlerFunc for edit requests
func HandleEdit(updateFunc func(id string, content string) error) gin.HandlerFunc {
	return func(c *gin.Context) {
		name := c.Param("id")
		if name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "name must not be empty"})
			return
		}

		var request struct {
			Content string `json:"content" binding:"required"`
		}
		if err := c.ShouldBindJSON(&request); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "content parameter is required"})
			return
		}

		if err := updateFunc(c.Param("id"), request.Content); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "update failed: " + err.Error()})
			return
		}

		c.JSON(http.StatusOK, gin.H{"status": 0, "message": "updated"})
	}
}

// HandleDelete returns a HandlerFunc for delete requests
func HandleDelete(deleteFunc func(id string) error) gin.HandlerFunc {
	return func(c *gin.Context) {
		name := c.Param("id")
		if name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "name must not be empty"})
			return
		}

		if err := deleteFunc(name); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "delete failed: " + err.Error()})
			return
		}

		c.JSON(http.StatusOK, gin.H{"status": 0, "message": "deleted"})
	}
}

// MCP prompt management
const MCPROOT = "data/mcp"

func McpLoadFile(filePath string) (interface{}, error) {
	if filePath == "" {
		return nil, nil
	}
	if !strings.HasSuffix(filePath, ".yaml") {
		return nil, nil
	}
	var ret struct {
		mcp.PluginConfig `yaml:",inline"`
		RawData          string `yaml:"raw_data"`
	}
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var config mcp.PluginConfig
	err = yaml.Unmarshal(data, &config)
	if err != nil {
		return nil, err
	}
	ret.RawData = string(data)
	ret.PluginConfig = config
	return ret, nil
}

func mcpReadAndSave(content string) error {
	// Ensure directory exists
	if err := os.MkdirAll(MCPROOT, 0755); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	// Parse YAML to validate format
	var config mcp.PluginConfig
	err := yaml.Unmarshal([]byte(content), &config)
	if err != nil {
		return fmt.Errorf("failed to parse YAML: %w", err)
	}

	// Extract ID
	id := config.Info.ID
	if id == "" {
		return errors.New("missing info.id field")
	}

	// Safety check
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("invalid filename")
	}

	filename, err := safeJoinPath(MCPROOT, id+".yaml")
	if err != nil {
		return err
	}
	return os.WriteFile(filename, []byte(content), 0644)
}

func mcpUpdateFunc(id string, content string) error {
	// Parse YAML to validate content format
	var config mcp.PluginConfig
	if err := yaml.Unmarshal([]byte(content), &config); err != nil {
		return fmt.Errorf("failed to parse YAML: %w", err)
	}

	// Validate filename safety
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("invalid filename")
	}

	// Use provided name as filename; allow file update without forcing a rename
	filePath, err := safeJoinPath(MCPROOT, id+".yaml")
	if err != nil {
		return err
	}
	return os.WriteFile(filePath, []byte(content), 0644)
}

func mcpDeleteFunc(id string) error {
	// Validate filename safety
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("invalid filename")
	}

	filePath, pathErr := safeJoinPath(MCPROOT, id+".yaml")
	if pathErr != nil {
		return pathErr
	}
	// Check if file exists
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return errors.New("file not found")
	}
	return os.Remove(filePath)
}

// AI application inspector management
const PromptCollectionsRoot = "data/prompt_collections"

type PromptCollection struct {
	CodeExec     bool   `json:"code_exec"`
	UploadFile   bool   `json:"upload_file"`
	Product      string `json:"product"`
	MultiModal   bool   `json:"multi_modal"`
	ModelVersion string `json:"model_version"`
	Prompt       string `json:"prompt"`
	UpdateDate   string `json:"update_date"`
	WebSearch    bool   `json:"web_search"`
	SecPolicies  bool   `json:"sec_policies"`
	Affiliation  string `json:"affiliation"`
	Id           string `json:"id"`
}

func promptCollectionLoadFile(filePath string) (interface{}, error) {
	if filePath == "" {
		return nil, nil
	}
	if !strings.HasSuffix(filePath, ".json") {
		return nil, nil
	}
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}
	var config PromptCollection
	err = json.Unmarshal(data, &config)
	if err != nil {
		return nil, err
	}
	base := filepath.Base(filePath)
	config.Id = strings.Split(base, ".")[0]
	return config, nil
}

func promptCollectionReadAndSave(content string) error {
	// Validate JSON format
	var collection map[string]interface{}
	err := json.Unmarshal([]byte(content), &collection)
	if err != nil {
		return fmt.Errorf("failed to parse JSON: %w", err)
	}

	// Use ID as filename
	id, ok := collection["id"].(string)
	if !ok || id == "" {
		return errors.New("missing id field")
	}

	// Safety check
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("invalid filename")
	}

	filename, err := safeJoinPath(PromptCollectionsRoot, id+".json")
	if err != nil {
		return err
	}
	return os.WriteFile(filename, []byte(content), 0644)
}

func promptCollectionUpdateFunc(id string, content string) error {
	// Validate JSON format
	var collection map[string]interface{}
	err := json.Unmarshal([]byte(content), &collection)
	if err != nil {
		return fmt.Errorf("invalid JSON format: %w", err)
	}

	// Validate filename safety
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("invalid filename")
	}

	filename, err := safeJoinPath(PromptCollectionsRoot, id+".json")
	if err != nil {
		return err
	}
	return os.WriteFile(filename, []byte(content), 0644)
}

func promptCollectionDeleteFunc(id string) error {
	// Validate filename safety
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("invalid filename")
	}

	filePath, err := safeJoinPath(PromptCollectionsRoot, id+".json")
	if err != nil {
		return err
	}

	// Check if file exists
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return errors.New("file not found")
	}

	return os.Remove(filePath)
}
func GetJailBreak(c *gin.Context) {
	promptSecurityDir, err := utils.ResolvePromptSecurityDir()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "Failed to resolve prompt security directory: " + err.Error(),
		})
		return
	}
	dataPath := filepath.Join(promptSecurityDir, "utils", "strategy_map.json")
	data, err := os.ReadFile(dataPath)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "Failed to read strategy map: " + err.Error(),
		})
		return
	}
	var data1 interface{}
	err = json.Unmarshal(data, &data1)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "Failed to parse strategy map: " + err.Error(),
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "success",
		"data":    data1,
	})
}

// ============== Agent Scan Config Management ==============
const AgentConfigRoot = "data/agents"
const PublicUser = "public_user"

// getAgentUserDir returns the agent config directory for a user.
// username must have passed validateUsername; safeJoinPath provides an extra defence layer.
func getAgentUserDir(username string) string {
	p, err := safeJoinPath(AgentConfigRoot, username)
	if err != nil {
		// fallback to public user dir; validateUsername should have caught this
		return filepath.Join(AgentConfigRoot, PublicUser)
	}
	return p
}

// validateUsername checks that a username is safe to use in file paths (prevents path traversal)
func validateUsername(username string) bool {
	if username == "" {
		return false
	}
	if strings.Contains(username, "..") || strings.ContainsAny(username, "/\\<>:\"|?*") {
		return false
	}
	return true
}

func HandleListAgentNames(c *gin.Context) {
	username := c.GetString("username")
	if !validateUsername(username) {
		username = PublicUser
	}

	names, err := listAgentConfigNames(username)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "failed to retrieve: " + err.Error(),
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "success",
		"data":    names,
	})
}

func HandleGetAgentConfig(c *gin.Context) {
	username := c.GetString("username")
	if !validateUsername(username) {
		username = PublicUser
	}

	name := strings.TrimSpace(c.Param("name"))
	if name == "" || !isValidName(name) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "invalid config name",
		})
		return
	}

	data, err := readAgentConfigContent(username, name)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			c.JSON(http.StatusNotFound, gin.H{
				"status":  1,
				"message": "config not found",
			})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "failed to read config: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "success",
		"data":    string(data),
	})
}

// testAgentConnectivity verifies Agent configuration connectivity.
// Returns (success, message, error).
func testAgentConnectivity(content string) (bool, string, error) {
	agentScanDir, err := utils.ResolveAgentScanDir()
	if err != nil {
		return false, "", fmt.Errorf("failed to resolve agent-scan directory: %v", err)
	}
	uvBin, err := utils.ResolveUvBin()
	if err != nil {
		return false, "", fmt.Errorf("failed to resolve uv binary: %v", err)
	}
	// Create temporary file for the YAML content
	tmpFile, err := os.CreateTemp("", "agent_connect_*.yaml")
	if err != nil {
		return false, "", fmt.Errorf("failed to create temporary config file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	// Write YAML content to temp file
	if _, err := tmpFile.WriteString(content); err != nil {
		tmpFile.Close()
		return false, "", fmt.Errorf("failed to write config file: %v", err)
	}
	tmpFile.Close()

	// Run Python connectivity test script using uv
	var lastLine string
	err = utils.RunCmd(
		agentScanDir,
		uvBin,
		[]string{"run", "test_client_connect.py", "--client_file", tmpFile.Name()},
		func(line string) {
			lastLine += line
		},
	)

	if err != nil {
		return false, "", fmt.Errorf("connectivity test execution failed: %v", err)
	}
	if lastLine != "" {
		gologger.Infoln("test_agent_connect", lastLine)
	}

	// Parse the JSON output from Python script
	var result ConnectResultUpdate
	if err := json.Unmarshal([]byte(lastLine), &result); err != nil {
		return false, "", fmt.Errorf("failed to parse connectivity test result: %v", err)
	}

	return result.Content.Success, result.Content.Message, nil
}

func HandleSaveAgentConfig(c *gin.Context) {
	username := c.GetString("username")
	if !validateUsername(username) {
		username = PublicUser
	}

	name := strings.TrimSpace(c.Param("name"))
	if name == "" || !isValidName(name) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "invalid config name",
		})
		return
	}

	var req struct {
		Content string `json:"content" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "content parameter is required",
		})
		return
	}
	content := strings.TrimSpace(req.Content)
	if content == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "content must not be empty",
		})
		return
	}

	// Validate Agent connectivity before saving the config (skip when ?verify=false).
	skipVerify := strings.ToLower(strings.TrimSpace(c.Query("verify"))) == "false"
	if !skipVerify {
		success, message, err := testAgentConnectivity(content)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"status":  1,
				"message": "connectivity check failed: " + err.Error(),
			})
			return
		}
		if !success {
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "connectivity check failed: " + message,
			})
			return
		}
	}

	// Create user-specific directory
	userDir := getAgentUserDir(username)
	if err := os.MkdirAll(userDir, 0755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "failed to create directory: " + err.Error(),
		})
		return
	}

	targetPath, err := resolveAgentConfigPathForWrite(username, name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "failed to save config: " + err.Error(),
		})
		return
	}

	if err := os.WriteFile(targetPath, []byte(content), 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "failed to save config: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "Saved successfully and connectivity check passed",
	})
}

func HandleDeleteAgentConfig(c *gin.Context) {
	username := c.GetString("username")
	if !validateUsername(username) {
		username = PublicUser
	}

	name := strings.TrimSpace(c.Param("name"))
	if name == "" || !isValidName(name) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "invalid config name",
		})
		return
	}

	deleted, err := deleteAgentConfig(username, name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "delete failed: " + err.Error(),
		})
		return
	}
	if !deleted {
		c.JSON(http.StatusNotFound, gin.H{
			"status":  1,
			"message": "config not found",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "deleted",
	})
}

// listAgentConfigNamesFromDir reads config names from a given directory
func listAgentConfigNamesFromDir(dir string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return []string{}, nil
		}
		return nil, err
	}

	var names []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		switch {
		case strings.HasSuffix(entry.Name(), ".yaml"):
			names = append(names, strings.TrimSuffix(entry.Name(), ".yaml"))
		case strings.HasSuffix(entry.Name(), ".yml"):
			names = append(names, strings.TrimSuffix(entry.Name(), ".yml"))
		}
	}
	return names, nil
}

// listAgentConfigNames lists config names for a user, merging user-dir and public-dir entries with deduplication
func listAgentConfigNames(username string) ([]string, error) {
	// Read configs from user directory
	userDir := getAgentUserDir(username)
	userNames, err := listAgentConfigNamesFromDir(userDir)
	if err != nil {
		return nil, err
	}

	// If not the public user, also merge configs from the public directory
	if username != PublicUser {
		publicDir := getAgentUserDir(PublicUser)
		publicNames, err := listAgentConfigNamesFromDir(publicDir)
		if err != nil {
			return nil, err
		}

		// Merge and deduplicate
		nameSet := make(map[string]struct{})
		for _, name := range userNames {
			nameSet[name] = struct{}{}
		}
		for _, name := range publicNames {
			nameSet[name] = struct{}{}
		}

		userNames = make([]string, 0, len(nameSet))
		for name := range nameSet {
			userNames = append(userNames, name)
		}
	}

	sort.Strings(userNames)
	return userNames, nil
}

// readAgentConfigContentFromDir reads config file content from a directory
func readAgentConfigContentFromDir(dir, name string) ([]byte, error) {
	name = strings.TrimSpace(name)
	if name == "" || !isValidName(name) {
		return nil, os.ErrNotExist
	}

	cleanDir := filepath.Clean(dir)
	rootDir := filepath.Clean(AgentConfigRoot)
	relDir, err := filepath.Rel(rootDir, cleanDir)
	if err != nil || relDir == ".." || strings.HasPrefix(relDir, ".."+string(filepath.Separator)) {
		return nil, os.ErrNotExist
	}

	for _, ext := range []string{".yaml", ".yml"} {
		path := filepath.Join(cleanDir, name+ext)
		data, err := os.ReadFile(path)
		if err == nil {
			return data, nil
		}
		if !errors.Is(err, os.ErrNotExist) {
			return nil, err
		}
	}
	return nil, os.ErrNotExist
}

// readAgentConfigContent reads config content, preferring the user directory with fallback to the public directory
func readAgentConfigContent(username, name string) ([]byte, error) {
	// Ensure the username is safe for path construction; fall back to public user directory otherwise
	safeUsername := username
	if !validateUsername(safeUsername) {
		safeUsername = PublicUser
	}
	name = strings.TrimSpace(name)
	if name == "" || !isValidName(name) {
		return nil, os.ErrNotExist
	}

	// Prefer user directory
	userDir := getAgentUserDir(safeUsername)
	data, err := readAgentConfigContentFromDir(userDir, name)
	if err == nil {
		return data, nil
	}
	if !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}

	// Fall back to public directory when user directory has no match
	if safeUsername != PublicUser {
		publicDir := getAgentUserDir(PublicUser)
		return readAgentConfigContentFromDir(publicDir, name)
	}

	return nil, os.ErrNotExist
}

// resolveAgentConfigPathForWrite resolves the write path (always writes to user directory)
func resolveAgentConfigPathForWrite(username, name string) (string, error) {
	userDir := getAgentUserDir(username)
	p1, err1 := safeJoinPath(userDir, name+".yaml")
	p2, err2 := safeJoinPath(userDir, name+".yml")
	if err1 != nil && err2 != nil {
		return "", err1
	}
	candidates := []string{}
	if err1 == nil {
		candidates = append(candidates, p1)
	}
	if err2 == nil {
		candidates = append(candidates, p2)
	}
	for _, path := range candidates {
		_, statErr := os.Stat(path)
		if statErr == nil {
			return path, nil
		}
		if statErr != nil && !errors.Is(statErr, os.ErrNotExist) {
			return "", statErr
		}
	}
	return p1, nil
}

// deleteAgentConfig deletes a config entry (only from the user directory)
func deleteAgentConfig(username, name string) (bool, error) {
	userDir := getAgentUserDir(username)
	for _, ext := range []string{".yaml", ".yml"} {
		path, pathErr := safeJoinPath(userDir, name+ext)
		if pathErr != nil {
			continue
		}
		err := os.Remove(path)
		if err == nil {
			return true, nil
		}
		if errors.Is(err, os.ErrNotExist) {
			continue
		}
		return false, err
	}
	return false, nil
}

// AgentConnectRequest represents the request body for agent connect test
type AgentConnectRequest struct {
	Content string `json:"content"`
}

// AgentPromptTestRequest represents the request body for agent prompt test
type AgentPromptTestRequest struct {
	Content string `json:"content"`
	Prompt  string `json:"prompt"`
}

// ProviderResponse represents the provider_response field in result
type ProviderResponse struct {
	Raw    interface{} `json:"raw"`
	Output *string     `json:"output"`
	Error  *string     `json:"error"`
}

// ConnectResultContent represents the content of resultUpdate response
type ConnectResultContent struct {
	Success          bool              `json:"success"`
	Message          string            `json:"message"`
	ProviderResponse *ProviderResponse `json:"provider_response"`
}

// ConnectResultUpdate represents the resultUpdate response from Python script
type ConnectResultUpdate struct {
	Type    string               `json:"type"`
	Content ConnectResultContent `json:"content"`
}

func HandleAgentConnect(c *gin.Context) {
	var req AgentConnectRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "Invalid request body: " + err.Error(),
		})
		return
	}

	if req.Content == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "Content cannot be empty",
		})
		return
	}

	// Delegate to shared connectivity test helper
	success, message, err := testAgentConnectivity(req.Content)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "Failed to run connectivity test: " + err.Error(),
		})
		return
	}

	if success {
		c.JSON(http.StatusOK, gin.H{
			"status":  0,
			"message": message,
		})
	} else {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": message,
		})
	}
}

func HandleAgentPromptTest(c *gin.Context) {
	var req AgentPromptTestRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "Invalid request body: " + err.Error(),
		})
		return
	}

	if req.Content == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "Content cannot be empty",
		})
		return
	}

	if req.Prompt == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "Prompt cannot be empty",
		})
		return
	}

	// Create temporary file for the YAML content
	tmpFile, err := os.CreateTemp("", "agent_prompt_test_*.yaml")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "Failed to create temporary file: " + err.Error(),
		})
		return
	}
	defer os.Remove(tmpFile.Name())

	// Write YAML content to temp file
	if _, err := tmpFile.WriteString(req.Content); err != nil {
		tmpFile.Close()
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "Failed to write config file: " + err.Error(),
		})
		return
	}
	tmpFile.Close()

	// Run Python prompt test script using uv
	agentScanDir, err := utils.ResolveAgentScanDir()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "Failed to resolve agent-scan directory: " + err.Error(),
		})
		return
	}
	uvBin, err := utils.ResolveUvBin()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "Failed to resolve uv binary: " + err.Error(),
		})
		return
	}
	var lastLine string
	err = utils.RunCmd(
		agentScanDir,
		uvBin,
		[]string{"run", "test_client_connect.py", "--client_file", tmpFile.Name(), "--prompt", req.Prompt},
		func(line string) {
			lastLine += line
		},
	)

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "Failed to run prompt test: " + err.Error(),
		})
		return
	}
	gologger.Infof("prompt test result: %s", lastLine)

	// Parse the JSON output from Python script
	var result ConnectResultUpdate
	if err := json.Unmarshal([]byte(lastLine), &result); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "Failed to parse result: " + err.Error(),
		})
		return
	}

	// Return result based on prompt test outcome
	if result.Content.Success {
		// Extract output from provider_response
		var output string
		if result.Content.ProviderResponse != nil {
			if result.Content.ProviderResponse.Output != nil && *result.Content.ProviderResponse.Output != "" {
				output = *result.Content.ProviderResponse.Output
			} else if result.Content.ProviderResponse.Raw != nil {
				// Fallback to raw response
				rawBytes, _ := json.Marshal(result.Content.ProviderResponse.Raw)
				output = string(rawBytes)
			}
		}
		if output == "" {
			output = result.Content.Message
		}
		c.JSON(http.StatusOK, gin.H{
			"status":  0,
			"message": output,
		})
	} else {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": result.Content.Message,
		})
	}
}

func HandleAgentTemplate(c *gin.Context) {
	enConfig := "agent-scan/config/provider_config_en.json"
	zhConfig := "agent-scan/config/provider_config_zh.json"
	language := c.DefaultQuery("language", "zh")
	var data []byte
	var err error
	if language == "zh" {
		data, err = os.ReadFile(zhConfig)
		if err != nil {
			gologger.WithError(err).Errorln("read zh config")
		}
	} else {
		data, err = os.ReadFile(enConfig)
		if err != nil {
			gologger.WithError(err).Errorln("read en config")
		}
	}
	c.Data(http.StatusOK, "application/json", data)
}
