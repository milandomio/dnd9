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

# 3. 启动web服务 + 验证
echo "[3/4] 启动web服务..."
cd web
kill $(lsof -t -i:8080) 2>/dev/null || true
sleep 0.5
(npx vite preview --port 8080 --host 0.0.0.0 &>/dev/null &) || { echo "FAILED to start web"; exit 1; }
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/)
if [ "$HTTP_CODE" = "200" ]; then
  echo "web started (HTTP $HTTP_CODE)"
else
  echo "FAILED: web returned HTTP $HTTP_CODE"
  exit 1
fi
cd ..

# 4. 自动git提交
echo "[4/4] 自动提交代码变更..."
git add -A
git commit -m "chore: deploy $(date +%Y-%m-%d)"

echo "=== 部署完成 ==="
echo "访问 http://localhost:8080"
