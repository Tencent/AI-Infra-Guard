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

	"github.com/Tencent/AI-Infra-Guard/common/agent"
	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/gin-gonic/gin"
	"gopkg.in/yaml.v3"
)

const AgentScanDir = "/app/agent-scan"
const UvBin = "/usr/local/bin/uv"

func HandleList(root string, loadFile func(filePath string) (interface{}, error)) gin.HandlerFunc {
	return func(c *gin.Context) {
		var allItems []interface{}
		err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
			if err != nil {
				return nil // 忽略错误
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
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "保存失败: " + err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{"status": 0, "message": "创建成功"})
	}
}

// HandleEdit 返回处理编辑请求的HandlerFunc
func HandleEdit(updateFunc func(id string, content string) error) gin.HandlerFunc {
	return func(c *gin.Context) {
		name := c.Param("id")
		if name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "名称不能为空"})
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
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "更新失败: " + err.Error()})
			return
		}

		c.JSON(http.StatusOK, gin.H{"status": 0, "message": "更新成功"})
	}
}

// HandleDelete 返回处理删除请求的HandlerFunc
func HandleDelete(deleteFunc func(id string) error) gin.HandlerFunc {
	return func(c *gin.Context) {
		name := c.Param("id")
		if name == "" {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "名称不能为空"})
			return
		}

		if err := deleteFunc(name); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "删除失败: " + err.Error()})
			return
		}

		c.JSON(http.StatusOK, gin.H{"status": 0, "message": "删除成功"})
	}
}

// mcp prompt管理
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
	// 确保目录存在
	if err := os.MkdirAll(MCPROOT, 0755); err != nil {
		return fmt.Errorf("创建目录失败: %w", err)
	}

	// 解析YAML验证格式
	var config mcp.PluginConfig
	err := yaml.Unmarshal([]byte(content), &config)
	if err != nil {
		return fmt.Errorf("YAML解析失败: %w", err)
	}

	// 获取ID
	id := config.Info.ID
	if id == "" {
		return errors.New("缺少info.id字段")
	}

	// 安全检查
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("无效的文件名")
	}

	filename := filepath.Join(MCPROOT, id+".yaml")
	return os.WriteFile(filename, []byte(content), 0644)
}

func mcpUpdateFunc(id string, content string) error {
	// 解析YAML验证内容格式
	var config mcp.PluginConfig
	if err := yaml.Unmarshal([]byte(content), &config); err != nil {
		return fmt.Errorf("YAML解析失败: %w", err)
	}

	// 安全检查文件名
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("无效的文件名")
	}

	// 使用提供的name作为文件名，允许更新文件而不强制更改文件名
	filePath := filepath.Join(MCPROOT, id+".yaml")
	return os.WriteFile(filePath, []byte(content), 0644)
}

func mcpDeleteFunc(id string) error {
	// 安全检查文件名
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("无效的文件名")
	}

	filePath := filepath.Join(MCPROOT, id+".yaml")
	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return errors.New("文件不存在")
	}
	return os.Remove(filePath)
}

// AI应用透视镜管理
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
	// 验证JSON格式
	var collection map[string]interface{}
	err := json.Unmarshal([]byte(content), &collection)
	if err != nil {
		return fmt.Errorf("JSON解析失败: %w", err)
	}

	// 获取ID作为文件名
	id, ok := collection["id"].(string)
	if !ok || id == "" {
		return errors.New("缺少id字段")
	}

	// 安全检查
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("无效的文件名")
	}

	filename := filepath.Join(PromptCollectionsRoot, id+".json")
	return os.WriteFile(filename, []byte(content), 0644)
}

func promptCollectionUpdateFunc(id string, content string) error {
	// 验证JSON格式
	var collection map[string]interface{}
	err := json.Unmarshal([]byte(content), &collection)
	if err != nil {
		return fmt.Errorf("JSON格式无效: %w", err)
	}

	// 安全检查文件名
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("无效的文件名")
	}

	filename := filepath.Join(PromptCollectionsRoot, id+".json")
	return os.WriteFile(filename, []byte(content), 0644)
}

func promptCollectionDeleteFunc(id string) error {
	// 安全检查文件名
	if strings.Contains(id, "..") || strings.ContainsAny(id, "/\\<>:\"|?*") {
		return errors.New("无效的文件名")
	}

	filePath := filepath.Join(PromptCollectionsRoot, id+".json")

	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return errors.New("文件不存在")
	}

	return os.Remove(filePath)
}
func GetJailBreak(c *gin.Context) {
	dataPath := filepath.Join(agent.DIR, "utils", "strategy_map.json")
	data, err := os.ReadFile(dataPath)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "error" + err.Error(),
		})
		return
	}
	var data1 interface{}
	err = json.Unmarshal(data, &data1)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "error" + err.Error(),
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

// getAgentUserDir 获取用户的 agent 配置目录
func getAgentUserDir(username string) string {
	return filepath.Join(AgentConfigRoot, username)
}

