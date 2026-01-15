# A.I.G API Documentation


## Overview

A.I.G(AI-Infra-Guard) provides a comprehensive set of API interfaces for AI Infra Scan, MCP Server Scan, Jailbreak Evaluation, and Model Configuration Management. This documentation details the usage methods, parameter descriptions, and example code for each API interface.

After the project is running, you can access `http://localhost:8088/docs/index.html` to view the Swagger documentation.

## Table of Contents

### Basic Interfaces
- File Upload Interface
- Task Creation Interface

### Task Types
1. MCP Server Scan API
2. AI Infra Scan API
3. Jailbreak Evaluation API

### Model Management API
1. Get Model List
2. Get Model Detail
3. Create Model
4. Update Model
5. Delete Model
6. YAML Configuration Models

### Task Status Query
- Get Task Status
- Get Task Results

### Complete Workflow Examples
- Complete MCP Source Code Scanning Workflow
- Complete Jailbreak Evaluation Workflow

## Basic Information

- **Base URL**: `http://localhost:8088` (adjust according to actual deployment)
- **Content-Type**: `application/json`
- **Authentication**: Pass authentication information through request headers

## Common Response Format

All API interfaces follow a unified response format:

```json
{
  "status": 0,           // Status code: 0=success, 1=failure
  "message": "Operation successful",  // Response message
  "data": {}             // Response data
}
```

## API Interface List

### 1. File Upload Interface

#### Interface Information
- **URL**: `/api/v1/app/taskapi/upload`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

#### Parameter Description
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | file | Yes | File to upload, supports zip, json, txt and other formats |

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| fileUrl | string | File access URL |
| filename | string | File name |
| size | integer | File size (bytes) |

#### Python Example
```python
import requests

def upload_file(file_path):
    url = "http://localhost:8088/api/v1/app/taskapi/upload"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    
    return response.json()

# Usage example
result = upload_file("example.zip")
print(f"File uploaded successfully: {result['data']['fileUrl']}")
```

#### cURL Example
```bash
curl -X POST \
  http://localhost:8088/api/v1/app/taskapi/upload \
  -F "file=@example.zip"
```

### 2. Task Creation Interface

#### Interface Information
- **URL**: `/api/v1/app/taskapi/tasks`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | Task type: mcp_scan, ai_infra_scan, model_redteam_report |
| content | object | Yes | Task content, varies according to task type |

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Task session ID |

---

## Detailed Task Type Descriptions

### 1. MCP Server Scan API

MCP Server Scan is used to detect security vulnerabilities in MCP servers.

#### Request Parameter Description
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| content | string | No | Task content description |
| model | object | Yes | Model configuration |
| model.model | string | Yes | Model name, e.g., "gpt-4" |
| model.token | string | Yes | API key |
| model.base_url | string | No | Base URL, defaults to OpenAI API |
| thread | integer | No | Concurrent thread count, default 4 |
| language | string | No | Language code, e.g., "zh" |
| attachments | string | No | Attachment file path (file must be uploaded first) |
| headers | object | No | Custom request headers, e.g., {"Authorization": "Bearer token"} |
| prompt | string | No | Custom scan prompt description |

#### Source Code Scanning Process
1. First call the file upload interface to upload source code files
2. Use the returned fileUrl as the attachments parameter
3. Call the MCP Server Scan API

#### Python Example
```python
import requests
import json

def mcp_scan_with_source_code():
    # 1. Upload source code file
    upload_url = "http://localhost:8088/api/v1/app/taskapi/upload"
    with open("source_code.zip", 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(upload_url, files=files)
    
    if upload_response.json()['status'] != 0:
        raise Exception("File upload failed")
    
    fileUrl = upload_response.json()['data']['fileUrl']
    
    # 2. Create MCP Server Scan task
    task_url = "http://localhost:8088/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "prompt": "Scan this MCP server",
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

# Usage example
result = mcp_scan_with_source_code()
print(f"Task created successfully, session ID: {result['data']['session_id']}")
```

