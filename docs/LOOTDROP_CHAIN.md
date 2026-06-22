# 掉落坐标关系链

## BloodsapBlade 坐标链示例

```
Id_Item_BloodsapBlade_5001
  →
  lootdrop_items: item_name="BloodsapBlade_5001", monster_name="SkeletonFootmanFromFakeDeath"
  lootdrop_name="Spawn_SkeletonFootmanFromFakeDeath_Unique"
    →
    lootdrop_groups: group_id="Id_LootDropGroup_SkeletonFootmanUnique"
    lootdrop_id="Id_Lootdrop_Spawn_SkeletonFootmanFromFakeDeath_Unique"
      →
      spawner_entries: spawner_keyword="SkeletonFootmanFakeDeath" + "SkeletonFootmanFromFakeDeath"
      entity_name="SkeletonFootmanFromFakeDeath_Unique"
      lootdrop_group_id="Id_LootDropGroup_SkeletonFootmanUnique"
        →
        spawners: keyword="SkeletonFootmanFromFakeDeath"
        包含两类坐标：
          1. original_keyword="SkeletonFootmanFromFakeDeath" — 直接引用
          2. original_keyword="SkeletonFootmanFakeDeath" — 多实体展开（search_engine.py multi_entity 逻辑）
```

## 三维坐标来源

| 来源 | 生成器 | entity_name | 坐标数 |
|------|--------|-------------|--------|
| 直接 spawner | `SkeletonFootmanFromFakeDeath` | `SkeletonFootmanFromFakeDeath_*` | varies |
| 多实体展开 | `SkeletonFootmanFakeDeath` → 展开为 `SkeletonFootmanFromFakeDeath` | `SkeletonFootmanFromFakeDeath_*` | varies |

## 关键代码路径

### 1. 坐标提取 — `search_engine.py:extract_spawners()`
```
map JSON BP_GameSpawner_C
  → ObjectName = "Id_Spawner_Monster_SkeletonFootmanFakeDeath"
  → strip_id_prefix → keyword = "SkeletonFootmanFakeDeath"
  → multi_entity_spawners 命中 → 展开为 entity_name "SkeletonFootmanFromFakeDeath"
  → DB: spawners.keyword = "SkeletonFootmanFromFakeDeath"
         spawners.original_keyword = "SkeletonFootmanFakeDeath"
```

### 2. 物品-怪物关联 — `db_manager.py:import_lootdrops()`
```
LootDrop JSON → LootDropGroup JSON
  → lootdrop_name "Spawn_SkeletonFootmanFromFakeDeath_Unique"
  → spawner_monster_map 覆盖 → monster_name = "SkeletonFootmanFromFakeDeath"
  → DB: lootdrop_items (BloodsapBlade_5001, SkeletonFootmanFromFakeDeath, ...)
```

### 3. 爆率查询 — `collector.py`
```
_spawner_ldg 构建：
  SELECT spawner_keyword, entity_name, lootdrop_group_id FROM spawner_entries
  → 优先存储首次出现的映射（当前 BUG: 相同 keyword 的多 variant 覆盖丢失）

_get_group_drop_rates(monster_name)：
  → _spawner_ldg.get(monster_name, "") → 映射到错误的 LootDropGroup
```

## 已知问题

### Bug: `_spawner_ldg` 首次命中覆盖

`drop_rate.py`（原 `collector.py`）：

```python
for _row in _c.execute(
    "SELECT DISTINCT spawner_keyword, entity_name, lootdrop_group_id FROM spawner_entries WHERE lootdrop_group_id != ''"
):
    for _key in (_row["spawner_keyword"], _row["entity_name"]):
        if _key and _key not in _spawner_ldg:
            _spawner_ldg[_key] = _row["lootdrop_group_id"]
```

一个 `spawner_keyword`（如 `SkeletonFootmanFromFakeDeath`）可能在多条记录中出现，对应不同 variant（Common/Elite/Nightmare/Unique）的 lootdrop_group_id。但当前逻辑仅存储**第一条**遇到的，后续 variant 的 group_id 被静默丢弃。

**影响**：Unique 物品（如 BloodsapBlade）的爆率被计算在 Common group 下 → 返回 `0.0`。

**修复方案**：构建 `entity_ldg_map: dict[str, set[str]]` 存储实体名称到所有可能 group_id 的映射，在 `_get_group_drop_rates` 中按优先级尝试。
