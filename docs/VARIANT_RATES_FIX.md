# 多变体爆率修复进度

## 修复历史

1. **bd5e08e** — `_ld_rate_totals` 归一化替代硬编码 `/10000.0`
2. **83c0cc2** — 变体聚合替换基础条目（`_new_gdi`）+ 排除 `_HR` group
3. **3d3394f** — group_drop_info spawn_rate 除以变体数 + rate_total 缓存
4. **898c238** — 移除 `item_count` 和 `group_count` 对爆率概率的乘法
5. **d0eef7b** — `_compute_variant_rate` 添加 `found` 守卫，权重 0 时不回退
6. **058c8da** — 彻底移除 `(full_grade, 0)` 回退机制，三处爆率函数统一

## 已完成的修改 (058c8da)

### 彻底移除 grade=0 回退机制
- **根因**: 三个爆率函数均使用 `for grade in (full_grade, 0)`：
  - 当 full_grade 条目存在但 luck_grade 权重为 0（游戏设计意图），会错误回退到 grade=0
  - 当 full_grade 不存在（如组未定义某层），回退到 grade=0 会丢失模式特异性（PVE/普通/豪客赛权重分布完全不同）
- **修复**: 三个函数全部改为只查 `full_grade`，无条目或权重为 0 均返回 0.0
- **典型影响**: 绷带(普通) VeryLow_3001 lg=2=0 → 之前回退到 VeryLow(lg=2=7400) 显示 74%，现正确显示 **0%**

## 已完成的修改 (d0eef7b)

### `_compute_variant_rate` 添加 `found` 守卫
- 与 `_compute_drop_rate` 保持一致：在 full_grade 找到匹配条目后 return（无论权重是否为 0），不回退

## 已完成的修改 (898c238)

### 1. 移除 `* item_count` 和 `* group_count`
- **根因**: `drop_count`（如 Arrow_2001 的 `drop_count=3`）和 `lootdrop_groups.drop_count`（如 PirateBowman 的 2）乘入概率公式，导致 >100% 爆率
- **修复**: 公式统一为 `_pool_weight / _shared / _rate_total`
- **影响**: 修复前 **44** 个实体 >100%（最高 400.8%），修复后 **0** 个

## 已完成的修改 (3d3394f)

### 1. group_drop_info spawn_rate 除以变体数
### 2. _compute_variant_rate 新增 _rt_cache 参数
### 3. items/props 变体聚合预计算缓存

## 关键数据结构

- `_ld_groups[group_id][dungeon_grade]` → `[(lootdrop_id, lootdrop_rate_id, drop_count)]`
- `_ld_rate_weights[rate_id][luck_grade]` → `total_weight`
- `_ld_rate_totals[rate_id]` → `sum(weights)` (通常 = 10000)
- `_ld_rate_items[lootdrop_id]` → `{item_name: (luck_grade, drop_count)}`
- `_ld_luck_grade_count[(lootdrop_id, luck_grade)]` → 该 lg 下的物品数
