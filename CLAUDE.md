# DarkFindV5

读取游戏原始 JSON 数据 → Python 清洗 → 输出后端 JSON 数据文件 → Ant Design React SSG (Vite) → 静态部署 → 浏览器端注水渲染。

> **参考项目**：文中所提「原项目」「v4」「findItemV4」均指 `/home/mio/fmod/findItemV4/`。

> **术语约定**：见 `AGENTS.md`（启动web、部署等）

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
│   ├── lint.sh / lint-fix.sh   # Lint 辅助脚本
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
│   │   ├── dungeon_modules_coords/   # 各模块内实体坐标（按模块名分文件）
│   │   └── meta.json                 # 数据日期元信息（{"dataDate":"YYYY-MM-DD"}）
│   └── img/               # → api/src/img/（管道后复制）
├── web/                 # React 前端（SSG）
│   ├── src/
│   │   ├── main.tsx, App.tsx
│   │   ├── ssr.tsx              # SSR 入口（renderToString + StaticRouter）
│   │   ├── vite-env.d.ts        # Vite 环境类型声明
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # 通用组件（MapDebug, Disclaimer, DebugCoordTable, NavBar）
│   │   ├── hooks/               # useDebug, useTheme, useDungeonModules
│   │   ├── context/             # React Context（SSRDataContext）
│   │   └── types/
│   ├── scripts/ssg.mjs        # SSG 构建脚本
│   ├── .husky/                # Git hooks (pre-commit)
│   ├── public/
│   │   └── data/             # 构建时从 ../data/ 复制
│   └── package.json
├── deploy.sh                 # 一键部署脚本（提交+管道+构建+部署）
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
cd web && npm run build

# 4. 启动web
cd web && kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5; (npx vite preview --port 8080 --host 0.0.0.0 &>/dev/null &) && echo "web started"
```

**注意：** `python main.py` 必须在 `npm run build` 之前运行。TS 类型检查在构建中自动执行 (`npx tsc --noEmit`)。

### 一键部署

```bash
./deploy.sh
```

自动执行：提交 → 管道 → 构建 → 交付，无需手动逐步操作。

## 数据流

```
游戏原始 JSON（/home/mio/fmod/Output/Exports/DungeonCrawler/...）
    ↓ api/main.py (清洗 + SQLite + FTS5，含 quest 数据)
api/output/json/ + api/src/img/
    ↓ main.py 自动交付 → data/{json/, img/}
    ↓ npm run build → web/public/data/（SSG 脚本内复制）
    ↓ Vite build → dist/data/
    ↓ GitHub Actions (actions/deploy-pages) → GitHub Pages
    ↓ 浏览器 fetch("./data/json/index.json") → 注水渲染
    ↓ meta.json 提供数据日期（{"dataDate":"YYYY-MM-DD"}），前端可读取显示

**无游戏文件部署：** DB（`api/data/darkfindv5.db`）包含全部数据（含 quest），放入 `api/data/` 后 `python main.py` 可直接生成所有 JSON。

### 远端仓库

- **GitHub**: `https://github.com/milandomio/dnd9.git`（origin）
- **Token**: `.github_token`（已在 `.gitignore` 中，勿提交）
- **部署**: GitHub Actions 自动构建 → 推送到 `gh-pages` 分支部署到 GitHub Pages
- **Pages 设置**: Settings → Pages → Source 选择 **Deploy from a branch**，分支选 `gh-pages`，目录选 `/ (root)`

### 推送到 dnd9（含 DB）

DB 是二进制文件，不纳入常规 git 追踪。推送时需要临时提交：

```bash
# 1. 提交代码改动
git add -A && git commit -m "feat: <描述>"

# 2. 临时添加 DB + 推送
cp api/data/darkfindv5.db /tmp/darkfindv5.db
git add -f api/data/darkfindv5.db && git commit -m "chore: update DB"
GIT_SSL_NO_VERIFY=1 git push origin main

# 3. 回退本地 DB 追踪
git reset HEAD~1
rm /tmp/darkfindv5.db
```

**注意：**
- `.github/workflows/deploy.yml` 因 token 缺少 `workflow` 权限，需通过 `--force` 推送或在 GitHub 网页手动创建
- `v4_reference/`、`WORKFLOW_PLAN.md`、`.deepseek/`、`mcp-servers/` 已在 `.gitignore` 中，不会推送到远端
- CI 环境无原始游戏文件，管道从 DB 读取全部数据（含 quest）

## 页面布局

