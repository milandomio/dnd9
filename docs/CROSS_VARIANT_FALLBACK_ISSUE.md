# 跨变体 Fallback 问题

## 问题描述

`compute_drop_rate` 和 `compute_variant_rate` 中的跨变体 fallback 逻辑（`_base` + `_VARIANT_SUFFIXES` 循环）会导致**未在 `lootdrop_rate_items` 中注册的变体名**从同物品的其他已注册变体"借用"爆率，产生不存在的数据。

## DB 注册情况

- `SurgicalKit`：仅有 `_4001`（luck_grade=4）14 条记录 → `_3001`/`_6001`/`_7001` 均无
- `HeaterShield`：仅有 `_5001`（grade=5）和 `_8001`（grade=8）各 24 条 → `_1001`~`_4001`/`_6001`/`_7001` 均无

## Fallback 链路（以 SurgicalKit_7001 为例）

```
item_name = "SurgicalKit_7001"
1. exact match → None（DB 无此变体）
2. compound suffix → None
3. _base = VARIANT_RE.sub → "SurgicalKit"
4. base exact → None
5. base + _VARIANT_SUFFIXES 循环 → "_4001" 命中 → 返回 luck_grade=4
```

第 5 步用错误变体的注册等级去取 pool weight，算出非零爆率。**该爆率在游戏中不存在。**

## 影响范围

所有 `lootdrop_rate_items` 中未注册的变体名都会通过 fallback 获得虚假爆率。已在页面中显示为实，用户会看到不应存在的掉落。

## 修正方案

1. 从 `compute_drop_rate` 和 `compute_variant_rate` 中移除 `_base` 跨变体 fallback（仅保留 exact match + compound suffix）
2. 确保 `compute_variant_rate` 中使用物品自身注册的 luck_grade（`_found_lg`）取 pool weight（之前讨论的 "item_lg" 命名——但 fallback 本身移除后此修正无意义）

### 需考虑的影响

- `HeaterShield_7001` 爆率消失（原本靠 fallback 借用 `_5001`/`_8001`）
- `SurgicalKit_3001`/`6001`/`7001` 爆率消失
- 任何只有部分变体注册的物品，未注册变体将显示 0% 爆率
- `HeaterShield_7001` 页面无爆率的问题与 fallback 是**两回事**——其 `variant_count` 为 None 是独立 Bug，参见注释

## 相关文件

- `/home/mio/fmod/DarkFindV5/api/src/drop_rate.py` — `compute_drop_rate` (line 313-320) 和 `compute_variant_rate` (line 563-569) 中的 `_base` fallback
- `/home/mio/fmod/DarkFindV5/api/src/lootdrop_builder.py` — `_variant_valid_trans` 过滤逻辑（lootdrop 详情页展示）
