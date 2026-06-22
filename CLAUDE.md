# DarkFindV5 Agent Instructions

游戏原始 JSON → Python 清洗 → React SSG (Vite + Ant Design) → 静态部署。

> **参考项目**：「v4」「findItemV4」均指 `/home/mio/fmod/findItemV4/`
> **技术参考**：数据管道、数据库、地图模块详细规范见 `docs/REFERENCE.md`

## 强制停止规则

1. **重复循环检测**：如果你发现自己在重复相同的代码修改或相同的思考，立刻停止输出！
2. **失败熔断**：连续 2 次修改代码未能通过测试，必须停下来向用户报告，禁止继续盲目重试。
3. **无话可说时**：只输出 `DONE`，绝对不要用废话填充。没有明确指令、或收到空白/无意义输入时同样直接 `DONE` 结束。

## 术语约定

- "我看到" — 部署后 http://localhost:8080/ 上的内容
- "前端" — `web/`，"后端" — `api/`，"db" — `api/data/darkfindv5.db`
- "坐标" — spawners 表中 x/y/z 三个 REAL 字段
- "启动web" — `cd web && kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5; (npx vite preview --port 8080 --host 0.0.0.0 &>/dev/null &) && echo "web started"`
- **最后总结必须用中文** — 完成任务后的总结、变更说明一律用中文输出

## 项目结构

```
DarkFindV5/
├── api/                  # 后端
│   ├── main.py               # 入口（运行管道 + 自动交付到 data/）
│   ├── src/
│   │   ├── collector.py          # 管道协调器（DB 导入 + 模块编排）
│   │   ├── config.py             # 路径配置 + 常量
│   │   ├── db_manager.py         # SQLite 建表/导入/查询
│   │   ├── translator.py         # NameResolver 类、regex 常量、翻译工具
│   │   ├── entity_export.py      # items/monsters/props JSON 导出
│   │   ├── drop_rate.py          # DropRateEngine 类（爆率预加载 + 计算）
│   │   ├── module_builder.py     # 地图模块构建 + 坐标导出
│   │   ├── lootdrop_builder.py   # lootdrop 索引 + 详情文件生成
│   │   ├── enrichment.py         # group_drop_info 注入 + 零爆率清理
│   │   ├── index_export.py       # quest 数据 + search_index 导出
│   │   ├── search_engine.py      # 地图文件遍历 + spawner 提取
│   │   ├── layout_utils.py       # 地图旋转值计算
│   │   ├── dungeon_mode.py       # DungeonGrade 分组代码解析
│   │   ├── pipeline_timer.py     # 管道步骤计时工具
│   │   ├── quest_collector.py    # 任务提取入口
│   │   ├── quest_extractor/      # 任务提取模块（12 个 Python 模块，含 __init__.py）
│   │   └── img/                  # 地图图片 .webp（不可再生，严**禁**清理）
│   ├── lint.sh / lint-fix.sh    # ruff lint 脚本
│   ├── data/                # DB（darkfindv5.db）
│   └── output/json/         # 管道输出
├── data/                 # 交付目录（main.py 自动维护，可重生，可清理）
│   ├── json/              # items/monsters/props/lootdrops/explore/quest_*/dungeon_modules 等
│   └── img/               # → api/src/img/
├── web/                 # React 前端（SSG）
│   ├── src/
│   │   ├── main.tsx             # 客户端入口
│   │   ├── ssr.tsx              # SSR 入口
│   │   ├── App.tsx              # 客户端入口（Provider 包装）
│   │   ├── AppInner.tsx         # 路由定义（Routes/Route 声明）
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # MapDebug, MapPanel, Disclaimer, DebugCoordTable, NavBar, QuestSearchBar
│   │   ├── hooks/               # useDebug, useTheme, useDungeonModules, useDataVersion, useSearchIndex
│   │   ├── context/             # SSRDataContext
│   │   └── types/               # data.ts, quest.ts
│   ├── scripts/ssg.mjs        # SSG 构建脚本（--quick 模式下详情页为 CSR）
│   └── public/data/           # 构建时从 ../data/ 复制
├── deploy.sh                 # 一键部署（管道→构建→启动服务→提交）
└── docs/REFERENCE.md         # 技术参考（数据管道/DB/地图模块详细规范）
```

