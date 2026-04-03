# A.I.G API ドキュメント


## 概要

A.I.G（AI-Infra-Guard）は、Agent Scan、MCPサーバースキャン、ジェイルブレイク評価、AIインフラスキャン、およびモデル構成管理のための包括的なAPIインターフェースを提供します。本ドキュメントでは、各APIインターフェースの使用方法、パラメータの説明、およびサンプルコードについて詳しく説明します。

プロジェクト起動後、`http://localhost:8088/docs/index.html` にアクセスしてSwaggerドキュメントを閲覧できます。

## 目次

### 基本インターフェース
- ファイルアップロードインターフェース
- タスク作成インターフェース

### タスクタイプ
1. Agent Scan API
2. MCPサーバースキャン API
3. ジェイルブレイク評価 API
4. AIインフラスキャン API

### モデル管理 API
1. モデル一覧取得
2. モデル詳細取得
3. モデル作成
4. モデル更新
5. モデル削除
6. YAML設定モデル

### タスクステータス照会
- タスクステータス取得
- タスク結果取得

### 完全なワークフロー例
- MCPソースコードスキャンの完全なワークフロー
- ジェイルブレイク評価の完全なワークフロー

## 基本情報

- **ベースURL**: `http://localhost:8088`（実際のデプロイに応じて調整してください）
- **Content-Type**: `application/json`
- **認証**: リクエストヘッダーを通じて認証情報を渡します

## 共通レスポンス形式

すべてのAPIインターフェースは統一されたレスポンス形式に従います：

```json
{
  "status": 0,           // ステータスコード: 0=成功, 1=失敗
  "message": "操作成功",  // レスポンスメッセージ
  "data": {}             // レスポンスデータ
}
```

## APIインターフェース一覧

### 1. ファイルアップロードインターフェース

#### インターフェース情報
- **URL**: `/api/v1/app/taskapi/upload`
- **メソッド**: `POST`
- **Content-Type**: `multipart/form-data`

#### パラメータ説明
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| file | file | はい | アップロードするファイル。zip、json、txtなどの形式に対応 |

#### レスポンスフィールド
| フィールド | 型 | 説明 |
|-----------|------|------|
| fileUrl | string | ファイルアクセスURL |
| filename | string | ファイル名 |
| size | integer | ファイルサイズ（バイト） |

#### Pythonサンプル
```python
import requests

def upload_file(file_path):
    url = "http://localhost:8088/api/v1/app/taskapi/upload"

    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)

    return response.json()

# 使用例
result = upload_file("example.zip")
print(f"ファイルアップロード成功: {result['data']['fileUrl']}")
```

#### cURLサンプル
```bash
curl -X POST \
  http://localhost:8088/api/v1/app/taskapi/upload \
  -F "file=@example.zip"
```

### 2. タスク作成インターフェース

#### インターフェース情報
- **URL**: `/api/v1/app/taskapi/tasks`
- **メソッド**: `POST`
- **Content-Type**: `application/json`

#### リクエストパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| type | string | はい | タスクタイプ: mcp_scan, ai_infra_scan, model_redteam_report |
| content | object | はい | タスク内容。タスクタイプに応じて異なります |

#### レスポンスフィールド
| フィールド | 型 | 説明 |
|-----------|------|------|
| session_id | string | タスクセッションID |

---

## タスクタイプの詳細説明

### 1. Agent Scan API

AIエージェント（Dify、Coze、またはカスタムHTTPエンドポイントなど）に対してセキュリティスキャンを実行し、プロンプトインジェクション、権限昇格、データ漏洩などの脆弱性を検出します。

> **注意**: Agent Scan APIはまだ利用できません。Agent ScanタスクのセットアップとトリガーにはWeb UIをご使用ください。

---

### 2. MCPサーバースキャン API

MCPサーバースキャンは、MCPサーバーのセキュリティ脆弱性を検出するために使用されます。

