# DB 新旧判断与导入生命周期修复方案

## 背景

当前后端启动后只判断 `GAME_ROOT.exists()`：

```python
game_available = GAME_ROOT.exists()
if game_available:
    # 每次都执行全量 importer
```

因此即使 `api/data/darkfindv5.db` 已存在且游戏解包数据没有变化，仍会重复执行：

- translations、items、monsters、props、modules 导入
- `spawner_entries` 清空并重新导入
- 全量地图 JSON 解析和 AttachParent 坐标计算
- lootdrop 关系和 rate 表导入
- quest 数据导入

这会造成不必要的耗时，也让“DB 已存在”和“首次生成 DB”两种状态共用一条不规范的
导入路径，增加半成品 DB、旧数据覆盖和阶段顺序错误的风险。

历史提交 `78d04b3b` 曾加入基于源文件 mtime 的 `_is_db_stale()`，但该逻辑后来在
`2bd1438b` 的 DB-only 改造中被移除。当前文档仍要求 `_is_db_stale()` 必须在
`DatabaseManager()` 构造之前执行，但生产代码已不再满足这一约定。

## 当前证据

最近一次完整管道总计 `50.58s`，其中：

| 阶段 | 当前耗时 | 说明 |
|---|---:|---|
| `lootdrops` | 22.01s | 包含详情生成和 enrichment |
| `extract_and_store_spawners` | 9.47s | 全量地图 JSON 和世界坐标解析 |
| `import_lootdrop_rates` 显示 | 11.61s | 实际包含约 10s 的 item 坐标链查询 |
| 全管道 | 50.58s | PipelineTimer 汇总 |

日志中 `item_coord_chain_map` 从 `22:09:27` 到 `22:09:37`，约耗时 10s。它发生在
`import_lootdrop_rates` phase 退出之后、下一个 timer step 开始之前，因此被错误归入
上一个 timer step。该查询是：

```text
lootdrop_rate_items
  -> lootdrop_groups
  -> spawner_entries
  -> DISTINCT item_name, spawner_keyword
```

SQLite 查询计划显示扫描 `lootdrop_rate_items`，为两张表创建 automatic covering index，
并建立 DISTINCT 临时 B-tree。`DropRateEngine.preload()` 已经构建了等价的
`base_item -> spawner_keyword` 内存索引，后续应移除这次重复 SQL。

## 目标

- DB 不存在时执行一次完整、原子的初始导入。
- DB 存在且源数据未变化时跳过全部 importer，只使用 DB 生成 JSON。
- DB 过期时重新构建完整 DB，但不让半成品覆盖当前有效 DB。
- 删除或新增源文件也能被检测到，不能只比较“最新文件 mtime”。
- 生成阶段继续遵守 DB-only 边界：stale 检查只读取路径、mtime、size 或 manifest，
  不读取游戏 JSON 内容；所有游戏 JSON 内容仍只在 importer 阶段写入 DB。
- 导入阶段、导出阶段和交付阶段职责明确，PipelineTimer 不再跨阶段错误归属耗时。
- 修复后热 DB、源数据未变化的运行应跳过约 9.47s 地图解析和重复 importer；同时移除
 约 10s 的 item 坐标链 SQL 查询。

## 生命周期状态

定义唯一的数据库准备状态：

```text
DB_MISSING
  -> REBUILD_REQUIRED

DB_EXISTS + source fingerprint differs
  -> REBUILD_REQUIRED

DB_EXISTS + source fingerprint equal + schema compatible
  -> DB_READY

source unavailable + valid DB exists
  -> DB_READY_FROM_EXISTING

source unavailable + DB missing/invalid
  -> FAIL_FAST
```

`GAME_ROOT.exists()` 只表示源数据是否可访问，不再决定是否导入。

### 源目录不可用时的强制保护

源数据不可用必须与“源数据为空”严格区分：

```text
source_available = False
  !=
source_available = True and source_files = 0
```

硬性规则：

- `GAME_ROOT` 或任一必需 source root 不存在时，freshness 检查返回
  `SOURCE_UNAVAILABLE`，不能返回 `STALE`。
- `SOURCE_UNAVAILABLE + 有效 DB` 只能走 DB-only；正式 DB 路径、mtime、大小和内容
  均不得改变。
