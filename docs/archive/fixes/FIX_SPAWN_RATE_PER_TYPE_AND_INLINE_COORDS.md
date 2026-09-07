# 修复记录：SpawnRate 按 spawner 类型区分 + 类型分裂条目内联坐标

## 问题

### 1. SpawnRate 未按 spawner 类型区分

`_group_drop_info` 中所有类型（特殊/随机/直接）共用 `get_combined_spawn_rate(_en)`，返回的是该实体在所有 spawner 中的合计，而非各 spawner 类型独立的值。

| 类型 | 实体 | 对应 Spawner | 正确 SpawnRate | 修复前显示 |
|------|------|-------------|---------------|-----------|
| 特殊 | OrnateChestLarge | ChestSpecial | 50%（25+25） | 50% ✅ |
| 随机 | OrnateChestLarge | OrnateChestLargeRandom | 3.44%（2.41+1.03） | **50% ❌** |
| 特殊 | OrnateChestMedium | ChestMedium | 5%（2.5+2.5） | 5% ✅ |
| 随机 | OrnateChestMedium | OrnateChestMediumRandom | 3.44%（2.41+1.03） | **5% ❌** |

### 2. 类型分裂条目坐标混用

P005 ref 优化将每个怪物类型的内联坐标替换为 `ref`（指向实体详情页），所有标签类型变体（重型华丽宝箱、重型华丽宝箱(特殊)(可能上锁)、重型华丽宝箱(随机)(可能上锁)）指向同一个 ref。

前端通过该 ref 获取了该实体的**全部**坐标（含所有标签类型），导致：
- 重型华丽宝箱（直接，1 坐标）显示 579 个点（含特殊+随机）
- 青铜华丽宝箱（直接，1 坐标）显示 164 个点（含组类型）
- 点击分类按钮时位置统计与标注的 `coord_count` 不一致

### 3. 浮点精度

`3.4400000000000004` 等浮点数显示不美观。

## 修复

### 文件：`api/src/lootdrop_builder.py`

#### 修复 1：SpawnRate 按 spawner 类型区分

替换 `_group_drop_info` 构建中的 `get_combined_spawn_rate(_en)`：

```python
# 旧：_sr = drop_engine.get_combined_spawn_rate(_en)
# 新：
_coord_labels = {_c["label"] for _c in _m_data["coords"] if _c.get("label")}

# 未上锁：从坐标标签查找对应 spawner_keyword 的 spawn_rate_detail
_sr_via_label = 0
for _cl in _coord_labels:
    _pair_sr = spawn_rate_detail.get((_cl, _en), 0)
    if _pair_sr > _sr_via_label:
        _sr_via_label = _pair_sr
_sr = _sr_via_label if _sr_via_label > 0 else drop_engine.get_combined_spawn_rate(_en)

# 可能上锁：从坐标标签 ∩ entity_spawners 取 locked+unlocked 之和
_common_sks = _coord_labels & entity_spawners.get(_en, set()) & entity_spawners.get(_locked_name, set())
```

同时添加 `_sr = round(_sr, 4)` 消除浮点误差。

#### 修复 2：类型分裂条目保持内联坐标

P005 ref 优化前先检测是否存在类型分裂条目：

```python
_type_suffixes = {"(特殊)", "(随机)", "组"}
_split_entities: set[str] = set()
for _m in monsters_out:
    if any(_s in _m.get("translation", "") for _s in _type_suffixes):
        _split_entities.add(_m.get("entity_name", _m["name"]))

if entity_page_map:
    for _m in monsters_out:
        if _m.get("entity_name", _m["name"]) in _split_entities:
            _m.pop("_coord_key", None)
            continue  # 保持内联坐标
        # 非分裂条目继续使用 ref 优化（如 黄金宝箱）
```

分裂实体（特殊/随机/组）存在时，**该实体的所有条目**（含直接名称）都跳过 ref，保持内联坐标。

### 修复 3：SpawnRate 精度

```python
_sr = round(_sr, 4)
```

加在 locked/non-locked 分支之后。

## 效果验证

| 条目 | coord_count | 修复前显示点数 | 修复后显示点数 |
|------|------------|--------------|--------------|
| 狮头宝箱(特殊)(可能上锁) | 17 | 25（含随机） | 17 ✅ |
| 狮头宝箱(随机)(可能上锁) | 8 | 25（含特殊） | 8 ✅ |
| 重型华丽宝箱 | 1 | 65（含特殊+随机） | 1 ✅ |
| 青铜华丽宝箱 | 1 | 164（含组） | 1 ✅ |

| 条目 | spawn_rate | 修复前 | 修复后 |
|------|-----------|--------|--------|
| 狮头宝箱(随机)(可能上锁) | 2.41+1.03=3.44% | 50% | 3.44% ✅ |
| 重型华丽宝箱(随机)(可能上锁) | 2.41+1.03=3.44% | 5.0% | 3.44% ✅ |

## 修复 4：生成器组排除出 variant 计数

### 问题

`/lootdrops/GoldenKey/` 页面中鬼王/巫妖/骷髅督军的坐标点显示"4种选1"，包含"生成器组"（`GameSpawnerGroup`）。该条目是生成器组容器本身，不应作为实体变体计入。

