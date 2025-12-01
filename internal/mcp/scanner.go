package mcp

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	utils2 "github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/client/transport"
	"github.com/mark3labs/mcp-go/mcp"
)

type Scanner struct {
	mutex         sync.Mutex
	results       []*Issue
	PluginConfigs []*PluginConfig
	aiModel       *models.OpenAI
	client        *client.Client
	csvResult     [][]string
	codePath      string
	url           string
	callback      func(data interface{})
	language      string
	logger        *gologger.Logger
}

type McpCallbackProcessing struct {
	Current int `json:"current"`
	Total   int `json:"total"`
}

type McpCallbackReadMe struct {
	Content string `json:"content"`
}

type McpModuleStart struct {
	ModuleName string
}

type McpModuleEnd struct {
	ModuleName string
	Result     string
}

func NewScanner(aiConfig *models.OpenAI, logger *gologger.Logger) *Scanner {
	if logger == nil {
		logger = gologger.NewLogger()
	}
	s := &Scanner{
		results:       make([]*Issue, 0),
		PluginConfigs: make([]*PluginConfig, 0),
		aiModel:       aiConfig,
		csvResult:     make([][]string, 0),
		language:      "zh",
		logger:        logger,
	}
	return s
}

func (s *Scanner) SetCallback(callback func(data interface{})) {
	s.callback = callback
}

func (s *Scanner) GetPluginsByCategory(category string) []*PluginConfig {
	plugins := make([]*PluginConfig, 0)
	for _, plugin := range s.PluginConfigs {
		for _, c := range plugin.Info.Category {
			if c == category {
				p := plugin
				plugins = append(plugins, p)
			}
		}
	}
	return plugins
}

func (s *Scanner) GetAllPluginNames() ([]string, error) {
	names := make([]string, 0)
	execPath, err := os.Executable()
	if err != nil {
		return nil, err
	}

	// 构建data/mcp目录路径
	dataDir := filepath.Join(filepath.Dir(execPath), "data", "mcp")

	// 如果相对路径不存在，尝试从工作目录查找
	if _, err := os.Stat(dataDir); os.IsNotExist(err) {
		wd, _ := os.Getwd()
		dataDir = filepath.Join(wd, "data", "mcp")
	}
	files, err := utils2.ScanDir(dataDir)
	if err != nil {
		return nil, err
	}

	for _, configPath := range files {
		if !strings.HasSuffix(configPath, ".yaml") {
			continue
		}
		plugin, err := NewYAMLPlugin(configPath)
		if err != nil {
			s.logger.Errorf("加载插件配置失败 %s: %v", configPath, err)
			continue
		}
		names = append(names, plugin.Info.ID)
	}
	return names, nil
}

func (s *Scanner) RegisterPlugin(plugins []string) error {
	// 获取当前执行文件的目录
	execPath, err := os.Executable()
	if err != nil {
		return err
	}

	// 构建data/mcp目录路径
	dataDir := filepath.Join(filepath.Dir(execPath), "data", "mcp")

	// 如果相对路径不存在，尝试从工作目录查找
	if _, err := os.Stat(dataDir); os.IsNotExist(err) {
		wd, _ := os.Getwd()
		dataDir = filepath.Join(wd, "data", "mcp")
	}
	files, err := utils2.ScanDir(dataDir)
	if err != nil {
		return err
	}

	for _, configPath := range files {
		if !strings.HasSuffix(configPath, ".yaml") {
			continue
		}
		plugin, err := NewYAMLPlugin(configPath)
		if err != nil {
			s.logger.Errorf("加载插件配置失败 %s: %v", configPath, err)
			continue
		}
		id := plugin.Info.ID
		if len(plugins) > 0 {
			for _, p := range plugins {
				if p == id {
					s.logger.Infof("加载插件 %s", plugin.Info.Name)
					s.PluginConfigs = append(s.PluginConfigs, plugin)
					break
				}
			}
		} else {
			s.logger.Infof("加载插件 %s", plugin.Info.Name)
			s.PluginConfigs = append(s.PluginConfigs, plugin)
		}
	}
	if len(s.PluginConfigs) == 0 {
		return fmt.Errorf("未加载任何插件")
	}
	return nil
}

