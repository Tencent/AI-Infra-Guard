# A.I.G API 文档

## 概述

A.I.G(AI-Infra-Guard) 提供了一套完整的API接口，用于AI基础设施扫描、MCP安全扫描和大模型安全体检。本文档详细介绍了各个API接口的使用方法、参数说明和示例代码。

项目运行后，可访问 `http://localhost:8088/docs/index.html` 查看Swagger文档。

## 基础信息

- **Base URL**: `http://localhost:8088` (根据实际部署调整)
- **Content-Type**: `application/json`
- **认证方式**: 通过请求头传递认证信息

## 通用响应格式

所有API接口都遵循统一的响应格式：

```json
{
  "status": 0,           // 状态码: 0=成功, 1=失败
  "message": "操作成功",  // 响应消息
  "data": {}             // 响应数据
}
```

## API 接口列表

### 1. 文件上传接口

#### 接口信息
- **URL**: `/api/v1/app/taskapi/upload`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`

#### 参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | 是 | 要上传的文件，支持zip、json、txt等格式 |

#### 响应字段
| 字段名 | 类型 | 说明 |
|--------|------|------|
| fileUrl | string | 文件访问URL |
| filename | string | 文件名 |
| size | integer | 文件大小（字节） |

#### Python 示例
```python
import requests

def upload_file(file_path):
    url = "http://localhost:8088/api/v1/app/taskapi/upload"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    
    return response.json()

# 使用示例
result = upload_file("example.zip")
print(f"文件上传成功: {result['data']['fileUrl']}")
```

#### cURL 示例
```bash
curl -X POST \
  http://localhost:8088/api/v1/app/taskapi/upload \
  -F "file=@example.zip"
```

### 2. 任务创建接口

#### 接口信息
- **URL**: `/api/v1/app/taskapi/tasks`
- **方法**: `POST`
- **Content-Type**: `application/json`

#### 请求参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type | string | 是 | 任务类型：mcp_scan、ai_infra_scan、model_redteam_report |
| content | object | 是 | 任务内容，根据任务类型不同而不同 |

#### 响应字段
| 字段名 | 类型 | 说明 |
|--------|------|------|
| session_id | string | 任务会话ID |

---

## 任务类型详细说明

### 1. MCP 安全扫描 API

MCP（Model Context Protocol）安全扫描用于检测MCP服务中的安全漏洞。

#### 请求参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| content | string | 否 | 任务内容描述 |
| model | object | 是 | 模型配置 |
| model.model | string | 是 | 模型名称，如"gpt-4" |
| model.token | string | 是 | API密钥 |
| model.base_url | string | 否 | 基础URL，默认为OpenAI API |
| thread | integer | 否 | 并发线程数，默认4 |
| language | string | 否 | 语言代码，如"zh" |
| attachments | string | 否 | 附件文件路径（需要先上传文件） |

#### 源码扫描流程
1. 先调用文件上传接口上传源码文件
2. 使用返回的fileUrl作为attachments参数
3. 调用MCP扫描API

#### Python 示例
```python
import requests
import json

def mcp_scan_with_source_code():
    # 1. 上传源码文件
    upload_url = "http://localhost:8088/api/v1/app/taskapi/upload"
    with open("source_code.zip", 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(upload_url, files=files)
    
    if upload_response.json()['status'] != 0:
        raise Exception("文件上传失败")
    
    fileUrl = upload_response.json()['data']['fileUrl']
    
    # 2. 创建MCP扫描任务
    task_url = "http://localhost:8088/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "content": "",
            "model": {
                "model": "gpt-4",
                "token": "sk-your-api-key",
                "base_url": "https://api.openai.com/v1"
            },
            "thread": 4,
            "language": "zh",
            "attachments": fileUrl
        }
    }
    
    response = requests.post(task_url, json=task_data)
    return response.json()

