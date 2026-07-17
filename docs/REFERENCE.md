# DarkFindV5 技术参考

> 本文档包含数据管道、数据库、地图模块的详细技术规范。
> 日常开发请参考 `CLAUDE.md`。

## 待修复问题

### ~~_8001 变体物品爆率：超级宝藏堆（SuperHoard）缺失~~ [已修复]

**背景**：25 个 Artifact 武器 `_8001` 变体（`LuckGrade=8`）已在 `db_manager.py` 中修复为独立条目。
但"宝藏堆"只显示了普通宝藏（`ID_Lootdrop_Spawn_Treasure`）的掉落，缺少"超级宝藏堆"（SuperHoard）的部分。

**关键差异**：

| 实体 | LootDropId | RateId | LG8 权重 | 含 _8001 |
|------|-----------|--------|---------|---------|
| 宝藏堆（普通） | `ID_Lootdrop_Spawn_Treasure` | `ID_Droprate_Hoard_Treasure*` | 全部为 0 | ✗（最大 LG=7） |
| 超级宝藏堆（SuperHoard） | `ID_Lootdrop_Drop_HoardWeaponArmor` | `ID_Droprate_Hoard_WeaponArmor*` | **部分 >0** | ✓（25 件 _8001） |

**超级宝藏堆中 _8001 的有效 LG8 权重**（rate_id 及对应 dungeon grade）：

| DungeonGrade | RateId | LG8 权重 |
|-------------|--------|---------|
| 3001-3031 | `ID_Droprate_Hoard_WeaponArmor_3xxx` | 5~30 |
| 4002 | `ID_Droprate_Hoard_WeaponArmor_4002` | 30 |
| 4012 | `ID_Droprate_Hoard_WeaponArmor_4012` | 30 |
| 4023 | `ID_Droprate_Hoard_WeaponArmor_4023` | 30 |

**数据来源**：
- `ID_LootDropGroup_SuperHoard.json` — 164 个条目，包含 `ID_Lootdrop_Drop_HoardWeaponArmor`（+ Gems、GoldCoinChest 等）
- `ID_Lootdrop_Drop_HoardWeaponArmor.json` — 1342 个物品，含 25 件 `_8001`（LG=8）
- `ID_Droprate_Hoard_WeaponArmor_*.json` — 41 个 rate 文件

**修复思路**：在 `_compute_drop_rate` 中或 spawner 映射阶段，超级宝藏堆（`Id_Spawner_New_Props_SuperHoard01_9`）的
掉落应使用 `ID_Lootdrop_Drop_HoardWeaponArmor` 及其对应的 `ID_Droprate_Hoard_WeaponArmor_*` 率值计算，而非普通宝藏堆的率值。

> **状态：已修复**（2026-06-21：参见 `docs/SUPERHOARD_FIX.md`）

### ~~零爆率过滤时分组标题残留~~ [已修复]

**背景**：详情页（`DetailPage.tsx`）的"隐藏0爆率坐标"功能只过滤了单个坐标点的显示，
分组标题始终渲染，导致选模式后组内全部坐标被隐藏时标题依然可见。

**修复**（2026-07-14）：将 `visibleSections` 预过滤改为 `sections.map` 内联判断。
每个 section 用与渲染 items **完全相同的 `labelMatch` + `gdi` + `modeFilter`** 检查是否有可见坐标，
无则 `return null`，标题和坐标一起隐藏。

**关键文件**：`web/src/pages/DetailPage.tsx`

## 数据管道

### DB 过期判断时序

`collector.py` 的 `run()` 中，`_is_db_stale()` 必须在 `DatabaseManager()` 构造**之前**调用，
否则 `sqlite3.connect()` 会先创建空 DB 文件，导致 mtime 为"现在"，过期判断始终返回 False，导入步骤被跳过。

**修复前**需要手动 `touch Game.json` 才能触发重建。**修复后**直接 `rm db && python main.py` 即可。

### 部署测试

**部署测试** = 删除 DB 文件后按完整流程部署：`rm api/data/darkfindv5.db && ./deploy.sh`（或单独 `python main.py && npm run build`）。确保管道从零开始重建全部数据。

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

**父级旋转：** 累加坐标时必须考虑父级的 `RelativeRotation.Yaw`。子组件的 `RelativeLocation` 在父级的局部坐标系中，
需要先按父级的累计 Yaw 旋转后再累加到世界坐标。`_resolve_world_loc()` 从根节点向叶节点遍历，逐级旋转累加：
```
world_x += local_x * cos(parent_yaw) - local_y * sin(parent_yaw)
world_y += local_x * sin(parent_yaw) + local_y * cos(parent_yaw)
```

**影响范围：** 约 16.5% 的 spawner（~1980 个）有父级变换，分布在 ~144 个地图文件中。
典型场景：`GameObjectLinker`、`SingleGameSpawnerGroup` 等分组容器下的 spawner。

