# Ventor QTest 内置模块

本目录集成自 [kexinoh/ventor_qtest](https://github.com/kexinoh/ventor_qtest)，
基于上游提交 `b76c2a2`。上游采用 MIT License，许可证全文见本目录 `LICENSE`。

为避免改变 `aig_api_checker` 已有行为，本模块：

- 使用独立的 Python 包命名空间；
- 仅通过新增的 `qtest` / `ventor` CLI 子命令启用；
- 使用独立的 `config/default.yaml` 配置；
- 不修改现有算法、`baselines.json` 或 HTTP API 路由；
- 将上游的绝对模块导入调整为包内相对导入。

调用方式：

```bash
python main.py qtest run
python main.py qtest run --config path/to/config.yaml
python main.py qtest openrouter-providers --model moonshotai/kimi-k2.5
python -m ventor_qtest --help
```

运行测试需要相应供应商的 API Key。默认配置支持通过
`MOONSHOT_API_KEY`、`SILICONFLOW_API_KEY` 和 `OPENROUTER_API_KEY`
环境变量传入。