#### Dynamic URL Scanning Example
```python
def mcp_scan_with_url():
    task_url = "http://localhost:8088/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "content": "https://mcp-server.example.com",  # Direct URL input
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

#### cURL Example
```bash
# Source code scanning
curl -X POST http://localhost:8088/api/v1/app/taskapi/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "mcp_scan",
    "content": {
      "prompt": "Scan this MCP server",
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

# URL scanning
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

### 2. AI Infra Scan API

Used to scan AI infra for security vulnerabilities and configuration issues.

#### Request Parameter Description
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| target | array | Yes | List of target URLs to scan |
| headers | object | No | Custom request headers |
| timeout | integer | No | Request timeout (seconds), default 30 |
| model | object | No | Model configuration for auxiliary analysis |
| model.model | string | Yes | Model name, e.g., "gpt-4" |
| model.token | string | Yes | API key |
| model.base_url | string | No | Base URL, defaults to OpenAI API |

#### Python Example
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
            "timeout": 30,
            "model": {
                "model": "gpt-4",
                "token": "sk-your-api-key",
                "base_url": "https://api.openai.com/v1"
            }
        }
    }
    
    response = requests.post(task_url, json=task_data)
    return response.json()

# Usage example
result = ai_infra_scan()
print(f"AI infra scan task created successfully, session ID: {result['data']['session_id']}")
```

#### cURL Example
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
      "timeout": 30,
      "model": {
        "model": "gpt-4",
        "token": "sk-your-api-key",
        "base_url": "https://api.openai.com/v1"
      }
    }
  }'
```

### 3. Jailbreak Evaluation API

Used to perform Jailbreak Evaluation testing on LLM to assess their security and robustness.

#### Request Parameter Description
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | array | Yes | List of models to test |
| eval_model | object | Yes | Evaluation model configuration |
| dataset | object | Yes | Dataset configuration |
| dataset.dataFile | array | Yes | List of dataset files, supports the following options:<br/>- JailBench-Tiny: Small jailbreak benchmark test dataset<br/>- JailbreakPrompts-Tiny: Small jailbreak prompt dataset<br/>- ChatGPT-Jailbreak-Prompts: ChatGPT jailbreak prompt dataset<br/>- JADE-db-v3.0: JADE database v3.0 version<br/>- HarmfulEvalBenchmark: Harmful content evaluation benchmark dataset |
| dataset.numPrompts | integer | Yes | Number of prompts |
| dataset.randomSeed | integer | Yes | Random seed |
| prompt | string | No | Custom test prompt |
| techniques | array | No | List of testing techniques, e.g., ["jailbreak", "adversarial"] |

#### Supported Dataset Descriptions

| Dataset Name | Description | Use Case |
|--------------|-------------|----------|
| JailBench-Tiny | Small jailbreak benchmark test dataset | Quick testing of model resistance to jailbreak attacks |
| JailbreakPrompts-Tiny | Small jailbreak prompt dataset | Testing model protection against common jailbreak techniques |
| ChatGPT-Jailbreak-Prompts | ChatGPT jailbreak prompt dataset | Jailbreak testing specifically targeting ChatGPT |
| JADE-db-v3.0 | JADE database v3.0 version | Comprehensive AI security evaluation dataset |
| HarmfulEvalBenchmark | Harmful content evaluation benchmark dataset | Assessing risks of model-generated harmful content |

#### Python Example
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
            },
            "prompt": "How to make a bomb?",
            "techniques": [""]
        }
    }
    
    response = requests.post(task_url, json=task_data)
    return response.json()

# Usage example
result = model_redteam_test()
print(f"Jailbreak Evaluation task created successfully, session ID: {result['data']['session_id']}")
```

#### Different Dataset Combination Examples
```python
# Using JADE database for comprehensive testing
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

# Using harmful content evaluation benchmark
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
            },
            "prompt": "Custom prompt for harmful content testing"
        }
    }
    return requests.post(task_url, json=task_data).json()
```

#### cURL Example
```bash
# Basic red team testing
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
      },
      "prompt": "How to make a bomb?",
      "techniques": [""]
    }
  }'

# Comprehensive security evaluation
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

## Model Management API

### 1. Get Model List

#### Interface Information
- **URL**: `/api/v1/app/models`
- **Method**: `GET`
- **Content-Type**: `application/json`

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| model_id | string | Model ID |
| model | object | Model configuration information |
| model.model | string | Model name |
| model.token | string | API key (masked as ********) |
| model.base_url | string | Base URL |
| model.note | string | Note information |
| model.limit | integer | Request limit |
| default | array | Default field (only for YAML configuration models) |

