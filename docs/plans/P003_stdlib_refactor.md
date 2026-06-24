# P003: 零依赖重构 — Pipeline 抽象 + DatabaseManager 拆分 + 类型模型

## 目标

不引入任何外部框架，纯 Python stdlib 重构后端三个架构问题，提升可维护性和可读性。

## 执行顺序：2 → 1 → 3

| 顺序 | 计划 | 风险 | 预期净行数变化 | 理由 |
|------|------|------|---------------|------|
| **1** | **Pipeline 抽象** | 低 | -100 | 模板代码消除，收益立竿见影 |
| **2** | **DatabaseManager 拆分** | 中 | -0（物理重组） | 关注点分离，改1300行不用看全部 |
| **3** | TypedDict 类型模型 | 低 | +80 | 类型安全，但投入产出比最低，建议最后做 |

---

## Step 1: Pipeline 抽象（执行顺序：第1）

### 现状

`collector.py` 每个步骤重复 4 行模板代码：

```python
timer.start_step("[DB] xxx")
_log("[N/9] xxx START")
count = db.import_xxx()
_log(f"[N/9] xxx DONE -> {count}")
```

9 个步骤 × 4 行 ≈ 36 行纯模板。步骤编号 `N/9` 分散在代码里，调整顺序要手动重编号。

### 可行性验证：✅ 可行

对比预期与实际代码：

| 计划假设 | 实际代码验证 | 结论 |
|---------|-------------|------|
| 步骤模板一致 | 9/9 的 `start_step` + `_log` 模式完全一致 | ✅ 模板化可行 |
| 子步骤需处理 | Step 6 含 3 个子操作 | ✅ 需要 `substep()` 或拆成 3 个独立 step |
| step 计数自动化 | 当前硬编码 `[N/9]` | ✅ 自动计算序号 |

### 修正方案

**核心设计：** `Pipeline` 类 + 上下文管理器

```python
class Pipeline:
    def __init__(self, log_dir=None):
        self.timer = PipelineTimer(log_dir)
        self._step_count = 0

    def step(self, label: str):          # 独立步骤（自动递增序号）
        self._step_count += 1
        return _StepContext(self, label, self._step_count, total=None)

    def phase(self, label: str, total: int):  # 预知总数的阶段（如 [1/9]）
        self._step_count += 1
        return _StepContext(self, label, self._step_count, total)
```

**用法：**

```python
pipe = Pipeline(LOG_DIR)

if game_available:
    with pipe.phase("translations", 9):
        db.import_translations()
    with pipe.phase("items", 9):
        db.import_items()
    # ...
    # Step 6 拆成 3 个独立 step（避免子步骤复杂度）
    with pipe.phase("monster_name_map", 11):
        monster_name_map = db.get_monster_name_map()
    with pipe.phase("load_spawner_data", 11):
        spawner_has_lootdrop, spawner_multi_entity, spawner_monster_map = load_all_spawner_data(monster_name_map)
    with pipe.phase("import_lootdrops", 11):
        count = db.import_lootdrops(spawner_monster_map)
```

### 收益

- 消除全部 `timer.start_step`/`_log START`/`_log DONE` 模板 → **净减 ~100 行**
- 新增步骤只需 `with pipe.step("name"):`，自动计时 + 日志 + 序号
- 管道顺序一目了然，不需要手动 `N/9` 编号
- `Pipeline` 可替换测试（注入 mock timer）

---

## Step 2: DatabaseManager 拆分（执行顺序：第2）

### 现状

`db_manager.py` 1349 行，包含三类混杂职责：

| 职责 | 示例方法 | 大约行数 |
|------|---------|---------|
| **Schema 管理** | `_create_tables()`, `_migrate_spawners_table()` | ~80 |
| **数据导入** | `import_items()`, `import_monsters()`, `import_lootdrops()` 等 13 个方法 | ~600 |
| **数据查询** | `get_item_entities()`, `get_all_coordinates()`, `get_spawner_entries_for_keyword()` 等 18 个方法 | ~400 |
| **工具函数** | `_load_json_dir()`, `_extract_item_name()`, `_ue_asset_base_name()` 等 | ~200 |

