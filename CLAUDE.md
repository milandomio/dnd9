# DarkFindV5

读取游戏原始 JSON 数据 → Python 清洗 → 输出后端 JSON 数据文件 → Ant Design React SSG (Vite) → 静态部署 → 浏览器端注水渲染。

> **参考项目**：文中所提「原项目」「v4」「findItemV4」均指 `/home/mio/fmod/findItemV4/`。

## 项目结构

```
DarkFindV5/
├── api/                  # 后端
│   ├── main.py               # 入口脚本（运行管道 + 自动交付到 data/）
│   ├── src/                  # 模块
│   │   ├── collector.py          # 数据清洗 + JSON 输出
│   │   ├── config.py             # 路径配置
│   │   ├── db_manager.py         # SQLite 建表/导入/查询
│   │   ├── search_engine.py      # 地图文件遍历 + 关键词匹配
│   │   ├── layout_utils.py       # 地图旋转值计算
│   │   ├── quest_collector.py    # 任务提取入口
│   │   ├── quest_extractor/      # 任务提取模块
│   │   └── img/                  # 地图图片 .webp（不可再生，严**禁**清理）
│   ├── data/                # DB 文件（darkfindv5.db）
│   ├── output/              # 管道输出
│   │   └── json/                # JSON 数据文件
│   └── pyproject.toml
├── data/                 # 交付目录（main.py 自动维护，可重生，可清理）
│   ├── json/              # → api/output/json/（管道后移入）
│   │   ├── items.json / items/
│   │   ├── monsters.json / monsters/
│   │   ├── props.json / props/
│   │   ├── lootdrops.json / lootdrops/
│   │   ├── dungeon_modules.json
│   │   ├── explore.json
│   │   ├── index.json
│   │   ├── entity_index.json      # 实体索引（名称、类型、翻译键）
│   │   ├── search_index.json      # 搜索索引（前端全局搜索用）
│   │   ├── quest_items.json
│   │   ├── quest_items_groups.json / quest_items_groups/
│   │   ├── quest_npc.json
│   │   └── dungeon_modules_coords/   # 各模块内实体坐标（按模块名分文件）
│   └── img/               # → api/src/img/（管道后复制）
├── web/                 # React 前端（SSG）
│   ├── src/
│   │   ├── main.tsx, App.tsx
│   │   ├── ssr.tsx              # SSR 入口（renderToString + StaticRouter）
│   │   ├── vite-env.d.ts        # Vite 环境类型声明
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # 通用组件（MapDebug, Disclaimer, DebugCoordTable, NavBar）
│   │   ├── hooks/               # useDebug, useTheme
│   │   ├── context/             # React Context（SSRDataContext）
│   │   └── types/
│   ├── public/
│   │   └── data/             # 构建时从 ../data/ 复制
│   └── package.json
├── .github/workflows/deploy.yml
├── LICENSE
└── CLAUDE.md
```

## 开发流程

### 前置规则：改动前先提交

每次对代码做任何改动之前（包括 Python 后端、React 前端、配置文件），必须先执行本地 git 提交，
将当前工作区状态落盘为 checkpoint。目的是让每次改动有清晰的边界，方便回退和追溯。

```bash
git commit -am "WIP: <改动摘要>"
```

如果当前有未跟踪的新文件（`??` 状态），先用 `git add` 纳入后再提交：

```bash
git add <新文件路径> && git commit -am "WIP: <改动摘要>"
```

### 修改入口 / 列表页时注意：不要直接改 data/ 下的自动生成文件

以下文件每次运行 `python main.py` 都会由 `api/src/collector.py` 重新生成并覆盖：
- `data/json/index.json` — 首页入口列表
- `data/json/items.json` / `monsters.json` / `props.json` / `lootdrops.json`
- `data/json/dungeon_modules.json`

如需添加/修改这些文件的内容，必须在 `api/src/collector.py` 中找到对应的生成代码进行修改，
而不是直接改 `data/json/` 下的产物文件，否则管道运行后会被覆盖丢失。

### 完整构建流程

