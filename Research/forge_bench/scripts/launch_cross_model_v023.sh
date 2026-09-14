#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="$(cd "$ROOT/.." && pwd)"
CONFIG_DIR="$ROOT/configs/cross_model_v0.2.3"
CASES="$ROOT/scenarios/v0.2/generated_cases.jsonl"
STAMP="${1:-20260907}"
LOG_DIR="$ROOT/artifacts/launcher_logs/forge_v023_cross_model_${STAMP}"
PID_DIR="$LOG_DIR/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

models=(
  glm-5.3-flash-***
  minimax-m2.5-***
  deepseek-v4-flash-***
  gpt-5.6-luna
)

for model in "${models[@]}"; do
  slug="$(printf '%s' "$model" | tr '.-' '__')"
  config="$CONFIG_DIR/$model.json"
  run_id="forge_v023_cross_${slug}_${STAMP}"
  log="$LOG_DIR/$slug.log"
  nohup bash -c '
    cd "$1"
    exec python3 forge_bench/scripts/run_v2_benchmark.py \
      --config "$2" \
      --cases "$3" \
      --run-id "$4"
  ' _ "$WORKSPACE" "$config" "$CASES" "$run_id" >"$log" 2>&1 </dev/null &
  echo "$!" > "$PID_DIR/$slug.pid"
  printf '%s pid=%s run=%s log=%s\n' "$model" "$!" "$run_id" "$log"
done

cat > "$LOG_DIR/README.txt" <<EOF
Launched: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Models: ${models[*]}
Design per model: 6 families x 8 conditions x 5 samples = 240 trajectories
Concurrency: 5 trajectory workers per model, 20 maximum across four processes
Scenario file: $CASES
EOF