#### リクエストパラメータ説明
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| content | string | いいえ | タスク内容の説明 |
| model | object | はい | モデル設定 |
| model.model | string | はい | モデル名（例: "gpt-4"） |
| model.token | string | はい | APIキー |
| model.base_url | string | いいえ | ベースURL。デフォルトはOpenAI API |
| thread | integer | いいえ | 同時実行スレッド数。デフォルト4 |
| language | string | いいえ | 言語コード（例: "zh"） |
| attachments | string | いいえ | 添付ファイルパス（事前にファイルをアップロードする必要があります） |
| headers | object | いいえ | カスタムリクエストヘッダー（例: {"Authorization": "Bearer token"}） |
| prompt | string | いいえ | カスタムスキャンプロンプトの説明 |

#### ソースコードスキャンプロセス
1. まずファイルアップロードインターフェースを呼び出してソースコードファイルをアップロード
2. 返されたfileUrlをattachmentsパラメータとして使用
3. MCPサーバースキャンAPIを呼び出す

#### Pythonサンプル
```python
import requests
import json

def mcp_scan_with_source_code():
    # 1. ソースコードファイルをアップロード
    upload_url = "http://localhost:8088/api/v1/app/taskapi/upload"
    with open("source_code.zip", 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(upload_url, files=files)

    if upload_response.json()['status'] != 0:
        raise Exception("ファイルアップロード失敗")

    fileUrl = upload_response.json()['data']['fileUrl']

    # 2. MCPサーバースキャンタスクを作成
    task_url = "http://localhost:8088/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "prompt": "このMCPサーバーをスキャン",
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

# 使用例
result = mcp_scan_with_source_code()
print(f"タスク作成成功、セッションID: {result['data']['session_id']}")
```

#### 動的URLスキャンの例
```python
def mcp_scan_with_url():
    task_url = "http://localhost:8088/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "content": "https://mcp-server.example.com",  # URLを直接入力
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

#### cURLサンプル
```bash
# ソースコードスキャン
curl -X POST http://localhost:8088/api/v1/app/taskapi/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "mcp_scan",
    "content": {
      "prompt": "このMCPサーバーをスキャン",
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

# URLスキャン
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

### 3. ジェイルブレイク評価 API

LLMに対してジェイルブレイク評価テストを実行し、セキュリティと堅牢性を評価するために使用されます。

#### リクエストパラメータ説明
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| model | array | はい | テスト対象モデルのリスト |
| eval_model | object | はい | 評価モデルの設定 |
| dataset | object | はい | データセット設定 |
| dataset.dataFile | array | はい | データセットファイルのリスト。以下のオプションに対応:<br/>- JailBench-Tiny: 小規模ジェイルブレイクベンチマークテストデータセット<br/>- JailbreakPrompts-Tiny: 小規模ジェイルブレイクプロンプトデータセット<br/>- ChatGPT-Jailbreak-Prompts: ChatGPTジェイルブレイクプロンプトデータセット<br/>- JADE-db-v3.0: JADEデータベース v3.0<br/>- HarmfulEvalBenchmark: 有害コンテンツ評価ベンチマークデータセット |
| dataset.numPrompts | integer | はい | プロンプト数 |
| dataset.randomSeed | integer | はい | ランダムシード |
| prompt | string | いいえ | カスタムテストプロンプト |
| techniques | array | いいえ | テスト技法のリスト（例: ["jailbreak", "adversarial"]） |

#### 対応データセットの説明

| データセット名 | 説明 | ユースケース |
|--------------|------|-------------|
| JailBench-Tiny | 小規模ジェイルブレイクベンチマークテストデータセット | ジェイルブレイク攻撃に対するモデルの耐性を迅速にテスト |
| JailbreakPrompts-Tiny | 小規模ジェイルブレイクプロンプトデータセット | 一般的なジェイルブレイク技法に対するモデルの防御をテスト |
| ChatGPT-Jailbreak-Prompts | ChatGPTジェイルブレイクプロンプトデータセット | ChatGPTに特化したジェイルブレイクテスト |
| JADE-db-v3.0 | JADEデータベース v3.0 | 包括的なAIセキュリティ評価データセット |
| HarmfulEvalBenchmark | 有害コンテンツ評価ベンチマークデータセット | モデルが生成する有害コンテンツのリスク評価 |

#### Pythonサンプル
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

# 使用例
result = model_redteam_test()
print(f"ジェイルブレイク評価タスク作成成功、セッションID: {result['data']['session_id']}")
```

#### 異なるデータセット組み合わせの例
```python
# JADEデータベースを使用した包括的テスト
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

# 有害コンテンツ評価ベンチマークの使用
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
            "prompt": "有害コンテンツテスト用のカスタムプロンプト"
        }
    }
    return requests.post(task_url, json=task_data).json()
