package database

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"

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

// LoadConfigFromEnv 从环境变量加载数据库配置
func LoadConfigFromEnv() *Config {
	// 默认数据库路径
	defaultDBPath := "db/tasks.db"

	// 从环境变量读取数据库路径
	if dbPath := os.Getenv("DB_PATH"); dbPath != "" {
		defaultDBPath = dbPath
	}

	return &Config{DBPath: defaultDBPath}
}

// InitDB 用 GORM 初始化数据库连接并返回 *gorm.DB
func InitDB(config *Config) (*gorm.DB, error) {
	// 确保数据库目录存在
	dir := filepath.Dir(config.DBPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("创建数据库目录失败: %v", err)
	}

	//打开数据库连接 - 启用WAL模式和共享缓存以支持并发访问
	db, err := gorm.Open(sqlite.Open(config.DBPath+"?_journal=WAL&_timeout=5000&cache=shared"), &gorm.Config{})
	if err != nil {
		gologger.WithError(err).Fatalln("无法打开数据库连接: %v", err)
	}
	// 获取底层的SQL DB以配置连接池
	sqlDB, err := db.DB()
	if err != nil {
		panic("failed to get database connection")
	}

	// 设置连接池参数
	sqlDB.SetMaxIdleConns(1000)
	sqlDB.SetMaxOpenConns(1000)

	return db, nil
}