### 互斥刷新组（BP_GameSpawnerGroup_C）

游戏内部分 spawner 配置为**多选一**随机刷新（4 个黄金宝箱中仅 1 个实际生成）。该关系通过 `BP_GameSpawnerGroup_C` 类型 actor 表达：所有属于同一组的 `BP_GameSpawner_C` 的 `SphereComponent` 都 attach 到该组 actor 的 `DefaultSceneRoot`。

**检测时机：** `search_engine.py:extract_spawners()` 解析地图 JSON 时实时检测。

**检测流程：**
1. 第一遍遍历收集所有 `BP_GameSpawnerGroup_C` 的 `RootComponent.ObjectPath` → 组名映射
2. `_resolve_world_loc()` 沿 AttachParent 链向上遍历时，检查当前节点是否在组映射中
3. 命中则设置 spawner 的 `group_parent` 字段（如 `BP_GameSpawnerGroup_C_2`）
4. 该字段随 spawner 存入 DB `spawners.group_parent` 列

**数据产出：**
- `mutually_exclusive_groups` DB 表：`(map_base, json_filename, group_name, search_term, spawner_count)`
- `dungeon_modules_coords/*.json`：实体级 `mutually_exclusive: true` 标志，前端图例显示 `(N选1)`
- 单个 spawner 不做互斥标记（至少 2 个同 keyword spawner 共享同一组时才启用）

**覆盖范围：** 约 800 个互斥组，覆盖黄金宝箱、怪物、陷阱、神坛等。

### 坐标分类名称获取优先级

坐标点的显示名称（即 `label` / `search_term`）决定了它在哪个实体页面下显示、以及使用哪个翻译键（`Name.Key`）渲染中文名。获取优先级如下：

1. **PreviewData（最高优先级）** — 地图 JSON 中 `BP_GameSpawner_C` 的 `Properties.PreviewData.AssetPathName` 字段直接指向被生成的实体（如 `.../Id_Props_FlatChestLarge`）。通过 `_preview_entity_name()` 提取实体名（如 `FlatChestLarge`），这是最精准的来源，因为同一 spawner 名称可能对应随机生成器（如 `ChestSpecial` 可产出 6 种宝箱），但 PreviewData 在每个坐标点上已锁定为具体实体。

2. **Spawner 关键词** — 从 `SpawnerDataAsset.ObjectName` 经 `strip_id_prefix()` 提取（如 `OrnateChestLarge`），用于 Aho-Corasick 关键词匹配。对非随机 spawner（单条目），该值通常与 PreviewData 实体名一致；对随机 spawner，仅在展开后（`multi_entity_spawners` 映射）以实体名为准。

3. **翻译键获取** — 通过实体名（如上一步确定的 `FlatChestLarge`）查找 `Id_Props_FlatChestLarge.json`（Props/Items/Monsters 目录），读取 `Properties.Name.Key`（如 `Text_DesignData_Props_Props_FlatChestLarge`），作为 `translation_key` 存入 DB 实体表。

**实现位置：**
- PreviewData 提取：`search_engine.py:_preview_entity_name()`（约 L236）
- 实体名匹配：`search_engine.py:build_matches()`（约 L576~L579，同时匹配 preview_name 和 keyword）
- 翻译键入库：`db_manager.py:import_props()` / `import_items()` / `import_monsters()`
- 分类映射：`db_manager.py:get_entity_classification()`（约 L839~L856，汇总三张实体表）

### 实体分类

`collector.py` 的 `run()` 通过 `db.get_entity_classification()` 从 DB 实体表直接构建分类映射，
返回 `dict[str, dict]`（entity_name → {types, translation_key}）。替代了旧版 `_build_entity_classification()`
逐文件扫描 ~3,249 个 JSON 的方式。

### Spawner 导入架构

Spawner 的插入逻辑直接在 `collector.py` 的 `run()` 中内联执行，
使用 `executemany` 批量插入（~32,000+ spawner 行）。
通过 `db.connect()` 获取原始 sqlite3.Connection 操作，而非通过 `db_manager.py` 的封装方法。

## 数据库

### 地图 ModuleType 缺失

部分 dungeon module JSON 的 `ModuleType` 为空，分组推断策略（`db_manager.py` 的 `import_dungeon_modules`）：

1. **sl_base 反查** — 从 SubLevelAsset 提取地图名，在已加载模块字典中查找其 ModuleType
2. **前缀推断（兜底）** — 从模块名前缀判断

**已推断示例：** Shipgraveyard_UnderSeaCave_02 → sl_base Shipgraveyard_TwinChamber → 反查到 ShipGraveyard

**~~剩余 19 个通用跨区域模块（无分组）~~** — 已临时解决（2026-06-19）：