```bash
# 1. 提交当前进度（改动前 checkpoint）
git commit -am "WIP: <描述>"

# 2. 运行数据管道（运行后自动交付 JSON + 图片到 data/）
cd api && python main.py

# 3. 构建前端（SSG 脚本自动从 data/ 复制到 public/data/）
cd ../web && npm run build

# 4. 预览（后台运行，端口 8080）
# ⚠️ codewhale 中 nohup + & 会被回收，改用 setsid：
kill $(lsof -t -i:8080) 2>/dev/null; setsid sh -c './node_modules/.bin/vite preview --port 8080 --host 0.0.0.0 > /tmp/vite-preview.log 2>&1 &'
```

**注意：** `python main.py` 必须在 `npm run build` 之前运行。TS 类型检查在构建中自动执行 (`npx tsc --noEmit`)。

## 数据流

```
游戏原始 JSON（/home/mio/fmod/Output/Exports/DungeonCrawler/...）
    ↓ api/main.py (清洗 + SQLite + FTS5)
api/output/json/ + api/src/img/
    ↓ main.py 自动交付 → data/{json/, img/}
    ↓ npm run build → web/public/data/（SSG 脚本内复制）
    ↓ Vite build → dist/data/
    ↓ GitHub Actions → gh-pages branch
    ↓ 浏览器 fetch("./data/json/index.json") → 注水渲染

**无游戏文件部署：** DB（`api/data/darkfindv5.db`）不纳入 git，从 GitHub Releases 下载后放入 `api/data/` 即可。

### DB 临时提交（push 前）

```bash
# 1. 备份
cp api/data/darkfindv5.db /tmp/darkfindv5.db

# 2. 提交 + rebase + push
git add -f api/data/darkfindv5.db && git commit -m "update DB"
git pull --rebase
git push

# 3. 回退本地跟踪
git reset HEAD~1

