#!/bin/bash

# AI-Infra-Guard 启动脚本
# 创建必要的目录和文件，设置权限，启动服务

set -e

# 权限修改失败时提示并继续（例如挂载卷上无法改权限）
warn_or_continue() { echo "Warning: $1" >&2; }

echo 正在初始化 AI-Infra-Guard 服务...
# 创建必要的目录
mkdir -p /app/db /app/uploads /app/logs

# ── Cross-platform data init ──────────────────────────────────────────────────
# On macOS/Windows Docker Desktop, volume mounts (./data:/app/data) overwrite
# the files that were baked into the image during build, leaving /app/data/mcp
# empty and causing "no plugins loaded" errors (GitHub issue #119).
#
# Fix: the Dockerfile keeps a bundled copy at /app/data_bundled.
# At startup we do a one-way rsync/cp that only fills in *missing* files,
# so user-added plugins are never deleted.
if [ -d "/app/data_bundled" ]; then
  echo "Checking bundled data files..."
  # Use cp -n (no-clobber) to copy bundled files without overwriting existing ones.
  # Works on both Alpine (busybox cp) and standard GNU/BSD cp.
  find /app/data_bundled -type f | while read src; do
    rel="${src#/app/data_bundled/}"
    dst="/app/data/${rel}"
    if [ ! -f "$dst" ]; then
      mkdir -p "$(dirname "$dst")"
      cp "$src" "$dst"
    fi
  done
  echo "Bundled data sync complete."
fi
# ─────────────────────────────────────────────────────────────────────────────

# 设置文件权限
echo 设置文件权限...
chmod 755 /app/db || warn_or_continue "Skip permission change on mounted volume"
chmod 755 /app/uploads || warn_or_continue "Skip permission change on mounted volume"
chmod 755 /app/logs || warn_or_continue "Skip permission change on mounted volume"

# 创建日志文件
echo 初始化日志文件...
touch /app/logs/trpc.log
chmod 644 /app/logs/trpc.log

echo 启动AI-Infra-Guard Web 服务...
exec ./ai-infra-guard webserver --server 0.0.0.0:8088