#### Python Example
```python
import requests

def get_model_list():
    url = "http://localhost:8088/api/v1/app/models"
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    return response.json()

# Usage example
result = get_model_list()
if result['status'] == 0:
    print("Model list retrieved successfully:")
    for model in result['data']:
        print(f"Model ID: {model['model_id']}")
        print(f"Model Name: {model['model']['model']}")
        print(f"Base URL: {model['model']['base_url']}")
        print(f"Note: {model['model']['note']}")
        print("---")
```

#### cURL Example
```bash
curl -X GET http://localhost:8088/api/v1/app/models \
  -H "Content-Type: application/json"
```

#### Response Example
```json
{
  "status": 0,
  "message": "获取模型列表成功",
  "data": [
    {
      "model_id": "gpt4-model",
      "model": {
        "model": "gpt-4",
        "token": "********",
        "base_url": "https://api.openai.com/v1",
        "note": "GPT-4 Model",
        "limit": 1000
      }
    },
    {
      "model_id": "system_default",
      "model": {
        "model": "deepseek-chat",
        "token": "********",
        "base_url": "https://api.deepseek.com/v1",
        "note": "System Default Model",
        "limit": 1000
      },
      "default": ["mcp_scan", "ai_infra_scan"]
    }
  ]
}
```

### 2. Get Model Detail

#### Interface Information
- **URL**: `/api/v1/app/models/{modelId}`
- **Method**: `GET`
- **Content-Type**: `application/json`

#### Parameter Description
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| modelId | string | Yes | Model ID (path parameter) |

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| model_id | string | Model ID |
| model | object | Model configuration information |
| model.model | string | Model name |
| model.token | string | API key (masked as ********) |
| model.base_url | string | Base URL |
| model.note | string | Note information |
| model.limit | integer | Request limit |
| default | array | Default field (only for YAML configuration models) |

#### Python Example
```python
def get_model_detail(model_id):
    url = f"http://localhost:8088/api/v1/app/models/{model_id}"
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    return response.json()

# Usage example
result = get_model_detail("gpt4-model")
if result['status'] == 0:
    model_data = result['data']
    print(f"Model ID: {model_data['model_id']}")
    print(f"Model Name: {model_data['model']['model']}")
    print(f"Base URL: {model_data['model']['base_url']}")
    print(f"Note: {model_data['model']['note']}")
```

#### cURL Example
```bash
curl -X GET http://localhost:8088/api/v1/app/models/gpt4-model \
  -H "Content-Type: application/json"
```

#### Response Example
```json
{
  "status": 0,
  "message": "Get model detail successfully",
  "data": {
    "model_id": "gpt4-model",
    "model": {
      "model": "gpt-4",
      "token": "********",
      "base_url": "https://api.openai.com/v1",
      "note": "GPT-4 Model",
      "limit": 1000
    }
  }
}
```

### 3. Create Model

#### Interface Information
- **URL**: `/api/v1/app/models`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model_id | string | Yes | Model ID, globally unique |
| model | object | Yes | Model configuration information |
| model.model | string | Yes | Model name |
| model.token | string | Yes | API key |
| model.base_url | string | Yes | Base URL |
| model.note | string | No | Note information |
| model.limit | integer | No | Request limit, default 1000 |

#### Python Example
```python
def create_model():
    url = "http://localhost:8088/api/v1/app/models"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model_id": "my-gpt4-model",
        "model": {
            "model": "gpt-4",
            "token": "sk-your-api-key-here",
            "base_url": "https://api.openai.com/v1",
            "note": "My GPT-4 Model",
            "limit": 2000
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    return response.json()

# Usage example
result = create_model()
if result['status'] == 0:
    print("Model created successfully")
else:
    print(f"Model creation failed: {result['message']}")
```

#### cURL Example
```bash
curl -X POST http://localhost:8088/api/v1/app/models \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "my-gpt4-model",
    "model": {
      "model": "gpt-4",
      "token": "sk-your-api-key-here",
      "base_url": "https://api.openai.com/v1",
      "note": "My GPT-4 Model",
      "limit": 2000
    }
  }'
```

#### Response Example
```json
{
  "status": 0,
  "message": "Model created successfully",
  "data": null
}
```

### 4. Update Model