### 根因

`coordinates.py:get_variant_counts()` 的 SQL 查询使用 `original_keyword` 分组计数，未排除 `has_lootdrop=0` 的非实体条目。

```
Crypt_DarkRitualRoom_01_HR_D.json / group=BP_GameSpawnerGroup_C_0:
  GhostKing      (has_lootdrop=1)  ← 实体
  Lich           (has_lootdrop=1)  ← 实体
  SkeletonWarlord(has_lootdrop=1)  ← 实体
  GameSpawnerGroup(has_lootdrop=0) ← 容器，不应计入
  → 旧 variant_count=4（含生成器组）❌
  → 新 variant_count=3（纯实体）✅
```

### 修复

`api/src/db/repositories/coordinates.py`：两个 WHERE 子句增加 `AND has_lootdrop = 1`。

### 效果

| 怪物 | 旧 variant_names | 新 variant_names |
|------|-----------------|-----------------|
| 鬼王 / 巫妖 / 骷髅督军 | ['鬼王', '骷髅督军', '巫妖', '生成器组'] | ['鬼王', '骷髅督军', '巫妖'] ✅ |

## 修复 5：模块综合爆率改为单点坐标求和

### 问题

`computeModuleScore` 使用乘积公式 `spawn_rate × dr × effectiveCount(dots)`，对变体坐标做 `1/variant_count` 打折。
阈值（控制显隐）和底部综合爆率均按此聚合值计算，但阈值只需控制显隐粒度，不需要精确到变体打折。

### 修复

`web/src/pages/LootdropDetailPage.tsx`：

1. **`LootdropCoord` 接口** 增加 `score?: number` 字段
2. **mapGroups dot** 新增 `d.score` 传递管道预计算值（`spawn_rate × dr / 100`）
3. **`computeModuleScore`** 改为直接求和每个坐标的 `score`，删除 `effectiveCount` 函数
4. **显示标签**：`综合爆率 → 单点综合爆率`，移除多余的 `/ 100` 除法
5. **阈值标签**：`乘积% → 单点综合爆率%`

### 效果

| 坐标类型 | 旧算法 | 新算法 |
|---------|-------|-------|
| 普通坐标 | `spawn_rate × dr × 1` | `score` = `spawn_rate × dr / 100` |
| 变体坐标(N种选1) | `spawn_rate × dr × 1/N`（打折） | `score` = `spawn_rate × dr / 100`（全额） |

## 修复 6：ChestLarge 分类条件收紧

### 问题

`_classify_label` 中 `"ChestLarge" in label` 条件过宽，将 `OrnateChestLarge` 等具体生成器名误判为"特殊"类型，导致其高 spawn_rate 污染同类聚合值。

例：`OrnateChestLarge` 生成器实际生成 `FlatChestLarge`、SpawnRate=100000，单条目公式得 1000%。被归入"特殊"类型后拉高该类型聚合值。

### 修复

`api/src/lootdrop_builder.py:_classify_label()`：`"ChestLarge" in label` → `label == "ChestLarge" or label.startswith("ChestLarge_")`

```python
# 旧
if "Special" in label or "ChestLarge" in label:
# 新  
if "Special" in label or label == "ChestLarge" or label.startswith("ChestLarge_"):
```

## 修复 7：SpawnRate 上限 100%

### 问题

单条目无 DG 的生成器公式 `raw_rate / 10000 * 100` 可能超过 100%（例：`OrnateChestLarge` → `100000 / 10000 * 100 = 1000%`）。

### 修复

两处计算后追加 `min(spawn_rate, 100.0)`：

- `api/src/search_engine.py:138` — 多实体展开的 spawn_rate 计算
- `api/src/db/importers/spawners.py:137` — DB 导入的 spawn_rate 计算

### 效果

| 条目 | 旧值 | 新值 |
|------|------|------|
| `OrnateChestLarge` → `FlatChestLarge` | 1000% | 100% ✅ |

## 修复 8：合并多实体条目保持内联坐标（水下宝藏堆映射丢失）

### 问题

`HoardChest01_3`（宝藏堆海底版）与其他 Hord 实体（Hoard01_3、Hoard01_6、Hoard01_9）共享翻译"宝藏堆"，且 spawner_keyword == entity_name，全部归类为"direct"类型合并到一个条目。ref 优化指向 `coords/Hoard01_3.json`（仅 10 坐标），但条目实际有 32 坐标（含 HoardChest01_3 的 6 个水下坐标），22 个坐标因 ref 丢失。

### 修复

`api/src/lootdrop_builder.py`：

1. 清理 `_bases` 前保存多基标志：
```python
_bases = _v.pop("_bases", None)
if _bases and len(_bases) > 1:
    _v["_multi_base"] = True
```

2. ref 优化时跳过多基条目：
```python
if _m.pop("_multi_base", None):
    _m.pop("_coord_key", None)
    continue
```

### 效果

| 条目 | 旧 | 新 |
|------|-----|-----|
| 宝藏堆 | ref=coords/Hoard01_3（仅 10 坐标） | 内联 32 坐标（含 HoardChest01_3 水下坐标）✅ |
| 超级宝藏堆 | ref=props/SuperHoard01_9（单实体，不受影响） | 同 ✅ |
