# 3. AI基础设施安全扫描

## a) 快速扫描模式

A.I.G的默认扫描模式即为快速扫描模式。它会根据内置的指纹库，快速识别目标站点的组件信息，并匹配相应的漏洞。

```bash
# 对单个目标进行快速扫描
./ai-infra-guard scan --url <target_url>

# 从文件中批量读取目标进行扫描
./ai-infra-guard scan -f <url_file>
```

## b) AI深度扫描模式

(此功能在未来版本中规划)

AI深度扫描模式将利用AI Agent对目标进行更深入的分析，尝试发现业务逻辑漏洞、0-day漏洞等更复杂的问题。

## c) 自定义扫描规则与指纹

A.I.G使用基于YAML的规则进行Web组件指纹识别和漏洞匹配。 

*   **指纹规则**: 存放在 `data/fingerprints` 目录中。 
*   **漏洞规则**: 存放在 `data/vuln` 目录中。 

您可以根据需要添加或修改这些规则，以扩展A.I.G的检测能力。

### 指纹规则示例 
`data/fingerprints/example-component.yaml`

```yaml
name: "ExampleComponent"
rules:
  - method: "keyword"
    keyword: "Powered by ExampleComponent"
```

### 漏洞规则示例 
`data/vuln/example-vuln.yaml`

```yaml
name: "ExampleComponent Remote Code Execution"
fingerprint:
  name: "ExampleComponent"
vulnerability:
  type: "rce"
  description: "A remote code execution vulnerability exists in ExampleComponent."
  remediation: "Upgrade ExampleComponent to version 2.0 or later."
```

## d) 当前支持的AI组件漏洞指纹

A.I.G目前支持对以下（但不限于）AI相关的Web组件进行指纹识别和漏洞扫描：

*   Jupyter Notebook
*   MLflow
*   Kubeflow
*   TensorBoard
*   Ray Dashboard
*   ... (请参考项目`data/fingerprints`目录获取最新列表)