这 19 个通用模块名（如 `AltarRoomAB_Center`、`Armory_Center`）实际未被使用：
- 无对应 JSON 文件（无 `ModuleType`）
- 无对应地图文件在目录结构中
- `db_manager.py:688` 清理无分组模块时被删除
- 数据库中仅存 `DarkRitualRoom_04`（属 Inferno 分组，有 39 条 spawner）

实际使用的是带区域前缀的版本（如 `Crypt_AltarRoomAB`、`Ruins_Armory`、`DeathHall` 等），均已有分组。

| 通用模块名 | 实际使用的区域版本 | 分组 |
|---|---|---|
| AltarRoomAB_Center | Crypt_AltarRoomAB | Crypt |
| Armory_Center | Armory, Ruins_Armory | Crypt, Ruins |
| Connector_Half_01~04 | (无对应版本) | — |
| CorridorofDarkPriests_Center | (无对应版本) | — |
| DarkMagicLibrary | DarkMagicLibrary_Center | Crypt |
| DarkRitualRoom_01~03 | Crypt_DarkRitualRoom_01 | Crypt |
| DarkRitualRoom_04 | DarkRitualRoom_04 | Inferno |
| DeathHall_Center | DeathHall | Crypt |
| GuardPost_Center | GuardPost, IceCave_Guardpost | Crypt, IceCavern |
| MimicRoom_Center | MimicRoom | Crypt |
| MummyRoom | (无对应版本) | — |
| PassingRoad_03 | (无对应版本) | — |
| Sewers_Center | Sewers | Crypt |
| Tomb | Tomb_Center, Cave_Tomb_Center, OldTomb | Crypt, GoblinCave |

### 地图图片匹配

`module_builder.py` 中 `_resolve_img()` 返回三态：

- `found` — Art 目录存在且找到匹配（含大小写/tail/数值后缀处理）
- `not_found` — Art 目录存在但无匹配 → 尝试 module_name
- `no_art` — 无 Art 目录（如 ShipGraveyard）→ sl_base_name 作为最终答案

**图片名优先级链：** SubLevelAsset(sl_base) → Module name → MapImage
**占位图跳过：** `RareModule_1x1` 和 `UnderConstruction_1x1` 在匹配链中被跳过，仅作前端最终兜底。

### Lootdrop 怪物名合并

`_Hard`/`_VeryHard`/`_Unique` 后缀变体在 lootdrop 解析阶段合入基础怪物名，避免重复掉落条目。

### 怪物变体翻译键合并

怪物列表中 `Abomination_Common` / `Abomination_Elite` / `Abomination_Nightmare` 等质量后缀变体通过**翻译键**合并，而非硬编码后缀剥离。

**合并机制（`entity_export.py` 怪物导出段）：**
1. 对每个怪物实体调用 `resolve_name(monster_name, translation_key, "monster")` 解析翻译
2. 按解析后的翻译文本分组。若翻译失败（返回原始名）且怪物名含质量后缀（`_Common`/`_Elite`/`_Nightmare`/`_Unique`），则剥离后缀后取基础条目的翻译作为分组键
3. 每组中优先使用 `translation_key` 非空的条目作为规范名（基础怪物）
4. 合并组内所有变体的坐标，去重后输出

**兜底原因：** `resolve_name()` 内部的后缀剥离链（`_RESOLVE_FUZZY_RE` → `_RESOLVE_FUZZY_PASS2_RE` → `_RESOLVE_STRIP_RE`）不覆盖 `_Common` 后缀，且部分变体（如 `FromFakeDeath` 系列）的翻译键不含后缀名，导致翻译查找失败。兜底逻辑确保这些变体也能正确归入基础怪物的分组。

**例外：** `_Unique` 后缀的独立命名怪（如 "幽暗愚者" ≠ "冰霜鬼童"、"狂牙" ≠ "冰霜狼"）有各自的中文翻译键，翻译成功，不触发兜底，独立保留。

**覆盖范围：** `_Common`、`_Elite`、`_Nightmare`、`_Unique` 后缀变体，以及任何共享翻译键的怪物（如 `DeathSkull_Summoned` 等特殊实体独立保留，因为其翻译键不同）。

**排除说明：** `entity_index.json` 未被前端使用（管道内部中间产物，被 `skip_deliver` 排除），无需合并。items 表无质量后缀变体（0 条记录），无需处理。

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

> **精度要求：** 所有生成概率和爆率的计算必须使用 `decimal.Decimal`，最终输出四舍五入到小数点后 4 位（`quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)`）。已在 `drop_rate._round_rate` 中实现，`enrichment.py` 等调用方统一使用此函数。

物品掉落涉及两层概率：**生成概率**（Spawner 是否出现）和**物品爆率**（出现后掉落什么）。

#### 生成概率（SpawnRate）

坐标点数据中关联的 `SpawnerDataAsset`（如 `Id_Spawner_New_Props_GoldChest`）对应
`Spawner/Spawner/Id_Spawner_New_Props_GoldChest.json`，其中 `SpawnRate` 字段为原始生成权重。