## V4 参考

符号链接 `v4_reference/` 提供只读参考（不要修改）：
- `group_config.json` — 分组翻译配置
- `src/config.py` — MODULE_OFFSET_MAP、HARDCODED_TRANSLATIONS

## MCP Tools

### fmodel-query
查询游戏解包数据（`/home/mio/fmod/Output/Exports/DungeonCrawler/...`）。
工具：`list_directory`、`search_files`、`read_file`、`get_file_info`、`search_json_keys`

### sqlite-debug
直接读写 `api/data/darkfindv5.db`。
工具：`query`、`execute`、`list_tables`、`describe_table`、`export_table`

## 项目上下文工具

当你需要理解整个项目结构、跨文件重构、或分析代码依赖关系时：

1. 先运行 `npx repomix --output .opencode/repo-context.txt`
2. 然后读取 `.opencode/repo-context.txt`

不需要逐文件 grep，一次打包后从上下文文件里找答案。

不要每次对话都重新 run，除非项目代码有较大改动。

## 开发流程

### 前置规则：改动前先提交

每次改动前必须先 git commit 作为 checkpoint：

```bash
git commit -am "WIP: <改动摘要>"
# 有新文件时先 git add
git add <新文件> && git commit -am "WIP: <改动摘要>"
```

### 关键警告

- **不要直接改 `data/` 下的自动生成文件** — 修改 `api/src/collector.py` 中的生成逻辑
- **`python main.py` 必须在 `npm run build` 之前运行**
- **TS 类型检查**：`npx tsc --noEmit`（构建中自动执行）

### 完整构建

```bash
git commit -am "WIP: <描述>"   # 1. checkpoint
cd api && python main.py        # 2. 数据管道（自动交付到 data/）
cd web && npm run build          # 3. 前端构建
# 4. 启动web + 验证
cd web && kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5; nohup npx vite preview --port 8080 --host 0.0.0.0 &>/tmp/vite.log & && sleep 2 && curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/
```

### 仅前端改动

只改 `web/` 代码时，不需要跑数据管道，直接构建 + 启动预览：

```bash
cd web && npm run build          # 1. 前端构建（含 TS 类型检查 + SSG）
# 2. 启动web + 验证
cd web && kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5; nohup npx vite preview --port 8080 --host 0.0.0.0 &>/tmp/vite.log & && sleep 2 && curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/
```

### 一键部署

```bash
./deploy.sh   # 管道 → 构建 → 启动服务 → git 提交
```

## 数据流

```
游戏 JSON → api/main.py → api/output/json/ + api/src/img/
→ 自动交付 → data/{json/, img/}
→ npm run build → web/public/data/ → dist/data/
→ GitHub Actions → GitHub Pages → 浏览器 fetch → 注水渲染
```

**无游戏文件部署：** DB 含全部数据，`python main.py` 可直接生成所有 JSON。

### 远端

- **GitHub**: `https://github.com/milandomio/dnd9.git`
- **Token**: `.github_token`（`.gitignore` 中）
- **部署**: Actions → `gh-pages` 分支 → GitHub Pages

### 推送到 dnd9（含 DB）

DB 在 `.gitignore` 中，默认不跟踪。推送时临时加入，推送后立即取消本地跟踪，确保远程有 DB（供 Actions 部署）而本地不跟踪。

