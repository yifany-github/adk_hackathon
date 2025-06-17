#!/bin/bash

# NHL Commentary Web Client 启动脚本

echo "🏒 NHL Commentary Web Client"
echo "=============================="

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 进入正确目录
cd "$(dirname "$0")"

echo "📍 当前目录: $(pwd)"
echo "🚀 启动Web服务器..."

# 启动服务器
python3 start_server.py

echo "👋 服务器已关闭" 