**DB 存储格式：** `spawner_entries.spawn_rate` 存储为百分比（0~100），按同 `SpawnerItemArray` 内的比例计算，四舍五入到小数点后 4 位（使用 `drop_rate._round_rate`）：
`_round_rate(100 * entry_rate / sum(all_rates_in_array))`

- 单条目 spawner：`SpawnRate=10000` → 100%
- 多条目 spawner（如 ChestLarge 含 9 个实体）：各条目按权重占比计算百分比
- 原始 `SpawnRate` 以 `10000` 为基准，`2500` = 25%（单条目时），`0` = 不生成

**实现位置：** `db_manager.py` 的 `import_spawner_entries()` 在导入时计算百分比并写入 `spawner_entries.spawn_rate`，`drop_rate.py` 的 `DropRateEngine.preload()` 预加载到内存供 O(1) 查询。

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

### 爆率显示实现 [已完成]

> **状态：** 生成概率（spawn_rate）和物品爆率（drop_rates）均已完成并通过预加载优化。

Lootdrop 详情页地图模块卡片图例显示格式：`黄金宝箱100%([PVE:25%][普通25%][豪客赛25%])`。

**DB 表结构（4 张表，已在 `db_manager.py` 中实现）：**

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `spawner_entries` | Spawner 条目（生成概率 + LootDropGroupId） | `spawner_keyword`, `entity_name`, `spawn_rate`, `lootdrop_group_id` |
| `lootdrop_groups` | LootDropGroup → LootDrop + Rate 映射 | `group_id`, `dungeon_grade`, `lootdrop_id`, `lootdrop_rate_id` |
| `lootdrop_rate_items` | LootDrop 中的物品列表 | `lootdrop_id`, `item_name`, `luck_grade`, `drop_count` |
| `lootdrop_rate_weights` | 各 LuckGrade 的权重 | `rate_id`, `luck_grade`, `weight` |

> **变体锁定说明：** 物品有 `_\d{4}` 变体后缀时（如 `Mitre_1001`–`Mitre_7001`），`item_name`
> 保留变体后缀，按 (lootdrop_id, base_name) 去重，优先级 `_5001 > _4001 > _3001`。
> 无以上变体时保留后缀最靠前的条目。`_compute_drop_rate()` 先用基础名查找，
> 未命中则依次尝试 `_5001` / `_4001` / `_3001` 后缀。

**多变体爆率展示：**

`variant_count > 1` 的物品/道具需在详情页展示所有有爆率的变体，各变体爆率之和 = 100%。

**变体查找链路：**
1. `spawner_entries` → `entity_name` → `lootdrop_group_id`（精确匹配，不加 `_HR` 后缀）
2. 游戏 JSON `LOOTDROP_DIR/ID_Lootdrop_Spawn_{name}.json` → `LootDropItemArray` 包含所有变体
3. 用基础名在 `_lootdrop_variants` 中倒查所有变体名 + `LuckGrade`

**爆率计算公式：**

变体爆率 = `weight[lg] / _ld_rate_totals[rate_id]`，其中 `_ld_rate_totals` 是该 rate_id 下所有非零权重之和。

等价于直接读游戏 JSON：
```
rate_file = LootDropRate/{lootdrop_rate_id}.json   # 来自 lootdrop_groups 表
DropRate = LootDropRateItemArray[luck_grade].DropRate
Total = sum(所有 DropRate)
变体爆率 = DropRate / Total
```

示例（Lifeleaf，`ID_Droprate_Herbs` 系列）：

| 变体 | lg | PVE (1023) | 普通 (2023) | 豪客赛 (3023) |
|------|----|-----------|------------|-------------|
| 普通 | 2  | 60%       | 50%        | 25%         |
| 优秀 | 3  | 35%       | 40%        | 55%         |
| 罕见 | 4  | 5%        | 10%        | 20%         |
| 合计 | —  | 100%      | 100%       | 100%        |

**注意事项：**
- 同一 `lootdrop_group` 在不同 `dungeon_grade` 下有不同 `lootdrop_rate_id`（如 `ID_Droprate_Herbs_1023` vs `ID_Droprate_Herbs_2023`），需按 grade 匹配
- 同一变体可能出现在多个 lootdrop 文件中（如 Lifeleaf_2001 同时在 `ID_Lootdrop_Spawn_Lifeleaf` 和 `ID_Lootdrop_Drop_Herbs`），需用 spawner 的 `lootdrop_group_id` 精确匹配，不加 `_HR` 后缀
- 变体聚合用 `_new_gdi` 替换基础条目（而非追加），确保各变体爆率之和 = 100%
- 默认变体（无后缀）如无爆率数据则不显示

**计算逻辑：**

`drop_rate.py` 的 `DropRateEngine.preload()` 在 lootdrop 详情导出前预加载全部爆率数据到内存：

