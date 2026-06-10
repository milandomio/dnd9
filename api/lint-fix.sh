#!/bin/bash
# Python 代码自动修复脚本

set -e

API_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$API_DIR"

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "🔧 Fixing ruff issues..."
ruff check --fix src/

echo ""
echo "🎨 Formatting with black..."
black src/

echo ""
echo "✅ All fixes applied!"