### 可行性验证：✅ 可行，但需修正预期

**验证发现的关键问题：**

| 发现 | 影响 |
|------|------|
| `collector.py` step 7 有直接 raw SQL 操作 `spawners` 表（`DELETE` + `executemany`），不经过 `DatabaseManager` | `spawners` 表的插入逻辑两端都有，拆分时需要决定这一块归谁 |
| `import_spawner_fallback_entities()` 从 `spawners` 表读数据（被上面那一步写入的） | 拆分后 `importer` 之间的依赖顺序清晰了（先 SpawnerImporter → 再 FallbackImporter） |
| `_migrate_spawners_table()` 检查 `has_lootdrop` 列是否存在（历史遗留列） | 迁移检查必须保留在 `SchemaManager` |
| 每个 `import_*()` 方法各自 `DELETE FROM` 全表 | 每个 importer 独立管理自己的表，互不影响 |

### 修正后的方案

```
api/src/db/
├── __init__.py          # 导出 DatabaseManager（向后兼容）
├── schema.py            # _create_tables() + _migrate_spawners_table()
├── core.py              # DatabaseManager 基类（连接管理 + 公共查询如 get_translations_map）
├── importers/
│   ├── __init__.py
│   ├── items.py         # import_items()
│   ├── monsters.py      # import_monsters()
│   ├── props.py         # import_props()
│   ├── modules.py       # import_dungeon_modules()
│   ├── lootdrops.py     # import_lootdrops()
│   ├── quests.py        # import_quest_items/npcs/explore_targets
│   └── spawners.py      # import_spawner_entries/groups/rates/fallback_entities
└── repositories/
    ├── __init__.py
    ├── items.py         # get_item_entities(), get_items_with_matches()
    ├── monsters.py      # get_monster_entities(), get_monster_name_map()
    ├── props.py         # get_props_entities()
    ├── modules.py       # get_dungeon_modules()
    ├── coordinates.py   # get_all_coordinates(), get_coord_variant_counts()
    ├── lootdrops.py     # get_lootdrop_relationships(), get_spawner_entries_for_keyword()
    └── quests.py        # get_quest_items(), get_quest_npcs(), get_explore_targets()
```

**关于 `collector.py` step 7 的 raw SQL：**
- `spawner_rows` 的构造逻辑（`collector.py lines 196-217`）留在 `collector.py`（它是管道逻辑，不是 DB 操作）
- 但 `DELETE FROM spawners` 和 `executemany` 调用包装成 `SpawnerRepository.replace_all(spawner_rows)`
- `import_spawner_fallback_entities()` 移入 `importers/spawners.py`

**关于预期行数：**
- 拆分前：`db_manager.py` 1349 行
- 拆分后：主文件变为 import/re-export 组合模式，~50 行；其余文件各 50-150 行
- 总代码行数加上组合模式的委托方法，**预计净减为 0**（行数守恒，不变少）
- 实际收益是物理分离，不是行数减少

### 组合模式（向后兼容）

```python
# api/src/db/__init__.py
class DatabaseManager:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.schema = SchemaManager(self.conn)
        self.schema.create_tables()
        self.importers = ImporterRegistry(self.conn)
        self.repos = RepositoryRegistry(self.conn)

    # 向后兼容：所有现有方法直接委托
    def import_items(self) -> int:
        return self.importers.items.import_all()
    def get_item_entities(self) -> list[dict]:
        return self.repos.items.get_all()
    # ...
```

这样外部调用方（`collector.py`、`drop_rate.py`、`module_builder.py` 等）**不需要改任何代码**。

### 收益

- 改物品导入只需看 `db/importers/items.py`（~100 行），不需在 1349 行里找
- 每个 importer/repository 可独立单元测试（建对应表即可，不需全量创建）
- 新增实体类型时，增加一个文件即可，不需往神类加方法
- 子类不会误用父类内部变量（当前模块级和类级各有重复 regex 常量）

---

## Step 3: TypedDict 类型模型（执行顺序：第3）

### 现状

