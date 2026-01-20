# Agent-Scan

AI Agent 驱动的自动化代码扫描和漏洞检测工具

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt
# 运行扫描
python main.py -m deepseek/deepseek-v3.2 -k sk-123456 --agent_provider demo_dify.yaml
```

## 命令行参数

```bash
python main.py [选项]

可选参数:
  --repo PATH              要扫描的项目路径
  -p, --prompt TEXT        自定义扫描提示词
  -m, --model TEXT         LLM 模型名称 (默认: deepseek/deepseek-v3.2-exp)
  -k, --api_key TEXT       API Key (默认从环境变量 OPENROUTER_API_KEY 读取)
  -u, --base_url TEXT      API 基础 URL (默认: https://openrouter.ai/api/v1)
  --agent_provider PATH    Agent provider 配置文件
  --language TEXT          输出语言 zh/en (默认: zh)
```
