# P002: collector.py 按职责拆分（优化版）

## 进度追踪

| Step | 模块 | 状态 | 完成时间 | 备注 |
|------|------|------|---------|------|
| 1 | translator.py | ✅ 完成 | 2026-06-22 | ~250 行，含 NameResolver 类 |
| 2 | entity_export.py | ✅ 完成 | 2026-06-22 | ~200 行，含 export_items/monsters/props |
| 3 | index_export.py | ✅ 完成 | 2026-06-22 | ~260 行，含 quest/index 导出 |
| 4 | drop_rate.py | ✅ 完成 | 2026-06-22 | ~280 行，含 DropRateEngine 类 |
| 5 | module_builder.py | ✅ 完成 | 2026-06-22 | ~550 行，含 build_modules_map/build_map_mappings/build_module_coords/build_modules_data |
| 6 | lootdrop_builder.py | ✅ 完成 | 2026-06-22 | ~520 行，含 build_merged_loot_map/build_loot_index/build_and_save_lootdrop_details |
| 7 | enrichment.py | ✅ 完成 | 2026-06-22 | ~260 行，含 group_drop_info 注入 + 零爆率清理 |
| 8 | collector.py 最终清理 | ✅ 完成 | 2026-06-22 | 移除未用函数/变量，454 行 |

**最终状态：**
- `collector.py`: 454 行（原始 2581 行，已减少 82.4%）
- `enrichment.py`: 262 行
- `module_builder.py`: 547 行
- `lootdrop_builder.py`: 518 行
- `drop_rate.py`: ~280 行
- `translator.py`: ~250 行
- `entity_export.py`: ~200 行
- `index_export.py`: ~260 行
- 验证命令：`cd api && python main.py`（返回 0）+ `./lint.sh`（通过）
- items/monsters/lootdrops 与基线完全匹配，props 仅条目顺序不同（数据一致）
- dungeon_modules.json、module coords 253 文件、lootdrops.json 均与基线一致

**下一步（Step 7: enrichment.py）：**
- 移 collector.py 中 group_drop_info 注入代码（items/monsters/props + 零爆率清理）

**Step 7-8 待提取代码位置（当前行号，Step 6 完成后）：**
- Step 7: lines 420-650（enrichment：group_drop_info 注入 items/monsters/props + 零爆率清理）
- Step 8: 最终清理

---

## Context

`collector.py` 已膨胀至 2580 行，其中 `run()` 函数约 2100 行，包含 17 个阶段（A-Q）。原计划提出 6 模块拆分，但模块边界与实际代码内聚性不匹配。本方案基于完整的代码依赖分析，提出 7 个新模块 + 1 个精简协调器。

**核心约束：**
- 不改数据流架构（Python → 静态 JSON → React SSG）
- 不改 DB schema、不改 JSON 输出格式
- `python main.py` 返回 0，`ruff check src/` 通过，JSON 输出与拆分前完全一致

## 模块总览

| 模块 | 路径 | 行数 | 来源阶段 |
|------|------|------|---------|
| `translator.py` | `api/src/translator.py` | ~170 | D + regex + 辅助函数 |
| `drop_rate.py` | `api/src/drop_rate.py` | ~500 | N.1, N.2, N.3 |
| `module_builder.py` | `api/src/module_builder.py` | ~500 | I, J, K, L |
| `lootdrop_builder.py` | `api/src/lootdrop_builder.py` | ~400 | E, M, N.5 |
| `entity_export.py` | `api/src/entity_export.py` | ~200 | F, G, H |
| `enrichment.py` | `api/src/enrichment.py` | ~300 | O |
| `index_export.py` | `api/src/index_export.py` | ~350 | P, Q |
| `collector.py` | `api/src/collector.py` | ~350 | A, B, C 协调 |

## 迁移顺序（风险从低到高）

### Step 1: translator.py（风险：低）

