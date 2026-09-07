# 性能优化计划草案 2：管线热点收敛

> 创建日期：2026-07-27
> 状态：阶段 A 已完成（A1、A2 保留；A3 实测后撤回）
> 基线：`api/logs/pipeline_20260727_005114.log`（热 DB 总计 98.18s）
> 前版：`docs/plans/PERF_PIPELINE_AND_RUNTIME.md`

## 1. 目标与约束

- 热 DB 管线目标：总计不高于 40s，`lootdrops` 不高于 30s，`locale export` 不高于 1s。
- 不改变爆率公式、坐标筛选、翻译键集合和详情 JSON 业务结构。
- 优先使用预索引、批量 API 和消除重复 I/O；暂不引入多进程、C 扩展或 Canvas 渲染。
- 每阶段用同一 DB 重跑管线，并对 locale key 集合和固定掉落样例做语义对比。

## 2. 当前基线

| 步骤 | 耗时 | 占比 | 类型 |
|------|------|------|------|
| lootdrops | 79.08s | 80.5% | CPU + JSON I/O |
| locale export | 14.16s | 14.4% | 重复 JSON 读取/解析 |
| data delivery | 2.08s | 2.1% | I/O |
| dungeon_modules export | 1.16s | 1.2% | CPU + I/O |
| 其他 | 1.70s | 1.8% | 混合 |

数据规模：`lootdrop_rate_items` 7867 行，其中变体数据 7248 行、295 个变体家族；掉落详情约 2300 个文件、约 664MB。

## 3. 阶段 A：低风险快赢（本轮实施）

### A1. Locale 去除 lootdrops 二次全盘解析

现状：`locale_builder._load_used_keys()` 在掉落文件全部写完后，再读取并递归遍历整个 `lootdrops/` 目录。

改造：

- `build_and_save_lootdrop_details()` 在生成详情时，将实际写出的 item、entity、GDI 和 rarity `translation_key` 加入共享集合。
- `build_locale_files()` 收到该集合时跳过 `lootdrops/` 重读；未传集合时保留原扫描路径，保证独立调用兼容。
- `items/monsters/props`、`search_index` 和 `dungeon_modules` 继续扫描，覆盖坐标池等非 loot 索引来源的 key。

验收：优化前后 10 个 locale 文件的 key 集合完全一致。

### A2. base item 反向 spawner 索引

现状：`get_base_item_spawners()` 每次调用都扫描全部 `_ld_rate_items`，复杂度约为 `O(变体家族数 × rate item 行数)`。

改造：`DropRateEngine.preload()` 一次构建：

```text
item_name
  -> base_item_name
  -> lootdrop_id
  -> group_id
  -> spawner_keyword
```

运行时直接按 `base_item_name` 查询集合。

验收：固定变体详情 JSON 与优化前逐字节一致。

### A3. 变体跨地图组批量爆率（未保留）

现状：调用端对每个 `(entity, group)` 分别调用 `get_variant_group_drop_rates()`，虽然引擎已有 `get_variant_rates_all_groups()`。

评估：每个变体先按实体汇总涉及的地图组，再一次性计算 `entity -> group -> mode rates`，生成 GDI 时只查结果表。

结果：固定样例语义一致，但 lootdrops 从 79.08s 变为 80.64s，没有形成可测收益，因此撤回该改造，保留原有结果缓存路径。

## 4. 后续阶段

| 阶段 | 内容 | 触发条件 |
|------|------|----------|
| B1 | 变体间复用 monsters/coords 骨架，减少重复复制、过滤和 score 重算 | 阶段 A 后 lootdrops 仍高于 30s |
| B2 | enrichment 合并到首次实体导出，统一 compact JSON | 阶段 A 后 I/O 仍占主导 |
| B3 | 将纯 JSON 写盘拆为有界线程池 | profile 证明写盘占比足够高 |
| C1 | `LootdropDetailPage` 分组、评分、排序整体 memo 化 | 浏览器 Performance 出现大于 50ms 长任务 |
| C2 | 密集地图点切换 SVG path/Canvas | memo 后仍有明显 DOM/布局开销 |
| D1 | stale 检测 manifest、HR/D 去重空间 hash | 冷 DB 重建成为高频操作 |

## 5. 验证清单

- [x] Python 语法检查和 API lint 通过。
- [x] Web `format`、`format:check`、TypeScript 检查通过。
- [x] 热 DB 管线完成并记录新分步耗时。
- [x] 10 个 locale 文件 key 集合和值无增减。
- [x] 固定掉落样例 JSON 语义一致（原输出存在非确定性对象键顺序，不能按字节验收）。
- [x] `docs/SESSION_CHANGES.md` 已追加。

## 6. 执行记录

| 日期 | 阶段 | 结果 |
|------|------|------|
| 2026-07-27 | A | 总计 98.18s → 82.31s；locale 14.16s → 0.48s；lootdrops 79.08s → 77.87s。A1、A2 保留，A3 因首次实测 lootdrops 80.64s 无收益而撤回。 |

阶段 A 将总时长减少 15.87s（16.2%），主要收益来自消除约 670MB lootdrops JSON 的二次读取和解析。lootdrops 仍占最终计时的 94.6%，下一阶段应 profile 变体详情的结构复制、坐标过滤、score 重算与 JSON 写盘占比，再决定 B1/B2/B3。
