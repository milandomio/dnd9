# 性能优化计划：变体爆率缓存

> 创建日期: 2026-07-12
> 状态: 待执行
> 预计收益: 4-7s（从 85s → 78s）

## 问题

变体爆率计算是管道最大瓶颈，占总耗时 81%（85s / 105s）。

- 267 个变体物品 × ~6 变体 = ~1600 次 `get_variant_group_drop_rates` 调用
- 每次调用遍历 ~15 个 (group, monster) 组合
- 每个组合调用 `compute_variant_rate` ~2.9 次 grade_data 条目
- **总字典查找：~418,000 次**

## 可缓存分析

### 跨变体相同的部分

| 数据 | 依赖 | 跨变体相同 |
|------|------|-----------|
| `grade_data` | `ldg_id, full_grade` | ✅ |
| `_shared` | `ld_id, _found_lg` | ✅（运行时发现） |
| `_rate_total` | `lr_id` | ✅ |
| `item_info` | `ld_id, item_name` | ✅ |

### 跨变体不同的部分

| 数据 | 依赖 | 跨变体相同 |
|------|------|-----------|
| `_pool_weight` | `lr_id, luck_grade` | ❌ |

## 优化方案

### 方案 1: grade_data 缓存（省 1-2s）

**文件**: `api/src/drop_rate.py`

在 `DropRateEngine` 中添加：

```python
self._grade_data_cache: dict[tuple[str, int], list] = {}

def _get_grade_data(self, ldg_id: str, full_grade: int) -> list:
    key = (ldg_id, full_grade)
    cached = self._grade_data_cache.get(key)
    if cached is not None:
        return cached
    result = self._ld_groups.get(ldg_id, {}).get(full_grade, [])
    self._grade_data_cache[key] = result
    return result
```

在 `compute_variant_rate` 中替换：

```python
# 旧
grade_data = self._ld_groups.get(ldg_id, {}).get(full_grade, [])
# 新
grade_data = self._get_grade_data(ldg_id, full_grade)
```

**省时原理**: 消除 24,030 次 × 2 次字典查找 = 48,060 次查找

### 方案 2: item 查找缓存（省 3-5s）

**文件**: `api/src/drop_rate.py`

在 `DropRateEngine` 中添加：

```python
self._item_lookup_cache: dict[tuple[str, str], tuple[int, int] | None] = {}
_SENTINEL = object()

def _lookup_item(self, ld_id: str, item_name: str) -> tuple[int, int] | None:
    key = (ld_id, item_name)
    cached = self._item_lookup_cache.get(key, _SENTINEL)
    if cached is not _SENTINEL:
        return cached

    rate_items = self._ld_rate_items.get(ld_id, {})
    item_info = rate_items.get(item_name)
    if item_info is not None:
        self._item_lookup_cache[key] = item_info
        return item_info

    # 尝试变体后缀
    for _sfx in _VARIANT_SUFFIXES:
        item_info = rate_items.get(item_name + _sfx)
        if item_info is not None:
            self._item_lookup_cache[key] = item_info
            return item_info

    # 尝试基础名
    _base = _VARIANT_RE.sub(r"\1", item_name) if item_name and _VARIANT_RE.match(item_name) else None
    if _base:
        item_info = rate_items.get(_base)
        if item_info is not None:
            self._item_lookup_cache[key] = item_info
            return item_info
        for _sfx in _VARIANT_SUFFIXES:
            item_info = rate_items.get(_base + _sfx)
            if item_info is not None:
                self._item_lookup_cache[key] = item_info
                return item_info

    self._item_lookup_cache[key] = None
    return None
```

在 `compute_variant_rate` 中替换：

```python
# 旧（~10 行查找逻辑）
rate_items = self._ld_rate_items.get(ld_id, {})
item_info = rate_items.get(item_name)
if item_info is None:
    for _sfx in _VARIANT_SUFFIXES:
        item_info = rate_items.get(item_name + _sfx)
        if item_info is not None:
            break
if item_info is None and _base:
    item_info = rate_items.get(_base)
    if item_info is None:
        for _sfx in _VARIANT_SUFFIXES:
            item_info = rate_items.get(_base + _sfx)
            if item_info is not None:
                break

# 新（1 行）
item_info = self._lookup_item(ld_id, item_name)
```

**省时原理**: 消除 418,122 次 × 6 次字典查找 → ~50,000 次查找（唯一 ld_id × item 组合）

## 不可行的方案

### ❌ 跨变体结果缓存

`compute_variant_rate` 结果依赖 `luck_grade`（变体不同），无法跨变体缓存。

### ❌ `_shared` 预计算

`_shared` 依赖 `_found_lg`（item 的 luck_grade），在运行时从 `_ld_rate_items` 查找得到，无法提前知道。

## 预期效果

| 优化 | 省时 | 累计 |
|------|------|------|
| grade_data 缓存 | 1-2s | 1-2s |
| item 查找缓存 | 3-5s | 4-7s |
| **总计** | **4-7s** | **85s → 78s** |

## 验证方式

```bash
rm api/data/darkfindv5.db && cd api && time python main.py
```

对比 `lootdrops` 步骤耗时。

## 注意事项

1. 缓存必须在 `preload()` 之后构建，不可在 `preload()` 期间使用
2. `_item_lookup_cache` 使用 `_SENTINEL` 区分"未查找"和"查找结果为 None"
3. 两个缓存互相独立，可单独实现和测试
