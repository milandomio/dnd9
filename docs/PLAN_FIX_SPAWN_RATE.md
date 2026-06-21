# 修复计划：Spawn Rate 显示不一致

## 问题

`/props/OrnateChestLarge/` 和 `/lootdrops/MysticalGem/` 中狮头宝箱的 `spawn_rate` 不一致：

| 页面 | 显示值 | 预期值 |
|------|--------|--------|
| props 详情页 `group_drop_info.spawn_rate` | 1000.0 | 25.0 |
| lootdrop 详情页 坐标 `spawn_rate` | 100 | 25.0 |

## 根因

### 问题 1：`_spawn_rate_cache` 命名空间污染

`collector.py:1556-1558`：
```python
for _key in (sk, en):  # sk=spawner_keyword, en=entity_name
    if _key and sr > _spawn_rate_cache.get(_key, 0):
        _spawn_rate_cache[_key] = sr
```

同一个 dict 同时用 `spawner_keyword` 和 `entity_name` 做 key。

DB 中存在 `(spawner_keyword='OrnateChestLarge', entity_name='FlatChestLarge', spawn_rate=1000.0)`，这条数据表示"OrnateChestLarge 这个生成器有 1000 权重生成 FlatChestLarge"。

但因为 `spawner_keyword = 'OrnateChestLarge'`，`_spawn_rate_cache['OrnateChestLarge'] = 1000.0`，完全覆盖了正确的实体生成率 25.0。

### 问题 2：Lootdrop 页坐标 spawn_rate 查找失败

`collector.py:1714-1718`：
```python
if _c.get("keyword") != _c.get("original_keyword", ""):
    _pair = (_c["keyword"], m_name)
    _sr = _spawn_rate_detail.get(_pair, 100)
```

坐标的 `keyword` 是 `'OrnateChestLarge'`（实体名），而 `spawner_entries` 表中的 `spawner_keyword` 是 `'ChestSpecial'`。pair `('OrnateChestLarge', 'OrnateChestLarge')` 在 `_spawn_rate_detail` 中不存在，返回默认值 100。

## 影响范围

| 影响点 | 当前值 | 修复后 |
|--------|--------|--------|
| Props 页 `group_drop_info.spawn_rate` | 被污染（如 1000.0） | 取 entity_name 对应的正确值 |
| Items 页 `group_drop_info.spawn_rate` | 可能也被同一 bug 影响 | 同样修正 |
| Monsters 页 `group_drop_info.spawn_rate` | 同上 | 同上 |
| Lootdrop 页坐标 `spawn_rate` | 部分坐标默认 100 | 从 `_spawn_rate_detail` 取正确值 |

## 修复方案

### A. `_spawn_rate_cache` 分离命名空间（`collector.py:1556-1558`）

将 entity_name 和 spawner_keyword 分别缓存：

```python
# 当前：混合 key
for _key in (sk, en):
    if _key and sr > _spawn_rate_cache.get(_key, 0):
        _spawn_rate_cache[_key] = sr

# 修复：分离
for _key in (sk, en):
    ...
    if _key and sr > _cache_by_entity.get(_key, 0):
        _cache_by_entity[_key] = sr  # 只存 entity_name 维度
```

但需保留 spawner_keyword 维度的缓存给其他查找用，或改用 `_spawn_rate_detail` 的 `(sk, en)` pair 实现精确查找。

### B. Lootdrop 页坐标查找使用 original_keyword（`collector.py:1714-1716`）

```python
# 当前：用 coord.keyword
_pair = (_c["keyword"], m_name)

# 修复：用 coord.original_keyword（即 spawner_keyword）
_pair = (_c.get("original_keyword") or _c["keyword"], m_name)
```

### C. Props 段 `group_drop_info` 的 spawn_rate 改用精确 pair 查找（`collector.py:2043`）

```python
# 当前：_spawn_rate_cache（被污染）
_sr = _spawn_rate_cache.get(_pname, 0.0)

# 修复：取该实体在各生成器中的最大精确 spawn_rate
_sr = max(
    _spawn_rate_detail.get((sk, _pname), 0) 
    for sk in _entity_spawners.get(_pname, set())
) if _entity_spawners.get(_pname) else 0.0
```

### D. 同理修复 Monsters 段（`collector.py:1995`）

```python
# 当前
_sr = _spawn_rate_cache.get(_mname, 0.0)
# 修复同 C
```

## 测试验证

1. 运行 `python main.py` 重新生成 JSON
2. 检查 `/props/OrnateChestLarge.json` 中 `group_drop_info` 的 `spawn_rate` 应为 25.0
3. 检查 `/lootdrops/MysticalGem.json` 中 OrnateChestLarge 坐标的 `spawn_rate` 应为 25.0
4. 检查组内未找到协调坐标的其他实体不受影响
5. 检查 Lifeleaf 等既是 prop 又是 item 的实体爆率信息不受影响
