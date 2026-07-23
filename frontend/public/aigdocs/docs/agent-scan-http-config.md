# HTTP 接口 Agent 配置指南

HTTP 接口配置允许您连接任意自定义的 HTTP 对话端点，适用于自建 Agent 服务或第三方非标准接口。

## 配置入口

**配置入口**：`设置` → `Agent配置` → `新增` → 选择「HTTP接口」

## 基础配置（必填）

- **Agent名称**：Agent自定义名称，用于标识和管理，唯一标识
- **URL**：目标 HTTP 端点的完整地址，例如：`https://api.example.com/chat`
- **HTTP方法**：选择请求方法，支持 POST、GET、PUT、PATCH、DELETE，默认 `POST`

## 高级配置（选填）

### 请求头

- **格式**：JSON 格式的 HTTP 请求头
- **默认值**：`{"Content-Type": "application/json"}`
- **示例**：
  ```json
  {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-token-here",
    "X-Custom-Header": "xxxxx"
  }
  ```
- **说明**：如需认证，可在此处添加 `Authorization` 等请求头

### 请求体

- **格式**：请求体模板，支持文本或 JSON 格式
- **占位符**：使用 `{{prompt}}` 作为测试输入的占位符，扫描时会自动替换为实际的测试 prompt
- **默认值**：`{"message": "{{prompt}}"}`
- **示例**：
  ```json
  {
    "query": "{{prompt}}",
    "user_id": "agent-user",
    "stream": false
  }
  ```
- **说明**：根据目标接口的实际请求格式填写，确保 `{{prompt}}` 占位符位于正确位置

### 响应解析器

响应解析器用于从 HTTP 响应中提取 Agent 的实际回复内容。

- **格式**：JSONPath 表达式或 JavaScript 表达式
- **配置方式**：
  - **响应是 JSON 格式**：使用 JSONPath 表达式提取嵌套字段
    - 示例：响应为 `{"reply": "内容"}`，配置 `json.reply`
    - 示例：响应为 `{"data": {"message": "内容"}}`，配置 `json.data.message`
  - **响应是文本格式**：可留空或使用 `response`
    - 示例：响应直接是文本 `"Agent的回复内容"`，响应解析器留空
- **如何确定配置**：先使用「Agent接入验证」功能测试，查看实际响应结构后再配置

### 超时时间（毫秒）

- **默认值**：`30000`（30秒）
- **说明**：请求超时时间，超过此时长未收到响应将视为失败

## 配置示例

### 示例 1：标准 JSON API

假设目标接口为 `POST https://api.example.com/chat`，请求格式为：
```json
{
  "message": "用户输入的内容",
  "user_id": "user123"
}
```

响应格式为：
```json
{
  "status": "success",
  "data": {
    "reply": "Agent的回复内容"
  }
}
```

**配置方式**：
- **URL**：`https://api.example.com/chat`
- **HTTP方法**：`POST`
- **请求头**：`{"Content-Type": "application/json", "Authorization": "Bearer your-token"}`
- **请求体**：`{"message": "{{prompt}}", "user_id": "agent-user"}`
- **响应解析器**：`json.data.reply`

### 示例 2：简单文本接口

假设目标接口为 `POST https://api.example.com/simple`，请求体直接是文本，响应也是文本。

**配置方式**：
- **URL**：`https://api.example.com/simple`
- **HTTP方法**：`POST`
- **请求头**：`{"Content-Type": "text/plain"}`
- **请求体**：`{{prompt}}`
- **响应解析器**：留空或填写 `response`

## Agent 接入验证

配置完成后，建议使用「Agent接入验证」功能进行快速测试。详细说明请参考 [Agent 配置 - Agent 接入验证](?menu=agent-scan#agent-接入验证) 部分。

对于 HTTP 接口，特别需要注意：
- 如果提取失败，检查响应解析器配置是否正确。
- 连通性校验失败时，需检查 URL、请求格式、响应解析器等配置是否正确

## 常见问题

**Q: 响应解析器如何配置？**  
A: 先使用「Agent接入验证」功能查看实际响应结构，然后根据响应格式配置对应的 JSONPath 或 JavaScript 表达式。

**Q: 如何支持流式响应？**  
A: 支持流式传递，如遇解析失败可更换为非流式。建议优先使用【同步请求（blocking 模式）】。

**Q: 请求体必须包含 `{{prompt}}` 吗？**  
A: 是的，`{{prompt}}` 是必需的占位符，扫描时会替换为实际的测试 prompt。

**Q: 支持文件上传吗？**  
A: 当前版本暂不支持文件上传，仅支持文本对话。

**Q: 如何知道接口的参数和响应格式？**  
A: 可以通过以下方式获取接口信息：

1. **查阅接口文档**：查看目标 Agent 服务提供的 API 文档，了解请求格式（URL、方法、请求头、请求体结构）和响应格式。
2. **使用「Agent接入验证」功能**：配置好基础信息后，使用界面中的「Agent接入验证」功能发送测试请求，查看实际返回的响应结构：
   - 在「Prompt Input」输入测试 prompt
   - 点击「运行测试」
   - 查看返回的原始响应（如果响应解析器配置不正确，可以看到完整的响应结构）
3. **使用浏览器开发者工具**：如果目标接口有 Web 界面，可以：
   - 打开浏览器开发者工具（F12）
   - 切换到「Network」标签
   - 在 Web 界面中发送一条消息
   - 查看对应的 HTTP 请求和响应，了解请求格式和响应结构
4. **使用 curl 或 Postman 测试**：使用命令行工具或 API 测试工具直接调用接口，观察请求和响应格式。
5. **查看响应解析器示例**：根据常见的响应格式配置响应解析器：
   - 如果响应是 `{"reply": "内容"}`，使用 `json.reply`
   - 如果响应是 `{"data": {"message": "内容"}}`，使用 `json.data.message`
   - 如果响应是 OpenAI 格式 `{"choices": [{"message": {"content": "内容"}}]}`, 使用 `json.choices[0].message.content`