| 内存 dict | 来源表 | 用途 |
|-----------|--------|------|
| `_spawner_ldg` | `spawner_entries` | spawner_keyword / entity_name → lootdrop_group_id |
| `_ld_groups` | `lootdrop_groups` | group_id → {dungeon_grade: [(lootdrop_id, rate_id, count)]} |
| `_ld_rate_items` + `_ld_luck_grade_count` | `lootdrop_rate_items` | lootdrop_id → {item_name: (luck_grade, count)}，含同 luck_grade 物品数统计 |
| `_ld_rate_weights` | `lootdrop_rate_weights` | rate_id → {luck_grade: total_weight} |
| `_ld_rate_totals` | 从 `_ld_rate_weights` 计算 | rate_id → 该 rate_id 下所有非零权重之和（用于归一化爆率） |

计算函数（`drop_rate.py` 的 `DropRateEngine` 方法）：
1. `compute_drop_rate(ldg_id, item_name, full_grade)` — 纯内存计算某物品在指定组+等级下的爆率（0~1），支持变体后缀回退
2. `get_group_drop_rates(item_name, monster_name, group_key)` — 遍历 PVE/普通/豪客赛三种模式，返回各模式最佳爆率
3. `compute_group_drop_rates(ldg_id, group_key)` — 计算某 lootdrop group 在某地图分组下所有物品的聚合爆率（用于怪物/道具基础条目）
4. `compute_variant_rate(ldg_id, luck_grade, full_grade, target_ld_id)` — 计算指定 luck_grade 变体的爆率（用于多变体聚合），通过 `target_ld_id` 限定只计算特定 lootdrop

> `lootdrop_rates.py` 的 `get_drop_rates_for_item_with_coords()` 已被上述内联逻辑替代，不再使用。

**前端显示（`LootdropDetailPage.tsx`）：**
- `spawn_rate` 字段从 coord 级别取（仅 ≠100 时显示）— **已生效**
- `drop_rates` 字段从 monster 级别取（`Record<string, number>`，key 为模式名）— **已生效**
- **per-coord score filter**：`score = spawn_rate × 豪客赛爆率 / 100`，`score < 0.5` 的坐标在导出阶段被过滤（`lootdrop_builder.py`）
- **分类按钮**：掉落详情页顶部的一组彩色按钮，包含"全部显示/隐藏全部"切换按钮和各怪物切换按钮
  - **max_score**：后管在 `lootdrop_builder.py` 中预计算 `max_score = max(spawn_rate × 豪客赛爆率 / 100)`，写入每个怪物条目，前端直接读取
  - **排序**：所有怪物按钮按 `max_score` 降序排列（`max_score=-1` 表示无爆率数据，排最后）
  - **默认隐藏**：`max_score < threshold`（默认 1.0）的怪物初始隐藏，在标题显示 `(+N)` 标记；`max_score` 为 null 或 < 0 的怪物始终可见
  - **交互**：点击单个按钮切换该怪物地图坐标的显隐；点击"全部显示"恢复全部可见，"隐藏全部"隐藏所有怪物
  - **阈值调节**：开启调试模式后，可通过滑块实时调整 threshold 值（0~10，步长 0.1）
  - **默认变体**：当怪物同时存在 `_Common`/`_Elite`/`_Nightmare` 等多个质量变体时，默认显示 **Elite 变体**的爆率（即 Elite 按钮初始为可见，Common/Nightmare 受 threshold 控制）

**地图模块排序规则（`LootdropDetailPage.tsx` `computeModuleScore`）：**

每个模块的排序分 = 所有坐标点的贡献之和，计算方式：

1. **regular 点**（`variant_count` 为空或 ≤1）：每个点贡献该怪物在此分组的 `baseScore`
   - `baseScore = spawn_rate × 豪客赛 / 100`（来自 `group_drop_info`，如骷髅法师 sr=100 dr=25 → 25）
2. **variant 点**（`variant_count > 1`）：按 `group_parent` 分组，每组代表 1 个有效刷怪位。每组贡献 1 份 `baseScore`（不论组内有多少个坐标点）
   - 例：CorridorofDarkPriests 有 6 个 variant 点（2 组各 3 点），共 2 个分组 → 贡献 2 × 25 = 50
   - 显示标签 `(6点选2)`：6 个坐标点分布在 2 个 variant group，共 2 个有效刷怪位
3. **分数相等时**：无 variant 点的模块排在前面（regular 优先）

**坐标 variant 标签显示规则（`LootdropDetailPage.tsx` `mDots` 渲染逻辑）：**

地图模块卡片下的坐标统计标签格式如下：

- **regular 点**（无 `group_parent` 或 `variant_count ≤ 1`）：`(N点)`
- **variant 点**（`variant_count > 1`，有 `group_parent`）：
  - 单实体多位置（`variant_names` 为空）：`(N点选M)` — M = 该地图上该实体的互斥组数（`group_parent` 去重）
  - 多实体组（`variant_names` 有值）：`(A、BN种选M)` — A/B 为实体名，N 为实体种数，M 为组数

