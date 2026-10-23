#!/usr/bin/env bash
# DarkFindV5 一键构建与本地预览。
#
# 面向普通用户：只需要 Python 3.10+ 和 Node 20+，不需要游戏解包文件。
# 仓库内的 api/data/darkfindv5.db 是预生成的完整数据库，管道会以 DB_ONLY
# 模式直接使用它导出 JSON，不重新解析游戏资产。
#
# 用法：
#   ./deploy.sh              构建并启动预览（默认 8081）
#   ./deploy.sh --port 9000  指定端口
#   ./deploy.sh --build-only 只构建，不启动服务
#
# 本脚本只做本地构建与预览，不执行任何 git 操作。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PORT=8081
BUILD_ONLY=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            PORT="${2:?--port 需要一个端口号}"
            shift 2
            ;;
        --build-only)
            BUILD_ONLY=1
            shift
            ;;
        -h|--help)
            sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "未知参数: $1（用 --help 查看用法）" >&2
            exit 1
            ;;
    esac
done

log() { printf '\n\033[1;36m%s\033[0m\n' "$1"; }
fail() { printf '\033[1;31m%s\033[0m\n' "$1" >&2; exit 1; }

# ── 环境检查 ────────────────────────────────────────────────────────────
log "[1/5] 检查运行环境"

command -v python3 >/dev/null 2>&1 || fail "未找到 python3，请先安装 Python 3.10+"
command -v node >/dev/null 2>&1 || fail "未找到 node，请先安装 Node.js 20+"
command -v npm >/dev/null 2>&1 || fail "未找到 npm"

PY_OK=$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 10) else 0)')
[[ "$PY_OK" = "1" ]] || fail "Python 版本过低，需要 3.10+（当前 $(python3 -V 2>&1)）"

NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]')
[[ "$NODE_MAJOR" -ge 20 ]] || fail "Node 版本过低，需要 20+（当前 $(node -v)）"

# DB 是普通用户唯一的数据来源，缺失时无法导出 JSON
[[ -f api/data/darkfindv5.db ]] || fail "缺少 api/data/darkfindv5.db。该文件随仓库提供，请确认 checkout 完整。"

echo "  python $(python3 -V 2>&1 | cut -d' ' -f2) / node $(node -v) / npm $(npm -v)"

# ── 后端数据管道 ────────────────────────────────────────────────────────
# 没有游戏解包目录时 db_freshness 返回 DB_ONLY，直接用预置 DB 导出
# data/json/**，而不是重建数据库。
log "[2/5] 导出数据"
(
    cd api
    export SQLITE_TMPDIR="${SQLITE_TMPDIR:-$ROOT_DIR/.tmp}"
    mkdir -p "$SQLITE_TMPDIR"
    python3 main.py
)

# ── 前端依赖 ────────────────────────────────────────────────────────────
log "[3/5] 安装前端依赖"
if [[ ! -d web/node_modules ]]; then
    ( cd web && npm ci )
else
    echo "  web/node_modules 已存在，跳过（需要重装请先删除该目录）"
fi

# ── 静态站点构建 ────────────────────────────────────────────────────────
log "[4/5] 构建静态站点"
( cd web && npm run build )

[[ -f web/dist/index.html ]] || fail "构建产物缺失：web/dist/index.html"

if [[ "$BUILD_ONLY" = "1" ]]; then
    log "构建完成"
    echo "  产物目录：web/dist"
    echo "  可直接上传到任意静态托管（Cloudflare Pages / GitHub Pages / Nginx）"
    exit 0
fi

# ── 本地预览 ────────────────────────────────────────────────────────────
log "[5/5] 启动本地预览"
if command -v lsof >/dev/null 2>&1; then
    EXISTING_PID=$(lsof -t -i:"$PORT" 2>/dev/null | head -1 || true)
    if [[ -n "${EXISTING_PID:-}" ]]; then
        echo "  端口 $PORT 被 PID $EXISTING_PID 占用，先停止它"
        kill "$EXISTING_PID" 2>/dev/null || true
        sleep 1
    fi
fi

( cd web && nohup npx vite preview --port "$PORT" --strictPort --host 0.0.0.0 >/tmp/darkfindv5-preview.log 2>&1 & )
sleep 3

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/" || echo "000")
if [[ "$HTTP_CODE" != "200" ]]; then
    echo "预览启动日志：" >&2
    tail -20 /tmp/darkfindv5-preview.log >&2 || true
    fail "预览服务返回 HTTP $HTTP_CODE"
fi

echo "  HTTP $HTTP_CODE"
log "完成"
echo "  本地访问：http://localhost:$PORT/"
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[[ -n "${LOCAL_IP:-}" ]] && echo "  局域网访问：http://$LOCAL_IP:$PORT/"
echo "  停止服务：kill \$(lsof -t -i:$PORT)"