**移动内容：**
- 所有 regex 常量（lines 53-90）：`_VARIANT_RE`, `_HARD_SUFFIX_RE`, `_UNIQUE_SUFFIX_RE`, `_QUALITY_RE`, `_ORE_QUALITY_RE`, `_ORE_ITEM_STRIP_RE`, `_ORE_ITEM_COORD_RE`, `_RESOLVE_STRIP_RE`, `_RESOLVE_FUZZY_RE`, `_RESOLVE_FUZZY_PASS2_RE`, `_DEBUG_VARIANT_RE`, `_LOCKED_RE`
- `_DUMMY_AS_MONSTER` 集合（lines 92-100）
- `resolve_name` 闭包 → 重构为 `NameResolver` 类（lines 397-529）
  - `__init__(self, translations: dict)` — 持有 translations dict
  - `resolve(self, name, translation_key=None, scope="item")` — 替代原闭包
  - 内部 `_resolve_name_inner` + `cracked_re` 逻辑不变
- `_build_coord_out`（lines 592-608）— 纯函数，只依赖 `HARDCODED_TRANSLATIONS`
- `_filter_coords`（lines 380-388）— 纯函数
- `_base_monster_name`（lines 1297-1302）— 纯函数
- `_ore_quality_key` + `_ORE_QUALITY_ORDER`（lines 710-714）

**接口：**
```python
class NameResolver:
    def __init__(self, translations: dict[str, str]): ...
    def resolve(self, name: str, translation_key: str | None = None, scope: str = "item") -> str: ...

def build_coord_out(c: dict, coord_variant_count: dict) -> dict: ...
def filter_coords(coords: list[dict], entity_names: set[str], is_prop: bool = False) -> list[dict]: ...
def base_monster_name(name: str) -> str: ...
def ore_quality_key(name: str) -> tuple: ...
```

**依赖：** `config.py`（HARDCODED_TRANSLATIONS, TRANSLATION_ALIAS_MAP, MODULE_NAME_OVERRIDE）

**collector.py 改动：**
- `from translator import NameResolver, build_coord_out, filter_coords, base_monster_name, ore_quality_key, ...`
- `resolver = NameResolver(translations)` 替代 `resolve_name` 闭包
- 所有 `resolve_name(x, y, z)` → `resolver.resolve(x, y, z)`

**验证：** diff 所有输出 JSON

---

### Step 2: entity_export.py（风险：低）

**移动内容：**
- Phase F: Items 导出（lines 610-650）
- Phase G: Monsters 导出（lines 652-705）
- Phase H: Props 导出（lines 707-784）

**接口：**
```python
def export_items(items, merged_loot, all_coords, resolve_name, skip_variants, coord_variant_count, output_dir) -> list[dict]: ...
def export_monsters(monsters, all_coords, resolve_name, coord_variant_count, output_dir) -> list[dict]: ...
def export_props(props, all_coords, resolve_name, props_spawner_info, coord_variant_count, output_dir) -> list[dict]: ...
```

**依赖：** `translator.py`, `config.py`

**验证：** diff items.json, monsters.json, props.json 及其详情目录

---

### Step 3: index_export.py（风险：低）

**移动内容：**
- Phase P: Quest 数据导出（lines 2168-2187）
- `_generate_quest_items_groups` 函数（lines 2319-2482）
- Phase Q: index.json + search_index.json（lines 2189-2304）

**接口：**
```python
def save_quest_data(db, output_dir) -> tuple[int, int, int, list[dict]]: ...
def generate_quest_items_groups(db, merged_loot, resolve_name, all_coords, modules, output_dir) -> None: ...
def build_and_save_indexes(items_index, monsters_index, props_index, loot_index, modules_data,
                           explore_count, quest_items_count, quest_npc_count, quest_npcs_data, output_dir) -> None: ...
```

**依赖：** `db_manager.py`, `translator.py`, `config.py`

**验证：** diff index.json, search_index.json, explore/quest_*/quest_items_groups/

---

### Step 4: drop_rate.py（风险：中）

**移动内容：**
- Phase N.1: 爆率数据预加载（lines 1304-1385）— `_spawner_ldg`, `_entity_ldg_all`, `_ore_ldg`, `_ld_groups`, `_ld_rate_items`, `_ld_luck_grade_count`, `_ld_rate_weights`, `_ld_rate_totals`, `_map_base_to_group`
- Phase N.2: 5 个计算函数（lines 1393-1575）— `_compute_drop_rate`, `_get_group_drop_rates`, `_compute_group_drop_rates`, `_compute_container_drop_rates`, `_compute_variant_rate`
- Phase N.3: spawn rate 缓存预加载（lines 1577-1626）— `_spawn_rate_cache`, `_spawn_rate_detail`, `_spawn_rate_by_mode`, `_entity_spawners`
- `_round_rate`, `_variant_suffixes`