func (s *Scanner) InputCommand(ctx context.Context, command string, argv []string) (*mcp.InitializeResult, error) {
	mcpClient, err := client.NewStdioMCPClient(
		command,
		argv,
	)
	if err != nil {
		return nil, err
	}
	s.client = mcpClient
	return utils.InitMcpClient(ctx, s.client)
}

func (s *Scanner) InputUrl(ctx context.Context, url string) (*mcp.InitializeResult, error) {
	dirs := []string{"", "/mcp", "/sse"}
	url = strings.TrimRight(url, "/")
	scan := func(ctx context.Context, url string) (*mcp.InitializeResult, error) {
		r, err := s.InputStreamLink(ctx, url)
		if err != nil {
			r, err = s.InputSSELink(ctx, url)
			if err != nil {
				return nil, err
			}
		}
		return r, nil
	}
	var err error
	for _, u := range dirs {
		link := url + u
		r, err := scan(ctx, link)
		if err == nil {
			return r, nil
		}
	}
	return nil, err
}

func (s *Scanner) InputSSELink(ctx context.Context, link string) (*mcp.InitializeResult, error) {
	opt := client.WithHTTPClient(&http.Client{Timeout: 10 * time.Second})
	mcpClient, err := client.NewSSEMCPClient(link, opt)
	if err != nil {
		return nil, err
	}
	r, err := utils.InitMcpClient(ctx, mcpClient)
	if err != nil {
		return nil, err
	}
	s.client = mcpClient
	return r, err
}

func (s *Scanner) InputStreamLink(ctx context.Context, link string) (*mcp.InitializeResult, error) {
	mcpClient, err := client.NewStreamableHttpClient(link, transport.WithHTTPTimeout(10*time.Second))
	if err != nil {
		return nil, err
	}
	r, err := utils.InitMcpClient(ctx, mcpClient)
	if err != nil {
		return nil, err
	}
	s.client = mcpClient
	return r, nil
}

func (s *Scanner) InputCodePath(codePath string) error {
	c, err := filepath.Abs(codePath)
	if err != nil {
		return err
	}
	s.codePath = c
	return nil
}

func (s *Scanner) SetLanguage(language string) error {
	if language == "" {
		s.language = "zh"
		return nil
	}
	if language == "zh-CN" {
		s.language = "zh"
	} else {
		s.language = language
	}
	return nil
}

type McpTemplate struct {
	CodePath              string
	DirectoryStructure    string
	StaticAnalysisResults string
	OriginalReports       string
	McpStructure          string
}

type McpResult struct {
	Issues []Issue
	Report []Issue
}

type CallbackWriteLog struct {
	Text       []byte
	ModuleName string
}

type tmpWriter struct {
	Callback   func(data interface{})
	Mux        sync.Mutex
	cache      []byte
	ModuleName string
}

func (t *tmpWriter) Write(p []byte) (n int, err error) {
	t.Mux.Lock()
	defer t.Mux.Unlock()
	for _, word := range p {
		t.cache = append(t.cache, word)
		if word == '\n' {
			if t.Callback != nil {
				t.Callback(CallbackWriteLog{t.cache, t.ModuleName})
			}
			t.cache = []byte{}
		}
	}
	return len(p), nil
}

func (t *tmpWriter) Finally() {
	if len(t.cache) > 0 {
		if t.Callback != nil {
			t.Callback(CallbackWriteLog{t.cache, t.ModuleName})
		}
		t.cache = []byte{}
	}
}

func (s *Scanner) getPluginByID(id string) (*PluginConfig, error) {
	for _, plugin := range s.PluginConfigs {
		if plugin.Info.ID == id {
			return plugin, nil
		}
	}
	return nil, fmt.Errorf("插件 %s 未找到", id)
}

func (s *Scanner) GetCsvResult() [][]string {
	return s.csvResult
}
