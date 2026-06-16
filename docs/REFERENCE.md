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

### DungeonGrade 地图分组代码识别

`Id_LootDropGroup_*.json` 中 `LootDropGroupItemArray` 的每项包含 `DungeonGrade` 字段（整数），
可直接识别该掉落所属的**地图分组**和**游戏模式**。

**编码规则**（4 位数字）：

| 位 | 含义 | 取值 |
|----|------|------|
| 第 1 位 | 游戏模式 | `1`=PVE, `2`=普通, `3`=豪客赛, `4`=逆袭赛 |
| 第 2 位 | 地图编号 | `0`=哥布林洞穴, `1`=冰图, `2`=废墟, `3`=水图 |
| 第 3-4 位 | 楼层 | `01`=1层, `02`=2层, `03`=3层 |

**示例**：`3001` → 模式 `3`(豪客赛) + 地图 `0`(哥布林) + 层 `01`(1层) → "豪客哥布林1层"

**完整代码表**（config.py `DUNGEON_GROUP_GRADES`）：

| base_code | group key | 中文名 | 楼层范围 |
|-----------|-----------|--------|---------|
| 001~002 | GoblinCave | 哥布林洞穴 | 1~2层 |
| 011~012 | IceCavern | 冰图 | 1~2层 |
| 021~023 | Crypt | 废墟 | 1~3层 |
| 031~032 | ShipGraveyard | 水图 | 1~2层 |

**用法**（`api/src/dungeon_mode.py`）：

```python
from dungeon_mode import parse_grade
info = parse_grade(3001)
# → {"grade": 3001, "mode": 3, "mode_name": "豪客赛",
#    "group": "GoblinCave", "group_label": "哥布林洞穴",
#    "floor": 1, "display": "豪客哥布林1层"}
```

**参考数据来源**：`Output/Exports/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/LootDrop/LootDropRate.py`
中的 `DUNGEON_GRADE_MAP` 和 `CSV_GRADE_BOSS_MAP`。

### 生成概率与物品爆率

物品掉落涉及两层概率：**生成概率**（Spawner 是否出现）和**物品爆率**（出现后掉落什么）。

#### 生成概率（SpawnRate）

坐标点数据中关联的 `SpawnerDataAsset`（如 `Id_Spawner_New_Props_GoldChest`）对应
`Spawner/Spawner/Id_Spawner_New_Props_GoldChest.json`，其中 `SpawnRate` 字段为原始生成权重。

**DB 存储格式：** `spawner_entries.spawn_rate` 存储为百分比（0~100），按同 `SpawnerItemArray` 内的比例计算：
`round(entry_rate / sum(all_rates_in_array) * 100)`

- 单条目 spawner：`SpawnRate=10000` → 100%
- 多条目 spawner（如 ChestLarge 含 9 个实体）：各条目按权重占比计算百分比
- 原始 `SpawnRate` 以 `10000` 为基准，`2500` = 25%（单条目时），`0` = 不生成

**实现位置：** `db_manager.py` 的 `import_spawner_entries()` 在导入时计算百分比，
`lootdrop_rates.py` 的 `get_spawn_rate_for_keyword()` 直接从 DB 读取百分比。

#### 物品爆率（DropRate）查询链

以 **FrozenIronKey（冰铁钥匙）** 在 **豪客冰图2层（3012）** 的爆率为例，完整查询链如下：

```
Id_Spawner_New_Props_GoldChest.json
│  Properties.SpawnerItemArray[0].LootDropGroupId
│  → "Id_LootDropGroup_GoldChest"
▼
Id_LootDropGroup_GoldChest.json
│  Properties.LootDropGroupItemArray（按 DungeonGrade 筛选）
│  → DungeonGrade: 3012 的条目
│    ├── LootDropId    → "ID_Lootdrop_Drop_FrozenIronKey"
│    ├── LootDropRateId → "ID_Droprate_Key_Low_3012"
│    └── LootDropCount → 1
▼
ID_Lootdrop_Drop_FrozenIronKey.json
│  Properties.LootDropItemArray[0]
│    ├── ItemId.AssetPathName → "Id_Item_FrozenIronKey"  ← 倒查物品的关键
│    ├── LuckGrade → 5                                   ← 物品等级
│    └── ItemCount → 1                                   ← 每次掉落数量
▼
ID_Droprate_Key_Low_3012.json
   Properties.LootDropRateItemArray（按 LuckGrade 筛选）
   → LuckGrade: 5 的条目
     └── DropRate → 2500  ← 即 25% 爆率（10000 = 100%）
```

**各层说明：**

