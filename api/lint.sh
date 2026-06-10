#!/bin/bash
# Python 代码质量检查脚本

set -e

API_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$API_DIR"

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "🔍 Running ruff check..."
ruff check src/

echo ""
echo "🎨 Checking black formatting..."
black --check src/

echo ""
echo "✅ All checks passed!"
