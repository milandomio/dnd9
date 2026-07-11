# 修复记录：entity_class 在 spawner fallback 导入后重建

## 重要性：高

此修复影响多个实体的翻译合并，修复了大量 lootdrop 页面中实体分类按钮显示错误的问题。

## 问题

`entity_class`（实体分类字典）在 pipeline 开始时从数据库构建，但 spawner fallback 实体（如 HoardChest01_3、SuperHoardChest01_9 等）是在之后才导入到数据库的。

这导致：
1. **翻译失败**：fallback 实体在 `entity_class` 中不存在，无法获取 `translation_key`
2. **分类按钮分裂**：同一翻译的实体（如"宝藏堆"）因翻译不同而显示为多个独立按钮
3. **坐标丢失**：翻译不同的实体无法正确合并坐标

## 影响范围

所有由 `import_spawner_fallback_entities` 添加的实体都会受影响，包括但不限于：

| 实体 | 正确翻译 | 修复前显示 |
|------|---------|-----------|
| HoardChest01_3 | 宝藏堆 | HoardChest01_3 |
| SuperHoardChest01_9 | 超级宝藏堆 | SuperHoardChest01_9 |
| 其他 spawner fallback 实体 | （各不相同） | （原始英文名） |

## 根因

`collector.py` 中的执行顺序：

```python
# 1. 构建 entity_class（此时 spawner fallback 实体尚未导入）
entity_class = db.get_entity_classification()  # ← 此时缺少 fallback 实体

# ... 其他导入 ...

# 2. 导入 spawner fallback 实体
added = db.import_spawner_fallback_entities()  # ← 实体此时才加入数据库

# 3. 使用 entity_class 构建 lootdrop（fallback 实体翻译失败）
loot_index = build_loot_index(..., entity_class, ...)
```

## 修复

在 `import_spawner_fallback_entities` 之后重建 `entity_class`：

```python
added = db.import_spawner_fallback_entities()
pipe.log(f"import_spawner_fallback_entities DONE -> {added}")
entity_class = db.get_entity_classification()  # ← 新增：重建分类
```

## 效果验证

### GoldCoinBag 掉落页

| 修复前 | 修复后 |
|--------|--------|
| 宝藏堆 (10 coords) | 宝藏堆 (16 coords) |
| HoardChest01_3 (6 coords) | （已合并到宝藏堆） |
| 超级宝藏堆 (9 coords) | 超级宝藏堆 (9 coords) |

### 分类按钮

| 修复前 | 修复后 |
|--------|--------|
| 3 个按钮（宝藏堆、HoardChest01_3、超级宝藏堆） | 2 个按钮（宝藏堆、超级宝藏堆） |

## commit

`687c766` — fix: rebuild entity_class after spawner fallback import
