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
│   │   ├── quest_items.json
│   │   └── quest_npc.json
│   └── img/               # → api/src/img/（管道后复制）
├── web/                 # React 前端（SSG）
│   ├── src/
│   │   ├── main.tsx, App.tsx
│   │   ├── pages/            # 页面组件
│   │   ├── components/       # 通用组件（MapDebug, Disclaimer, DebugCoordTable）
│   │   ├── hooks/            # useDebug hook
│   │   └── types/
│   ├── public/
│   │   └── data/             # prebuild 从 ../data/ 复制
│   └── package.json
├── .github/workflows/deploy.yml
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

### 完整构建流程

```bash
# 1. 提交当前进度（改动前 checkpoint）
git commit -am "WIP: <描述>"

# 2. 运行数据管道（运行后自动交付 JSON + 图片到 data/）
cd api && python main.py

# 3. 构建前端（prebuild 自动从 data/ 复制到 public/data/）
cd ../web && npm run build

# 4. 预览（后台运行，端口 8080）
# ⚠️ codewhale 中 nohup + & 会被回收，改用 setsid：
setsid sh -c 'vite preview --port 8080 --host 0.0.0.0 > /tmp/vite-preview.log 2>&1 &'
```

**注意：** `python main.py` 必须在 `npm run build` 之前运行。TS 类型检查在构建中自动执行 (`npx tsc --noEmit`)。

## 数据流

```
游戏原始 JSON（/home/mio/fmod/Output/Exports/DungeonCrawler/...）
    ↓ api/main.py (清洗 + SQLite + FTS5)
api/output/json/ + api/src/img/
    ↓ main.py 自动交付 → data/{json/, img/}
    ↓ npm run prebuild → web/public/data/
    ↓ Vite build → dist/data/
    ↓ GitHub Actions → gh-pages branch
    ↓ 浏览器 fetch("./data/json/index.json") → 注水渲染
```

## 页面布局

| 级别 | 页面 | 一行列数 |
|------|------|---------|
| 主页 | `index` | 4 |
| 列表页 | `items`, `monsters`, `props`, `lootdrops` | 3 |
| 详情页 | 实体详情 | 4 (CSS Grid, 支持 1x1/2x1/1x2/2x2) |

详情页地图卡片：按 `size_y` → `size_x` 升序排列，坐标范围 `Math.max(size_x, size_y) * 1600`。

## 组件架构

| 组件 | 用途 | 消费页面 |
|------|------|---------|
| `components/MapDebug.tsx` | 坐标变换、像素映射、调试按钮/输入框样式 | DetailPage, LootdropDetailPage |
| `components/Disclaimer.tsx` | 统一"数据有误差"警告 | HomePage, DetailPage, LootdropDetailPage |
| `components/DebugCoordTable.tsx` | 调试模式坐标详情表（含勾选隐藏/地图/怪物切换） | DetailPage, LootdropDetailPage |
| `hooks/useDebug.tsx` | 调试开关、偏移量状态 | DetailPage, LootdropDetailPage |

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