```python
def get_item_entities(self) -> list[dict]:
    c = self.conn.cursor()
    c.execute("SELECT item_name, translation_key, category, variant_count FROM item_entities")
    return [dict(r) for r in c.fetchall()]
```

调用方只能通过看 SQL 或运行时才知道字段名。

### 可行性验证：✅ 可行，但投入产出比最低

**验证各个方法的实际返回结构：**

| 方法 | 返回类型 | 字段数 | JSON 反序列化 | 可行性 |
|------|---------|--------|-------------|--------|
| `get_item_entities()` | `list[dict]` | 4 | 否 | ✅ 简单 |
| `get_monster_entities()` | `list[dict]` | 2 | 否 | ✅ 简单 |
| `get_props_entities()` | `list[dict]` | 2 | 否 | ✅ 简单 |
| `get_dungeon_modules()` | `list[dict]` | 7+2 | 是（aliases JSON） | ✅ 需处理 `json.loads` |
| `get_quest_items()` | `list[dict]` | 8 | 否 | ✅ 简单 |
| `get_quest_npcs()` | `list[dict]` | 4+1 | 是（quests JSON） | ✅ 需处理 `json.loads` |
| `get_all_coordinates()` | `dict[str, list[dict]]` | 11 | 否 | ✅ 需嵌套类型 |
| `get_spawner_entries_for_keyword()` | `list[dict]` | 5 | 是（dungeon_grades JSON） | ✅ 需处理 `json.loads` |
| `get_coord_variant_counts()` | `dict[tuple, tuple[int, list]]` | — | 否 | ✅ 已是强类型，加别名即可 |

### 方案

```python
# models.py（纯 TypedDict，零开销）
from typing import TypedDict

class ItemEntity(TypedDict):
    item_name: str
    translation_key: str
    category: str
    variant_count: int

class SpawnerCoord(TypedDict):
    keyword: str
    x: float
    y: float
    z: float
    yaw: float
    json_filename: str
    version: str
    map_base: str
    original_keyword: str
    spawner_type: str
    group_parent: str

class DungeonModule(TypedDict):
    module_name: str
    translation_key: str
    module_group: str
    size_x: int
    size_y: int
    sl_base_name: str
    map_image_name: str
    aliases: list[str]
    rotation: float
```

### 重要考量：调用方需要修改

仅仅改返回类型不够，调用方也需要从 `r["item_name"]` 改为 `r.item_name` 才能真正获得类型检查收益。这个改动面大但风险低（纯机械替换）。

现有所有调用 `r["xxx"]` 的地方需要扫描并修改：
- `collector.py`
- `entity_export.py`
- `drop_rate.py`
- `module_builder.py`
- `lootdrop_builder.py`
- `enrichment.py`
- `index_export.py`

### 收益

- IDE 自动补全 + 重构自动改名
- 消除 `r["xxx"]` 拼写错误（当前各处散落的 dict 读取）
- 数据流动边界清晰（DB → 业务逻辑 → JSON 输出各有明确模型）
- `TypedDict` 是 Python 3.8+ 内置，零依赖零运行时开销

### 建议时机

Step 2 完成后做。因为 Step 2 已经分离出 `db/repositories/xxx.py`，每个文件对应一个实体，TypedDict 定义可以放在对应的 repository 文件顶部，而不是独立的 `models.py`。更内聚：

```python
# db/repositories/items.py
class ItemEntity(TypedDict):
    item_name: str
    translation_key: str
    category: str
    variant_count: int

class ItemRepository:
    def get_all(self) -> list[ItemEntity]: ...
```

---

## 不动的内容

- 数据流架构（Python → 静态 JSON → React SSG）
- DB schema 和 JSON 输出格式
- `config.py` 常量（只改导入方式）
- 其他模块（`search_engine.py`, `quest_extractor/` 等只改第 3 步的类型标注）

## 验收标准

```bash
# 每 Step 完成后：
cd api && python main.py                      # 返回码 0
cd api && ruff check src/                      # 无错误
# JSON 输出与重构前一致（需先建基线）
diff -r /tmp/p003_baseline_json/ api/output/json/
```

## 基线建立

```bash
cd api && python main.py && cp -r output/json/ /tmp/p003_baseline_json/
```