```

#### cURLサンプル
```bash
# 基本的なレッドチームテスト
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

# 包括的セキュリティ評価
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

### 4. AIインフラスキャン API

AIインフラのセキュリティ脆弱性と設定上の問題をスキャンするために使用されます。

#### リクエストパラメータ説明
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| target | array | はい | スキャン対象URLのリスト |
| headers | object | いいえ | カスタムリクエストヘッダー |
| timeout | integer | いいえ | リクエストタイムアウト（秒）。デフォルト30 |
| model | object | いいえ | 補助分析用のモデル設定 |
| model.model | string | はい | モデル名（例: "gpt-4"） |
| model.token | string | はい | APIキー |
| model.base_url | string | いいえ | ベースURL。デフォルトはOpenAI API |

#### Pythonサンプル
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

# 使用例
result = ai_infra_scan()
print(f"AIインフラスキャンタスク作成成功、セッションID: {result['data']['session_id']}")
```

#### cURLサンプル
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

---

## モデル管理 API

### 1. モデル一覧取得

#### インターフェース情報
- **URL**: `/api/v1/app/models`
- **メソッド**: `GET`
- **Content-Type**: `application/json`

#### レスポンスフィールド
| フィールド | 型 | 説明 |
|-----------|------|------|
| model_id | string | モデルID |
| model | object | モデル設定情報 |
| model.model | string | モデル名 |
| model.token | string | APIキー（********でマスク表示） |
| model.base_url | string | ベースURL |
| model.note | string | メモ情報 |
| model.limit | integer | リクエスト上限 |
| default | array | デフォルトフィールド（YAML設定モデルのみ） |

#### Pythonサンプル
```python
import requests

def get_model_list():
    url = "http://localhost:8088/api/v1/app/models"
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    return response.json()

# 使用例
result = get_model_list()
if result['status'] == 0:
    print("モデル一覧取得成功:")
    for model in result['data']:
        print(f"モデルID: {model['model_id']}")
        print(f"モデル名: {model['model']['model']}")
        print(f"ベースURL: {model['model']['base_url']}")
        print(f"メモ: {model['model']['note']}")
        print("---")
```

#### cURLサンプル
```bash
curl -X GET http://localhost:8088/api/v1/app/models \
  -H "Content-Type: application/json"
```

#### レスポンス例
```json
{
  "status": 0,
  "message": "モデル一覧の取得に成功しました",
  "data": [
    {
      "model_id": "gpt4-model",
      "model": {
        "model": "gpt-4",
        "token": "********",
        "base_url": "https://api.openai.com/v1",
        "note": "GPT-4 モデル",
        "limit": 1000
      }
    },
    {
      "model_id": "system_default",
      "model": {
        "model": "deepseek-chat",
        "token": "********",
        "base_url": "https://api.deepseek.com/v1",
        "note": "システムデフォルトモデル",
        "limit": 1000
      },
      "default": ["mcp_scan", "ai_infra_scan"]
    }
  ]
}
```

### 2. モデル詳細取得

#### インターフェース情報
- **URL**: `/api/v1/app/models/{modelId}`
- **メソッド**: `GET`
- **Content-Type**: `application/json`

#### パラメータ説明
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| modelId | string | はい | モデルID（パスパラメータ） |

#### レスポンスフィールド
| フィールド | 型 | 説明 |
|-----------|------|------|
| model_id | string | モデルID |
| model | object | モデル設定情報 |
| model.model | string | モデル名 |
| model.token | string | APIキー（********でマスク表示） |
| model.base_url | string | ベースURL |
| model.note | string | メモ情報 |
| model.limit | integer | リクエスト上限 |
| default | array | デフォルトフィールド（YAML設定モデルのみ） |

#### Pythonサンプル
```python
def get_model_detail(model_id):
    url = f"http://localhost:8088/api/v1/app/models/{model_id}"
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    return response.json()

