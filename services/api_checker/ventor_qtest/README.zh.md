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
python main.py qtest afl-run
python main.py qtest afl-run --config path/to/afl.yaml
python main.py qtest openrouter-providers --model moonshotai/kimi-k2.5
python -m ventor_qtest --help
```

Ventor-QTest 包含两个互补方法：

- `run`：长序列 EFL，通过可信参考逐位置重评分，报告运行级偏离及其上尾；
- `afl-run`（别名 `repeated-run`）：重复请求 AFL，从目标接口返回的文本计数重建有限类别分布，报告经过有限样本零假设偏差校正的平均 coarsened-KL。

AFL 的目标接口不需要提供 `logprobs`，仅可信参考接口需要。默认
`config/afl.yaml` 使用论文中的 12 个约束上下文、每上下文 50 次请求、
参考侧类别合并和 20,000 次参数化零假设抽样。输出保留负的有限样本 AFL，
并给出可信区间、单侧检验和 Holm 校正。采集支持 checkpoint 续跑，但不包含
三天采集、盲化、冻结或解盲等论文实验管理流程。

运行测试需要相应供应商的 API Key。默认配置支持通过
`MOONSHOT_API_KEY`、`SILICONFLOW_API_KEY`、`OPENROUTER_API_KEY` 和
`DEEPSEEK_API_KEY`
环境变量传入。