**数据来源（`coordinates.py:get_variant_counts()`）：**
- Query 1（多实体组，`COUNT(DISTINCT original_keyword) > 1`）：`variant_count` = 实体种数，`variant_names` = 实体名列表
- Query 2（单实体多位置，`COUNT(DISTINCT original_keyword) = 1`）：`variant_count` = `COUNT(*)`（组内 spawner 总数），`variant_names` = 空

**group_parent 传递链路：**
1. `search_engine.py` 提取地图 JSON 时检测 `BP_GameSpawnerGroup_C` → 写入 `spawners.group_parent`
2. `coordinates.py` 的 `get_variant_counts()` 按 `(map_base, json_filename, group_parent)` 分组统计
3. `lootdrop_builder.py` / `translator.py:build_coord_out()` 将 `group_parent` 写入坐标 JSON
4. 前端 `LootdropDetailPage.tsx` 用 `group_parent` 去重计算组数 M；`DetailPage.tsx` 用 `variant_count > 1` 触发 `(N点选1)`

排序链：得分降序 → 有 variant 标记 → 坐标点数降序 → size_y 升序 → size_x 升序

**已修改文件清单：**
- `api/src/config.py` — `LOOTDROP_RATE_DIR`、`DUNGEON_GROUP_GRADES`（8组）、`MODULE_GROUP_FLOOR_SUFFIXES`
- `api/src/db_manager.py` — 4 张表 + 导入/查询方法
- `api/src/drop_rate.py` — `DropRateEngine` 类（爆率预加载 + 计算方法）
- `api/src/lootdrop_builder.py` — lootdrop 索引 + 详情文件生成 + per-coord score filter + max_score 预计算
- `api/src/enrichment.py` — group_drop_info 注入 items/monsters/props + 零爆率清理
- `api/src/collector.py` — 管道协调器（DB 导入 + 模块编排）
- `web/src/pages/LootdropDetailPage.tsx` — 接口扩展 + 图例显示 + 分类按钮 + 阈值滑块

**掉落表列表页分组（`ListPage.tsx`）：**

| 分组 | 图标 | 判定条件 | 数量 |
|------|------|---------|------|
| 武器装备 | ⚔️ | `variant_count` ∈ {7, 8} | 251 |
| 饰品 | 💍 | `variant_count` = 5 | 19 |
| 神器 | 🏺 | 名称以 `_8001` 结尾（独立变体） | 25 |
| 稀有掉落 | ✨ | `variant_count` ∉ {5, 7, 8} 且 `max_score` < 2.5 | 19 |
| 物品 | 📦 | `variant_count` ∉ {5, 7, 8} 且 `max_score` ≥ 2.5 | 163 |

**`_8001` 变体拆分：**
8 变体物品（`_1001`~`_8001`）的最后一个 `_8001` 变体独立成条目，不参与变体合并。
- 基名 `variant_count` 降为 7，归类 武器装备
- `_8001` 自有独立翻译和爆率，归类 **神器**

**阈值计算：**
- `max_score` = `max(spawn_rate × 豪客赛爆率 / 100)`，取该物品所有怪物中的最大值
- 例：怪物生成概率 90%，该物品的豪客赛爆率 10%，则 `max_score = 90 × 10 / 100 = 9.0`
- 分组显示顺序：稀有掉落 → 物品 → 饰品 → 武器装备

### 旋转值

从 Layout JSON 文件计算，优先级：`module_name` → `sl_base_name`，默认 1（90°）。

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
| 物品/怪物/实体/掉落 `/:page` | `"list-{page}"` | 见下文"SSR 数据源统一" | SSR 存在即跳过 |
| 任务探索 `/explore` | `"explore"` | `explore.json` | SSR 存在即跳过 |
| 任务物品 `/quest_items` | `"quest_items"` | `quest_items_groups.json` | SSR 存在即跳过 |
| 任务物品分组 `/quest_items/:group` | `"quest_items_groups/{group}"` | `quest_items_groups/{group}.json` | SSR 有 entities 时跳过 |
| 任务NPC `/quest_npc` | `"quest_npc"` | `quest_npc.json` | SSR 存在即跳过 |
| 地图模块 `/dungeon_modules` | 无 | `useDungeonModules()` hook | 始终客户端 fetch |
| 地图模块分组 `/dungeon_modules/:group` | `"dungeon_modules/{group}"` | `useDungeonModules()` hook（filter） | 优先 SSR，否则回退 hook |

### SSR 数据源统一（列表页）

列表页的 SSR 数据统一使用 `search_index.json`（按 `page` 字段过滤），而非独立的 `{page}.json`。

**原因（历史问题）：** 列表页有两个数据源——SSR 注入用 `{page}.json`、客户端运行时后备用 `search_index.json`。字段需同步维护，新增字段（如 `hr100`）容易只改一处，导致客户端导航（非 F5）到列表页时缺少该字段。

