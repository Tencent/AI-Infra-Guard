package database

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

// Config 用于保存数据库配置
type Config struct {
	DBPath string
}

// NewConfig 创建一个新的数据库配置
func NewConfig(dbPath string) *Config {
	return &Config{DBPath: dbPath}
}

// InitDB 用 GORM 初始化数据库连接并返回 *gorm.DB
func InitDB(config *Config) (*gorm.DB, error) {
	// 确保数据库目录存在
	dir := filepath.Dir(config.DBPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("创建数据库目录失败: %v", err)
	}

	// 用 GORM 打开数据库
	db, err := gorm.Open(sqlite.Open(config.DBPath), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("连接数据库失败: %v", err)
	}

	return db, nil
}
