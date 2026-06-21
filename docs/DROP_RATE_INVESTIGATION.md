# EmberGem 掉落页问题分析

## 问题概述

`/lootdrops/EmberGem/` 页面存在两个问题：
1. "狮头宝箱(随机)(可能上锁)" 不显示
2. Firedeep_MiningPassage 的狮头宝箱坐标缺失

---

## 问题1：狮头宝箱(随机) 不显示

### 原因

`OrnateChestLargeRandom`（随机变体生成器）的坐标**仅存在于 Ruins 地图**，不存在于 GoblinCave 或 FireDeep：

| map_base | 所属分组 |
|----------|---------|
| OssuaryEdge | Ruins |
| Ruins_Forest_02 | Ruins |
| Ruins_Forest_08 | Ruins |
| Ruins_GreatHall_01_Destroyed | Ruins |
| Ruins_Keep | Ruins |
| Ruins_Square_02 | Ruins |
| Ruins_UndergroundAltar_01 | Ruins |
| Ruins_WollfColony | Ruins |

**GoblinCave 地图中的 OrnateChestLarge_Locked 使用 `original_keyword=ChestSpecial`，不是 `OrnateChestLargeRandom`。**

### 数据验证

- EmberGem 的 lootdrop_rate_items 中有 `OrnateChestLarge` 和 `OrnateChestLarge_Locked`（entity_name），但没有 `OrnateChestLargeRandom`（这是 spawner keyword，不是 entity_name）
- `_classify_label` 根据 original_keyword 分类：
  - `ChestSpecial` → "special" → "(特殊)"
  - `OrnateChestLargeRandom` → "random" → "(随机)"
- Ruins 分组下 `_compute_drop_rate` 返回 0%（因为 grade 数据中无 EmberGem 条目），导致 score=0 被过滤

### 结论

"狮头宝箱(随机)" 在当前数据中确实没有有效坐标能通过 score 过滤。这不是 bug，而是数据本身如此。

---

## ~~问题2：Firedeep_MiningPassage 狮头宝箱坐标缺失~~ [已修复：变体识别]

### 现象

EmberGem JSON 中 `OrnateChestLarge_special`（狮头宝箱(特殊)(可能上锁)）仅有 4 个坐标：

| map | spawn_rate | score |
|-----|-----------|-------|
| Firedeep_BurningCourt | 25.0 | 0.75 |
| Firedeep_CollapsedDigSite | 25.0 | 0.75 |
| Firedeep_LavaCrossway | 25.0 | 0.75 |
| Firedeep_MagmaFalls | 25.0 | 0.75 |

**Firedeep_MiningPassage 缺失**，但它在 DB 中有坐标：

| keyword | original_keyword | group_parent | 数量 |
|---------|-----------------|--------------|------|
| OrnateChestLarge | ChestSpecial | BP_GameSpawnerGroup_C_1 | 2 |
| OrnateChestLarge_Locked | ChestSpecial | BP_GameSpawnerGroup_C_1 | 2 |

坐标位置（两组共享同一位置，locked merge 后应为 2 个去重点）：
- (204.2, 1334.1, 505.0)
- (-207.4, -1380.6, 500.0)

### 变体分析

MiningPassage 的 `BP_GameSpawnerGroup_C_1` 包含 9 种不同 keyword（共 20 个 spawner）：

```
FlatChestLarge, Mimic_Large_Flat, Mimic_Large_MidLevel, Mimic_Large_Ornate,
Mimic_Large_Simple, OrnateChestLarge, OrnateChestLarge_Locked,
SimpleChestLarge, WoodChestLarge
```

`get_coord_variant_counts()` 返回 `count=20, names=[]`（模式2：同 keyword 多点共享 group）。

spawn_rate 计算：`round(25.0 / 20, 1) = 1.3`
score：`1.3 * 3.0 / 100 = 0.039` > 阈值 0.0（总坐标 < 100）

**理论上应通过 score 过滤，但实际缺失。需要进一步调试 collector.py 确认原因。**

### 可能原因

1. `_coord_variant_count` 的 key 是 `(map_base, json_filename, group_parent)`，MiningPassage 的 json_filename 可能与预期不同
2. locked merge 去重步骤可能意外移除了 MiningPassage 坐标
3. `_map_base_to_group` 可能未包含 MiningPassage

### ~~待办~~ [已通过变体识别解决]

- [x] MiningPassage 坐标缺失问题已通过变体识别机制修复

---

## 已修复的问题

### "X点选1" 显示错误：variant_count 被当作点数（已修复）

**页面**：`/lootdrops/EmberGem/`、所有详情页地图图例

**现象**：狮头宝箱(特殊) 在 MiningPassage 显示"20点选1"，实际只有 2 个 spawn 点（每个点 20 个变体）。

**原因**：前端代码（`LootdropDetailPage.tsx`、`DetailPage.tsx`）在 `variant_count > 1` 时直接用 `variant_count` 显示"X点选1"，但 `variant_count` 是每个 spawn 点的变体数，不是 spawn 点数。多个变体共享同一坐标，应按坐标去重计算实际点数。

**修复**：
- `LootdropDetailPage.tsx`：用 `new Set(mDots.map(d => \`${d.x},${d.y},${d.z}\`)).size` 计算去重后的点数
- `DetailPage.tsx`：同上逻辑

### GoldChest spawn_rate 4.5% → 100%（已修复，commit beacb04）

原因：
1. `get_coord_variant_counts()` 返回 `COUNT(*)` 而非 `COUNT(DISTINCT original_keyword)`
2. `_entity_max_variant` 跨所有坐标取最大变体数
3. group_drop_info spawn_rate 被错误除以变体数

修复：
- db_manager.py: `row["total"]` → `row["cnt"]`
- collector.py: 移除 `_entity_max_variant` 和 spawn_rate 除以变体数逻辑