**修复：** `ssg.mjs` 中列表页 SSR 数据改为从 `search_index.json` 过滤提取。`search_index.json` 成为列表页的单一数据源，同时服务于搜索和列表渲染。

**为什么详情页没有此问题：** 详情页的 SSR 数据和客户端 fetch 指向同一个文件（`{page}/{name}.json`），不存在两套数据源，因此不会出现字段不一致。

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

### 详情页模块数据获取

items/monsters/props/lootdrops 的详情页通过 `useDungeonModules()` hook 获取模块数据（包括翻译、分组、旋转/偏移/尺寸等）。每个坐标点的 `c.map` 字段存储模块名称，详情页用 `globalModules.get(c.map)` 在共享 Map 中查找对应模块信息。

为了保证模块数据在详情页渲染前就绪，设计了两层预加载：

1. **`AppInner.tsx:30` 主动预取** — `useDungeonModules()` 在顶层路由组件中调用，在所有详情页挂载之前就开始加载 `dungeon_modules.json`
2. **`<link rel="preload">`** — Vite 构建时注入版本化 preload tag（`/data/{shortVer}/json/dungeon_modules.json`），让浏览器在解析 HTML 后立即开始下载

**版本化 preload URL：** preload 路径中的 `{shortVer}` 是 `dataDate` 的 base36 编码（如 `ti9oey`），每次数据更新时自动变化。使用版本化路径的原因：
- 与客户端的 fetch URL 一致（`useDungeonModules.ts` 使用相同版本化路径）
- 避免浏览器缓存旧版本数据
- 与 CDN 缓存破坏策略配合（`ssg.mjs` 构建时将 `data/json/` 复制到 `dist/data/{shortVer}/json/`）

**防重复请求：** hooks 内置模块级缓存（`cachedModules`/`cachedIndex` + `cachedPromise` + `cachedVersion`），同名 Map 引用始终共享，不产生重复请求。`dataVersion` 为空时跳过 fetch，等待 `meta.json` 版本信息到达后再发起请求。

### 共享 Hook

- `useDungeonModules()` — 全局缓存 `dungeon_modules.json`，所有页面（详情页、地图模块列表/分组/详情页、探索页）复用同一份模块 Map。URL 使用版本化路径 `/data/{dataVersion}/json/dungeon_modules.json`。
- `useSearchIndex()` / `getPageEntries()` — 全局缓存 `search_index.json`，供 NavBar 搜索使用，同时也是列表页客户端的**主数据源**（列表页 SSR 数据也来自同一文件）。`{page}.json` 仅作为客户端取数失败时的最终回退

### search_term_matches 精确度问题 [已被 AC 自动机移除替代]

> **状态：已过期** — 该修复基于 AC 自动机 `match_keyword()` 的 re-match 补丁，已被后续的 AC 自动机整体移除（2025-06-19，变体后缀剥离 + `extract_all_spawners()` 直接匹配）彻底替代。AC 移除后子串前缀匹配不再存在，详见下方章节。

**历史问题：** `search_engine.py` 的 `match_keyword()` 会将 `FrostWyvernEgg`（物品）也匹配到
搜索词 `FrostWyvern`（怪物），因为 `FrostWyvern` 是 `FrostWyvernEgg` 的前缀子串。
同样 `Banshee_Soulflame`（props）会被匹配到 `Banshee`（怪物）。

**当时的修复方案：** 在 re-match 步中构建 `search_term → entity_type` 映射，
当短词和长词属于不同实体类型时丢弃短词。

**修复效果：** `Banshee_Soulflame` 坐标不再出现在 `Banshee` 怪物页面，
`FrostWyvernEgg` 坐标不再出现在 `FrostWyvern` 怪物页面。

### 坐标按 Spawner 类型拆分（label-type split）

同一实体（如 `OrnateChestLarge`）可能从多种 spawner keyword 生成（`ChestSpecial`、`OrnateChestLargeRandom`、`OrnateChestLarge_UnderSea`）。为了在前端区分这些不同的生成来源，`lootdrop_builder.py` 按 `original_keyword` 的语义类型拆分坐标：

| 类型 | 识别规则 | 翻译后缀 | 示例 |
|------|---------|---------|------|
| `direct` | label == entity_name 或 label.startswith(entity_name + "_") | 无 | `OrnateChestLarge_UnderSea` → `狮头宝箱` |
| `special` | label 含 "Special" 或 "ChestLarge" | `(特殊)` | `ChestSpecial` → `狮头宝箱(特殊)` |
| `random` | label 含 "Random" | `(随机)` | `OrnateChestLargeRandom` → `狮头宝箱(随机)` |
| `other` | 以上都不匹配 | 无 | `GoldChest__UnderSea`(对 entity `GoldChest_UnderSea`) → `黄金宝箱` |

