#!/bin/bash

# AI-Infra-Guard 启动脚本
# 创建必要的目录和文件，设置权限，启动服务

set -e

echo 正在初始化 AI-Infra-Guard 服务...
# 创建必要的目录
mkdir -p /ai-infra-guard/db /ai-infra-guard/uploads /ai-infra-guard/logs

# 创建数据库文件（如果不存在）
if [ ! -f /ai-infra-guard/db/tasks.db ]; then
    echo "创建数据库文件..."
    touch /ai-infra-guard/db/tasks.db
fi

# 设置文件权限
echo 设置文件权限...
chmod 666 /ai-infra-guard/db/tasks.db 2>/dev/null || true
chmod 777 /ai-infra-guard/db 2>/dev/null || true
chmod 777 /ai-infra-guard/uploads 2>/dev/null || true

# 创建日志文件
echo 初始化日志文件...
touch /ai-infra-guard/logs/trpc.log
chmod 666 /ai-infra-guard/logs/trpc.log 2>/dev/null || true
chmod 777 /ai-infra-guard/logs 2>/dev/null || true

echo 启动AI-Infra-Guard Web 服务...
exec ./ai-infra-guard webserver 