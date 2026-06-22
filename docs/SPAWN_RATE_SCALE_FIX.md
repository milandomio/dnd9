# SpawnRate 缩放比例修复

## 根因

`db_manager.py:1089` 硬编码 `raw_rate / 10000 * 100`，假设所有 Spawner 的总池 = 10000，但实际游戏不同 Spawner 总池不统一：

| Spawner | 总池 (SpawnRate 之和) | 对当前公式的影响 |
|---------|----------------------|----------------|
| ChestSpecial | 10,000 | ✅ 正确 |
| ChestMedium | ~1,000,000 | ❌ 偏大 100× |
| ChestLarge | ~1,000,000 | ❌ 偏大 100× |
| OrnateChestLargeRandom | ~1,450,040 | ❌ 偏大 ~145× |

受影响的实体包括所有来自非 ChestSpecial 的宝箱/容器类道具。

## 修复方案

在 `api/src/db_manager.py` 的 `import_spawner_entries()` 中，拆分为三种情况：

### 第一步：计算聚合值

```python
# 当前 spawner 文件所有条目的 SpawnRate 总和（用作无 DG 条目的分母）
_total_pool = max(sum(item.get("SpawnRate", 10000) for item in items), 1)

# 按 grade 后缀（地图分组代码）聚合 SpawnRate
# 例如 grade=1001 → suffix=1(GoblinCave), grade=2022 → suffix=22(Crypt)
_suffix_totals: dict[int, int] = {}
for item in items:
    dg_list = item.get("DungeonGrades", []) or []
    if dg_list:
        suffixes = set(g % 1000 for g in dg_list)
        sr = item.get("SpawnRate", 10000)
        for s in suffixes:
            _suffix_totals[s] = _suffix_totals.get(s, 0) + sr
```

### 第二步：三种分支

| 情况 | 条件 | 公式 |
|------|------|------|
| **有 DG** | `item.get("DungeonGrades")` 非空 | `raw_rate / _suffix_totals[suffix] * 100`，跨 suffix 取 min |
| **无 DG + 多条目** | `DG=[]` 且 spawner 条目数 > 1 | `raw_rate / _total_pool * 100` |
| **单条目** | spawner 条目数 == 1 | `raw_rate / 10000 * 100`（硬编码兜底）|

替换原有硬编码公式：`spawn_rate = round(min(_rates), 2) if _rates else round(raw_rate / 10000 * 100, 2)`

### 效果验证

| 实体 | 所在 Spawner | SpawnRate | 总池 | 旧值 | 新值 |
|------|-------------|-----------|------|------|------|
| CofferSmall (迷你宝盒) | ChestMedium | 30,000 | ~1,000,000 | 300% | 3% |
| SimpleChestMedium | ChestLarge | 549,960 | ~1,000,000 | 5,499.6% | 55% |
| OrnateChestLarge (狮头无锁) | ChestSpecial | 2,500 | 10,000 | 25% | 25% (不变) |
| OrnateChestLarge_Locked | ChestSpecial | 2,500 | 10,000 | 25% | 25% (不变) |
| OrnateChestLarge | OrnateChestLargeRandom | 35,000 | ~1,450,040 | 350% | 2.41% |
| GoldChest | GoldChest | 10,000 | 10,000 | 100% | 100% (不变, 单条目) |

### 狮头宝箱锁+无锁合计（前端已合并）

`enrichment.py`（原 `collector.py`）中 locked-merge 逻辑取 `_spawn_rate_detail` 中 same-keyword 的 locked + unlocked 之和，跨 keyword 取 max。

- ChestSpecial 下：25+25=50%
- OrnateChestLargeRandom 下：2.41+1.03=3.44%
- 面板显示：max(50, 3.44) = **50%**（由 ChestSpecial 提供）

## 涉及文件

- `api/src/db_manager.py` — `import_spawner_entries()` 第 1071~1098 行
- **无需修改** enrichment.py/drop_rate.py/前端（数据管道输出正确值后自动生效）

## 重建命令

```bash
git commit -am "WIP: fix spawn_rate scale - per-spawner total pool"
cd api && python main.py
cd ../web && npm run build
```