# 使用示例
result = mcp_scan_with_source_code()
print(f"任务创建成功，会话ID: {result['data']['session_id']}")
```

#### 动态URL扫描示例
```python
def mcp_scan_with_url():
    task_url = "http://localhost:8088/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "content": "https://mcp-server.example.com",  # 直接填写URL
            "model": {
                "model": "gpt-4",
                "token": "sk-your-api-key",
                "base_url": "https://api.openai.com/v1"
            },
            "thread": 4,
            "language": "zh"
        }
    }
    
    response = requests.post(task_url, json=task_data)
    return response.json()
```

#### cURL 示例
```bash
# 源码扫描
curl -X POST http://localhost:8088/api/v1/app/taskapi/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "mcp_scan",
    "content": {
      "content": "",
      "model": {
        "model": "gpt-4",
        "token": "sk-your-api-key",
        "base_url": "https://api.openai.com/v1"
      },
      "thread": 4,
      "language": "zh",
      "attachments": "http://localhost:8088/uploads/example.zip"
    }
  }'

# URL扫描
curl -X POST http://localhost:8088/api/v1/app/taskapi/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "mcp_scan",
    "content": {
      "content": "https://mcp-server.example.com",
      "model": {
        "model": "gpt-4",
        "token": "sk-your-api-key",
        "base_url": "https://api.openai.com/v1"
      },
      "thread": 4,
      "language": "zh"
    }
  }'
```

### 2. AI 基础设施扫描 API

用于扫描AI基础设施的安全漏洞和配置问题。

#### 请求参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| target | array | 是 | 扫描目标URL列表 |
| headers | object | 否 | 自定义请求头 |
| timeout | integer | 否 | 请求超时时间（秒），默认30 |

#### Python 示例
```python
def ai_infra_scan():
    task_url = "http://localhost:8088/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "ai_infra_scan",
        "content": {
            "target": [
                "https://ai-service1.example.com",
                "https://ai-service2.example.com"
            ],
            "headers": {
                "Authorization": "Bearer your-token",
                "User-Agent": "AI-Infra-Guard/1.0"
            },
            "timeout": 30
        }
    }
    
    response = requests.post(task_url, json=task_data)
    return response.json()

# 使用示例
result = ai_infra_scan()
print(f"AI基础设施扫描任务创建成功，会话ID: {result['data']['session_id']}")
```

#### cURL 示例
```bash
curl -X POST http://localhost:8088/api/v1/app/taskapi/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "ai_infra_scan",
    "content": {
      "target": [
        "https://ai-service1.example.com",
        "https://ai-service2.example.com"
      ],
      "headers": {
        "Authorization": "Bearer your-token",
        "User-Agent": "AI-Infra-Guard/1.0"
      },
      "timeout": 30
    }
  }'
```

### 3. 大模型安全体检 API

用于对AI模型进行红队测试，评估模型的安全性和鲁棒性。

#### 请求参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| model | array | 是 | 测试模型列表 |
| eval_model | object | 是 | 评估模型配置 |
| dataset | object | 是 | 数据集配置 |
| dataset.dataFile | array | 是 | 数据集文件列表，支持以下选项：<br/>- JailBench-Tiny: 小型越狱基准测试数据集<br/>- JailbreakPrompts-Tiny: 小型越狱提示词数据集<br/>- ChatGPT-Jailbreak-Prompts: ChatGPT越狱提示词数据集<br/>- JADE-db-v3.0: JADE数据库v3.0版本<br/>- HarmfulEvalBenchmark: 有害内容评估基准数据集 |
| dataset.numPrompts | integer | 是 | 提示词数量 |
| dataset.randomSeed | integer | 是 | 随机种子 |

#### 支持的数据集说明

| 数据集名称 | 描述 | 适用场景 |
|------------|------|----------|
| JailBench-Tiny | 小型越狱基准测试数据集 | 快速测试模型对越狱攻击的抵抗能力 |
| JailbreakPrompts-Tiny | 小型越狱提示词数据集 | 测试模型对常见越狱技术的防护 |
| ChatGPT-Jailbreak-Prompts | ChatGPT越狱提示词数据集 | 专门针对ChatGPT的越狱测试 |
| JADE-db-v3.0 | JADE数据库v3.0版本 | 全面的AI安全评估数据集 |
| HarmfulEvalBenchmark | 有害内容评估基准数据集 | 评估模型生成有害内容的风险 |

#### Python 示例
```python
def model_redteam_test():
    task_url = "http://localhost:8088/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "model_redteam_report",
        "content": {
            "model": [
                {
                    "model": "gpt-4",
                    "token": "sk-your-api-key",
                    "base_url": "https://api.openai.com/v1"
                },
                {
                    "model": "claude-3",
                    "token": "your-anthropic-key",
                    "base_url": "https://api.anthropic.com/v1"
                }
            ],
            "eval_model": {
                "model": "gpt-4",
                "token": "sk-your-eval-key",
                "base_url": "https://api.openai.com/v1"
            },
            "dataset": {
                "dataFile": [
                    "JailBench-Tiny",
                    "JailbreakPrompts-Tiny",
                    "ChatGPT-Jailbreak-Prompts"
                ],
                "numPrompts": 100,
                "randomSeed": 42
            }
        }
    }
    
    response = requests.post(task_url, json=task_data)
    return response.json()

