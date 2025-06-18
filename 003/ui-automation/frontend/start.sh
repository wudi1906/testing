#!/bin/bash

echo "正在启动UI自动化测试系统前端..."
echo

# 检查Node.js版本
if ! command -v node &> /dev/null; then
    echo "错误: 未找到Node.js，请先安装Node.js 18+"
    exit 1
fi

# 检查npm版本
if ! command -v npm &> /dev/null; then
    echo "错误: 未找到npm，请检查Node.js安装"
    exit 1
fi

# 显示版本信息
echo "Node.js版本: $(node --version)"
echo "npm版本: $(npm --version)"
echo

# 检查是否存在node_modules
if [ ! -d "node_modules" ]; then
    echo "正在安装依赖..."
    npm install --legacy-peer-deps
    if [ $? -ne 0 ]; then
        echo "依赖安装失败，请检查网络连接"
        exit 1
    fi
fi

# 启动开发服务器
echo "启动开发服务器..."
npm run dev
