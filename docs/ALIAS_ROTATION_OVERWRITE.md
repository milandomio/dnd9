# 模块别名旋转值覆盖与图片解析修复

## 问题现象

`monsters/BabyTurtle/` 中 `ShipGraveyard_BladehandRefuge` 旋转值为 270°，实际应为 0°。

同类对比：`items/Shackles/` 中 `ShipGraveyard_FloatingVillage` 旋转 0° 正确。

## 根因

### 旋转值覆盖（原有问题）

两个 `Id_DungeonModule_*.json` 的 `SubLevelAssetD_HR` 指向同一地图图片，触发别名合并逻辑：

| 文件 | module_name | SubLevelAssetD_HR → sl_base | 合并后 |
|------|------------|---------------------------|--------|
| BladehandRefuge | `ShipGraveyard_BladehandRefuge` | `ShipGraveyard_SkullIsland_D` → `ShipGraveyard_SkullIsland` | `ShipGraveyard_SkullIsland` |
| SkullIsland | `ShipGraveyard_SkullIsland` | 自身 → `ShipGraveyard_SkullIsland` | `ShipGraveyard_SkullIsland` |

旧代码中 BladehandRefuge（字母序靠前）先处理：别名合并 → `module_name = ShipGraveyard_SkullIsland`，旋转查询 `module_rotations.get(module_name) = 270°`（因为 module_name 已被覆盖为 SkullIsland）。**两个模块 Layout 旋转值不同（0° vs 270°），别名合并后旋转值丢失。**

### build_map_mappings 污染（拆分模块后引入）

将别名模块拆分为独立行后，`build_map_mappings` 的 pass-2 映射将别名模块的 `sl_base_name` 无条件加入 `module_to_maps[alias_module]`，导致：

- `module_to_maps['ShipGraveyard_BladehandRefuge']` 错误包含 `'ShipGraveyard_SkullIsland'`
- SkullIsland 的坐标被 BladehandRefuge 聚合，旋转值从错误的模块读取

### 图片解析优先规则（原有设计缺陷）

旧解析逻辑：先查 `sl_base_name`（共享图片），只有在 `sl_base_name` 未找到时才查 `module_name`。对于有独立文件的别名模块（BladehandRefuge），即使 `api/src/img/` 中存在 `ShipGraveyard_BladehandRefuge.webp`，因为 `sl_base_name`（SkullIsland）的图片已命中，模块名自己的图片永远不会被使用。

## 修复

### 1. 图片解析优先规则（`module_builder.py:161-168`）

当 `module_name != sl_base_name` 时，优先尝试模块名自己的图片：

```python
if module_name != sl:
    img_name, art_status = _try_resolve(module_name)
    if art_status != "found":
        img_name, art_status = _try_resolve(sl)
else:
    img_name, art_status = _try_resolve(sl)
```

### 2. module_to_maps 守卫（`module_builder.py:266`）

当 `sl` 已有独立模块时，不将其加入别名模块的 `module_to_maps`：

```python
if sl not in modules_map:
    module_to_maps.setdefault(mn, set()).add(sl)
```

### 3. 模块拆分（`modules.py:86-91`）

BladehandRefuge 和 SkullIsland 各自保留独立行，不执行别名合并。

## 影响范围

只 `ShipGraveyard_BladehandRefuge` 一处修改：

| 字段 | 旧值 | 新值 |
|------|------|------|
| `img_name` | `ShipGraveyard_SkullIsland` | `ShipGraveyard_BladehandRefuge` |
| `rotate` | 270° | 0° |

其他 `mn != sl_base` 模块（EmptyModule_*、Ruins_Chapel 等 `sl_base=""`）最终 `img_name` 与旧代码一致。

## 文件

- `api/src/module_builder.py:161-168` — 图片解析优先规则
- `api/src/module_builder.py:266` — module_to_maps 守卫
- `api/src/db/importers/modules.py:86-91` — 别名模块拆分