| 层级 | 文件 | 关键字段 | 作用 |
|------|------|---------|------|
| Spawner | `Id_Spawner_New_Props_GoldChest.json` | `SpawnRate`, `LootDropGroupId` | 生成概率 + 指向掉落组 |
| LootDropGroup | `Id_LootDropGroup_GoldChest.json` | `DungeonGrade`, `LootDropId`, `LootDropRateId` | 按地图模式筛选掉落项 |
| LootDrop | `ID_Lootdrop_Drop_FrozenIronKey.json` | `ItemId`, `LuckGrade`, `ItemCount` | 确定物品、等级、数量 |
| LootDropRate | `ID_Droprate_Key_Low_3012.json` | `LuckGrade`, `DropRate` | 按等级查爆率 |

**数值规则：**
- `SpawnRate` / `DropRate` 均以 `10000` 为 100%，`2500` = 25%，`0` = 不掉落
- `LuckGrade` 范围 0~8，等级越高物品越稀有
- `LootDropCount` 表示该掉落组每次触发时的抽取次数
- 同一 `LootDropGroup` 中可有多条 `DungeonGrade: 3012` 的条目，每条对应不同物品类型（如钥匙、宝石、饰品等），各自有独立的 `LootDropRateId`

### 爆率显示实现 [进行中]

> **状态：** 生成概率（spawn_rate）已完成并验证。物品爆率（drop_rates）代码已编写，因循环内逐坐标 DB 查询导致管道耗时过长（~70s），暂时注释掉，待优化后重新启用。

Lootdrop 详情页地图模块卡片图例显示格式：`黄金宝箱100%([PVE:25%][普通25%][豪客赛25%])`。

**DB 表结构（4 张表，已在 `db_manager.py` 中实现）：**

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `spawner_entries` | Spawner 条目（生成概率 + LootDropGroupId） | `spawner_keyword`, `entity_name`, `spawn_rate`, `lootdrop_group_id` |
| `lootdrop_groups` | LootDropGroup → LootDrop + Rate 映射 | `group_id`, `dungeon_grade`, `lootdrop_id`, `lootdrop_rate_id` |
| `lootdrop_rate_items` | LootDrop 中的物品列表 | `lootdrop_id`, `item_name`, `luck_grade`, `drop_count` |
| `lootdrop_rate_weights` | 各 LuckGrade 的权重 | `rate_id`, `luck_grade`, `weight` |

**计算逻辑（`lootdrop_rates.py`）：**

1. `get_spawn_rate_for_keyword(db, keyword)` — 从 `spawner_entries` 取 max(spawn_rate)，已是百分比（0~100）
2. `get_drop_rates_for_item_with_coords(db, item, monster, coords, ...)` — **暂时未使用**（见下方注释清单）

**暂时注释的代码（爆率计算）：**

| 文件 | 位置 | 注释内容 |
|------|------|---------|
| `api/src/collector.py` | `_get_drop_rates()` 函数定义（约 L1298~L1313） | 整个函数体注释掉 |
| `api/src/collector.py` | lootdrop detail 循环内（约 L1335~L1345） | `_get_drop_rates()` 调用和 `merged[base]["drop_rates"]` 赋值注释掉 |
| `api/src/collector.py` | 爆率查找表构建（约 L1272~L1288） | `map_base_to_group` 字典构建注释掉 |

**注释原因：** `get_drop_rates_for_item_with_coords()` 对每个 (item, monster) 组合执行多次 DB 查询（遍历 mode × group × floor_suffix），452 个物品 × 多怪物 × 多坐标 = 数万次查询，导致 lootdrops 详情导出耗时 ~70s（占管道总时间 97%）。

**待优化方向：**
- 预加载所有爆率数据到内存，避免逐次 DB 查询
- 或在 DB 层面批量查询后 Python 侧分组

**前端显示（`LootdropDetailPage.tsx`）：**
- `spawn_rate` 字段从 coord 级别取（仅 ≠100 时显示）— **已生效**
- `drop_rates` 字段从 monster 级别取（`Record<string, number>`，key 为模式名）— **暂时无数据**

**已修改文件清单：**
- `api/src/config.py` — 新增 `LOOTDROP_RATE_DIR`、扩展 `DUNGEON_GROUP_GRADES`（8组）、添加 `MODULE_GROUP_FLOOR_SUFFIXES`
- `api/src/db_manager.py` — 新增 4 张表 + `import_spawner_entries()` / `import_lootdrop_groups()` / `import_lootdrop_rate_items()` / `import_lootdrop_rate_weights()` + `get_spawner_entries_for_keyword()` / `get_item_drop_rate()`
- `api/src/lootdrop_rates.py` — 新建，爆率计算模块（从 DB 查询）
- `api/src/collector.py` — 管道步骤 9 导入爆率数据，lootdrop 详情段计算 `spawn_rate`（`drop_rates` 暂时注释）
- `web/src/pages/LootdropDetailPage.tsx` — 接口扩展 + 图例显示格式
- `docs/REFERENCE.md` — 本章节

