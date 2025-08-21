.venv/bin/python cli_run.py \
  --plugins plugin/example_custom_metric_plugin.py \
  --model google/gemini-2.0-flash-001 \
  --base_url {url} \
  --api_key {token} \ 
  --scenarios "MultiDataset:csv_file=output_prompts.csv,num_prompts=2,random_seed=123" \
  --techniques Raw \
  --choice serial \
  --metric CustomLengthMetric \
  --report result_metric_plugin.md