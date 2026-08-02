# Agent Reference Archive

从 `CLAUDE.md` 拆出的长期参考内容。主文档只保留高频执行规则，本文件保存低频但仍有价值的项目背景、页面结构、架构约定和历史索引。

## V4 参考

符号链接 `v4_reference/` 提供只读参考（不要修改）：

- `group_config.json` — 分组翻译配置
- `src/config.py` — MODULE_OFFSET_MAP、HARDCODED_TRANSLATIONS

## 项目结构

```
DarkFindV5/
├── api/                  # 后端
│   ├── main.py               # 入口（运行管道 + 自动交付到 data/）
│   ├── src/
│   │   ├── collector.py          # 管道协调器（DB 导入 + 模块编排）
│   │   ├── config.py             # 路径配置 + 常量
│   │   ├── db_manager.py         # 重新导出（向后兼容，实际实现在 db/ 包）
│   │   ├── db/                   # 数据库包
│   │   │   ├── __init__.py       # DatabaseManager 组合类
│   │   │   ├── schema.py         # 建表/迁移
│   │   │   ├── _helpers.py       # 共享工具函数
│   │   │   ├── importers/        # 数据导入（items/monsters/props/modules/lootdrops/quests/spawners）
│   │   │   └── repositories/     # 数据查询（同上 + coordinates）
│   │   ├── pipeline.py           # Pipeline 抽象（步骤上下文管理器）
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
│   │   └── img/                  # 地图图片 .webp（不可再生，严禁清理）
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
│   ├── scripts/ssg.mjs        # SSG 构建脚本（普通非默认变体 CSR；默认变体与神器保留 SSG）
│   └── public/data/           # 构建时从 ../data/ 复制
├── deploy.sh                 # 一键部署（管道→构建→启动服务→提交）
└── docs/                     # 技术文档、计划、排障记录
```

Lootdrop 变体的静态范围：普通变体只生成默认变体实体 HTML，普通非默认变体不生成 SSG 实体文件并由 CSR 渲染；`_8001` 神器变体独立保留 SSG。完整规则见 [`REFERENCE_FRONTEND_DATA.md`](REFERENCE_FRONTEND_DATA.md) 和 [`BUILD_AND_DEPLOY.md`](BUILD_AND_DEPLOY.md)。

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
| `useDungeonModules.ts` | 地图模块数据（详情页已改用 `_modules` 内联） | DungeonModules/Group |
| `useDataVersion.ts` | 数据版本（缓存 bust） | Disclaimer, NavBar, List, Explore |
| `useSearchIndex.ts` | 搜索索引（全局缓存 search_index.json） | NavBar |

## 详情页同步规则

`DetailPage.tsx` 同时处理 items、monsters、props 三种实体详情页（通过 `/:page/:name` 路由）。`LootdropDetailPage.tsx` 是独立的掉落详情页；`DungeonModuleDetailPage.tsx`（`/dungeon_modules/:group/:name`）也是独立详情页。

功能更新需同步：

- `DetailPage.tsx` — items/monsters/props 共用，更新一处即覆盖三张表
- `LootdropDetailPage.tsx` — 掉落详情页，功能独立但 UI 样式应保持一致
- `DungeonModuleDetailPage.tsx` — 地图模块详情页；模块及坐标实体名称必须使用 `translation_key` + `t()`，分组面包屑复用 `formatGroupLabel()`

爆率显示规则：

- `group_drop_info` 字段已注入 items、monsters、props 三张表的详情 JSON
- 地图模块图片下爆率：仅当该模块坐标会触发生成率运算（`variant_count > 1` / N点选m 等，`adjRate` 会改数值）时显示；否则与分组头「参考爆率」相同，不重复复制
- 非变体、无运算 spawn 不在模块下显示爆率
- items 的 `drop_rates` 是指定物品的爆率；monsters/props 的 `drop_rates` 是该实体所有可掉落物品的聚合爆率
- 爆率样式参考 `LootdropDetailPage` 的怪物列表区域

## Fetch URL 规则

所有 `fetch()` 和 CSS `url()` 中的数据路径必须使用绝对路径（`/data/...`），不能使用相对路径（`./data/...`）。

原因：嵌套路由（如 `/items/Bandage/`）刷新时，相对路径 `./data/json/items/Bandage.json` 会解析为 `/items/Bandage/data/json/items/Bandage.json`，命中 SPA fallback 返回 HTML 而非 JSON，导致页面空白。

部署环境：自定义域名 `dnd9.icetar.com`，部署在根路径，`vite.config.ts` 中 `base: '/'`。

## useDataVersion 状态同步

多个组件各自调用同一个自定义 hook 时，每个组件有独立的 `useState`。如果 hook 内部通过异步操作更新状态，只有触发该操作的组件实例会被更新，其他调用者的 state 保持初始值。

踩坑记录：`useDataVersion()` 被 `Disclaimer` 和 `DetailPage` 等多个组件调用。fetch `meta.json` 后 `setDate()` 只更新了 `Disclaimer` 的 state，`DetailPage` 的 `dataVersion` 始终为空，导致详情页 F5 刷新后不加载数据。

