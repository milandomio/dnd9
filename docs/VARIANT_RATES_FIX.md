# 多变体爆率修复进度

## 修复历史

1. **bd5e08e** — `_ld_rate_totals` 归一化替代硬编码 `/10000.0`
2. **83c0cc2** — 变体聚合替换基础条目（`_new_gdi`）+ 排除 `_HR` group
3. **3d3394f** (WIP) — group_drop_info spawn_rate 除以变体数 + rate_total 缓存

## 已完成的修改 (3d3394f)

### 1. group_drop_info spawn_rate 除以变体数
- 位置: `collector.py` ~line 1577, `_entity_max_variant` 逻辑
- 从已处理的 `coord_out["variant_count"]` 收集每个 entity 的最大变体数
- 在 group_drop_info 计算时 `round(_sr / _max_vc, 1)`
- **问题**: 用户说不应该用变体数做分母，应该用爆率文件自身的分母

### 2. _compute_variant_rate 新增 _rt_cache 参数
- 位置: `collector.py` `_compute_variant_rate` 函数
- 新增 `_rt_cache: dict[str, int] | None = None` 参数
- 使用 `_rt_cache.setdefault(lr_id, _ld_rate_totals.get(lr_id, 10000))` 共享分母

### 3. items/props 变体聚合预计算缓存
- 位置: `collector.py` items 变体聚合循环 (~line 1920) 和 props 变体聚合循环 (~line 2140)
- 在变体循环前预计算 `_rt_cache`，传入 `_compute_variant_rate`

## 未解决的问题

**Bandage 爆率仍超 100%**:
- PVE: 100% ✓
- 普通: 172% ✗ (应为 100%)
- 豪客赛: 161.5% ✗ (应为 100%)

**根因分析**:
- `ID_LootDropGroup_Bandage` 的每个 grade 只有 1 个 `(ld_id, lr_id)` 条目
- 每个 `lr_id` 的权重 lg=2+3+4 总和 = 10000，`rate_total` = 10000
- 理论上 `_pool_weight / _shared * group_count / _rate_total` 应该归一化到 100%
- 问题可能在 `_shared`（`_ld_luck_grade_count`）或 `group_count` 导致不同变体的贡献不一致

**调试方向**:
- 打印 `_compute_variant_rate` 中每个变体的 `_pool_weight`, `_shared`, `group_count`, `_rate_total`
- 检查 `_ld_luck_grade_count[(ld_id, lg)]` 是否对所有变体一致
- 检查 grade_data 中是否有多个条目导致权重累加

## 关键数据结构

- `_ld_groups[group_id][dungeon_grade]` → `[(lootdrop_id, lootdrop_rate_id, drop_count)]`
- `_ld_rate_weights[rate_id][luck_grade]` → `total_weight`
- `_ld_rate_totals[rate_id]` → `sum(weights)` (通常 = 10000)
- `_ld_rate_items[lootdrop_id]` → `{item_name: (luck_grade, drop_count)}`
- `_ld_luck_grade_count[(lootdrop_id, luck_grade)]` → 该 lg 下的物品数

## Bandage 示例数据

| lr_id | lg=2 (普通) | lg=3 (优秀) | lg=4 (罕见) | total |
|-------|------------|------------|------------|-------|
| VeryLow | 7400 | 2500 | 100 | 10000 |
| VeryLow_1011 | 6750 | 3000 | 250 | 10000 |
| VeryLow_1012 | 5500 | 4000 | 500 | 10000 |
| VeryLow_1021 | 7400 | 2500 | 100 | 10000 |
| VeryLow_1022 | 6750 | 3000 | 250 | 10000 |
| VeryLow_1023 | 5500 | 4000 | 500 | 10000 |

每个 lr_id 的 lg=2+3+4 权重总和均为 10000，理论上应归一化到 100%。