# 使用例
result = get_model_detail("gpt4-model")
if result['status'] == 0:
    model_data = result['data']
    print(f"モデルID: {model_data['model_id']}")
    print(f"モデル名: {model_data['model']['model']}")
    print(f"ベースURL: {model_data['model']['base_url']}")
    print(f"メモ: {model_data['model']['note']}")
```

#### cURLサンプル
```bash
curl -X GET http://localhost:8088/api/v1/app/models/gpt4-model \
  -H "Content-Type: application/json"
```

#### レスポンス例
```json
{
  "status": 0,
  "message": "モデル詳細の取得に成功しました",
  "data": {
    "model_id": "gpt4-model",
    "model": {
      "model": "gpt-4",
      "token": "********",
      "base_url": "https://api.openai.com/v1",
      "note": "GPT-4 モデル",
      "limit": 1000
    }
  }
}
```

### 3. モデル作成

#### インターフェース情報
- **URL**: `/api/v1/app/models`
- **メソッド**: `POST`
- **Content-Type**: `application/json`

#### リクエストパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| model_id | string | はい | モデルID。グローバルに一意である必要があります |
| model | object | はい | モデル設定情報 |
| model.model | string | はい | モデル名 |
| model.token | string | はい | APIキー |
| model.base_url | string | はい | ベースURL |
| model.note | string | いいえ | メモ情報 |
| model.limit | integer | いいえ | リクエスト上限。デフォルト1000 |

#### Pythonサンプル
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
            "note": "My GPT-4 モデル",
            "limit": 2000
        }
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()

# 使用例
result = create_model()
if result['status'] == 0:
    print("モデル作成成功")
else:
    print(f"モデル作成失敗: {result['message']}")
```

#### cURLサンプル
```bash
curl -X POST http://localhost:8088/api/v1/app/models \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "my-gpt4-model",
    "model": {
      "model": "gpt-4",
      "token": "sk-your-api-key-here",
      "base_url": "https://api.openai.com/v1",
      "note": "My GPT-4 モデル",
      "limit": 2000
    }
  }'
```

#### レスポンス例
```json
{
  "status": 0,
  "message": "モデルの作成に成功しました",
  "data": null
}
```

### 4. モデル更新

#### インターフェース情報
- **URL**: `/api/v1/app/models/{modelId}`
- **メソッド**: `PUT`
- **Content-Type**: `application/json`

#### パラメータ説明
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| modelId | string | はい | モデルID（パスパラメータ） |
| model | object | はい | モデル設定情報 |
| model.model | string | いいえ | モデル名 |
| model.token | string | いいえ | APIキー（`********`または空で送信すると元の値を保持） |
| model.base_url | string | いいえ | ベースURL |
| model.note | string | いいえ | メモ情報 |
| model.limit | integer | いいえ | リクエスト上限 |

**注意**:
- tokenフィールドに`********`または空文字列を渡した場合、トークンは更新されず元の値が保持されます
- 部分的なフィールド更新に対応しています。渡されなかったフィールドは元の値が保持されます

#### Pythonサンプル
```python
def update_model(model_id):
    url = f"http://localhost:8088/api/v1/app/models/{model_id}"
    headers = {
        "Content-Type": "application/json"
    }
    # メモとリミットのみ更新し、トークンは変更しない
    data = {
        "model": {
            "model": "gpt-4-turbo",
            "token": "********",  # 元のトークンを保持
            "base_url": "https://api.openai.com/v1",
            "note": "更新されたメモ情報",
            "limit": 3000
        }
    }

    response = requests.put(url, json=data, headers=headers)
    return response.json()

# 使用例
result = update_model("my-gpt4-model")
if result['status'] == 0:
    print("モデル更新成功")
else:
    print(f"モデル更新失敗: {result['message']}")
```

#### トークン更新の例
```python
def update_model_token(model_id, new_token):
    url = f"http://localhost:8088/api/v1/app/models/{model_id}"
    data = {
        "model": {
            "model": "gpt-4",
            "token": new_token,  # 新しいトークンを渡す
            "base_url": "https://api.openai.com/v1",
            "note": "APIキーを更新",
            "limit": 2000
        }
    }

    response = requests.put(url, json=data)
    return response.json()
```