解决方式：使用模块级 `listeners` 集合 + `notify()` 模式，fetch 完成后通知所有订阅者更新 state。

## React Hydration 规则

React #310 = "Rendered more hooks than during the previous render"，hook 数量在渲染间不一致。

### 规则 1：所有 hooks 必须在条件返回之前

```tsx
// 错误：useMemo 在条件返回之后，首次渲染不调用
function Page() {
  const [data, setData] = useState(null);
  useEffect(() => { fetch(...).then(setData); }, []);
  if (!data) return <Loading />;
  const sorted = useMemo(() => data.items.sort(...), [data]);
}

// 正确：所有 hooks 在条件返回之前
function Page() {
  const [data, setData] = useState(null);
  useEffect(() => { fetch(...).then(setData); }, []);
  const items = data?.items ?? [];
  const sorted = useMemo(() => items.sort(...), [items]);
  if (!data) return <Loading />;
}
```

### 规则 2：SSR 和客户端组件树必须一致

- SSR (`ssr.tsx`) 和客户端 (`App.tsx`) 的 Provider 嵌套必须相同
- 不要在客户端添加 SSR 没有的包装组件（如 `AntdConfigProvider`）
- 如果 SSR 有 `SSRDataContext.Provider`，客户端也必须有（值可以为 `null`）

### 规则 3：SSG Quick 模式下 SSR 数据不完整

Quick 模式只注入 `{ name, translation }`，缺少 `monsters`、`coords` 等字段。

```tsx
// 错误：不完整对象是 truthy，通过 null 检查但缺少必要字段
const [data, setData] = useState(ssrData?.item || null);

// 正确：验证必要字段存在
const [data, setData] = useState(
  ssrData?.item?.monsters ? ssrData.item : null
);
```

详细修复记录见 `docs/DEBUG_HYDRATION.md`。

## 前端排错流程

遇到前端水合错误（#418/#423/#310）时，按以下顺序排查：

1. **Playwright 自动抓取**：见 `docs/DEBUG_HYDRATION_WITH_PLAYWRIGHT.md` 方案一，用无头浏览器打开页面收集控制台报错
2. **Vite 终端日志**：见同一文档方案二，检查服务端日志是否有水合警告
3. **curl 快速判断**：见方案三，区分是 SSR 报错还是 CSR 水合错误

全站回归测试脚本：`/tmp/test_all_pages.mjs`（Playwright 批量打开 1235 个 SSG 页面，统计 #418/#423/#310 错误数）。

## 数据管道关键规则

- `_is_db_stale()` 必须在 `DatabaseManager()` 构造之前调用
- `search_engine.py` 排除地图变体：`_SR`、`_BossTest`、`_Resize`、`_Test`、含 `Arena` 的文件名、`ArenaStart` 目录
- 坐标通过 `db.get_all_coordinates()` 批量获取，避免 N+1
- Spawner 坐标必须递归解析 `AttachParent` 链累加世界坐标（约 16.5% spawner 有父级变换）
- 实体分类通过 `db.get_entity_classification()` 从 DB 直接构建
- Spawner 使用 `executemany` 批量插入
- `_Hard`/`_VeryHard`/`_Unique` 后缀在 lootdrop 解析阶段合入基础怪物名，避免重复掉落条目
- 地图图片优先级：`SubLevelAsset(sl_base) → Module name → MapImage`
- 占位图 `RareModule_1x1` / `UnderConstruction_1x1` 被跳过
- `modules_map` 必须在实体导出（items/monsters/props）之前构建，供 `_modules` 内联注入
- 实体 JSON（items/monsters/props/lootdrops）均包含 `_modules` 字段，内联引用模块的旋转/偏移/尺寸/分组/翻译/图片数据

## 子池（ObjectLinker）变体显示规则

提到“子池”时按以下流程处理：

1. **数据来源**：`api/src/db/repositories/coordinates.py:get_sub_group_pool_info()` — 按 `(map, file, gp, sgp)` 分组，统计各 ObjectLinker 子池的 DISTINCT 实体种类数和实体名列表
2. **名称翻译**：`api/src/collector.py` — 用 `entity_classification` 判断实体类型（monster/props/item），取 `translation_key` 调用 `NameResolver.resolve()` 翻译
3. **JSON 注入**：`api/src/translator.py:build_coord_out` — 每个 coord 写 `sub_pool_size`（子池种数）和 `sub_pool_names`（翻译后的实体名列表）
4. **前端渲染**：`web/src/pages/DetailPage.tsx` — 按 `sub_group_parent` 分组，显示 `(entityName1、entityName2、...poolSize种选uniquePos · uniquePos点选1)`
5. **最大同时存在**：包含该实体的 distinct linker 数量（每个 linker 只生成 1 个实体，不因多个 spawn 点而增加）

详细分析见 `docs/BLINDFALL_PIT_PROBABILITY_ANALYSIS.md`。