```bash
# 1. 提交普通变更（工作区干净时跳过此步）
git add -A && git commit -m "feat: <描述>"

# 2. 备份 DB → 强制追踪 → 提交
cp api/data/darkfindv5.db /tmp/darkfindv5.db
git add -f api/data/darkfindv5.db && git commit -m "chore: update DB"

# 3. 推送（含 DB 提交）
GIT_SSL_NO_VERIFY=1 git push origin main

# 4. 撤销本地 DB 提交（远程保留，本地取消跟踪）
git reset HEAD~1 && rm /tmp/darkfindv5.db
```

## 页面布局

| 页面 | 路由 | 列数 |
|------|------|------|
| 主页 | `/` | 4 |
| 列表页 | `/items` `/monsters` `/props` `/lootdrops` `/explore` `/quest_items` `/quest_npc` | 3 |
| 详情页 | `/items/:name` 等 | 4 (CSS Grid, 1x1/2x1/1x2/2x2) |
| 任务物品分组 | `/quest_items/:group` | 3 |
| 任务 NPC 详情 | `/quest_npc/:npc_name` | 4 |
| 地图模块表 | `/dungeon_modules` | 4 (分组列表) |
| 地图模块分组 | `/dungeon_modules/:group` | 4 |
| 地图模块详情 | `/dungeon_modules/:group/:name` | 全宽 |

## 组件架构

| 组件 | 用途 | 消费页面 |
|------|------|---------|
| `MapDebug.tsx` | 坐标变换、像素映射、调试样式 | Detail, LootdropDetail |
| `MapPanel.tsx` | 地图面板（坐标点渲染 + z 高度着色） | Detail, LootdropDetail, DungeonModuleDetail, QuestItemGroup |
| `Disclaimer.tsx` | "数据有误差"警告 | Home, Detail, LootdropDetail |
| `DebugCoordTable.tsx` | 调试坐标表 | Detail, LootdropDetail |
| `NavBar.tsx` | 导航栏 | 全局 |
| `QuestSearchBar.tsx` | 任务搜索栏 | QuestNPC, QuestNPCDetail |
| `useDebug.tsx` | 调试开关/偏移量 | Detail, LootdropDetail |
| `useTheme.tsx` | 主题切换 | 全局 |
| `useDungeonModules.ts` | 地图模块数据 | DungeonModules/Group/Detail |
| `useDataVersion.ts` | 数据版本（缓存 bust） | Disclaimer, NavBar, List, Explore |
| `useSearchIndex.ts` | 搜索索引（全局缓存 search_index.json） | NavBar |

### 详情页同步规则

`DetailPage.tsx` 同时处理 items、monsters、props 三种实体详情页（通过 `/:page/:name` 路由）。`LootdropDetailPage.tsx` 是独立的掉落详情页。

**功能更新需同步的页面：**
- `DetailPage.tsx` — items/monsters/props 共用，更新一处即覆盖三张表
- `LootdropDetailPage.tsx` — 掉落详情页，功能独立但 UI 样式应保持一致

**爆率显示规则（三表同步）：**
- `group_drop_info` 字段已注入 items、monsters、props 三张表的详情 JSON
- 只在坐标对应的 spawn 文件是变体（`variant_count > 1`）时，才在地图模块图片下显示爆率
- 非变体 spawn 不显示爆率
- items 的 `drop_rates` 是指定物品的爆率；monsters/props 的 `drop_rates` 是该实体所有可掉落物品的聚合爆率
- 爆率样式参考 `LootdropDetailPage` 的怪物列表区域

### Fetch URL 必须使用绝对路径

所有 `fetch()` 和 CSS `url()` 中的数据路径必须使用绝对路径（`/data/...`），不能使用相对路径（`./data/...`）。

**原因：** 嵌套路由（如 `/items/Bandage/`）刷新时，相对路径 `./data/json/items/Bandage.json` 会解析为 `/items/Bandage/data/json/items/Bandage.json`，命中 SPA fallback 返回 HTML 而非 JSON，导致页面空白。客户端路由跳转不受影响（`dataVersion` 已缓存，fetch 立即执行）。

