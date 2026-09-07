# Enrichment 二次 I/O 优化计划

## 背景

当前管道先将 items、monsters、props 详情写入 `api/output/json/`，再由
`enrichment.py` 重新读取这些 JSON，并读取 lootdrop 详情中的
`group_drop_info`，修改后再次写回。lootdrop 详情约 664MB，重复解析和实体文件
二次写入会增加管道耗时。

## 目标

- lootdrop 生成阶段直接把已经计算好的 `group_drop_info` 传给 enrichment。
- entity export 阶段保留实体详情对象在内存中，enrichment 不再读取实体 JSON。
- 将实体详情写盘延后到 enrichment 完成后，每个详情文件只写一次。
- 保持 DB schema、前端 JSON 结构、掉落率公式和零率清理语义不变。

## 方案

1. `entity_export.py` 的三个导出函数增加可选的内存结果容器。
   - 有容器时只生成对象，不立即写详情文件。
   - 索引文件和既有返回值保持不变。
2. `lootdrop_builder.py` 在完成基础 lootdrop 详情计算后，将非变体详情的
   `group_drop_info` 写入共享内存映射。
3. `collector.py` 将三类实体对象和 lootdrop GDI 映射传给 `enrichment.py`。
4. `enrichment.py` 只操作内存对象，完成直接生成物品、怪物、props 的 GDI
   注入及零率清理后统一写出详情文件。
5. lootdrop 变体引用检查使用已导出的 `entity_page_map`，允许实体详情延后
   写盘，不改变引用路径。

## 不变项

- 原始解包数据仍只在 DB importer 预载入阶段读取。
- DB 仍是规范化数据源；`group_drop_info` 继续作为导出阶段派生数据，不写回 DB。
- `lootdrops/*.json`、`items/*.json`、`monsters/*.json`、`props/*.json` 的字段
  和内容语义不变。
- 变体详情仍只生成实际存在的变体，并保留现有 ref、坐标预算和翻译键逻辑。

## 验收

- enrichment 阶段不再调用 `json.load()` 读取 lootdrop、items、monsters、props
  详情文件。
- 正常管道生成的实体详情文件各只进行一次详情写入。
- 固定样例的 JSON 语义对比通过，特别是 `group_drop_info`、变体详情和零率清理。
- 后端测试、Python 编译、runtime I/O guard 和前端类型检查通过。
- 记录优化前后分阶段耗时；若性能无收益，保留内存传递设计并继续 profile 计算热点。

## 执行状态

状态：已完成，待后续使用同一数据集和同一机器进行基线对比。

- `entity_export.py` 将 items、monsters、props 详情对象保留在内存中，索引仍即时写出。
- `lootdrop_builder.py` 将非变体 lootdrop 的 `group_drop_info` 直接写入共享映射。
- `enrichment.py` 不再解析 lootdrop 或实体详情 JSON；它完成内存注入和零率清理后，将每个实体详情写出一次。
- 2026-08-01 完整管道完成，当前数据集产出 95 个带 GDI 的 items、134 个 monsters、45 个 props；quick SSG 成功生成 3,067 条路由，根路径和 Bandage 详情页均返回 HTTP 200。
- 本次没有同一工作树修改前的对照运行，因此不将本次 `lootdrops 96.30s` 直接与历史基线比较；后续应在固定 DB、解包数据和硬件条件下运行 A/B 管道对比。

## 风险与回退

- 风险：延后写盘后，变体 ref 检查可能误判实体文件不存在；通过
  `entity_page_map` 作为已导出页面集合规避。
- 风险：内存中实体对象被 enrichment 修改后影响后续索引；当前索引已在
  enrichment 前建立，且只新增/清理详情字段。
- 回退：移除内存容器参数，恢复 entity export 即时写盘和 enrichment 的文件读取，
  不涉及 DB 或前端结构。
