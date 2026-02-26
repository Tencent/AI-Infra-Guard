#!/bin/bash

# AI-Infra-Guard 启动脚本
# 创建必要的目录和文件，设置权限，启动服务

set -e

# 权限修改失败时提示并继续（例如挂载卷上无法改权限）
warn_or_continue() { echo "Warning: $1" >&2; }

echo 正在初始化 AI-Infra-Guard 服务...
# 创建必要的目录
mkdir -p /ai-infra-guard/db /ai-infra-guard/uploads /ai-infra-guard/logs

# 设置文件权限
echo 设置文件权限...
chmod 755 /ai-infra-guard/db || warn_or_continue "Skip permission change on mounted volume"
chmod 755 /ai-infra-guard/uploads || warn_or_continue "Skip permission change on mounted volume"
chmod 755 /ai-infra-guard/logs || warn_or_continue "Skip permission change on mounted volume"

# 创建日志文件
echo 初始化日志文件...
touch /ai-infra-guard/logs/trpc.log
chmod 644 /ai-infra-guard/logs/trpc.log

echo 启动AI-Infra-Guard Web 服务...
exec ./ai-infra-guard webserver --server 0.0.0.0:8088