# 4. 删临时备份
rm /tmp/darkfindv5.db
```

**注意：** 下次 push 前必须 `git pull --rebase`，可能因二进制冲突导致失败。推荐直接正常跟踪 DB 避免此问题。

## 页面布局

| 级别 | 页面 | 一行列数 |
|------|------|---------|
| 主页 | `index` | 4 |
| 列表页 | `items`, `monsters`, `props`, `lootdrops`, `explore`, `quest_items`, `quest_npc` | 3 |
| 详情页 | 实体详情 | 4 (CSS Grid, 支持 1x1/2x1/1x2/2x2) |
| 地图模块表 | `dungeon_modules` | 4 (分组列表) → 4 (模块网格) → 全宽 (详情+坐标) |

详情页地图卡片：按 `size_y` → `size_x` 升序排列，坐标范围 `Math.max(size_x, size_y) * 1600`。

## 组件架构

| 组件 | 用途 | 消费页面 |
|------|------|---------|
| `components/MapDebug.tsx` | 坐标变换、像素映射、调试按钮/输入框样式 | DetailPage, LootdropDetailPage |
| `components/Disclaimer.tsx` | 统一"数据有误差"警告 | HomePage, DetailPage, LootdropDetailPage |
| `components/DebugCoordTable.tsx` | 调试模式坐标详情表（含勾选隐藏/地图/怪物切换） | DetailPage, LootdropDetailPage |
| `components/NavBar.tsx` | 导航栏 | 全局 |
| `hooks/useDebug.tsx` | 调试开关、偏移量状态 | DetailPage, LootdropDetailPage |
| `hooks/useTheme.tsx` | 主题切换 | 全局 |

## 数据管道

### DB 过期判断时序

`collector.py` 的 `run()` 中，`_is_db_stale()` 必须在 `DatabaseManager()` 构造**之前**调用，
否则 `sqlite3.connect()` 会先创建空 DB 文件，导致 mtime 为"现在"，过期判断始终返回 False，导入步骤被跳过。

**修复前**需要手动 `touch Game.json` 才能触发重建。**修复后**直接 `rm db && python main.py` 即可。

### `_SR` 地图文件过滤

`search_engine.py` 的 `_list_map_jsons()` 遍历地图文件时需排除 `_SR` 后缀变体。
`_SR` 是地图的旧版变体（如 `FourWayConnect_SR_D.json`），不应出现在 spawner 搜索结果中。

**修复前** 39034 个 spawner，**修复后** 38444 个（减少 590 条）。

### 坐标批量获取

`collector.py` 的 `run()` 在导出阶段通过 `db.get_all_coordinates()` 一次性获取所有实体坐标，
返回 `dict[str, list[dict]]`（search_term → 坐标列表）。后续所有导出段（items、monsters、props、
dungeon_modules_coords、lootdrops）通过 `all_coords.get(name, [])` 查询，消除了逐实体 N+1 查询。

### 实体分类

`collector.py` 的 `run()` 通过 `db.get_entity_classification()` 从 DB 实体表直接构建分类映射，
返回 `dict[str, dict]`（entity_name → {types, translation_key}）。替代了旧版 `_build_entity_classification()`
逐文件扫描 ~3,249 个 JSON 的方式。

### Spawner 导入架构

Spawner 和 search_term_matches 的插入逻辑直接在 `collector.py` 的 `run()` 中内联执行，
使用 `executemany` 批量插入（~32,000+ spawner 行 + ~483 matched term 行）。
通过 `db.connect()` 获取原始 sqlite3.Connection 操作，而非通过 `db_manager.py` 的封装方法。

## 数据库

### 地图 ModuleType 缺失

部分 dungeon module JSON 的 `ModuleType` 为空，分组推断策略（`db_manager.py` 的 `import_dungeon_modules`）：

1. **sl_base 反查** — 从 SubLevelAsset 提取地图名，在已加载模块字典中查找其 ModuleType
2. **前缀推断（兜底）** — 从模块名前缀判断

**已推断示例：** Shipgraveyard_UnderSeaCave_02 → sl_base Shipgraveyard_TwinChamber → 反查到 ShipGraveyard

**剩余 19 个通用跨区域模块（无分组）：**

| # | 模块名 | sl_base |
|---|--------|---------|
| 1 | AltarRoomAB_Center | AltarRoomAB_Center |
| 2 | Armory_Center | (空) |
| 3-6 | Connector_Half_01~04 | (空) |
| 7 | CorridorofDarkPriests_Center | (空) |
| 8 | DarkMagicLibrary | (空) |
| 9-11 | DarkRitualRoom_01~03 | (空) |
| 12 | DarkRitualRoom_04 | DarkRitualRoom_04 |
| 13 | DeathHall_Center | DeathHall_Center |
| 14 | GuardPost_Center | (空) |
| 15 | MimicRoom_Center | (空) |
| 16 | MummyRoom | MummyRoom |
| 17 | PassingRoad_03 | (空) |
| 18 | Sewers_Center | (空) |
| 19 | Tomb | (空) |

这些模块在前端无分组标题栏，直接排列在地图网格底部。sl_base 为空表示 JSON 中无 SubLevelAsset 属性。

### 地图图片匹配

`collector.py` 中 `_resolve_img()` 返回三态：

- `found` — Art 目录存在且找到匹配（含大小写/tail/数值后缀处理）
- `not_found` — Art 目录存在但无匹配 → 尝试 module_name
- `no_art` — 无 Art 目录（如 ShipGraveyard）→ sl_base_name 作为最终答案

**图片名优先级链：** SubLevelAsset(sl_base) → Module name → MapImage  
**占位图跳过：** `RareModule_1x1` 和 `UnderConstruction_1x1` 在匹配链中被跳过，仅作前端最终兜底。

### 坐标合并

`_Hard`/`_VeryHard`/`_Unique` 后缀变体的坐标合入基础怪物，避免同一怪物显示多个重复按钮。

### 旋转值

从 Layout JSON 文件计算，优先级：`module_name` → `sl_base_name`，默认 1（90°）。

### 废弃方法

`db_manager.py` 的 `get_item_coordinates()` 已被 `get_all_coordinates()` 取代，不再被 `collector.py` 调用。
保留为死代码，待后续清理。
