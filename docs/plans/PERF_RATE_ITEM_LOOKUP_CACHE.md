# 掉落率物品匹配缓存优化计划

## 背景

`DropRateEngine.compute_drop_rate()` 对每个 `(lootdrop_id, item_name, dungeon_grade)`
调用 `_find_rate_item()`。当查询的是未带品质后缀的基底物品、且掉落池没有同名
精确条目时，函数会扫描整个 `rate_items` 字典，筛选 `_1001` 至 `_7001` 变体：

1. 精确查 `rate_items[item_name]`；命中直接返回。
2. 带品质后缀的查询未命中时直接返回 `None`，不能借用其他品质。
3. 未带后缀的查询扫描同一 LootDrop 的所有物品，排除 `_8001`。
4. 优先选真实存在的 `_5001`，否则选数值最高的后缀。

此语义与 `REFERENCE_DROP_RATES.md` 的变体规则一致，不能改变。

## 证据

2026-08-01 固定数据集的 profile：

| 指标 | 实测 |
|---|---:|
| lootdrop 详情构建 | 93.819s |
| 基础 `group_rates` | 72.368s |
| `_find_rate_item()` | 67.507s |
| `_find_rate_item()` 占基础 `group_rates` | 93.3% |
| 候选池线性扫描占 `_find_rate_item()` | 98.6% |

当前 DB 的 `lootdrop_rate_items` 结构：

| 指标 | 数量 |
|---|---:|
| 行数 | 44,459 |
| LootDrop 池数 | 395 |
| 每池平均不同物品数 | 112.01 |
| 单池最大不同物品数 | 1,346 |
| `(lootdrop_id, 基底物品)` 变体族数 | 6,682 |
| 每变体族平均品质数 | 6.59 |

细粒度 profile 确认瓶颈是候选池扫描本身；逐候选计时会产生显著测量开销，故不以其
绝对秒数作为验收基准。原始日志保存在 `/tmp/darkfindv5-group-rates-profile.log` 和
`/tmp/darkfindv5-find-rate-profile.log`。

## 目标

- 将已预加载 LootDrop 的基底物品回退查询由每次 O(池大小) 扫描改为 O(1) 查表。
- 精确条目、`_5001` 优先、最高真实品质和排除 `_8001` 的结果保持完全一致。
- 不改 DB schema、导出 JSON、掉落率公式、变体可用性或前端契约。
- 在相同 DB、数据集和机器上验证 `group_rates` 与 lootdrop 详情构建显著下降。

## 设计

### 预加载索引

在 `DropRateEngine.__init__()` 增加私有索引：

```python
_ld_preferred_base_items: dict[str, dict[str, list[tuple[int, int]]]]
```

键为 `lootdrop_id -> base_item_name`，值直接引用 `_ld_rate_items` 中已经存在的
`[(luck_grade, drop_count), ...]` 列表，不复制条目数据。

在 `preload()` 已构建完 `_ld_rate_items` 后，逐个 LootDrop 池遍历一次：

1. 仅处理匹配品质后缀的物品名。
2. 忽略 `_8001`。
3. 对同一个基底名保留 `_5001`；若不存在 `_5001`，保留后缀数值最高的条目。
4. 即使某池没有可回退变体，也写入空映射，表示该池已完成预计算。

额外内存上限为 6,682 个字典键及其对既有列表的引用，远小于现有 44,459 行
`_ld_rate_items` 数据。

### 查询路径

在 `compute_drop_rate()` 内用一个私有 resolver 替换直接调用 `_find_rate_item()`：

1. 先从 `rate_items` 精确查找，保持现有优先级。
2. 若查询名带品质后缀但未精确命中，返回 `None`。
3. 若为无后缀基底名，直接从 `_ld_preferred_base_items[lootdrop_id]` 查询。
4. 仅当测试或外部调用手工构造 `DropRateEngine`、未执行 `preload()` 时，回退到原
   `_find_rate_item()` 线性扫描，保留现有单元测试和内部调用兼容性。

`compute_variant_rate()` 保持现状：其查询带品质后缀，已有精确查询语义，不应通过基底
回退索引。

## 实施步骤

1. 在 `drop_rate.py` 增加预加载索引与私有 resolver；不修改 `_find_rate_item()` 的
   既有语义，作为未预加载 fallback 与基准实现保留。
2. 让 `compute_drop_rate()` 使用 resolver；仅替换无后缀且无精确命中的分支。
3. 扩展 `api/tests/test_drop_rate.py`：
   - 精确基底条目优先于变体；
   - `_5001` 优先于更高品质；
   - 无 `_5001` 时取最高真实品质；
   - `_8001` 不参与基底回退；
   - 缺失带后缀查询仍为 0；
   - 未调用 `preload()` 的手工 engine 保持原线性回退行为。
4. 用固定 DB 运行完整管道，比较 profile 中 `group_rates`、`_find_rate_item()` 与
   `lootdrops`；再执行 JSON 语义抽样和前端 SSG 验证。

## 验收

- 现有掉落率单元测试与新增优先级测试通过。
- 以同一 DB 的 `compute_drop_rate()` 样例对照，缓存路径与 `_find_rate_item()` 的原始
  路径逐项返回相同的 luck-grade 列表或 `None`。
- 完整管道中的 `group_rates` 显著低于 `72.368s` 基线；记录实际改善，不预先承诺固定
  百分比。
- `lootdrops/*.json`、`items/*.json`、`monsters/*.json`、`props/*.json` 的结构和
  掉落率值保持一致；变体详情、零爆率处理和引用路径均通过既有验证。
- Ruff、Black、Python 单元测试、完整管道、前端 Prettier、TypeScript、SSG 和 HTTP
  200 验证通过。

## 风险与回退

- 风险：预加载索引把 `_8001` 或不存在的 `_5001` 误选为回退值。通过显式后缀测试和
  原始 resolver 对照测试防止。
- 风险：漏掉手工构造的 engine，导致单元测试或内部调用失去基底回退。resolver 在没有
  预加载标记时使用原始扫描逻辑。
- 回退：移除预加载索引与 resolver 调用，恢复 `compute_drop_rate()` 对
  `_find_rate_item()` 的直接调用；不涉及数据迁移或前端回退。

## 状态

状态：待实施。