#### cURLサンプル
```bash
# メモ情報のみ更新
curl -X PUT http://localhost:8088/api/v1/app/models/my-gpt4-model \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "model": "gpt-4-turbo",
      "token": "********",
      "base_url": "https://api.openai.com/v1",
      "note": "更新されたメモ情報",
      "limit": 3000
    }
  }'

# トークンの更新
curl -X PUT http://localhost:8088/api/v1/app/models/my-gpt4-model \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "model": "gpt-4",
      "token": "sk-new-api-key-here",
      "base_url": "https://api.openai.com/v1",
      "note": "APIキーを更新",
      "limit": 2000
    }
  }'
```

#### レスポンス例
```json
{
  "status": 0,
  "message": "モデルの更新に成功しました",
  "data": null
}
```

### 5. モデル削除

#### インターフェース情報
- **URL**: `/api/v1/app/models`
- **メソッド**: `DELETE`
- **Content-Type**: `application/json`

#### リクエストパラメータ
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| model_ids | array | はい | 削除するモデルIDのリスト。一括削除に対応 |

#### Pythonサンプル
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

# 単一モデルの削除
result = delete_models(["my-gpt4-model"])
if result['status'] == 0:
    print("モデル削除成功")

# 複数モデルの一括削除
result = delete_models(["model1", "model2", "model3"])
if result['status'] == 0:
    print("一括削除成功")
```

#### cURLサンプル
```bash
# 単一モデルの削除
curl -X DELETE http://localhost:8088/api/v1/app/models \
  -H "Content-Type: application/json" \
  -d '{
    "model_ids": ["my-gpt4-model"]
  }'

# 複数モデルの一括削除
curl -X DELETE http://localhost:8088/api/v1/app/models \
  -H "Content-Type: application/json" \
  -d '{
    "model_ids": ["model1", "model2", "model3"]
  }'
```

#### レスポンス例
```json
{
  "status": 0,
  "message": "削除に成功しました",
  "data": null
}
```

### 6. YAML設定モデル

APIを通じてデータベースに作成するモデルに加えて、YAML設定ファイルを通じてシステムレベルのモデルを定義することもできます。

#### 設定ファイルの場所
`db/model.yaml`

#### YAML設定フォーマット
```yaml
- model_id: system_default
  model_name: deepseek-chat
  token: sk-your-api-key
  base_url: https://api.deepseek.com/v1
  note: システムデフォルトモデル
  limit: 1000
  default:
    - mcp_scan
    - ai_infra_scan

- model_id: eval_model
  model_name: gpt-4
  token: sk-your-eval-key
  base_url: https://api.openai.com/v1
  note: 評価モデル
  limit: 2000
  default:
    - model_redteam_report
```

#### フィールド説明
| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| model_id | string | はい | モデルID |
| model_name | string | はい | モデル名 |
| token | string | はい | APIキー |
| base_url | string | はい | ベースURL |
| note | string | いいえ | メモ情報 |
| limit | integer | いいえ | リクエスト上限 |
| default | array | いいえ | このモデルをデフォルトで使用するタスクタイプのリスト |

#### 機能説明
- YAML設定モデルは**読み取り専用**であり、APIを通じて変更・削除できません
- YAML設定モデルは、一覧および詳細を取得する際にデータベースモデルとマージされます
- `default`フィールドはYAMLモデル固有のもので、モデルが適用されるデフォルトのタスクタイプを識別するために使用されます
- YAML設定はシステム起動時に自動的に読み込まれます

---

## タスクステータス照会

### タスクステータス取得

#### インターフェース情報
- **URL**: `/api/v1/app/taskapi/status/{id}`
- **メソッド**: `GET`

#### パラメータ説明
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| id | string | はい | タスクセッションID |

#### レスポンスフィールド
| フィールド | 型 | 説明 |
|-----------|------|------|
| session_id | string | タスクセッションID |
| status | string | タスクステータス: pending, running, completed, failed |
| title | string | タスクタイトル |
| created_at | integer | 作成タイムスタンプ（ミリ秒） |
| updated_at | integer | 更新タイムスタンプ（ミリ秒） |
| log | string | タスク実行ログ |

#### Pythonサンプル
```python
def get_task_status(session_id):
    url = f"http://localhost:8088/api/v1/app/taskapi/status/{session_id}"
    response = requests.get(url)
    return response.json()