# 使用示例
result = model_redteam_test()
print(f"大模型安全体检任务创建成功，会话ID: {result['data']['session_id']}")
```

#### 不同数据集组合示例
```python
# 使用JADE数据库进行全面测试
def comprehensive_redteam_test():
    task_data = {
        "type": "model_redteam_report",
        "content": {
            "model": [{"model": "gpt-4", "token": "sk-your-key"}],
            "eval_model": {"model": "gpt-4", "token": "sk-eval-key"},
            "dataset": {
                "dataFile": ["JADE-db-v3.0"],
                "numPrompts": 500,
                "randomSeed": 123
            }
        }
    }
    return requests.post(task_url, json=task_data).json()

# 使用有害内容评估基准
def harmful_content_test():
    task_data = {
        "type": "model_redteam_report",
        "content": {
            "model": [{"model": "gpt-4", "token": "sk-your-key"}],
            "eval_model": {"model": "gpt-4", "token": "sk-eval-key"},
            "dataset": {
                "dataFile": ["HarmfulEvalBenchmark"],
                "numPrompts": 200,
                "randomSeed": 456
            }
        }
    }
    return requests.post(task_url, json=task_data).json()
```

#### cURL 示例
```bash
# 基础大模型安全体检
curl -X POST http://localhost:8088/api/v1/app/taskapi/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "model_redteam_report",
    "content": {
      "model": [
        {
          "model": "gpt-4",
          "token": "sk-your-api-key",
          "base_url": "https://api.openai.com/v1"
        }
      ],
      "eval_model": {
        "model": "gpt-4",
        "token": "sk-your-eval-key",
        "base_url": "https://api.openai.com/v1"
      },
      "dataset": {
        "dataFile": ["JailBench-Tiny", "JailbreakPrompts-Tiny"],
        "numPrompts": 100,
        "randomSeed": 42
      }
    }
  }'

# 全面安全评估
curl -X POST http://localhost:8088/api/v1/app/taskapi/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "model_redteam_report",
    "content": {
      "model": [{"model": "gpt-4", "token": "sk-your-key"}],
      "eval_model": {"model": "gpt-4", "token": "sk-eval-key"},
      "dataset": {
        "dataFile": ["JADE-db-v3.0", "HarmfulEvalBenchmark"],
        "numPrompts": 500,
        "randomSeed": 123
      }
    }
  }'
```

---

## 任务状态查询

### 获取任务状态

#### 接口信息
- **URL**: `/api/v1/app/taskapi/status/{id}`
- **方法**: `GET`

#### 参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | string | 是 | 任务会话ID |

#### 响应字段
| 字段名 | 类型 | 说明 |
|--------|------|------|
| session_id | string | 任务会话ID |
| status | string | 任务状态：pending、running、completed、failed |
| title | string | 任务标题 |
| created_at | integer | 创建时间戳（毫秒） |
| updated_at | integer | 更新时间戳（毫秒） |
| log | string | 任务执行日志 |

#### Python 示例
```python
def get_task_status(session_id):
    url = f"http://localhost:8088/api/v1/app/taskapi/status/{session_id}"
    response = requests.get(url)
    return response.json()

