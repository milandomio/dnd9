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

## Lootdrop 变体构建范围

SSG 不为普通 lootdrop 变体生成全量实体文件，避免每个品质变体重复占用静态文件预算：

- 普通变体仅生成默认品质变体的 SSG HTML；默认后缀优先为 `_5001`，否则取最高可用品质。
- 普通非默认变体不生成 `dist/{lang}/lootdrops/{name}_{suffix}/index.html`，由浏览器 CSR 加载基底 JSON 后渲染。
- `_8001` 神器变体仍单独生成 SSG HTML。
- 无爆率后缀只生成静态提示壳；这类壳不包含完整实体 SSR 数据。
- 变体 URL 仍可由构建脚本注册，注册 URL 不等于生成实体 HTML 文件；`generateStatic: false` 的路由必须被跳过默认语言、多语言副本、legacy redirect 和 sitemap 输出。

## IndexNow

IndexNow 已接入主站 GitHub Actions：静态密钥文件随构建发布到 `dist/{key}.txt`，发布到 `gh-pages` 后自动读取该文件和各语言 sitemap，向 IndexNow API 批量提交 URL。

首次配置：

1. 将 IndexNow 提供的 `{key}.txt` 文件放入 `web/public/`，文件名和内容都必须是同一个密钥。
2. 推送一次 `main`，确认 `https://dnd9.icetar.com/{key}.txt` 返回该密钥文本。
3. 查看 Actions 日志，确认 URL 批次提交返回 `200` 或 `202`。

不需要配置 GitHub Secret。更换密钥时同步替换 `web/public/` 中的验证文件。

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
- **部署**: Actions → `gh-pages` 分支 → Cloudflare Pages（使用 CF 提供的三级域名根目录；不使用 `/dnd9/` 二级路径，也不需要 CNAME 文件）
- **Sitemap**: SSG 默认将全部语言 URL 合并到直接包含页面 URL 的 `sitemap.xml`；超过 Cloudflare Pages 的 25 MiB 或 Sitemap 50,000 URL 限制时，按低优先级语言逐个保留为 `sitemap-{lang}.xml`，根文件仍保持 `urlset`。所有语言子 sitemap 同时由 `robots.txt` 声明。

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
