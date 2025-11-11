# 模型管理功能快速启动指南

## 启动服务

1. **编译项目**：
```bash
cd /Users/lbx/Desktop/AI-Infra-Guard
go build -o ai-infra-guard cmd/agent/main.go
```

2. **启动服务**：
```bash
./ai-infra-guard
```

服务默认运行在 `http://localhost:8080`

## 访问界面

- **Web管理界面**：http://localhost:8080/model-management.html
- **API文档**：查看 `/api/v1/app/models` 相关接口

## 功能测试

1. **运行自动化测试**：
```bash
./test_model_management.sh
```

2. **手动测试步骤**：
   - 打开浏览器访问模型管理界面
   - 点击"添加模型"标签页
   - 选择模型类型（OpenAI兼容 或 HTTP REST端点）
   - 填写相应配置信息
   - 点击"创建模型"
   - 在模型列表中查看新创建的模型
   - 对于HTTP端点模型，可以点击"测试API"按钮进行实时测试

## 支持的模型类型

### 1. OpenAI兼容模型
- **API Token**：OpenAI API密钥
- **Base URL**：API基础地址，如 `https://api.openai.com/v1`
- **模型名称**：如 `gpt-4`, `gpt-3.5-turbo`

### 2. HTTP REST端点模型
- **HTTP端点URL**：完整的API端点地址
- **HTTP方法**：GET、POST、PUT、PATCH
- **请求头**：JSON格式的HTTP头部
- **请求体模板**：支持 `{{.Prompt}}` 等变量替换
- **响应转换逻辑**：JavaScript函数或JSON路径表达式

## 示例配置

### OpenAI模型配置
```json
{
  "model_id": "gpt4-model",
  "model": {
    "model": "gpt-4",
    "model_type": "openai", 
    "token": "sk-your-api-key",
    "base_url": "https://api.openai.com/v1",
    "limit": 1000
  }
}
```

### HTTP端点模型配置
```json
{
  "model_id": "custom-api", 
  "model": {
    "model": "Custom Chat API",
    "model_type": "http_endpoint",
    "http_endpoint": "https://api.example.com/v1/chat",
    "http_method": "POST",
    "http_headers": "{\"Authorization\": \"Bearer your-token\"}",
    "http_request_body": "{\"message\": \"{{.Prompt}}\"}",
    "http_response_transform": "data.response.text",
    "limit": 500
  }
}
```

## 故障排除

1. **数据库连接问题**：检查数据库配置和连接状态
2. **端口占用**：确保8080端口未被其他服务占用
3. **权限问题**：确保有文件读写权限
4. **依赖缺失**：运行 `go mod tidy` 确保依赖完整

## 日志查看

查看 `logs/trpc.log` 文件获取详细的系统日志信息。