# 使用示例
status = get_task_status("550e8400-e29b-41d4-a716-446655440000")
print(f"任务状态: {status['data']['status']}")
print(f"执行日志: {status['data']['log']}")
```

#### cURL 示例
```bash
curl -X GET http://localhost:8088/api/v1/app/taskapi/status/550e8400-e29b-41d4-a716-446655440000
```

### 获取任务结果

#### 接口信息
- **URL**: `/api/v1/app/taskapi/result/{id}`
- **方法**: `GET`

#### 参数说明
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | string | 是 | 任务会话ID |

#### 响应说明
返回详细的扫描结果，包括：
- 发现的漏洞列表
- 安全评估报告
- 修复建议
- 风险等级评估

#### Python 示例
```python
def get_task_result(session_id):
    url = f"http://localhost:8088/api/v1/app/taskapi/result/{session_id}"
    response = requests.get(url)
    return response.json()

# 使用示例
result = get_task_result("550e8400-e29b-41d4-a716-446655440000")
if result['status'] == 0:
    print("扫描结果:")
    print(json.dumps(result['data'], indent=2, ensure_ascii=False))
else:
    print(f"获取结果失败: {result['message']}")
```

#### cURL 示例
```bash
curl -X GET http://localhost:8088/api/v1/app/taskapi/result/550e8400-e29b-41d4-a716-446655440000
```

---

## 完整工作流程示例

### MCP 源码扫描完整流程

```python
import requests
import time
import json

def complete_mcp_scan_workflow():
    base_url = "http://localhost:8088"
    
    # 1. 上传源码文件
    print("1. 上传源码文件...")
    upload_url = f"{base_url}/api/v1/app/taskapi/upload"
    with open("mcp_source.zip", 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(upload_url, files=files)
    
    if upload_response.json()['status'] != 0:
        raise Exception("文件上传失败")
    
    fileUrl = upload_response.json()['data']['fileUrl']
    print(f"文件上传成功: {fileUrl}")
    
    # 2. 创建MCP扫描任务
    print("2. 创建MCP扫描任务...")
    task_url = f"{base_url}/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "content": "",
            "model": {
                "model": "gpt-4",
                "token": "sk-your-api-key",
                "base_url": "https://api.openai.com/v1"
            },
            "thread": 4,
            "language": "zh",
            "attachments": fileUrl
        }
    }
    
    task_response = requests.post(task_url, json=task_data)
    if task_response.json()['status'] != 0:
        raise Exception("任务创建失败")
    
    session_id = task_response.json()['data']['session_id']
    print(f"任务创建成功，会话ID: {session_id}")
    
    # 3. 轮询任务状态
    print("3. 监控任务执行...")
    status_url = f"{base_url}/api/v1/app/taskapi/status/{session_id}"
    
    while True:
        status_response = requests.get(status_url)
        status_data = status_response.json()
        
        if status_data['status'] != 0:
            raise Exception("获取任务状态失败")
        
        task_status = status_data['data']['status']
        print(f"当前状态: {task_status}")
        
        if task_status == "completed":
            print("任务执行完成！")
            break
        elif task_status == "failed":
            raise Exception("任务执行失败")
        
        time.sleep(10)  # 等待10秒后再次检查
    
    # 4. 获取扫描结果
    print("4. 获取扫描结果...")
    result_url = f"{base_url}/api/v1/app/taskapi/result/{session_id}"
    result_response = requests.get(result_url)
    
    if result_response.json()['status'] != 0:
        raise Exception("获取扫描结果失败")
    
    scan_results = result_response.json()['data']
    print("扫描结果:")
    print(json.dumps(scan_results, indent=2, ensure_ascii=False))
    
    return scan_results