**待完成步骤：**
1. 优化爆率查询性能（预加载或批量查询）
2. 取消 `collector.py` 中 `drop_rates` 相关注释
3. 运行 `python main.py` 验证 JSON 输出（检查 `drop_rates` 字段）
4. 运行 `npm run build` 验证前端构建
5. 启动 web 预览，访问 `/lootdrops/FrozenIronKey` 验证图例显示

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
| 任务探索 `/explore` | `"explore"` | `explore.json` | SSR 存在即跳过 |
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

### search_term_matches 精确度问题

当前 `search_engine.py` 对 spawner 的匹配逻辑会将 `FrostWyvernEgg`（物品）也匹配到搜索词 `FrostWyvern`（怪物），
因为 `FrostWyvern` 是 `FrostWyvernEgg` 的前缀子串。

**问题表现：** `lootdrops/FrozenIronKey.json` 中出现 `FrostWyvernEgg` 坐标的 2 条记录，
其中 `label: "FrostWyvernEgg"` 的 spawner 实际上是一个物品生成点（物品无法作为容器/怪物掉落物品），
不应出现在掉落来源列表中。但当前匹配逻辑不区分 spawner 类型（物品 vs 怪物），导致错误关联。

**影响：** 坐标被计入但 spawn_rate 需回退用 `m_name`（怪物名）查询，因为 `spawner_entries` 中不存在
`FrostWyvernEgg` 条目（无同名 `Id_Spawner_*.json`）。

**待修复方向：**
- 在 `search_engine.py` 的匹配逻辑中增加 spawner 类型过滤，确保物品类 spawner 不被匹配到怪物/容器搜索词
- 或建立 spawner 类型白名单（仅怪物/容器/掉落物参与 lootdrops 关联）

### ChestSpecial → 具体宝箱类型概率丢失

`Id_Spawner_New_Props_ChestSpecial`（如 `Firedeep_MiningPassage` 中的 2 个 spawner）是一个**概率生成器**，
其 `SpawnerItemArray` 中包含多种宝箱类型及各自权重：

| 产出宝箱 | spawn_rate |
|---------|-----------|
| OrnateChestLarge | 25% |
| OrnateChestLarge_Locked | 25% |
| SimpleChestLarge | 27% |
| WoodChestLarge | 10% |
| FlatChestLarge | 10% |
| Mimic_* | ~3% |

**当前问题：** 
1. `search_engine.py` 将 `ChestSpecial` 匹配为搜索词 `"ChestSpecial"`，而非 `"OrnateChestLarge"`，导致其坐标不被归入 OrnateChestLarge 的 lootdrops 来源
2. 即使关联上，当前 spawn_rate 缓存以 `m_name` 查 `OrnateChestLarge`，`OrnateChestLarge` 作为 spawner_keyword 的 rate=100 会覆盖 ChestSpecial 中的 25%

**影响：** 概率宝箱坐标存在但不在掉落来源列表中显示，玩家看不到游戏内实际概率。

**待修复方向：**
- 对随机 spawner（如 ChestSpecial、ChestLarge、OrnateChestLargeRandom），应将其子实体的概率分摊到各自对应的 lootdrop 条目上
- spawn_rate 缓存键需要区分 label（实际 spawner）和 entity_name（产出实体），而非用 m_name 统一查 max

### 生成概率查询优化

`get_spawn_rate_for_keyword()` 在 lootdrops 详情导出阶段被逐坐标调用，导致：
- 同一怪物名对 N 个坐标重复查 N 次 `spawner_entries` 表
- 第二个参数 `map_base` 传入但从未使用

**优化方案：** 在 `collector.py` 中预加载所有 `spawner_entries` 到内存 dict（key 为 `spawner_keyword` + `entity_name`，
value 为 `max(spawn_rate)`），坐标循环内直接查内存，消除 N+1。

## 已完成优化

- **路由级代码分割** — `React.lazy()` 拆分 6 个页面（DetailPage、LootdropDetailPage、QuestItemGroupPage、QuestNPCDetailPage、DungeonModuleGroupPage、DungeonModuleDetailPage），主 bundle 84KB → 32KB
- **SSR 数据复用** — DungeonModuleGroupPage 优先使用 `useSSRData()` 预渲染数据，避免客户端重复 fetch
- **无用 JSON 清理** — `entity_index.json`（271KB）、`quest_items.json`（88KB）从交付目录移除（管道内部仍保留）