- `SOURCE_UNAVAILABLE + DB 缺失/无效` 必须 fail fast，并返回“无法重建 DB”的错误；
  不得先连接 SQLite 创建空 DB。
- `--rebuild-db` 也必须先验证 source_available；源目录不存在时拒绝执行，不能成为
  删除 DB 的旁路。
- 不允许以 `latest_source_mtime = 0`、空 manifest 或空目录 manifest 表示“源比 DB 旧”。
  manifest 无法读取时是 `SOURCE_UNAVAILABLE`，不是 fresh/stale。
- 任何 `unlink(DB_PATH)` 都必须从正式入口删除；stale 判断函数只能返回状态，不能
  直接执行删除。
- 推荐始终写 `darkfindv5.db.building` 并在成功后 `os.replace()`，正常流程不删除正式
  DB。这样即使 source 在运行中消失，也只会使 building DB 失败，不会破坏正式 DB。

## 方案设计

### 1. stale 检查必须在打开 DB 之前

新增独立模块，建议放在 `api/src/db_freshness.py`：

```python
freshness = inspect_database(DB_PATH, source_roots, schema_version)
```

调用顺序固定为：

```text
main.py
  -> inspect_database()       # 此时不能创建 sqlite 连接
  -> decide DB_MISSING/FRESH/STALE
  -> collector.run(import_required=...)
  -> DatabaseManager()
```

不能先执行 `DatabaseManager(DB_PATH)` 再判断，因为 SQLite 连接可能创建 DB 文件并
更新 mtime，导致空 DB 被误判为新 DB。

### 2. 使用 source manifest，不只比较最新 mtime

只比较：

```text
latest_source_mtime > db_mtime
```

无法检测源文件删除，也无法识别某些目录层级中的内容替换。因此使用持久化 manifest：

```json
{
  "schema_version": 1,
  "sources": {
    "translations": {"file_count": 0, "max_mtime_ns": 0, "total_size": 0, "digest": "..."},
    "entities": {"file_count": 0, "max_mtime_ns": 0, "total_size": 0, "digest": "..."},
    "modules": {"file_count": 0, "max_mtime_ns": 0, "total_size": 0, "digest": "..."},
    "spawners": {"file_count": 0, "max_mtime_ns": 0, "total_size": 0, "digest": "..."},
    "maps": {"file_count": 0, "max_mtime_ns": 0, "total_size": 0, "digest": "..."},
    "lootdrops": {"file_count": 0, "max_mtime_ns": 0, "total_size": 0, "digest": "..."},
    "quests": {"file_count": 0, "max_mtime_ns": 0, "total_size": 0, "digest": "..."}
  }
}
```

建议第一阶段将 manifest 存在 DB 的 `pipeline_meta` 表中，避免旁路文件和 DB 脱节：

```sql
CREATE TABLE IF NOT EXISTS pipeline_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
```

至少保存：

- `schema_version`
- `import_complete`
- `source_manifest`
- `source_latest_mtime_ns`
- `import_completed_at`
- `generator_version`

为了兼容现有 DB：没有 `pipeline_meta` 或 `import_complete != 1` 时必须视为 stale，
不能直接复用。

### 3. 源数据分组与导入依赖

第一阶段可以采用“任意源组变化就完整重建”的安全策略，不立即实现局部增量：

```text
translations / entities / modules / spawners / maps / lootdrops / quests
  任意 fingerprint 变化
    -> 全量重建 DB
```

完整重建顺序固定为：

```text
translations
-> items / monsters / props / dungeon_modules
-> spawner_entries
-> monster_name_map
-> load_all_spawner_data
-> lootdrop relationships
-> maps/spawners 坐标
-> fallback entities
-> rebuild entity classification
-> quests
-> lootdrop_groups / rate_items / rate_weights
-> write pipeline_meta(import_complete=1)
```

`entity_classification` 在 fallback entities 写入后必须重新构建；该顺序是已有数据正确
性的强制约束，不能因为引入 stale 分支而提前缓存旧 classification。

### 4. 原子重建，禁止半成品 DB

不直接删除并重写唯一正式 DB。采用临时路径：

```text
darkfindv5.db
darkfindv5.db.building
```

