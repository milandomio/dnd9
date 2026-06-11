#!/bin/bash
set -e

echo "=== DarkFindV5 部署开始 ==="

# 1. 运行后端管道
echo "[1/4] 运行后端数据管道..."
cd api && python main.py
cd ..

# 2. 构建前端
echo "[2/4] 构建前端..."
cd web && npm run build
cd ..

# 3. 启动web服务
echo "[3/4] 启动web服务..."
cd web
kill $(lsof -t -i:8080) 2>/dev/null || true
sleep 0.5
(npx vite preview --port 8080 --host 0.0.0.0 &>/dev/null &) && echo "web started"
cd ..

# 4. 自动git提交
echo "[4/4] 自动提交代码变更..."
git add -A
git commit -m "chore: deploy $(date +%Y-%m-%d)"

echo "=== 部署完成 ==="
echo "访问 http://localhost:8080"
