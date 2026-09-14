#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="$(cd "$ROOT/.." && pwd)"
CONFIG_DIR="$ROOT/configs/v0.2.2_full_factorial_shards"
LOG_DIR="$ROOT/artifacts/launcher_logs/forge_v022_full_factorial_20260904"
PID_DIR="$LOG_DIR/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

families=(
  mailbox_triage
  artifact_recovery
  atlas_release
  calendar_coordination
  evaluation_optimization
  dataset_migration
)

for family in "${families[@]}"; do
  config="$CONFIG_DIR/$family.json"
  run_id="forge_v022_full_${family}_20260904"
  log="$LOG_DIR/$family.log"
  nohup bash -c '
    cd "$1"
    exec python3 forge_bench/scripts/run_v2_benchmark.py \
      --config "$2" \
      --run-id "$3"
  ' _ "$WORKSPACE" "$config" "$run_id" >"$log" 2>&1 </dev/null &
  echo "$!" > "$PID_DIR/$family.pid"
  printf '%s pid=%s run=%s log=%s\n' \
    "$family" "$!" "$run_id" "$log"
done

cat > "$LOG_DIR/README.txt" <<EOF
Launched: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Model: hy4-preview-***
Design: 6 families x 8 conditions x 5 samples = 240 trajectories
Each family has an independent immutable run directory.
Use monitor_full_factorial.py to inspect progress.
EOF
