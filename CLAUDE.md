# DarkFindV5 Agent Instructions

> **重要**：每句废话 = 用户一次输入的数倍成本。只输出必要内容：判断需求 → 执行 → 等反馈。禁止情绪安抚、铺垫、总结性废话。

**运行环境：WSL 下的 Ubuntu，不要直接执行 win 环境的命令行工具。**

**默认工作分支**：`dev`。`main` 分支已回滚至 `f9177a5`（多语言 P8-P12 前），仅保留 translation_EN 特性。新增功能在 dev 分支开发。

游戏原始 JSON → Python 清洗 → React SSG (Vite + Ant Design) + PWA (vite-plugin-pwa / Workbox) → 静态部署。

## 子文档查阅规则

遇到对应任务时必须先查对应文档：

| 场景 | 先查文档 |
|------|----------|
| 改代码、提交、预检、pre-commit/TS/Prettier 问题 | `docs/DEVELOPMENT_WORKFLOW.md` |
| 数据管道、前端构建、启动 web、HTTP 200 验证、部署、DB 推送 | `docs/BUILD_AND_DEPLOY.md` |
| 项目结构、页面布局、组件职责、Hydration 排障、数据管道细节、子池、PWA 缓存、文档索引 | `docs/AGENT_REFERENCE.md` |
| 数据管道、数据库、地图模块详细规范 | `docs/REFERENCE.md` |
| 多语言 (i18n) 架构、locale 字典、语言路由、P8-P12 进度 | `docs/plans/MULTILANG_PLAN.md` |
| PWA 架构规划 | `docs/PWA_ROADMAP.md` |
| 前端水合错误 Playwright 排查 | `docs/DEBUG_HYDRATION_WITH_PLAYWRIGHT.md` |
| Hydration #310 历史修复 | `docs/DEBUG_HYDRATION.md` |

参考项目：「v4」「findItemV4」均指 `/home/mio/fmod/findItemV4/`；详细说明见 `docs/AGENT_REFERENCE.md`。

## 存档文件夹规则

`api/src/_archived/` 中的代码已废弃，**严禁修改**。任何改动都应针对活跃代码。搜索时跳过此目录。

## 强制停止规则

1. **重复循环检测**：如果你发现自己在重复相同的代码修改或相同的思考，立刻停止输出！
2. **失败熔断**：连续 2 次修改代码未能通过测试，必须停下来向用户报告，禁止继续盲目重试。
3. **无话可说时**：只输出 `DONE`，绝对不要用废话填充。没有明确指令、或收到空白/无意义输入时同样直接 `DONE` 结束。
4. **禁止擅自推送**：除非用户明确要求"推送远程""提交并推送""push"，否则严禁执行任何 git push 操作。仅做本地提交留作 checkpoint。

## 文档强制规则

**每次改动（包括回退和修复）必须在其完成后的最后一步将摘要追加到 `docs/SESSION_CHANGES.md`。** 这是不可跳过的步骤，优先级与构建验证相同。

要求：
- 按日期分区（`# YYYY-MM-DD 会话修改记录`），当天已有则追加
- 每条记录至少包含：**改动原因、变更文件、关键逻辑/映射关系**
- 回退操作必须注明被回退的内容和原因
- 必须在 commit 之前完成文档追加

## 术语约定

- "我看到" — 部署后 http://localhost:8080/ 上的内容
- "前端" — `web/`，"后端" — `api/`，"db" — `api/data/darkfindv5.db`
- "坐标" — spawners 表中 x/y/z 三个 REAL 字段
- "启动web" — `cd web && kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5; (npx vite preview --port 8080 --host 0.0.0.0 &>/dev/null &) && echo "web started"`
- "详情页" / "列表页" — 如无特别说明，默认指 lootdrops/monsters/props/items 这四个实体类型所属的详情页和列表页
- **最后总结必须用中文** — 完成任务后的总结、变更说明一律用中文输出

## MCP Tools

### fmodel-query
查询游戏解包数据（`/home/mio/fmod/Output/Exports/DungeonCrawler/...`）。
工具：`list_directory`、`search_files`、`read_file`、`get_file_info`、`search_json_keys`

**查询游戏数据必须使用此 MCP 工具，禁止用 `Bash(find/grep/cat)` 直接操作游戏解包目录。**

### sqlite-debug
直接读写 `api/data/darkfindv5.db`。
工具：`query`、`execute`、`list_tables`、`describe_table`、`export_table`

**DB 查询必须使用此 MCP 工具，禁止用 `Bash(python3 -c "import sqlite3…")` 方式。**

## 项目上下文工具

当你需要理解整个项目结构、跨文件重构、或分析代码依赖关系时：

1. 先运行 `npx repomix --output .opencode/repo-context.txt`
2. 然后读取 `.opencode/repo-context.txt`

不需要逐文件 grep，一次打包后从上下文文件里找答案。

不要每次对话都重新 run，除非项目代码有较大改动。

## 开发/构建强制入口

- 改代码前必须按 `docs/DEVELOPMENT_WORKFLOW.md` 创建 checkpoint；如存在用户未提交改动，只处理本任务相关文件，禁止回退他人改动。
- 提交前必须按 `docs/DEVELOPMENT_WORKFLOW.md` 手动跑 format / format:check / tsc 预检。
- 构建、启动 web、部署、DB 推送必须按 `docs/BUILD_AND_DEPLOY.md` 执行；构建完成后必须验证 HTTP 200。
- 禁止直接执行实时输出的长流程命令；`python main.py`、`npm run build`、部署、全站测试等必须重定向到日志后单独读取，避免阻塞 TUI。
- 不要直接改 `data/` 下的自动生成文件；修改 `api/src/collector.py` 等生成逻辑。
- `python main.py` 必须在 `npm run build` 之前运行。