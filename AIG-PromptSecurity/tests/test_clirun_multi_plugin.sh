.venv/bin/python cli_run.py \
  --plugins plugin/example_custom_metric_plugin.py plugin/example_custom_vulnerability_plugin.py plugin/example_custom_attack_plugin.py\
  --model google/gemini-2.0-flash-001 \
  --base_url {url} \
  --api_key {token} \ 
  --scenarios SimpleCustomVulnerability \
  --techniques CustomPrefixAttack \
  --metric CustomLengthMetric \
  --report result_multi_plugin.md