## PWA / Service Worker 缓存规则

SW 通过 `vite-plugin-pwa` + Workbox 生成（`web/vite.config.ts`），配置要点：

- `registerType: 'autoUpdate'` — 新版本静默更新，不弹用户提示条
- `maxEntries` 必须等于实际资源数量，由 `vite.config.ts` 中 hardcode：`df5-html=1300`、`df5-data-json=3300`、`df5-data-img=250`、`df5-meta=1`
- 新部署后 `StaleWhileRevalidate` / `NetworkFirst` 策略自动用新数据更新同名缓存，`maxEntries` 够大不会被 LRU 驱逐

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

## 文档索引

| 文档 | 说明 |
|------|------|
| `DEVELOPMENT_WORKFLOW.md` | 日常改动、预检、提交规则 |
| `BUILD_AND_DEPLOY.md` | 构建、预览验证、部署、DB 推送 |
| `AGENT_REFERENCE.md` | 低频架构/页面/排障/文档索引归档 |
| `REFERENCE.md` | 技术参考索引 |
| `REFERENCE_DATA_PIPELINE.md` | 数据管道、Spawner、坐标和实体分类 |
| `REFERENCE_DROP_RATES.md` | 生成概率、物品爆率和变体显示 |
| `REFERENCE_MAP_MODULES.md` | 地图模块、Layout、旋转和图片 |
| `REFERENCE_FRONTEND_DATA.md` | SSR/SSG、JSON 加载和 Hydration |
| `REFERENCE_ARCHIVE.md` | 技术参考历史全文，只读 |
| `plans/MULTILANG_PLAN.md` | 多语言文档索引 |
| `plans/MULTILANG_ARCHITECTURE.md` | 多语言路由、翻译键和 Provider |
| `plans/MULTILANG_BUILD_AND_TEST.md` | 多语言构建、PWA 和验收 |
| `plans/MULTILANG_STATUS.md` | 多语言阶段状态和已知问题 |
| `plans/MULTILANG_PLAN_ARCHIVE.md` | 多语言原计划历史全文，只读 |
| `PWA_ROADMAP.md` | PWA 架构规划 |
| `DEBUG_HYDRATION.md` | Hydration #310 错误修复记录 |
| `DEBUG_HYDRATION_WITH_PLAYWRIGHT.md` | 前端水合错误 Playwright 排错方案 |
| `SESSION_CHANGES.md` | 当前会话修改记录（按日期追加） |
| `SESSION_CHANGES_ARCHIVE.md` | 历史会话修改记录，只读 |
| `ALIAS_ROTATION_OVERWRITE.md` | 别名旋转覆盖修复 |
| `BACKEND_AUDIT_FIX_PLAN.md` | 后端审计修复计划 |
| `CACHE_FIXES.md` | 缓存修复记录 |
| `DROP_RATE_INVESTIGATION.md` | 爆率问题调查 |
| `FIX_ARTIFACT_VARIANT_SWITCH.md` | 神器变体切换修复 |
| `FIX_ENTITY_CLASS_REBUILD.md` | 实体分类重建修复 |
| `FIX_PLAN_lootdrop_module_sort_by_score.md` | lootdrop 模块按 score 排序修复 |
| `FIX_PLAN_lootdrop_ref_coord_filter.md` | lootdrop 引用坐标过滤修复 |
| `FIX_SPAWN_RATE_PER_TYPE_AND_INLINE_COORDS.md` | 刷怪率按类型修复 + 内联坐标 |
| `LOOTDROP_CHAIN.md` | 掉落链分析 |
| `MODULES_LOAD_PERF.md` | 地图模块加载性能 |
| `NAVIGATION_FETCH_BUG.md` | 导航 fetch 路径 Bug |
| `P001_AUDIT_FIX_PLAN.md` | 审计修复计划 P001 |
| `PERF_LOOTDROPS_OPTIMIZATION.md` | lootdrops 性能优化（历史已完成） |
| `PERF_VARIANT_DROP_RATE_CACHE.md` | 变体爆率缓存（**废弃**） |
| `plans/PERF_PIPELINE_AND_RUNTIME.md` | 管线+运行时性能优化草案（待执行） |
| `PLAN_CONTAINER_GENERATOR_ENTITIES.md` | 容器生成器实体页计划 |
| `PLAN_FIX_SPAWN_RATE.md` | 刷怪率修复计划 |
| `PWA_SW_PLAN.md` | Service Worker 计划 |
| `QUEST_DUNGEON_TYPE.md` | 任务地下城类型 |
| `SPAWN_RATE_SCALE_FIX.md` | 刷怪率缩放修复 |
| `SSR_FIELD_VALIDATION.md` | SSR 字段验证 |
| `SUPERHOARD_FIX.md` | Superhoard 修复 |
| `VARIANT_RATES_FIX.md` | 变体爆率修复 |
| `BLINDFALL_PIT_PROBABILITY_ANALYSIS.md` | Blindfall Pit 子池概率分析 |
| `plans/` | 历史方案（P001-P005） |