**接口：**
```python
class DropRateEngine:
    def preload(self, db: DatabaseManager, modules_data: list[dict]) -> None: ...

    # 计算方法
    def compute_drop_rate(self, ldg_id: str, item_name: str, full_grade: int) -> float: ...
    def get_group_drop_rates(self, item_name: str, monster_name: str, group_key: str) -> dict[str, float]: ...
    def compute_group_drop_rates(self, ldg_id: str, group_key: str) -> dict[str, float]: ...
    def compute_container_drop_rates(self, ldg_id: str, group_key: str) -> dict[str, float]: ...
    def compute_variant_rate(self, ldg_id, luck_grade, full_grade, target_ld_id="", rt_cache=None) -> float: ...

    # 只读属性（供 lootdrop_builder/enrichment 访问）
    @property
    def spawner_ldg(self) -> dict[str, str]: ...
    @property
    def entity_ldg_all(self) -> dict[str, set[str]]: ...
    @property
    def ore_ldg(self) -> dict[str, str]: ...
    @property
    def spawn_rate_cache(self) -> dict[str, float]: ...
    @property
    def spawn_rate_detail(self) -> dict[tuple[str, str], float]: ...
    @property
    def spawn_rate_by_mode(self) -> dict[tuple[str, str], dict[str, float]]: ...
    @property
    def entity_spawners(self) -> dict[str, set[str]]: ...
    @property
    def map_base_to_group(self) -> dict[str, str]: ...
```

**依赖：** `db_manager.py`, `config.py`, `translator.py`（regex 常量）

**关键决策：** 用类而非模块函数，因为 5 个计算函数引用 7+ 个预加载 dict，作为方法可直接访问 `self._ld_groups`，避免每个函数传 7 个参数。

**注意：** `preload()` 需要 `modules_data`（来自 module_builder），因此必须在 module_builder 之后调用。