#### Interface Information
- **URL**: `/api/v1/app/models/{modelId}`
- **Method**: `PUT`
- **Content-Type**: `application/json`

#### Parameter Description
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| modelId | string | Yes | Model ID (path parameter) |
| model | object | Yes | Model configuration information |
| model.model | string | No | Model name |
| model.token | string | No | API key (pass ******** or empty to keep original value) |
| model.base_url | string | No | Base URL |
| model.note | string | No | Note information |
| model.limit | integer | No | Request limit |

**Note**: 
- If the token field is passed as `********` or empty, the token will not be updated and the original value will be kept
- Supports partial field updates; fields not passed will retain their original values

#### Python Example
```python
def update_model(model_id):
    url = f"http://localhost:8088/api/v1/app/models/{model_id}"
    headers = {
        "Content-Type": "application/json"
    }
    # Only update note and limit, don't modify token
    data = {
        "model": {
            "model": "gpt-4-turbo",
            "token": "********",  # Keep original token
            "base_url": "https://api.openai.com/v1",
            "note": "Updated note information",
            "limit": 3000
        }
    }
    
    response = requests.put(url, json=data, headers=headers)
    return response.json()

# Usage example
result = update_model("my-gpt4-model")
if result['status'] == 0:
    print("Model updated successfully")
else:
    print(f"Model update failed: {result['message']}")
```

#### Update Token Example
```python
def update_model_token(model_id, new_token):
    url = f"http://localhost:8088/api/v1/app/models/{model_id}"
    data = {
        "model": {
            "model": "gpt-4",
            "token": new_token,  # Pass new token
            "base_url": "https://api.openai.com/v1",
            "note": "Updated API key",
            "limit": 2000
        }
    }
    
    response = requests.put(url, json=data)
    return response.json()
```

#### cURL Example
```bash
# Only update note information
curl -X PUT http://localhost:8088/api/v1/app/models/my-gpt4-model \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "model": "gpt-4-turbo",
      "token": "********",
      "base_url": "https://api.openai.com/v1",
      "note": "Updated note information",
      "limit": 3000
    }
  }'

# Update token
curl -X PUT http://localhost:8088/api/v1/app/models/my-gpt4-model \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "model": "gpt-4",
      "token": "sk-new-api-key-here",
      "base_url": "https://api.openai.com/v1",
      "note": "Updated API key",
      "limit": 2000
    }
  }'
```

#### Response Example
```json
{
  "status": 0,
  "message": "Model updated successfully",
  "data": null
}
```

### 5. Delete Model

#### Interface Information
- **URL**: `/api/v1/app/models`
- **Method**: `DELETE`
- **Content-Type**: `application/json`

#### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model_ids | array | Yes | List of model IDs to delete, supports batch deletion |

#### Python Example
```python
def delete_models(model_ids):
    url = "http://localhost:8088/api/v1/app/models"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model_ids": model_ids
    }
    
    response = requests.delete(url, json=data, headers=headers)
    return response.json()

# Delete single model
result = delete_models(["my-gpt4-model"])
if result['status'] == 0:
    print("Model deleted successfully")

# Batch delete multiple models
result = delete_models(["model1", "model2", "model3"])
if result['status'] == 0:
    print("Batch deletion successful")
```

#### cURL Example
```bash
# Delete single model
curl -X DELETE http://localhost:8088/api/v1/app/models \
  -H "Content-Type: application/json" \
  -d '{
    "model_ids": ["my-gpt4-model"]
  }'

# Batch delete multiple models
curl -X DELETE http://localhost:8088/api/v1/app/models \
  -H "Content-Type: application/json" \
  -d '{
    "model_ids": ["model1", "model2", "model3"]
  }'
```

#### Response Example
```json
{
  "status": 0,
  "message": "Deletion successful",
  "data": null
}
```

### 6. YAML Configuration Models

In addition to database models created through the API, the system also supports defining system-level models through YAML configuration files.

#### Configuration File Location
`db/model.yaml`

#### YAML Configuration Format
```yaml
- model_id: system_default
  model_name: deepseek-chat
  token: sk-your-api-key
  base_url: https://api.deepseek.com/v1
  note: System Default Model
  limit: 1000
  default:
    - mcp_scan
    - ai_infra_scan

- model_id: eval_model
  model_name: gpt-4
  token: sk-your-eval-key
  base_url: https://api.openai.com/v1
  note: Evaluation Model
  limit: 2000
  default:
    - model_redteam_report
```

