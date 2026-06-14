# DarkFindV5 技术参考

> 本文档包含数据管道、数据库、地图模块的详细技术规范。
> 日常开发请参考 `CLAUDE.md`。

## 数据管道

### DB 过期判断时序

`collector.py` 的 `run()` 中，`_is_db_stale()` 必须在 `DatabaseManager()` 构造**之前**调用，
否则 `sqlite3.connect()` 会先创建空 DB 文件，导致 mtime 为"现在"，过期判断始终返回 False，导入步骤被跳过。

**修复前**需要手动 `touch Game.json` 才能触发重建。**修复后**直接 `rm db && python main.py` 即可。

### 地图文件过滤

`search_engine.py` 的 `_list_map_jsons()` 遍历地图文件时需排除以下变体：
- `_SR` — 地图旧版变体（如 `FourWayConnect_SR_D.json`）
- `_BossTest`、`_Resize`、`_Test` — 测试/调试变体
- 含 `Arena` 的文件名、`ArenaStart` 目录 — 竞技场文件

### 坐标批量获取

`collector.py` 的 `run()` 在导出阶段通过 `db.get_all_coordinates()` 一次性获取所有实体坐标，
返回 `dict[str, list[dict]]`（search_term → 坐标列表）。后续所有导出段（items、monsters、props、
dungeon_modules_coords、lootdrops）通过 `all_coords.get(name, [])` 查询，消除了逐实体 N+1 查询。

### Spawner 坐标提取与 AttachParent 链

`search_engine.py` 的 `extract_spawners()` 从地图 JSON 提取 spawner 坐标。地图中每个 `BP_GameSpawner_C`
通过其 `RootComponent`（`SphereComponent`/`SceneComponent`）的 `RelativeLocation` 获取位置。

**关键规则：** 部分 SceneComponent 有 `AttachParent` 字段指向父级组件，此时 `RelativeLocation` 是相对于
父级的偏移量，**不是世界坐标**。必须沿 `AttachParent` 链递归累加所有祖先的 `RelativeLocation` 才能得到世界坐标。

`AttachParent` 通过 `ObjectPath`（如 `xxx/MapName.390`）引用父级，后缀数字为 JSON 数组索引。
无 `AttachParent` 的组件直接使用 `RelativeLocation` 作为世界坐标。

**影响范围：** 约 16.5% 的 spawner（~1980 个）有父级变换，分布在 ~144 个地图文件中。
典型场景：`GameObjectLinker`、`SingleGameSpawnerGroup` 等分组容器下的 spawner。

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

### Lootdrop 怪物名合并

`_Hard`/`_VeryHard`/`_Unique` 后缀变体在 lootdrop 解析阶段合入基础怪物名，避免重复掉落条目。

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
      "Rotation": { "X": 0.0, "Y": 0.0, "Z": 0.707, "W": 0.707 }
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

## JSON 加载机制

SSG 构建时，`ssg.mjs` 将路由数据注入 `<script>window.__SSR_DATA__={...}</script>`。
客户端通过 `useSSRData(key)` 读取，有 SSR 数据则跳过 fetch，否则回退到客户端请求。

### 列表页

| 页面 | SSR Key | 客户端 Fetch | SSR 跳过条件 |
|------|---------|-------------|-------------|
| 主页 `/` | `"home"` | `index.json` | SSR 存在即跳过 |
| 物品/怪物/实体/掉落 `/:page` | `"list-{page}"` | `{page}.json` | SSR 存在即跳过 |
| 探索地点 `/explore` | `"explore"` | `explore.json` | SSR 存在即跳过 |
| 任务物品 `/quest_items` | `"quest_items"` | `quest_items_groups.json` | SSR 存在即跳过 |
| 任务物品分组 `/quest_items/:group` | `"quest_items_groups/{group}"` | `quest_items_groups/{group}.json` | SSR 有 entities 时跳过 |
| 任务NPC `/quest_npc` | `"quest_npc"` | `quest_npc.json` | SSR 存在即跳过 |
| 地图模块 `/dungeon_modules` | 无 | `useDungeonModules()` hook | 始终客户端 fetch |
| 地图模块分组 `/dungeon_modules/:group` | `"dungeon_modules/{group}"` | `useDungeonModules()` hook（filter） | 优先 SSR，否则回退 hook |

### 详情页

| 页面 | SSR Key | 客户端 Fetch | SSR 跳过条件 |
|------|---------|-------------|-------------|
| 物品/怪物/实体详情 `/:page/:name` | `"{page}/{name}"` | `{page}/{name}.json` | quick 模式仍 fetch（SSR 无 coords） |
| 掉落详情 `/lootdrops/:name` | `"lootdrops/{name}"` | `lootdrops/{name}.json` | quick 模式仍 fetch（SSR 无 monsters） |
| 任务NPC详情 `/quest_npc/:npc_name` | `"quest_npc"`（共享） | `quest_npc.json` | SSR 存在即跳过 |
| 地图模块详情 `/dungeon_modules/:group/:name` | 无 | `dungeon_modules_coords/{name}.json` | 始终客户端 fetch |

### `--quick` 模式行为

列表页：完整 SSR 数据注入，客户端跳过 fetch。
详情页：仅注入 `{name, translation}` 用于 SEO，客户端仍需 fetch 完整数据。

### 共享 Hook

- `useDungeonModules()` — 全局缓存 `dungeon_modules.json`，所有地图模块页面复用同一份数据
- `useSearchIndex()` — 全局缓存 `search_index.json`，供 NavBar 搜索使用

## 已完成优化

- **路由级代码分割** — `React.lazy()` 拆分 6 个页面（DetailPage、LootdropDetailPage、QuestItemGroupPage、QuestNPCDetailPage、DungeonModuleGroupPage、DungeonModuleDetailPage），主 bundle 84KB → 32KB
- **SSR 数据复用** — DungeonModuleGroupPage 优先使用 `useSSRData()` 预渲染数据，避免客户端重复 fetch
- **无用 JSON 清理** — `entity_index.json`（271KB）、`quest_items.json`（88KB）从交付目录移除（管道内部仍保留）