// validateUsername 验证用户名安全性（防止路径穿越）
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
			"message": "获取失败: " + err.Error(),
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
			"message": "配置名称非法",
		})
		return
	}

	data, err := readAgentConfigContent(username, name)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			c.JSON(http.StatusNotFound, gin.H{
				"status":  1,
				"message": "配置不存在",
			})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "读取失败: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "success",
		"data":    string(data),
	})
}

// testAgentConnectivity 测试Agent配置的连通性
// 返回 (success, message, error)
func testAgentConnectivity(content string) (bool, string, error) {
	// Create temporary file for the YAML content
	tmpFile, err := os.CreateTemp("", "agent_connect_*.yaml")
	if err != nil {
		return false, "", fmt.Errorf("创建临时文件失败: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	// Write YAML content to temp file
	if _, err := tmpFile.WriteString(content); err != nil {
		tmpFile.Close()
		return false, "", fmt.Errorf("写入配置文件失败: %v", err)
	}
	tmpFile.Close()

	// Run Python connectivity test script using uv
	var lastLine string
	err = utils.RunCmd(
		AgentScanDir,
		UvBin,
		[]string{"run", "test_client_connect.py", "--client_file", tmpFile.Name()},
		func(line string) {
			lastLine += line
		},
	)

	if err != nil {
		return false, "", fmt.Errorf("连通性测试执行失败: %v", err)
	}
	if lastLine != "" {
		gologger.Infoln("test_agent_connect", lastLine)
	}

	// Parse the JSON output from Python script
	var result ConnectResultUpdate
	if err := json.Unmarshal([]byte(lastLine), &result); err != nil {
		return false, "", fmt.Errorf("解析测试结果失败: %v", err)
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
			"message": "配置名称非法",
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
			"message": "content不能为空",
		})
		return
	}

	// 检测Agent连通性
	success, message, err := testAgentConnectivity(content)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "连通性检测失败: " + err.Error(),
		})
		return
	}
	if !success {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "连通性检测失败: " + message,
		})
		return
	}

	// 创建用户专属目录
	userDir := getAgentUserDir(username)
	if err := os.MkdirAll(userDir, 0755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "创建目录失败: " + err.Error(),
		})
		return
	}

	targetPath, err := resolveAgentConfigPathForWrite(username, name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "保存失败: " + err.Error(),
		})
		return
	}

	if err := os.WriteFile(targetPath, []byte(content), 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "保存失败: " + err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "保存成功，连通性验证通过",
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
			"message": "配置名称非法",
		})
		return
	}

	deleted, err := deleteAgentConfig(username, name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "删除失败: " + err.Error(),
		})
		return
	}
	if !deleted {
		c.JSON(http.StatusNotFound, gin.H{
			"status":  1,
			"message": "配置不存在",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "删除成功",
	})
}

// listAgentConfigNamesFromDir 从指定目录读取配置名称列表
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

// listAgentConfigNames 列出用户的配置名称（合并用户目录和公共目录，去重）
func listAgentConfigNames(username string) ([]string, error) {
	// 读取用户目录的配置
	userDir := getAgentUserDir(username)
	userNames, err := listAgentConfigNamesFromDir(userDir)
	if err != nil {
		return nil, err
	}

	// 如果不是公共用户，还需要合并公共目录的配置
	if username != PublicUser {
		publicDir := getAgentUserDir(PublicUser)
		publicNames, err := listAgentConfigNamesFromDir(publicDir)
		if err != nil {
			return nil, err
		}

		// 合并并去重
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

// readAgentConfigContentFromDir 从指定目录读取配置内容
func readAgentConfigContentFromDir(dir, name string) ([]byte, error) {
	for _, ext := range []string{".yaml", ".yml"} {
		path := filepath.Join(dir, name+ext)
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

// readAgentConfigContent 读取配置内容（优先用户目录，fallback 到公共目录）
func readAgentConfigContent(username, name string) ([]byte, error) {
	// 优先从用户目录读取
	userDir := getAgentUserDir(username)
	data, err := readAgentConfigContentFromDir(userDir, name)
	if err == nil {
		return data, nil
	}
	if !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}

	// 如果不是公共用户且用户目录没有，尝试从公共目录读取
	if username != PublicUser {
		publicDir := getAgentUserDir(PublicUser)
		return readAgentConfigContentFromDir(publicDir, name)
	}

	return nil, os.ErrNotExist
}

// resolveAgentConfigPathForWrite 解析写入路径（写入用户目录）
func resolveAgentConfigPathForWrite(username, name string) (string, error) {
	userDir := getAgentUserDir(username)
	candidates := []string{
		filepath.Join(userDir, name+".yaml"),
		filepath.Join(userDir, name+".yml"),
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
	return candidates[0], nil
}

// deleteAgentConfig 删除配置（只删除用户目录的配置）
func deleteAgentConfig(username, name string) (bool, error) {
	userDir := getAgentUserDir(username)
	for _, ext := range []string{".yaml", ".yml"} {
		path := filepath.Join(userDir, name+ext)
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

	// 使用公共的连通性测试函数
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
	var lastLine string
	err = utils.RunCmd(
		AgentScanDir,
		UvBin,
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
