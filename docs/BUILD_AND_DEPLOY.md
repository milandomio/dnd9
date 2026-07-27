# Build And Deploy

本文件保存构建、预览验证、部署和远端信息。触发条件：运行数据管道、构建前端、启动 web、验证 HTTP 200、部署、处理 DB 推送时阅读。

## 完整构建

```bash
git commit -am "WIP: <描述>"                    # 1. checkpoint
cd api && python main.py > pipeline.log 2>&1     # 2. 数据管道（含 locale 字典导出）
cd web && npm run build > build.log 2>&1         # 3. 前端构建（含 SSG 多语言 HTML 后处理）
# 4. 启动web + 强制验证
cd web && kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5; nohup npx vite preview --port 8080 --host 0.0.0.0 &>/tmp/vite.log & && sleep 2 && curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/
```

`python main.py` 在 search_index 步骤后自动运行 `build_locale_files`，生成 `data/json/locale/{lang}.json`（10种语言）。`npm run build` 中的 `ssg.mjs` 使用这些 locale 字典为每种语言生成 HTML 副本（dist/{lang}/...）。完整构建产物约 1.28 GB。

禁止直接执行实时输出的长流程命令。`python main.py`、`npm run build`、`./deploy.sh`、Playwright 全站测试等在 WSL 中必须使用 `nohup <command> > 日志文件 2>&1 &` 后台启动；随后用短命令检查进程和单独读取日志，避免等待前台流程结束而阻塞 TUI。

构建完成后必须验证 web 服务可用（HTTP 200），不可跳过。若返回非 200，必须排查错误并修复至返回 200 为止。

常见原因：端口被占用（检查 `lsof -t -i:8080`）、构建产物损坏（`rm -rf dist && npm run build`）、数据文件缺失（运行 `python main.py`）。

## 仅前端改动

只改 `web/` 代码时，不需要跑数据管道，直接构建 + 启动预览：

```bash
cd web && npm run build > build.log 2>&1      # 1. 前端构建（含 TS 类型检查 + SSG）
# 2. 启动web + 强制验证（同完整构建规则）
cd web && kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5; nohup npx vite preview --port 8080 --host 0.0.0.0 &>/tmp/vite.log & && sleep 2 && curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/
```

## 一键部署

```bash
./deploy.sh > deploy.log 2>&1   # 管道 → 构建 → 启动服务 → git 提交
```

## 数据流

```
游戏 JSON → api/main.py → api/output/json/ + api/src/img/
→ 自动交付 → data/{json/, img/}
→ npm run build → web/public/data/ → dist/data/
→ GitHub Actions → gh-pages 分支 → Cloudflare Pages → 浏览器 fetch → 注水渲染
```

无游戏文件部署：DB 含全部数据，`python main.py` 可直接生成所有 JSON。

## 远端

- **GitHub**: `https://github.com/milandomio/dnd9.git`
- **Token**: `.github_token`（`.gitignore` 中）
- **部署**: Actions → `gh-pages` 分支 → Cloudflare Pages（自定义域名在 CF Dashboard 设置，不需要 CNAME 文件）

## 推送到 dnd9（含 DB）

DB 在 `.gitignore` 中，默认不跟踪。推送时临时加入，推送后立即取消本地跟踪，确保远程有 DB（供 Actions 部署）而本地不跟踪。

```bash
git add -A && git commit -m "feat: <描述>"
git update-index --no-skip-worktree api/data/darkfindv5.db 2>/dev/null
if git diff --quiet HEAD -- api/data/darkfindv5.db; then
  git update-index --skip-worktree api/data/darkfindv5.db
  GIT_SSL_NO_VERIFY=1 git push origin main
  exit 0
fi
cp api/data/darkfindv5.db /tmp/darkfindv5.db
git add -f api/data/darkfindv5.db && git commit --no-verify -m "chore: update DB"
GIT_SSL_NO_VERIFY=1 git push origin main
git reset HEAD~1 && rm /tmp/darkfindv5.db
git update-index --skip-worktree api/data/darkfindv5.db
```