流程：

1. stale 或 missing 时，在 `darkfindv5.db.building` 创建全新 schema。
2. 所有 importer 只写 `.building`。
3. 每个阶段记录行数和关键表非空校验。
4. 最后写 `pipeline_meta.import_complete=1` 和 source manifest。
5. 关闭连接。
6. 用 `os.replace(building_db, DB_PATH)` 原子替换正式 DB。
7. 失败时删除 `.building`，保留旧 DB；若原 DB 不存在则明确失败。

这样即使地图解析、lootdrop 导入或 quest 导入中途异常，也不会留下“看起来存在但内容
不完整”的 DB。

### 5. 规范 collector 入口

`collector.run()` 改为接收明确的模式，而不是自行根据目录存在与否决定：

```python
run(import_required=False)  # fresh DB，纯 DB 导出
run(import_required=True, db_path=building_db)  # 全量构建
```

规则：

- `import_required=False`：禁止调用任何 importer；只调用 repositories、builders、exporters。
- `import_required=True`：只对 building DB 调用完整 importer 顺序。
- 不允许“DB 存在但仍部分首次导入”的混合模式。
- `--rebuild-db` 可作为显式强制重建开关，忽略 freshness 结果。
- 源目录不存在时，若 DB 有效则走 DB-only；若 DB 无效则 fail fast，不创建空 DB 后继续导出。

### 6. 修复计时边界

每个阶段必须用独立 `with pipe.step(...)` 包住完整操作，不能依赖下一阶段开始时
自动结束上一个 timer：

```text
source freshness
DB import: each importer separately
DB export preparation
item_coord_chain_map / replacement index
entity export
module export
drop rate preload
lootdrop index
lootdrop details
enrichment
quest export
locale export
delivery
```

这样 `item_coord_chain_map` 不会伪装成 `import_lootdrop_rates` 耗时，才能准确判断优化
收益。

## item_coord_chain_map 优化

当前最直接的实现方式是复用 `DropRateEngine` 已有索引：

```text
DropRateEngine.preload()
  -> _ld_rate_items
  -> _ld_id_to_groups
  -> _group_to_spawners
  -> _base_item_spawners
```

然后将 `collector.py` 的三表 JOIN 替换为：

```python
item_coord_chain_map = {
    base: set(spawners)
    for base, spawners in drop_engine.base_item_spawners.items()
}
```

需要先调整准备顺序，使 `DropRateEngine.preload()` 在 `export_items()` 之前可用；
`modules_data` 由 DB 和已加载的 items/monsters/props 构建，不依赖实体 JSON 已经写出，
可在不改变 DB-only 边界的前提下前移模块数据准备。若不希望调整顺序，则新增一个只构建
该反向索引的 preload 子阶段，禁止再次执行三表 JOIN。

验收必须对比旧 SQL map 与新内存 map 的 key 和 spawner 集合完全一致，尤其覆盖：

- `_8001` 和普通品质后缀合并
- 空 entity_name 的容器
- `spawner_keyword != entity_name`
- 链式坐标不能经过物品名 `filter_coords()`

## 测试矩阵

### Freshness

- DB 不存在：创建 building DB，完整导入，成功后原子替换。
- DB 存在且 manifest 相同：所有 importer 调用次数为 0。
- DB mtime/manifest 早于源：完整重建。
- 新增源文件：触发重建。
- 删除源文件：manifest 差异触发重建。
- 源目录不可用且 DB 有效：DB-only 成功。
- 源目录不可用且 DB 缺失：fail fast，不创建空 DB。
- `GAME_ROOT` 不存在且 DB 有效：DB 文件 inode、mtime、大小保持不变，不能调用 unlink。
- 必需 source root 部分缺失：按 `SOURCE_UNAVAILABLE` 处理，不得生成空 manifest 或触发重建。
- 源目录不可用时使用 `--rebuild-db`：拒绝执行且正式 DB 保持不变。
- 导入中途抛错：正式 DB 不被替换，building DB 被清理。
- schema/generator version 不兼容：强制重建。

### 数据语义

