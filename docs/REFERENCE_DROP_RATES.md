# 爆率与掉落参考

本文集中说明 SpawnRate、DropRate 和掉落详情显示。地图模块旋转与 Layout 规则见 [`REFERENCE_MAP_MODULES.md`](REFERENCE_MAP_MODULES.md)。旧调查和完整字段记录见 [`REFERENCE_ARCHIVE.md`](REFERENCE_ARCHIVE.md) 的“生成概率与物品爆率”章节。

## 两层概率

- **生成概率**：Spawner 是否生成。`SpawnerItemArray` 内按条目权重归一化，写入 `spawner_entries.spawn_rate`，范围为 0 到 100。
- **物品爆率**：Spawner 生成后从 LootDrop 中抽到目标物品的概率。游戏原始 `DropRate` 以 10000 为 100%，导出时按有效权重总和归一化。
- 所有计算使用 `decimal.Decimal`；最终通过 `drop_rate._round_rate` 以 `ROUND_HALF_UP` 保留 4 位小数。

## 查询链

```text
SpawnerDataAsset
  -> LootDropGroupId
  -> LootDropGroup(DungeonGrade)
  -> LootDropId + LootDropRateId
  -> LootDropItemArray(ItemId, LuckGrade, ItemCount)
  -> LootDropRateItemArray(LuckGrade, DropRate)
```

`DungeonGrade` 先映射到地图组、模式和楼层，再选对应 `LootDropRateId`。同一 lootdrop group 在不同 grade 下不能复用 rate。

## DB 预加载

`DropRateEngine.preload()` 将查询链压入内存，避免详情导出时重复 SQL：

| 内存索引 | 来源 | 用途 |
|----------|------|------|
| `_spawner_ldg` | `spawner_entries` | entity/spawner -> lootdrop group |
| `_ld_groups` | `lootdrop_groups` | group -> grade -> lootdrop/rate/count |
| `_ld_rate_items` | `lootdrop_rate_items` | lootdrop -> item/luck grade/count |
| `_ld_rate_weights` | `lootdrop_rate_weights` | rate -> luck grade 权重 |
| `_ld_rate_totals` | 权重汇总 | 爆率归一化分母 |

主要计算入口为 `compute_drop_rate()`、`get_group_drop_rates()`、`compute_group_drop_rates()` 和 `compute_variant_rate()`。

## 变体规则

- `variant_count > 1` 时，详情页展示有爆率的多个品质变体，变体爆率合计应为 100%。
- 变体查询必须先使用 spawner 的 `lootdrop_group_id` 精确匹配 LootDrop，再从该 LootDrop 反查变体；不能只按物品名全局搜索。
- 普通 `_1001` 到 `_7001` 变体可按基底详情共享来源数据；独立 `_8001` 保留自身详情和翻译键。
- `_compute_drop_rate()` 基础名未命中时，按约定的品质后缀回退；不得把不同 lootdrop group 的 rate 混用。

## 掉落详情显示

- 坐标级 `spawn_rate` 只有不等于 100 时才显示。
- 实体级 `drop_rates` 是该实体的聚合爆率；物品级则是指定物品爆率。
- 坐标 score 为 `spawn_rate * high_roller_rate / 100`，低于导出阈值的坐标可在 `lootdrop_builder.py` 过滤。
- 怪物来源按钮按 `max_score` 降序；没有爆率数据的条目排最后并保持可见。
- 变体点按 `group_parent` 去重计算有效刷怪位，不能直接用坐标点数代替互斥组数。
- 无变体运算时，模块卡片不重复渲染与分组头相同的参考爆率。

## 常见错误

- 把 SpawnRate 当成 DropRate，导致详情页概率虚高。
- 使用合成显示名查询 DB，导致特殊/随机来源查不到 lootdrop group；查询应使用规范 `entity_name`。
- lock merge 时用组合概率覆盖所有坐标；每个坐标必须保留自身 Spawner 的原始生成率。
- 只给 monsters 写 `translation_key`，遗漏 props 容器来源，造成非中文掉落页面回退中文。