| 级别 | 页面 | 路由 | 一行列数 |
|------|------|------|---------|
| 主页 | `index` | `/` | 4 |
| 列表页 | `items`, `monsters`, `props`, `lootdrops`, `explore`, `quest_items`, `quest_npc` | 对应路径 | 3 |
| 详情页 | 实体详情 | `/items/:name` 等 | 4 (CSS Grid, 支持 1x1/2x1/1x2/2x2) |
| 任务物品分组 | `QuestItemGroupPage` | `/quest_items/:group` | 3 |
| 任务 NPC 详情 | `QuestNPCDetailPage` | `/quest_npc/:npc_name` | 4 |
| 地图模块表 | `DungeonModulesPage` | `/dungeon_modules` | 4 (分组列表) |
| 地图模块分组 | `DungeonModuleGroupPage` | `/dungeon_modules/:group` | 4 (模块网格) |
| 地图模块详情 | `DungeonModuleDetailPage` | `/dungeon_modules/:group/:name` | 全宽 (详情+坐标) |

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
| `hooks/useDungeonModules.ts` | 地图模块数据获取与缓存 | DungeonModulesPage, DungeonModuleGroupPage, DungeonModuleDetailPage |

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

## 地图模块表 V2

### 数据来源

Layout JSON 文件位于：`/home/mio/fmod/Output/Exports/DungeonCrawler/Content/DungeonCrawler/Maps/Dungeon/Layouts/`

### Layout 文件命名规则

```
{区域名}_{尺寸}_{序号}_{版本}_{后缀}.json
```

| 字段 | 说明 | 示例 |
|------|------|------|
| 区域名 | 地图区域 | ShipGraveyard, Crypt, Firedeep, IceAbyss 等 |
| 尺寸 | 网格大小 | 3x3, 4x4, 5x5, 7x7 |
| 序号 | 同区域同尺寸的变体 | 01, 02（可选） |
| 版本 | 普通版/豪客版 | `_N_` = 普通版, `_HR_` = 豪客版 |

### Layout 文件内容结构

每个 Layout JSON 包含：

1. **DCWorldSettings** — 地图世界设置，包含 `OverrideDungeonData`（DungeonDataAsset 引用）
2. **LevelStreamingAlwaysLoaded** — 子模块地图的流式加载引用（包含 `WorldAsset` 路径）
3. **BlockingVolume** — 碰撞体积
4. **AkSpatialAudioVolume** — 空间音频体积
5. **其他组件** — 植被、特效、蓝图实例等

### 子模块变体

每个子模块（如 ShipGraveyard_CircleIsland）拆分为多个变体层级：

| 变体 | 含义 | 典型内容 |
|------|------|---------|
| `_A` | 区域逻辑层 (Area/Active) | `BP_DungeonModule_C`（模块逻辑蓝图）、`BoxComponent`（触发区域） |
| `_D` | 装饰细节层 (Decoration/Detail) | StaticMesh、Foliage（植被）、Decal（贴花） |
| `_S` | 空间音频层 (Sound/Spatial) | `DCAkSpatialAudioVolume`、`AkLateReverbComponent`、`AkSurfaceReflectorSetComponent` |
| `_HR_D` | 豪客版地图布局 (High Roller) | 豪客版专属的装饰美术资源（复用普通版逻辑和音频层） |

**设计目的：** 将逻辑、装饰、声音拆分到独立子地图，便于独立编辑和流式加载。

### 子模块字段结构

Layout JSON 中通过 `LevelStreamingAlwaysLoaded` 条目引用子模块，每个条目包含以下字段：

