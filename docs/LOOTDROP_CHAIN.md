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

## 问题（已部分缓解）

### `_spawner_ldg` 首次命中覆盖

`collector.py` 第 1304-1311 行：

```python
for _row in _c.execute(
    "SELECT DISTINCT spawner_keyword, entity_name, lootdrop_group_id FROM spawner_entries WHERE lootdrop_group_id != ''"
):
    for _key in (_row["spawner_keyword"], _row["entity_name"]):
        if _key and _key not in _spawner_ldg:
            _spawner_ldg[_key] = _row["lootdrop_group_id"]
```

`spawner_keyword`（如 `SkeletonFootmanFromFakeDeath`）有多个 variant 记录，但仅存储**第一条**遇到的。但 `entity_name` 键（含 `_Unique`/`_Elite` 等后缀）各 variant 独立不冲突。

**缓解原因**（2025-06 修复）：`_get_group_drop_rates()` 使用 `entity_name`（含质量后缀）作为查询键（`collector.py:1702`），精确命中 Unique 变体的正确 group_id。**非已知 bug** 导致 BloodsapBlade 爆率计算失败（前次 session 确认 `group_drop_info` 正确填充）。

**仍存风险**：若通过 `spawner_keyword`（不含后缀）查询，会错误命中第一条记录的对应 variant。当前代码路径无此调用，但需注意后续改动。