- 固定 items、monsters、props、lootdrops JSON 抽样对比。
- `group_drop_info`、变体、零率清理、坐标、translation key 集合不变。
- `item_coord_chain_map` 新旧集合对比。
- DB 重建后 `pipeline_meta.import_complete=1` 且 manifest 可复核。

### 性能

- 源未变化的热 DB：确认跳过 importer 和地图解析。
- 源变化的冷 DB：确认完整导入时间不劣于当前基线。
- 独立记录 freshness、item chain、map extraction、lootdrop、delivery 时间。

## 实施阶段

1. **阶段 A：生命周期修复**
   - 新增 freshness/manifest API。
   - 恢复 DB 打开前 stale 判断。
   - 增加明确 DB-only / full import 模式。
2. **阶段 B：原子导入**
   - building DB、完成标记、行数校验、原子替换。
   - 增加 `--rebuild-db` 和失败清理。
3. **阶段 C：移除 10 秒重复 JOIN**
   - 前移/拆分 DropRateEngine preload，复用 `_base_item_spawners`。
   - 修正 PipelineTimer 阶段边界。
4. **阶段 D：精细增量**
   - 仅在全量重建稳定后，按 source group 分别跳过不相关 importer。
   - 不在第一阶段引入局部表更新，避免依赖链再次失控。

## 回退策略

- freshness 判断异常时，允许 `--rebuild-db` 强制全量构建。
- manifest 不存在或格式错误时按 stale 处理，不信任旧 DB。
- 原子替换失败时保留旧正式 DB和 building DB 日志，禁止静默覆盖。
- 不恢复“GAME_ROOT 存在即导入”的隐式行为。

## 状态

状态：阶段 A-C 已完成并验证；阶段 D 精细增量暂不实施。

### 已完成

- 新增 `api/src/db_freshness.py`：只读取 source root 的路径、文件名、大小和 mtime，
  生成 manifest；不读取游戏 JSON 内容。核心实体表必须存在且非空，metadata-only DB
  不会被误判为有效。
- `inspect_database()` 已定义 `DB_READY`、`DB_ONLY`、`REBUILD_REQUIRED` 和
  `FAIL_FAST` 决策；source root 不可用时不会返回 stale。
- 源不可用且有效 DB 存在时返回 `DB_ONLY`；源不可用且 DB 缺失/无效时 fail fast；
  `--rebuild-db` 在源不可用时同样 fail fast。
- schema 新增 `pipeline_meta`，`DatabaseManager` 新增 meta 读写接口。
- `collector.run()` 已接收 `import_required`、`db_path` 和 `source_manifest`，不再以
  `GAME_ROOT.exists()` 隐式决定 importer。
- `main.py` 已增加 `--rebuild-db`、building DB 路径和 `os.replace()` 原子替换入口；
  stale 判断在 `DatabaseManager()` 之前执行，正式 DB 不在 normal rebuild 路径被 unlink。
- DB-only 使用 SQLite read-only 连接，跳过 schema 创建和 migration；source 不可用时复用
  legacy DB 不会改写正式 DB。
- full import 在写 `pipeline_meta.import_complete=1` 前校验 building DB 的核心数据，写入
  manifest、generator/schema version 和 UTC `import_completed_at` 后才原子替换。
- `item_coord_chain_map` 已改为复用 `DropRateEngine.base_item_spawners`，并独立计时；
  空 spawner 集合不保留，实际新旧索引均为 529 个 item key。

### 验证（2026-08-02）

- `python3 -m unittest discover -s api/tests -p 'test_*.py'`：27 tests OK。
- Ruff、Black、Python 编译、Prettier 和 TypeScript 均通过。
- 最终强制 full rebuild 成功：`38.45s`，building DB 写入 6 项 `pipeline_meta` 后替换正式 DB。
- 最终 hot DB-only 成功：`24.84s`，日志确认 `DB_READY` 且无 importer / 地图解析阶段。
- 旧 SQL JOIN 对照和内存索引均为 529 个 item key，独立阶段耗时低于日志显示精度。
- quick SSG 成功：3,067 routes、12,007 localized HTML、17,011 dist files；
  `http://localhost:8080/` 返回 HTTP 200。

### 后续

1. 阶段 D 可在需要时按 source group 实现局部 importer 跳过；当前任意 manifest 变化仍安全地完整重建。
