# 生成概率未校验楼层登记 Bug

## 问题描述

网站为某个「地图分组 × 怪物来源」展示的**生成概率**，在**该怪物 spawner 并未登记对应楼层 grade** 时，仍然沿用了同模式下其它楼层登记的生成率。即：**生成概率没有对应的楼层登记，却也被赋予一样的生成率**，导致页面显示游戏里本不该存在的刷怪概率。

## 具体案例：SoulDevotedFolio / FlameButterfly

- 页面：`/lootdrops/SoulDevotedFolio/`，来源怪物 `FlameButterfly`，显示分组 FireDeep，普通模式生成概率 **0.05%**。
- 怪物坐标全部落在 `Firedeep_*` 地图模块（`Firedeep_Emberflow` 等），`map_base → module_group = FireDeep`。
- 游戏数据 `Id_Dungeon_FloorRule_Firedeep.json` 明确该下本 `DefaultDungeonGrade: 2002`（普通·哥布林基准·2层）。
- 但 `Id_Spawner_Monster_FlameButterfly.json` 的 SpawnerItemArray 中，带 `LootDropGroupId` 的怪物 spawn 登记等级白名单**不包含 2002**：

| spawn_rate | dungeon_grades（白名单） |
|---|---|
| 0.01 | `[0, 1001, 1011, 1012, 1021, 1022, 1023, 1031, 4001, 4011, 4012, 4021, 4022, 4023, 4031]` |
| 0.05 | `[2001, 2011, 2012, 2021, 2022, 2023, 2031, 3001, 3002, 3011, 3012, 3021, 3022, 3023, 3031]` |

→ 普通模式登记的楼层后缀为 `{1, 11, 12, 21, 22, 23, 31}`，**唯独没有 suffix=2（FireDeep/2002）**。按游戏自身逻辑，在 2002 下本中该 spawn 不生效，生成概率应为 **0**。

## 数据链路与根因

1. **原始文件**（数据源）：`Id_Spawner_Monster_FlameButterfly.json`，`SpawnRate=5`、同池 `9995` → `5/10000 = 0.05%`。
2. **落库**：`api/src/db/importers/spawners.py:110-149` 按「(keyword, entity, spawn_rate, dungeon_grades)」写入 `spawner_entries`，`spawn_rate` 与 `dungeon_grades` 白名单分离存储。
3. **按模式聚合**：`api/src/drop_rate.py:238-275` 遍历 `spawner_entries`，只取 grade 千位判定模式（`2001 → mode 2 = 普通`），`_spawn_rate_by_mode`/`_spawn_rate_detail` **不看楼层后缀**。
4. **写入分组 JSON**：`api/src/lootdrop_builder.py:798-839` 用坐标的 `map_base → group(FireDeep)` 挂上该 `spawn_rate=0.05`。
5. **显示**：前端 `ReferenceDropRates.tsx` 渲染 `group_drop_info[FireDeep].spawn_rate`。

**根因**：生成概率走「按模式聚合、与楼层无关」的缓存；而坐标归属用「map_base → 模块组 → FireDeep」，两者之间**缺少用 spawner 的 `dungeon_grades` 白名单对该分组对应楼层（FireDeep→2002）做二次校验**。坐标摆放在该地图里，但该地图对应楼层的 spawn 登记缺失时，网站仍沿用其它楼层同模式的值。

> 注：爆率（100%）是**正确**的——`lootdrop_groups` 对 2002 登记了 `ID_Lootdrop_Quest_FlameButterfly → ID_Droprate_UniqueMonsterDrop`（luck_grade=5 → 10000/10000）。爆率按 grade 查表，生成概率按模式聚合，两者来源不同，本 Bug 只影响生成概率列。

## 影响范围

所有「坐标所在模块组的楼层在怪物 spawner 白名单中缺失，却仍显示同模式生成率」的怪物/物品。当前仅确认 `FlameButterfly`（FireDeep/2002），需全量交叉核对。

## 修复方向（未定，待评估）

1. 全量交叉核对：对每个怪物，比对「坐标所在分组对应的楼层 suffix」与「`spawner_entries.dungeon_grades` 的 suffix」，列出所有「坐标在但该楼层无 spawn 登记」的怪物，评估影响面。
2. 清洗时对坐标分组做楼层校验：分组楼层（FireDeep→2002）未在 spawner 白名单时，生成概率置 0 或剔除该坐标/来源。
3. 若确有例外需人工判读（同模块可能被多个楼层布局复用），以核对清单结果为准。

## 相关文件

- 游戏数据：`Data/Generated/V2/Spawner/Spawner/Id_Spawner_Monster_FlameButterfly.json`
- 游戏数据：`Data/Generated/V2/Dungeon/Dungeon/Id_Dungeon_FloorRule_Firedeep.json`（`DefaultDungeonGrade: 2002`）
- `api/src/db/importers/spawners.py` — spawn_rate 折算与 dungeon_grades 落库
- `api/src/drop_rate.py` — `_spawn_rate_by_mode`/`_spawn_rate_detail` 按模式聚合（`drop_rate.py:238-275`）
- `api/src/lootdrop_builder.py` — `group_drop_info` 分组挂载 spawn_rate（`lootdrop_builder.py:798-839`）
- `api/src/config.py` — `MODULE_GROUP_FLOOR_SUFFIXES`（FireDeep → [2] → full_grade 2002）
