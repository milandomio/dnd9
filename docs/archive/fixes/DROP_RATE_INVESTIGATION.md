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

## 问题2：Firedeep_MiningPassage 狮头宝箱坐标缺失 [已修复]

### 现象

EmberGem JSON 中 `OrnateChestLarge_special`（狮头宝箱(特殊)(可能上锁)）仅有 4 个坐标（缺少 MiningPassage）：

| map | spawn_rate | score |
|-----|-----------|-------|
| Firedeep_BurningCourt | 25.0 | 0.75 |
| Firedeep_CollapsedDigSite | 25.0 | 0.75 |
| Firedeep_LavaCrossway | 25.0 | 0.75 |
| Firedeep_MagmaFalls | 25.0 | 0.75 |

### 根因

`_coord_variant_count` 的 key `(map_base, json_filename, group_parent)` 中 MiningPassage 的 `json_filename` 与预期不匹配（文件名大小写差异），导致 variant_count 识别失败、坐标被意外过滤。

### 修复

通过变体识别机制的改进解决（详见 `docs/VARIANT_RATES_FIX.md`）：统一文件名大小写处理，确保 MiningPassage 的坐标正确计入。

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
- lootdrop_builder.py（原 collector.py）: 移除 `_entity_max_variant` 和 spawn_rate 除以变体数逻辑
