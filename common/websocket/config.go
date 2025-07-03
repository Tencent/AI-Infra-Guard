package websocket

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// FileUploadConfig 文件上传配置
type FileUploadConfig struct {
	UploadDir string `json:"upload_dir"` // 文件上传目录
	BaseURL   string `json:"base_url"`   // 文件访问的基础URL
}

// DefaultFileUploadConfig 默认文件上传配置
func DefaultFileUploadConfig() *FileUploadConfig {
	return &FileUploadConfig{
		UploadDir: "./uploads",
		BaseURL:   "/uploads",
	}
}

// LoadFileUploadConfigFromEnv 从环境变量加载文件上传配置
func LoadFileUploadConfigFromEnv() *FileUploadConfig {
	config := DefaultFileUploadConfig()

	// 从环境变量读取配置
	if uploadDir := os.Getenv("FILE_UPLOAD_DIR"); uploadDir != "" {
		config.UploadDir = uploadDir
	}

	if baseURL := os.Getenv("FILE_BASE_URL"); baseURL != "" {
		config.BaseURL = baseURL
	}

	return config
}

// ValidateConfig 验证配置的有效性
func (c *FileUploadConfig) ValidateConfig() error {
	// 检查存储目录是否存在或可以创建
	if err := c.ensureUploadDir(); err != nil {
		return fmt.Errorf("存储目录配置错误: %v", err)
	}

	// 检查BaseURL格式
	if c.BaseURL == "" {
		return fmt.Errorf("BaseURL不能为空")
	}

	// 确保BaseURL以/开头
	if !strings.HasPrefix(c.BaseURL, "/") {
		c.BaseURL = "/" + c.BaseURL
	}

	return nil
}

// ensureUploadDir 确保上传目录存在并且可写
func (c *FileUploadConfig) ensureUploadDir() error {
	// 获取绝对路径
	absPath, err := filepath.Abs(c.UploadDir)
	if err != nil {
		return fmt.Errorf("无法解析存储路径: %v", err)
	}

	// 检查目录是否存在
	if _, err := os.Stat(absPath); os.IsNotExist(err) {
		// 目录不存在，尝试创建
		if err := os.MkdirAll(absPath, 0755); err != nil {
			return fmt.Errorf("无法创建存储目录 %s: %v", absPath, err)
		}
	}

	// 检查目录是否可写
	if err := c.checkDirWritable(absPath); err != nil {
		return fmt.Errorf("存储目录不可写: %v", err)
	}

	// 更新为绝对路径
	c.UploadDir = absPath
	return nil
}

// checkDirWritable 检查目录是否可写
func (c *FileUploadConfig) checkDirWritable(dir string) error {
	// 尝试创建一个临时文件来测试写权限
	testFile := filepath.Join(dir, ".test_write")
	file, err := os.Create(testFile)
	if err != nil {
		return err
	}
	defer func() {
		file.Close()
		os.Remove(testFile) // 清理测试文件
	}()
	return nil
}

// GetFileURL 根据文件名生成完整的文件访问URL
func (c *FileUploadConfig) GetFileURL(fileName string) string {
	return fmt.Sprintf("%s/%s", c.BaseURL, fileName)
}