# 使用例
status = get_task_status("550e8400-e29b-41d4-a716-446655440000")
print(f"タスクステータス: {status['data']['status']}")
print(f"実行ログ: {status['data']['log']}")
```

#### cURLサンプル
```bash
curl -X GET http://localhost:8088/api/v1/app/taskapi/status/550e8400-e29b-41d4-a716-446655440000
```

### タスク結果取得

#### インターフェース情報
- **URL**: `/api/v1/app/taskapi/result/{id}`
- **メソッド**: `GET`

#### パラメータ説明
| パラメータ | 型 | 必須 | 説明 |
|-----------|------|------|------|
| id | string | はい | タスクセッションID |

#### レスポンス説明
以下を含む詳細なスキャン結果を返します：
- 検出された脆弱性のリスト
- セキュリティ評価レポート
- 改善推奨事項
- リスクレベル評価

#### Pythonサンプル
```python
def get_task_result(session_id):
    url = f"http://localhost:8088/api/v1/app/taskapi/result/{session_id}"
    response = requests.get(url)
    return response.json()

# 使用例
result = get_task_result("550e8400-e29b-41d4-a716-446655440000")
if result['status'] == 0:
    print("スキャン結果:")
    print(json.dumps(result['data'], indent=2, ensure_ascii=False))
else:
    print(f"結果取得失敗: {result['message']}")
```

#### cURLサンプル
```bash
curl -X GET http://localhost:8088/api/v1/app/taskapi/result/550e8400-e29b-41d4-a716-446655440000
```

---

## 完全なワークフロー例

### MCPソースコードスキャンの完全なワークフロー

```python
import requests
import time
import json

