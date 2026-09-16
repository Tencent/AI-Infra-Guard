#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${1:-$ROOT/configs/quickstart.json}"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ -z "${LLM_API_KEY:-}" ]]; then
  echo "Error: LLM_API_KEY is not set." >&2
  echo "Copy .env.example to .env and set the key, or export LLM_API_KEY." >&2
  exit 2
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "$ROOT/scripts/run_benchmark.py" --config "$CONFIG"
