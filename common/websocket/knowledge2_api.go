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
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/gin-gonic/gin"
	"gopkg.in/yaml.v3"
)

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

func HandleListAgentNames(c *gin.Context) {
	names, err := listAgentConfigNames()
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
	name := strings.TrimSpace(c.Param("name"))
	if name == "" || !isValidName(name) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "配置名称非法",
		})
		return
	}

	data, err := readAgentConfigContent(name)
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

func HandleSaveAgentConfig(c *gin.Context) {
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
	// todo: 校验content yaml连通性

	if err := os.MkdirAll(AgentConfigRoot, 0755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "创建目录失败: " + err.Error(),
		})
		return
	}

	targetPath, err := resolveAgentConfigPathForWrite(name)
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
		"message": "创建成功",
	})
}

func HandleDeleteAgentConfig(c *gin.Context) {
	name := strings.TrimSpace(c.Param("name"))
	if name == "" || !isValidName(name) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "配置名称非法",
		})
		return
	}

	deleted, err := deleteAgentConfig(name)
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

func listAgentConfigNames() ([]string, error) {
	entries, err := os.ReadDir(AgentConfigRoot)
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
	sort.Strings(names)
	return names, nil
}

func readAgentConfigContent(name string) ([]byte, error) {
	for _, ext := range []string{".yaml", ".yml"} {
		path := filepath.Join(AgentConfigRoot, name+ext)
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

func resolveAgentConfigPathForWrite(name string) (string, error) {
	candidates := []string{
		filepath.Join(AgentConfigRoot, name+".yaml"),
		filepath.Join(AgentConfigRoot, name+".yml"),
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

func deleteAgentConfig(name string) (bool, error) {
	for _, ext := range []string{".yaml", ".yml"} {
		path := filepath.Join(AgentConfigRoot, name+ext)
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