# 执行完整流程
if __name__ == "__main__":
    try:
        results = complete_mcp_scan_workflow()
        print("MCP扫描完成！")
    except Exception as e:
        print(f"扫描失败: {e}")
```

### 模型红队测评完整流程

```python
def complete_redteam_workflow():
    base_url = "http://localhost:8088"
    
    # 1. 创建大模型安全体检
    print("1. 创建大模型安全体检任务...")
    task_url = f"{base_url}/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "model_redteam_report",
        "content": {
            "model": [
                {
                    "model": "gpt-4",
                    "token": "sk-your-api-key",
                    "base_url": "https://api.openai.com/v1"
                }
            ],
            "eval_model": {
                "model": "gpt-4",
                "token": "sk-your-eval-key",
                "base_url": "https://api.openai.com/v1"
            },
            "dataset": {
                "dataFile": [
                    "JailBench-Tiny",
                    "JailbreakPrompts-Tiny",
                    "ChatGPT-Jailbreak-Prompts"
                ],
                "numPrompts": 100,
                "randomSeed": 42
            }
        }
    }
    
    task_response = requests.post(task_url, json=task_data)
    if task_response.json()['status'] != 0:
        raise Exception("任务创建失败")
    
    session_id = task_response.json()['data']['session_id']
    print(f"大模型安全体检任务创建成功，会话ID: {session_id}")
    
    # 2. 监控任务执行
    print("2. 监控任务执行...")
    status_url = f"{base_url}/api/v1/app/taskapi/status/{session_id}"
    
    while True:
        status_response = requests.get(status_url)
        status_data = status_response.json()
        
        if status_data['status'] != 0:
            raise Exception("获取任务状态失败")
        
        task_status = status_data['data']['status']
        print(f"当前状态: {task_status}")
        
        if task_status == "completed":
            print("红队测评完成！")
            break
        elif task_status == "failed":
            raise Exception("大模型安全体检失败")
        
        time.sleep(30)  # 大模型安全体检通常需要更长时间
    
    # 3. 获取测评结果
    print("3. 获取测评结果...")
    result_url = f"{base_url}/api/v1/app/taskapi/result/{session_id}"
    result_response = requests.get(result_url)
    
    if result_response.json()['status'] != 0:
        raise Exception("获取测评结果失败")
    
    redteam_results = result_response.json()['data']
    print("大模型安全体检结果:")
    print(json.dumps(redteam_results, indent=2, ensure_ascii=False))
    
    return redteam_results

# 执行红队测评流程
if __name__ == "__main__":
    try:
        results = complete_redteam_workflow()
        print("大模型安全体检完成！")
    except Exception as e:
        print(f"大模型安全体检失败: {e}")
```

## 错误处理

### 常见错误码
| 状态码 | 说明 | 解决方案 |
|--------|------|----------|
| 0 | 成功 | - |
| 1 | 失败 | 查看message字段获取详细错误信息 |

### 错误处理示例
```python
def handle_api_response(response):
    """处理API响应的通用函数"""
    data = response.json()
    
    if data['status'] == 0:
        return data['data']
    else:
        raise Exception(f"API调用失败: {data['message']}")

# 使用示例
try:
    result = handle_api_response(response)
    print("操作成功:", result)
except Exception as e:
    print("操作失败:", str(e))
```

## 注意事项

1. **认证**: 确保在请求头中包含正确的认证信息
2. **文件大小**: 上传文件大小限制请参考服务器配置
3. **超时设置**: 根据任务复杂度合理设置超时时间
4. **并发限制**: 避免同时创建过多任务，以免影响系统性能
5. **结果保存**: 及时保存扫描结果，避免数据丢失
6. **数据集选择**: 根据测试需求选择合适的数据集组合
7. **模型配置**: 确保测试模型和评估模型配置正确

## 技术支持

如有问题，请联系技术支持团队或查看项目文档。
