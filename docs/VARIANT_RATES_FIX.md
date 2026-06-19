# 多变体爆率修复进度

## 修复历史

1. **bd5e08e** — `_ld_rate_totals` 归一化替代硬编码 `/10000.0`
2. **83c0cc2** — 变体聚合替换基础条目（`_new_gdi`）+ 排除 `_HR` group
3. **3d3394f** — group_drop_info spawn_rate 除以变体数 + rate_total 缓存
4. **HEAD** — 移除 `item_count` 和 `group_count` 对爆率概率的乘法

## 已完成的修改 (HEAD)

### 1. `_compute_drop_rate` 移除 `* item_count` 和 `* group_count`
- **根因**: `rate_items` 的 `drop_count`（如 Arrow_2001 的 `drop_count=3`）被乘入概率公式，
  导致 66.8% × 3 = 200.4%。同 `group_count`（`lootdrop_groups.drop_count`）乘以概率后
  也使 PirateBowman 等怪物出现 66.8% × 2 = 133.6%。
- **修复**: 爆率公式从 `_pool_weight / _shared * group_count * item_count / _rate_total`
  改为 `_pool_weight / _shared / _rate_total`，`item_count` 和 `group_count` 不再影响概率。
- **影响**: 取消了三处乘法：`_compute_drop_rate`、`_compute_group_drop_rates`、`_compute_variant_rate`

### 2. 全量扫描确认
- 修复前: **44** 个 items/monsters 有 >100% 爆率（最高 400.8%）
- 修复后: **0** 个 items/monsters 超过 100%

## 已完成的修改 (3d3394f)

### 1. group_drop_info spawn_rate 除以变体数
- 位置: `collector.py` ~line 1577, `_entity_max_variant` 逻辑
- 从已处理的 `coord_out["variant_count"]` 收集每个 entity 的最大变体数
- 在 group_drop_info 计算时 `round(_sr / _max_vc, 1)`

### 2. _compute_variant_rate 新增 _rt_cache 参数
- 位置: `collector.py` `_compute_variant_rate` 函数
- 新增 `_rt_cache: dict[str, int] | None = None` 参数
- 使用 `_rt_cache.setdefault(lr_id, _ld_rate_totals.get(lr_id, 10000))` 共享分母

### 3. items/props 变体聚合预计算缓存
- 位置: `collector.py` items 变体聚合循环 (~line 1920) 和 props 变体聚合循环 (~line 2140)
- 在变体循环前预计算 `_rt_cache`，传入 `_compute_variant_rate`

## 关键数据结构

- `_ld_groups[group_id][dungeon_grade]` → `[(lootdrop_id, lootdrop_rate_id, drop_count)]`
- `_ld_rate_weights[rate_id][luck_grade]` → `total_weight`
- `_ld_rate_totals[rate_id]` → `sum(weights)` (通常 = 10000)
- `_ld_rate_items[lootdrop_id]` → `{item_name: (luck_grade, drop_count)}`
- `_ld_luck_grade_count[(lootdrop_id, luck_grade)]` → 该 lg 下的物品数