```json
{
  "Type": "LevelStreamingAlwaysLoaded",
  "Name": "LevelStreamingAlwaysLoaded_0",
  "Properties": {
    "WorldAsset": {
      "AssetPathName": "/Game/DungeonCrawler/Maps/Dungeon/Modules/{区域名}/{模块名}/{变体名}.{变体名}",
      "SubPathString": ""
    },
    "LevelTransform": {
      "Translation": { "X": 3200.0, "Y": 9600.0, "Z": 0.0 },
      "Rotation": { "X": 0.0, "Y": 0.0, "Z": 0.707, "W": 0.707 }  // 可选
    },
    "LevelColor": {
      "R": 0.0, "G": 0.039, "B": 1.0, "A": 1.0,
      "Hex": "0037FF"
    }
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `WorldAsset.AssetPathName` | string | 子模块地图路径，格式 `/Game/.../Modules/{区域}/{模块}/{变体}.{变体}` |
| `WorldAsset.SubPathString` | string | 子路径（通常为空） |
| `LevelTransform.Translation` | {X,Y,Z} | 子模块在主地图中的位置偏移 |
| `LevelTransform.Rotation` | {X,Y,Z,W} | 四元数旋转（可选，默认无旋转） |
| `LevelColor.Hex` | string | 编辑器中该层级的可视化颜色（见下表） |

### LevelColor 颜色编码

| 变体 | Hex 颜色 | RGB 含义 |
|------|----------|----------|
| `_A` | `0037FF` | 蓝色 (R=0, G≈0.04, B=1) |
| `_D` | `00FF5D` | 绿色 (R=0, G=1, B≈0.11) |
| `_S` | `00FFFD` | 青色 (R=0, G=1, B≈0.98) |
| `_HR_D` | `FF0069` | 粉红色 (R=1, G=0, B≈0.14) |

**区分 `_D` 和 `_HR_D`：** 主要通过 `WorldAsset.AssetPathName` 中的变体名后缀判断，`LevelColor.Hex` 仅作编辑器可视化辅助。

### DCDungeonModuleDataAsset 配置

游戏运行时模块加载由 `DCDungeonModuleDataAsset` 配置文件驱动，位于：
`/home/mio/fmod/Output/Exports/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Dungeon/DungeonModule/`

配置文件结构示例（`Id_DungeonModule_Ruins_Forest_01.json`）：

```json
{
  "Type": "DCDungeonModuleDataAsset",
  "Name": "Id_DungeonModule_Ruins_Forest_01",
  "Properties": {
    "Name": {
      "Key": "Text_DesignData_Dungeon_DungeonModule_Forest_A",
      "LocalizedString": "Forest A"
    },
    "ModuleType": "EDCDungeonModuleType::Ruins",
    "Size": { "X": 1, "Y": 1 },
    "SubLevelAssetA": { "AssetPathName": ".../Ruins_Forest_01_A..." },
    "SubLevelAssetD": { "AssetPathName": ".../Ruins_Forest_01_D..." },
    "SubLevelAssetD_HR": { "AssetPathName": ".../Ruins_Forest_01_HR_D..." },
    "SubLevelAssetS": { "AssetPathName": ".../Ruins_Forest_01_S..." },
    "MapImage": { "AssetPathName": ".../Ruins_Forest_01..." }
  }
}
```

| 字段 | 说明 |
|------|------|
| `Name.Key` | 翻译键（精准定位本地化文本） |
| `Name.LocalizedString` | 显示名称（英文） |
| `SubLevelAssetA` | _A 变体（逻辑层，含实体 spawner） |
| `SubLevelAssetD` | _D 变体（普通版地图布局） |
| `SubLevelAssetD_HR` | _HR_D 变体（豪客版地图布局），若无则豪客版使用 _D |
| `SubLevelAssetS` | _S 变体（音频层） |
| `MapImage` | 地图预览图片 |

### MapImage 提取规则

1. **直接提取**：从 `MapImage.AssetPathName` 获取图片文件名（去掉路径和扩展名）
2. **占位符检测**：若提取到 `UnderConstruction_1x1` 或 `RareModule_1x1`，视为占位符
3. **回退匹配**：
   - 占位符或无 MapImage → 尝试 `{_A 变体文件名}.webp`
   - 仍无匹配 → 尝试 `{模块名}.webp`

**图片目录**：`/home/mio/fmod/Output/Exports/DungeonCrawler/Content/DungeonCrawler/Data/Art/DungeonModuleMapImage/{区域名}/`

### 地图模块表 V2 采集规则

采集 `DCDungeonModuleDataAsset` 配置文件，输出以下字段：

| 字段 | 来源 | 说明 |
|------|------|------|
| 区域 | `ModuleType` 去掉 `EDCDungeonModuleType::` 前缀 | 如 `Crypt`, `Ruins`, `ShipGraveyard` |
| 模块名 | `Name.LocalizedString` | 如 `Forest A`, `Admirer's Room` |
| 翻译键 | `Name.Key` | 如 `Text_DesignData_Dungeon_DungeonModule_Forest_A` |
| _A 变体 | `SubLevelAssetA.AssetPathName` 提取文件名 | 逻辑层，含实体 spawner |
| _D 变体 | `SubLevelAssetD.AssetPathName` 提取文件名 | 普通版地图布局，若无则为空 |
| _HR_D 变体 | `SubLevelAssetD_HR.AssetPathName` 提取文件名 | 豪客版地图布局，若无则复用 _D |
| MapImage | `MapImage.AssetPathName` 提取文件名 | 地图预览图片，占位符则回退匹配 |

**输出路径**：`data/json/dungeon_modules_v2.json`

**说明：**
- `_D` 列为空表示该模块无独立普通版地图布局（复用豪客版或不存在）
- `_HR_D` 列若与 `_D` 相同，表示该模块无独立豪客版地图布局