**验证：** diff lootdrops/*.json（每个文件必须完全匹配）

---

### Step 5: module_builder.py（风险：中）

**移动内容：**
- Phase I: 地图模块构建 + 图片解析（lines 786-906）
- Phase J: Module-Map 双向映射（lines 907-924）
- Phase K: 模块坐标构建（lines 926-1117）
- Phase L: 模块列表过滤保存（lines 1119-1183）
- `_resolve_img`（lines 2523-2580）
- `_match_in_dir`（lines 2485-2520）

**接口：**
```python
def build_modules_map(db, resolve_name) -> dict[str, dict]: ...
def build_map_mappings(modules_map) -> tuple[dict[str, str], dict[str, set[str]]]: ...
def build_and_save_module_coords(db, modules_map, map_to_module, resolve_name,
                                  items, monsters, props, output_dir) -> dict[str, dict]: ...
def build_and_save_modules_data(modules_map, module_to_maps, merged_coords, output_dir) -> list[dict]: ...
```

**依赖：** `db_manager.py`, `translator.py`, `config.py`, `layout_utils.py`

**验证：** diff dungeon_modules.json, dungeon_modules_coords/, entity_index.json

---

### Step 6: lootdrop_builder.py（风险：中高）

**移动内容：**
- Phase E: 合并 lootdrop 映射（lines 531-590）
- Phase M: Lootdrops 索引（lines 1185-1265）
- Phase N.5: Lootdrops 详情主循环（lines 1668-1913）
- `_classify_label` + `_label_type_suffix`

**接口：**
```python
def build_merged_loot_map(db) -> tuple[dict, dict, set, dict, dict]: ...
def build_loot_index(merged_loot, items, monsters, entity_class, resolve_name) -> list[dict]: ...
def build_and_save_lootdrop_details(loot_index, drop_engine, all_coords, resolve_name,
                                     og_to_keywords, coord_variant_count, output_dir) -> dict[str, float]: ...
```

**依赖：** `db_manager.py`, `translator.py`, `drop_rate.py`, `config.py`

**验证：** diff lootdrops.json, lootdrops/*.json

---

### Step 7: enrichment.py（风险：中）

**移动内容：**
- Phase O: 实体 group_drop_info 注入（lines 1923-2166）
  - O.1: 从 lootdrop 文件读取注入 items
  - O.2: 直接 spawn 物品的 group_drop_info
  - O.3: Monsters 注入
  - O.4: Props 注入（含 locked/UnderSea 变体处理）
  - O.5: 零爆率清理

**接口：**
```python
def enrich_all_entities(drop_engine, loot_index, item_max_score, modules_data, output_dir) -> None: ...
```

**依赖：** `drop_rate.py`, `config.py`

**验证：** diff items/*.json, monsters/*.json, props/*.json（group_drop_info 字段）, lootdrops.json（max_score）

---

### Step 8: collector.py 最终清理（风险：低）

**保留内容：**
- `_log()` 函数
- `_save()` 函数（各模块可直接用 `json.dump` 或从 config 导入 OUTPUT_DIR）
- `_get_newest_mtime()`, `_is_db_stale()`, `_SOURCE_PATHS`
- `_ue_asset_base_name()`
- `run()` 函数精简为 ~200 行编排代码

**精简后的 run() 结构：**
```python
def run():
    # Phase A: DB 初始化（15 行）
    # Phase B: DB 导入 9 步（150 行，委托 db_manager）
    # Phase C: 从 DB 加载实体（35 行）
    # Phase D: resolver = NameResolver(translations)（3 行）
    # Phase E: lootdrop_builder.build_merged_loot_map（5 行）
    # Phase F-H: entity_export 三函数（15 行）
    # Phase I-L: module_builder 四函数（20 行）
    # Phase M: lootdrop_builder.build_loot_index（10 行）
    # Phase N: DropRateEngine.preload + build_and_save_lootdrop_details（8 行）
    # Phase O: enrichment.enrich_all_entities（5 行）
    # Phase P-Q: index_export 三函数（15 行）
    # 清理 + 返回 timer（5 行）
```

**最终验证：**
1. `cd api && python main.py` — 返回码 0
2. `cd api && ruff check src/` — 无错误
3. diff `api/output/json/` 全部 JSON 与拆分前基线一致

---

## lootdrop_rates.py 处置

**存档，不删除。** 该模块（106 行）从未被 collector.py 导入。collector 有自己的内联实现（预加载内存缓存 + O(1) 查询），功能完全覆盖且性能更优。新的 `drop_rate.py` 取代其全部功能。

移动到存档目录：
```bash
mkdir -p api/src/_archived
mv api/src/lootdrop_rates.py api/src/_archived/
```

---

## 依赖关系图

```
config.py
  └─► translator.py
        └─► entity_export.py
        └─► module_builder.py (+ layout_utils.py, db_manager.py)
        └─► drop_rate.py (+ db_manager.py)
              └─► lootdrop_builder.py
              └─► enrichment.py
        └─► index_export.py (+ db_manager.py)
  └─► collector.py（协调所有模块 + db_manager + pipeline_timer + quest_collector + search_engine）
```

## 接口参数上限

| 模块 | 最多参数 | 函数 |
|------|---------|------|
| entity_export.py | 7 | `export_items` |
| lootdrop_builder.py | 7 | `build_and_save_lootdrop_details` |
| index_export.py | 10 | `build_and_save_indexes` |
| module_builder.py | 8 | `build_and_save_module_coords` |

均在可接受范围内，无需引入 Context/Options 对象。

## 基线建立（实施前）

```bash
cd api && python main.py
cp -r output/json/ /tmp/p002_baseline_json/
```

每个 Step 完成后：
```bash
diff -r /tmp/p002_baseline_json/ api/output/json/
```

## 关键文件清单

| 文件 | 角色 |
|------|------|
| `api/src/collector.py` | 拆分源（2580 行） |
| `api/src/config.py` | 所有模块共享常量 |
| `api/src/db_manager.py` | DatabaseManager |
| `api/src/lootdrop_rates.py` | 待存档（dead code，移至 `_archived/`） |
| `api/src/layout_utils.py` | module_builder 依赖 |
| `api/main.py` | 入口，调用 `collector.run()` |