**实现位置：** `lootdrop_builder.py` 的 `_classify_label()` 函数和标签循环。

**合并规则：** 相同 `m_trans + 类型后缀` 的实体合并到同一 merged 条目。例如 `OrnateChestLarge` 和 `OrnateChestLarge_UnderSea` 的 `ChestSpecial_UnderSea` 坐标都归类为 `special`，合并到 `狮头宝箱(特殊)`。

**group_drop_rates 查询注意：** 对非 direct 类型，`_get_group_drop_rates()` 必须使用 `entity_name`（如 `OrnateChestLarge`）而非 `name`（如 `OrnateChestLarge_special`）作为查询键，否则无法找到对应 lootdrop_group_id → `_hk_lookup` 为空 → score=0 → 全部被过滤。（2025-06-18 修复）

**影响范围：** 随机生成器类 spawner（ChestSpecial、ChestLarge、ChestSpecial_UnderSea、ChestLarge_UnderSea 等），以及含 Random 关键词的 spawner。使得狮头宝箱能拆分为 direct/special/random 三个独立条目。

### 生成概率查询优化

`get_spawn_rate_for_keyword()` 在 lootdrops 详情导出阶段被逐坐标调用，导致：
- 同一怪物名对 N 个坐标重复查 N 次 `spawner_entries` 表
- 第二个参数 `map_base` 传入但从未使用

**优化方案：** 在 `drop_rate.py` 的 `DropRateEngine.preload()` 中预加载所有 `spawner_entries` 到内存 dict（key 为 `spawner_keyword` + `entity_name`，
value 为 `max(spawn_rate)`），坐标循环内直接查内存，消除 N+1。

### Lock merge 与 spawn_rate 覆写修复 [2025-06-18]

当 merged 条目同时包含锁定（`_Locked`）和非锁定变体的坐标时，lock merge 负责：
1. 翻译添加 `(可能上锁)` 后缀
2. 按 `(x, y, z, file)` 去重
3. ~~将全部坐标的 `spawn_rate` 覆写为 `_combined_rate`（如 25+25=50）~~ ← **已删除**

**原 bug：** `_combined_rate` 被应用到条目内所有坐标，即使坐标来自非锁定实体/其他 keyword 对（如 `ChestLarge_UnderSea` 的 3.68%），导致显示概率虚高。

**修复：** 删除 `_c["spawn_rate"] = _combined_rate` 行，每个坐标保留其原始 `spawn_rate`（来自 `spawner_entries`）。去重仅移除同一位置的重复坐标，不改变概率。

**效果：** 狮头宝箱(特殊) 的 spawn_rate 从 50% 恢复为 25%（ChestSpecial）和 15%（ChestSpecial_UnderSea）。

## 已完成优化

- **vendor 分包** — `vite.config.ts` 的 `manualChunks` 将 antd 和 react 相关依赖拆分为独立 chunk，减少主 bundle 体积
- **SSR 数据复用** — DungeonModuleGroupPage 优先使用 `useSSRData()` 预渲染数据，避免客户端重复 fetch
- **无用 JSON 清理** — `entity_index.json`（271KB）、`quest_items.json`（88KB）从交付目录移除（管道内部仍保留）

## 已完成：Spawner 变体合并 & AC 自动机移除

> **状态：已完成**（2025-06-19）

在 `load_all_spawner_data()` 和 `extract_spawners()` 中对 entity_name 应用变体后缀剥离，使 spawner keyword 直接等于基准实体名，无需 AC 自动机子串匹配。

**剥离规则（`strip_variant_suffixes()` 函数，`search_engine.py:13`）：**
| 模式 | 说明 |
|------|------|
| `_(Common\|Elite\|Nightmare\|Unique)$` | 质量变体 |
| `_(Hard\|VeryHard)$` | 难度变体 |
| `_\d{4}$` | 编号变体（如物品 `Mitre_5001`） |

**改动内容：**
- `search_engine.py`：新增 `strip_variant_suffixes()`，删除 `build_automaton()`/`match_keyword()`/`build_all_matches()`；新增 `extract_all_spawners()` 替代匹配逻辑
- `collector.py`：spawner 存储直接以 variant-stripped keyword 入库
- `db_manager.py`：删除 `search_term_matches` 表定义，删除 `get_spawner_matches()`，`get_all_coordinates()` 改为直接查 spawners 表按 keyword 分组
- `.github/workflows/deploy.yml`：删除 `pip install pyahocorasick`

**搜索索引**：由 `api/src/index_export.py` 在数据管道中直接生成 `search_index.json`，无 AC 自动机依赖。

**影响数据：**
- spawner 行数 ~61,359（72 个多实体展开器正确展开）
- 实体数：items=92, monsters=138, props=247, lootdrops=452（数据截至 2025-06-19，AC 自动机移除时）
- 怪物数减少（~143→138）因 AC 前缀假阳性匹配的坐标不再错误归入；正确坐标不变
