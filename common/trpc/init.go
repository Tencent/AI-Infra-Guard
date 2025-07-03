package trpc

import (
	"git.code.oa.com/trpc-go/trpc-go"
)

// InitTrpc 初始化trpc-go
func InitTrpc(configPath string) error {
	// 加载全局配置
	err := trpc.LoadGlobalConfig(configPath)
	if err != nil {
		return err
	}

	// 创建trpc server（这会加载插件、启动admin等）
	_ = trpc.NewServer()

	return nil
}

// GetTrpcConfig 获取trpc配置
func GetTrpcConfig() *trpc.Config {
	return trpc.GlobalConfig()
}