**部署环境：** 自定义域名 `dnd9.icetar.com`，部署在根路径，`vite.config.ts` 中 `base: '/'`，绝对路径 `/data/...` 在本地预览和生产环境均正确解析。

### 共享 Hook 状态：useDataVersion 必须同步所有调用者

多个组件各自调用同一个自定义 hook 时，每个组件有独立的 `useState`。如果 hook 内部通过异步操作更新状态，只有触发该操作的组件实例会被更新，其他调用者的 state 保持初始值。

**踩坑记录：** `useDataVersion()` 被 `Disclaimer` 和 `DetailPage` 等多个组件调用。fetch `meta.json` 后 `setDate()` 只更新了 `Disclaimer` 的 state，`DetailPage` 的 `dataVersion` 始终为空，导致详情页 F5 刷新后不加载数据。

**解决方式：** 使用模块级 `listeners` 集合 + `notify()` 模式，fetch 完成后通知所有订阅者更新 state。

## React Hydration 规则（防止 #310 错误）

React #310 = "Rendered more hooks than during the previous render"，hook 数量在渲染间不一致。

### 规则 1：所有 hooks 必须在条件返回之前

```tsx
// ❌ 错误 — useMemo 在条件返回之后，首次渲染不调用
function Page() {
  const [data, setData] = useState(null);
  useEffect(() => { fetch(...).then(setData); }, []);
  if (!data) return <Loading />;
  const sorted = useMemo(() => data.items.sort(...), [data]); // ← 只在 data 有值时调用
}

// ✅ 正确 — 所有 hooks 在条件返回之前
function Page() {
  const [data, setData] = useState(null);
  useEffect(() => { fetch(...).then(setData); }, []);
  const items = data?.items ?? [];
  const sorted = useMemo(() => items.sort(...), [items]);     // ← 始终调用
  if (!data) return <Loading />;
}
```

### 规则 2：SSR 和客户端组件树必须一致

Provider 层数、顺序、类型必须完全匹配。差异会导致 fiber 树 hook 链表错位。

- SSR (`ssr.tsx`) 和客户端 (`App.tsx`) 的 Provider 嵌套必须相同
- 不要在客户端添加 SSR 没有的包装组件（如 `AntdConfigProvider`）
- 如果 SSR 有 `SSRDataContext.Provider`，客户端也必须有（值可以为 `null`）

### 规则 3：SSG Quick 模式下 SSR 数据不完整

Quick 模式只注入 `{ name, translation }`，缺少 `monsters`、`coords` 等字段。

```tsx
// ❌ 不完整对象是 truthy，通过 null 检查但缺少必要字段
const [data, setData] = useState(ssrData?.item || null);

// ✅ 验证必要字段存在
const [data, setData] = useState(
  ssrData?.item?.monsters ? ssrData.item : null
);
```

详细修复记录见 `docs/DEBUG_HYDRATION.md`。

## 数据管道关键规则

- `_is_db_stale()` 必须在 `DatabaseManager()` 构造**之前**调用
- `search_engine.py` 排除地图变体：`_SR`、`_BossTest`、`_Resize`、`_Test`、含 `Arena` 的文件名、`ArenaStart` 目录
- 坐标通过 `db.get_all_coordinates()` 批量获取，避免 N+1
- Spawner 坐标必须递归解析 `AttachParent` 链累加世界坐标（约 16.5% spawner 有父级变换）
- 实体分类通过 `db.get_entity_classification()` 从 DB 直接构建
- Spawner 使用 `executemany` 批量插入
- `_Hard`/`_VeryHard`/`_Unique` 后缀在 lootdrop 解析阶段合入基础怪物名，避免重复掉落条目
- 地图图片优先级：`SubLevelAsset(sl_base) → Module name → MapImage`
- 占位图 `RareModule_1x1` / `UnderConstruction_1x1` 被跳过