def complete_mcp_scan_workflow():
    base_url = "http://localhost:8088"

    # 1. ソースコードファイルをアップロード
    print("1. ソースコードファイルをアップロード中...")
    upload_url = f"{base_url}/api/v1/app/taskapi/upload"
    with open("mcp_source.zip", 'rb') as f:
        files = {'file': f}
        upload_response = requests.post(upload_url, files=files)

    if upload_response.json()['status'] != 0:
        raise Exception("ファイルアップロード失敗")

    fileUrl = upload_response.json()['data']['fileUrl']
    print(f"ファイルアップロード成功: {fileUrl}")

    # 2. MCPスキャンタスクを作成
    print("2. MCPスキャンタスクを作成中...")
    task_url = f"{base_url}/api/v1/app/taskapi/tasks"
    task_data = {
        "type": "mcp_scan",
        "content": {
            "prompt": "このMCPサーバーをスキャン",
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
        raise Exception("タスク作成失敗")

    session_id = task_response.json()['data']['session_id']
    print(f"タスク作成成功、セッションID: {session_id}")

    # 3. タスクステータスをポーリング
    print("3. タスク実行を監視中...")
    status_url = f"{base_url}/api/v1/app/taskapi/status/{session_id}"

    while True:
        status_response = requests.get(status_url)
        status_data = status_response.json()

        if status_data['status'] != 0:
            raise Exception("タスクステータスの取得に失敗")

        task_status = status_data['data']['status']
        print(f"現在のステータス: {task_status}")

        if task_status == "completed":
            print("タスク実行完了！")
            break
        elif task_status == "failed":
            raise Exception("タスク実行失敗")

        time.sleep(10)  # 10秒後に再確認

    # 4. スキャン結果を取得
    print("4. スキャン結果を取得中...")
    result_url = f"{base_url}/api/v1/app/taskapi/result/{session_id}"
    result_response = requests.get(result_url)

    if result_response.json()['status'] != 0:
        raise Exception("スキャン結果の取得に失敗")

    scan_results = result_response.json()['data']
    print("スキャン結果:")
    print(json.dumps(scan_results, indent=2, ensure_ascii=False))

    return scan_results

# 完全なワークフローを実行
if __name__ == "__main__":
    try:
        results = complete_mcp_scan_workflow()
        print("MCPサーバースキャン完了！")
    except Exception as e:
        print(f"スキャン失敗: {e}")
```

### ジェイルブレイク評価の完全なワークフロー

```python
def complete_redteam_workflow():
    base_url = "http://localhost:8088"

    # 1. ジェイルブレイク評価タスクを作成
    print("1. ジェイルブレイク評価タスクを作成中...")
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
        raise Exception("タスク作成失敗")

    session_id = task_response.json()['data']['session_id']
    print(f"ジェイルブレイク評価タスク作成成功、セッションID: {session_id}")

    # 2. タスク実行を監視
    print("2. タスク実行を監視中...")
    status_url = f"{base_url}/api/v1/app/taskapi/status/{session_id}"

    while True:
        status_response = requests.get(status_url)
        status_data = status_response.json()

        if status_data['status'] != 0:
            raise Exception("タスクステータスの取得に失敗")

        task_status = status_data['data']['status']
        print(f"現在のステータス: {task_status}")

        if task_status == "completed":
            print("ジェイルブレイク評価完了！")
            break
        elif task_status == "failed":
            raise Exception("ジェイルブレイク評価失敗")

        time.sleep(30)  # レッドチーム評価は通常時間がかかります

    # 3. 評価結果を取得
    print("3. 評価結果を取得中...")
    result_url = f"{base_url}/api/v1/app/taskapi/result/{session_id}"
    result_response = requests.get(result_url)

    if result_response.json()['status'] != 0:
        raise Exception("評価結果の取得に失敗")

    redteam_results = result_response.json()['data']
    print("ジェイルブレイク評価結果:")
    print(json.dumps(redteam_results, indent=2, ensure_ascii=False))

    return redteam_results

# ジェイルブレイク評価ワークフローを実行
if __name__ == "__main__":
    try:
        results = complete_redteam_workflow()
        print("ジェイルブレイク評価完了！")
    except Exception as e:
        print(f"ジェイルブレイク評価失敗: {e}")
```

## エラーハンドリング

### 一般的なエラーコード
| ステータスコード | 説明 | 対処法 |
|-------------|------|--------|
| 0 | 成功 | - |
| 1 | 失敗 | messageフィールドで詳細なエラー情報を確認してください |

### エラーハンドリングの例
```python
def handle_api_response(response):
    """APIレスポンスを処理する共通関数"""
    data = response.json()

    if data['status'] == 0:
        return data['data']
    else:
        raise Exception(f"API呼び出し失敗: {data['message']}")

# 使用例
try:
    result = handle_api_response(response)
    print("操作成功:", result)
except Exception as e:
    print("操作失敗:", str(e))
```

## 注意事項

### 全般的な注意事項
1. **認証**: リクエストヘッダーに正しい認証情報が含まれていることを確認してください
2. **ファイルサイズ**: ファイルアップロードのサイズ制限についてはサーバー設定を参照してください
3. **タイムアウト設定**: タスクの複雑さに応じて適切なタイムアウト時間を設定してください
4. **同時実行制限**: システムパフォーマンスへの影響を避けるため、同時に大量のタスクを作成しないでください
5. **結果の保存**: データ損失を防ぐため、スキャン結果を速やかに保存してください

### タスク関連の注意事項
6. **データセット選択**: テスト要件に基づいて適切なデータセットの組み合わせを選択してください
7. **モデル設定**: テストモデルと評価モデルの設定が正しいことを確認してください

### モデル管理の注意事項
8. **モデルIDの一意性**: モデル作成時、model_idはグローバルに一意である必要があります
9. **トークンのセキュリティ**: APIキーはレスポンスで自動的に`********`でマスクされます。フロントエンドでの表示・編集時にご注意ください
10. **トークンの更新**: モデル更新時、tokenフィールドが空または`********`の場合、トークンは更新されず元の値が保持されます
11. **モデルの検証**: システムはモデル作成時にtokenとbase_urlを自動的に検証します
12. **YAMLモデル**: YAML経由で設定されたモデルは読み取り専用であり、APIを通じて変更・削除できません
13. **一括削除**: モデル削除は複数のmodel_idを渡して一括削除に対応しています
14. **権限制御**: モデルの作成者のみが、そのモデルの閲覧・変更・削除が可能です

## テクニカルサポート

問題がございましたら、テクニカルサポートチームにお問い合わせいただくか、プロジェクトドキュメントを参照してください。
