# 数据管道参考

本文只保留管道运行时需要的规则。地图模块和爆率细节分别见 [`REFERENCE_MAP_MODULES.md`](REFERENCE_MAP_MODULES.md) 与 [`REFERENCE_DROP_RATES.md`](REFERENCE_DROP_RATES.md)；完整历史记录见 [`REFERENCE_ARCHIVE.md`](REFERENCE_ARCHIVE.md) 的“数据管道”章节。

## 管道顺序

`api/src/collector.py` 负责协调 DB 导入、Spawner 解析、实体导出、地图模块构建、掉落详情和 locale 导出。

- **数据访问边界**：游戏解包 JSON 只能在导入阶段批量写入 `darkfindv5.db`；`collector.py`、各 builder、exporter、locale 生成和部署构建只能读取 DB/repository 返回的数据，禁止在生成阶段直接读取解包 JSON。这样 CI、部署与本地运行使用相同的数据源。
- `_is_db_stale()` 必须在 `DatabaseManager()` 构造之前调用，避免 SQLite 建空文件后把 mtime 更新为当前时间。
- 删除 DB 的部署测试使用 `rm api/data/darkfindv5.db` 后运行 `python main.py`，确认从零导入。
- `modules_map` 必须在 items、monsters、props 导出前构建，供实体 JSON 的 `_modules` 或共享模块数据使用。
- 所有实体坐标先由 `db.get_all_coordinates()` 批量获取，导出阶段按 `all_coords.get(name, [])` 查询，禁止逐实体 N+1 查询。
- Spawner 插入使用 `executemany`；不要恢复逐行插入。

## 地图文件与坐标

`search_engine.py` 遍历地图 JSON 时排除 `_SR`、`_BossTest`、`_Resize`、`_Test`、文件名含 `Arena` 的文件，以及 `ArenaStart` 目录。

Spawner 坐标必须沿 `AttachParent` 链递归累加，并按父级累计 Yaw 旋转局部坐标。没有父级时直接使用 `RelativeLocation`。父级链解析是世界坐标正确性的必要条件。

`BP_GameSpawnerGroup_C` 表示互斥刷新组：解析时建立 RootComponent 到组名的映射，命中 AttachParent 链后写入 `group_parent`。只有至少两个同 keyword spawner 共享一组时，前端才显示互斥标签。

## 实体分类与名称

- 分类映射通过 `db.get_entity_classification()` 从 items、monsters、props 表构建，不再扫描数千个 JSON。
- 坐标实体名优先取 `PreviewData.AssetPathName`，再退回 `SpawnerDataAsset.ObjectName`。
- 翻译键从实体 JSON 的 `Properties.Name.Key` 在导入阶段获取并写入实体表/翻译表；后续导出和 locale 收集只使用 DB 中的 key。
- `_Hard`、`_VeryHard`、`_Unique` 等掉落实体后缀在 lootdrop 解析阶段合并，避免重复掉落源。
- 怪物质量变体优先按翻译键合并；翻译失败时才对 `_Common`、`_Elite`、`_Nightmare`、`_Unique` 使用基础名兜底。

## 物品坐标链式反查

没有直接地面坐标的物品，按以下关系从 lootdrop 容器反查：

```text
lootdrop_rate_items.item_name
  -> lootdrop_rate_items.lootdrop_id
  -> lootdrop_groups.lootdrop_id
  -> lootdrop_groups.group_id
  -> spawner_entries.lootdrop_group_id
  -> spawner_entries.spawner_keyword
  -> spawners.keyword -> 坐标
```

实现位于 `collector.py` 的 `item_coord_chain_map` 和 `entity_export.py` 的物品坐标回退。链式坐标的 `keyword` 是容器名，不能再经过只允许物品名的 `filter_coords()`。

## 子池

ObjectLinker 子池的固定链路如下：

1. `coordinates.py:get_sub_group_pool_info()` 按 `(map, file, gp, sgp)` 统计 DISTINCT 实体。
2. `collector.py` 根据实体分类取得 `translation_key`。
3. `translator.py:build_coord_out()` 写入 `sub_pool_size`、`sub_pool_names` 或结构化 `sub_pool_entries`。
4. `DetailPage.tsx` 按 `sub_group_parent` 渲染成员名和选择关系。

最大同时存在数按 distinct linker 计，不按刷怪点数量重复计算。

## 交付检查

- 修改管道逻辑后先运行 `python main.py`，再运行前端构建。
- 不直接修改 `data/` 自动生成文件；修改 `api/src/` 生成逻辑。
- 查询游戏解包数据使用 fmodel MCP；查询 DB 使用 sqlite-debug MCP。
