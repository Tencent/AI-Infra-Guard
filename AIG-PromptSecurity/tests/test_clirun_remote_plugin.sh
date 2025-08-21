echo "running local test server"
# cd tests/remote_server; python -m http.server 8000 &

echo "running test"
.venv/bin/python cli_run.py \
  --plugins http://127.0.0.1:8000/remote_my_folder_plugin.zip \
  --model google/gemini-2.0-flash-001 \
  --base_url {url} \
  --api_key {token} \ 
  --scenarios "RemoteTxtPromptVulnerability" \
  --techniques Raw \
  --choice serial \
  --metric RandomMetric \
  --report remote_my_folder_plugin.md