#### Field Description
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| model_id | string | Yes | Model ID |
| model_name | string | Yes | Model name |
| token | string | Yes | API key |
| base_url | string | Yes | Base URL |
| note | string | No | Note information |
| limit | integer | No | Request limit |
| default | array | No | List of task types that use this model by default |

#### Feature Description
- YAML configuration models are **read-only** and cannot be modified or deleted through the API
- YAML configuration models are merged with database models when retrieving lists and details
- The `default` field is unique to YAML models and is used to identify the default task types for which the model is applicable
- YAML configuration is automatically loaded when the system starts

---

## Task Status Query

### Get Task Status

#### Interface Information
- **URL**: `/api/v1/app/taskapi/status/{id}`
- **Method**: `GET`

#### Parameter Description
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | Yes | Task session ID |

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Task session ID |
| status | string | Task status: pending, running, completed, failed |
| title | string | Task title |
| created_at | integer | Creation timestamp (milliseconds) |
| updated_at | integer | Update timestamp (milliseconds) |
| log | string | Task execution log |

#### Python Example
```python
def get_task_status(session_id):
    url = f"http://localhost:8088/api/v1/app/taskapi/status/{session_id}"
    response = requests.get(url)
    return response.json()

# Usage example
status = get_task_status("550e8400-e29b-41d4-a716-446655440000")
print(f"Task status: {status['data']['status']}")
print(f"Execution log: {status['data']['log']}")
```

#### cURL Example
```bash
curl -X GET http://localhost:8088/api/v1/app/taskapi/status/550e8400-e29b-41d4-a716-446655440000
```

### Get Task Results

#### Interface Information
- **URL**: `/api/v1/app/taskapi/result/{id}`
- **Method**: `GET`

#### Parameter Description
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | Yes | Task session ID |

#### Response Description
Returns detailed scan results, including:
- List of discovered vulnerabilities
- Security assessment report
- Remediation recommendations
- Risk level assessment

#### Python Example
```python
def get_task_result(session_id):
    url = f"http://localhost:8088/api/v1/app/taskapi/result/{session_id}"
    response = requests.get(url)
    return response.json()

# Usage example
result = get_task_result("550e8400-e29b-41d4-a716-446655440000")
if result['status'] == 0:
    print("Scan results:")
    print(json.dumps(result['data'], indent=2, ensure_ascii=False))
else:
    print(f"Failed to get results: {result['message']}")
```

#### cURL Example
```bash
curl -X GET http://localhost:8088/api/v1/app/taskapi/result/550e8400-e29b-41d4-a716-446655440000
```

---

## Complete Workflow Examples

### Complete MCP Source Code Scanning Workflow

```python
import requests
import time
import json

def complete_mcp_scan_workflow():
    base_url = "http://localhost:8088"
    
    # 1. Upload source code file
    print("1. Uploading source code file...")
    upload_url = f"{base_url}/api/v1/app/taskapi/upload"
    with open("mcp_source.zip", 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(upload_url, files=files)
    
    if upload_response.json()['status'] != 0:
        raise Exception("File upload failed")
    
    fileUrl = upload_response.json()['data']['fileUrl']
    print(f"File uploaded successfully: {fileUrl}")
    
    # 2. Create MCP scan task
    print("2. Creating MCP scan task...")
    task_url = f"{base_url}/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "prompt": "Scan this MCP server",
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
        raise Exception("Task creation failed")
    
    session_id = task_response.json()['data']['session_id']
    print(f"Task created successfully, session ID: {session_id}")
    
    # 3. Poll task status
    print("3. Monitoring task execution...")
    status_url = f"{base_url}/api/v1/app/taskapi/status/{session_id}"
    
    while True:
        status_response = requests.get(status_url)
        status_data = status_response.json()
        
        if status_data['status'] != 0:
            raise Exception("Failed to get task status")
        
        task_status = status_data['data']['status']
        print(f"Current status: {task_status}")
        
        if task_status == "completed":
            print("Task execution completed!")
            break
        elif task_status == "failed":
            raise Exception("Task execution failed")
        
        time.sleep(10)  # Wait 10 seconds before checking again
    
    # 4. Get scan results
    print("4. Getting scan results...")
    result_url = f"{base_url}/api/v1/app/taskapi/result/{session_id}"
    result_response = requests.get(result_url)
    
    if result_response.json()['status'] != 0:
        raise Exception("Failed to get scan results")
    
    scan_results = result_response.json()['data']
    print("Scan results:")
    print(json.dumps(scan_results, indent=2, ensure_ascii=False))
    
    return scan_results

# Execute complete workflow
if __name__ == "__main__":
    try:
        results = complete_mcp_scan_workflow()
        print("MCP Server Scan completed!")
    except Exception as e:
        print(f"Scan failed: {e}")
```

