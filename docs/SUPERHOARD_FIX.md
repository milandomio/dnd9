# 超级宝藏堆缺失问题分析

## 分析结论

经过完整的数据流追踪，发现问题出在 **爆率精度丢失 → score 过滤归零** 的链条上：

**根因：爆率极小 → round 归零 → score=0 → 被过滤**

1. **数据是正确的**：DB 中 `ID_LootDropGroup_SuperHoard` 组已正确关联 `ID_Lootdrop_Drop_HoardWeaponArmor`，并使用了正确的 `ID_Droprate_Hoard_WeaponArmor_*` 率表（LG8 权重 >0，如 3021 级为 5）
2. **`_entity_ldg_all` 已正确处理**：`Hoard01_9` 的物群映射同时包含了 `Id_LootDropGroup_Hoard` 和 `ID_LootDropGroup_SuperHoard`，`_get_group_drop_rates` 会尝试两个组并取最佳值
3. **精度丢失是关键**：
   - LG8 权重 = 5，25 件 `_8001` 分摊 → 每件 `5/25/10000 = 0.00002 = 0.002%`
   - `_compute_drop_rate` 返回 `total_weight = 0.00002`
   - `best_rate * 100 = 0.002`
   - `round(0.002, 1) = 0.0` ← 精度丢失在这里
   - `score = 100 * 0.0 / 100 = 0` → 被 `if score > 0` 过滤掉
4. **连带问题**：`lootdrop_items` 中有 3 个怪物名（`Hoard01`、`Hoard01_5`、`HoardChest01`）在地图中不存在对应 spawner 坐标，产生空条目浪费处理

## 修复方案

| # | 问题 | 修复位置 |
|---|------|----------|
| 1 | 爆率 `round` 过早导致精度丢失 | `_get_group_drop_rates` (L1442) |
| 2 | `score` 使用了舍入后的爆率 | loot 详情循环 (L1794~L1803) |
| 3 | 怪物名无对应坐标 | `spawner_entries` 或 `lootdrop_items` |
| 4 | 超级宝藏堆与普通宝藏堆共用同一 label | 可选优化 |

## 关键修改

不需要改 DB 数据（数据已经是正确的），只需改 `collector.py` 中两个函数的精度处理逻辑。具体而言：让 `drop_rates` 存储原始值（用于算分）并在前端做舍入展示。

### 修改 1：删除 `round` 精度截断

**文件**：`api/src/collector.py`

- L1442：`round(best_rate * 100, 1)` → `best_rate * 100`
- L1475：`round(best_rate * 100, 1)` → `best_rate * 100`
- L1917：`round(_best_rate * 100, 1)` → `_best_rate * 100`

### 修改 2：score 使用原始爆率

**文件**：`api/src/collector.py`

- L1803~L1804：`_score = _c.get("spawn_rate", 0) * _hk / 100` 改为使用原始 `drop_rates`（非 round 后的值）
- L1815：同处理

### 修改 3：清理无坐标的怪物名

**文件**：`api/src/collector.py` 或 `api/src/db_manager.py`

- 从 `lootdrop_items` 或 `merged_loot` 中剔除 `Hoard01`、`Hoard01_5`、`HoardChest01` 等无坐标条目

### 修改 4（可选）：分离超级宝藏堆 label

需涉及 `search_engine.py` → `spawners` 表 → `collector.py` 多级联动，见 `docs/REFERENCE.md` 中关于 SuperHoard 的讨论。
