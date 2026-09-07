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

## 修复方案（已全部完成）

| # | 问题 | 修复位置 | 状态 |
|---|------|----------|------|
| 1 | 爆率精度丢失 | `_round_rate` 改用 `decimal.Decimal` 量化到 3 位小数 | ✅ |
| 2 | SuperHoard 与 Hoard 共用 label | `search_engine.py` 跳过 SuperHoard redirect；`config.py` 添加 HARDCODED_TRANSLATIONS | ✅ |
| 3 | SuperHoard 无独立 entity 分类 | `enrichment.py`（原 `collector.py`）往 `entity_class` 注入 SuperHoard props | ✅ |
| 4 | SuperHoard 不出现在物品怪物列表 | `lootdrop_builder.py`（原 `collector.py`）merged_loot 注入 SuperHoard spawner 关键字 | ✅ |

## 实际修改汇总

### 1. 爆率精度修复（`a549848`）
- 引入 `decimal.Decimal`，`_round_rate` 使用 `Decimal(str(v)).quantize("0.001", ROUND_HALF_UP)`，替代 `round(v, 1)`
- 所有爆率输出点均通过该函数，消除浮点长尾（如 `0.011999999999999999` → `0.012`）

### 2. SuperHoard 实体分离
- **`api/src/search_engine.py`**：SuperHoard 关键字不走 redirect，保留独立 identity
- **`api/src/config.py`**：添加 `SuperHoard01_9` / `SuperHoardChest01_9` 翻译 "超级宝藏堆"
- **`api/src/enrichment.py`**（原 `collector.py`）：`entity_class` 注入 SuperHoard 为 props 类型
- **`api/src/lootdrop_builder.py`**（原 `collector.py`）：`merged_loot` 注入 SuperHoard spawner 关键字，使其出现在物品怪物列表中