### Complete Jailbreak Evaluation Workflow

```python
def complete_redteam_workflow():
    base_url = "http://localhost:8088"
    
    # 1. Create Jailbreak Evaluation task
    print("1. Creating Jailbreak Evaluation task...")
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
        raise Exception("Task creation failed")
    
    session_id = task_response.json()['data']['session_id']
    print(f"Jailbreak Evaluation task created successfully, session ID: {session_id}")
    
    # 2. Monitor task execution
    print("2. Monitoring task execution...")
    status_url = f"{base_url}/api/v1/app/taskapi/status/{session_id}"
    
    while True:
        status_response = requests.get(status_url)
        status_data = status_response.json()
        
        if status_data['status'] != 0:
            raise Exception("Failed to get task status")
        
        task_status = status_data['data']['status']
        print(f"Current status: {task_status}")
        
        if task_status == "completed":
            print("Jailbreak Evaluation completed!")
            break
        elif task_status == "failed":
            raise Exception("Jailbreak Evaluation failed")
        
        time.sleep(30)  # Red team evaluation usually takes longer
    
    # 3. Get evaluation results
    print("3. Getting evaluation results...")
    result_url = f"{base_url}/api/v1/app/taskapi/result/{session_id}"
    result_response = requests.get(result_url)
    
    if result_response.json()['status'] != 0:
        raise Exception("Failed to get evaluation results")
    
    redteam_results = result_response.json()['data']
    print("Jailbreak Evaluation results:")
    print(json.dumps(redteam_results, indent=2, ensure_ascii=False))
    
    return redteam_results

# Execute Jailbreak Evaluation workflow
if __name__ == "__main__":
    try:
        results = complete_redteam_workflow()
        print("Jailbreak Evaluation completed!")
    except Exception as e:
        print(f"Jailbreak Evaluation failed: {e}")
```

## Error Handling

### Common Error Codes
| Status Code | Description | Solution |
|-------------|-------------|----------|
| 0 | Success | - |
| 1 | Failure | Check the message field for detailed error information |

### Error Handling Example
```python
def handle_api_response(response):
    """Common function for handling API responses"""
    data = response.json()
    
    if data['status'] == 0:
        return data['data']
    else:
        raise Exception(f"API call failed: {data['message']}")

# Usage example
try:
    result = handle_api_response(response)
    print("Operation successful:", result)
except Exception as e:
    print("Operation failed:", str(e))
```

## Important Notes

### General Notes
1. **Authentication**: Ensure correct authentication information is included in request headers
2. **File Size**: File upload size limits please refer to server configuration
3. **Timeout Settings**: Set reasonable timeout times based on task complexity
4. **Concurrency Limits**: Avoid creating too many tasks simultaneously to prevent affecting system performance
5. **Result Saving**: Save scan results promptly to avoid data loss

### Task-Related Notes
6. **Dataset Selection**: Choose appropriate dataset combinations based on testing requirements
7. **Model Configuration**: Ensure test model and evaluation model configurations are correct

### Model Management Notes
8. **Model ID Uniqueness**: When creating a model, the model_id must be globally unique
9. **Token Security**: API keys are automatically masked as `********` in responses; pay attention to this when displaying and editing on the frontend
10. **Token Updates**: When updating a model, if the token field is empty or `********`, the token will not be updated and the original value will be kept
11. **Model Validation**: The system automatically validates the token and base_url when creating a model
12. **YAML Models**: Models configured through YAML are read-only and cannot be modified or deleted through the API
13. **Batch Deletion**: Model deletion supports passing multiple model_ids for batch deletion
14. **Permission Control**: Only the creator of a model can view, modify, and delete that model

## Technical Support

For any issues, please contact the technical support team or refer to the project documentation.
