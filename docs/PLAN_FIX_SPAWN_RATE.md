# 修复记录：Props 详情页 Spawn Rate & Drop Rates

## 问题

`/props/OrnateChestLarge/` 页面显示的参考爆率中：
- `spawn_rate: 1000.0`（应为 25.0）
- `drop_rates: {PVE: 3.0, 普通: 10.0, 豪客赛: 22.5}`（聚合计算错误）

## 根因

### 问题 1：`_spawn_rate_cache` 命名空间污染

`collector.py:1556-1558` 用同一个 dict 同时以 `spawner_keyword` 和 `entity_name` 做 key。
DB 中 `(spawner_keyword='OrnateChestLarge', entity_name='FlatChestLarge', spawn_rate=1000.0)` 导致
`_spawn_rate_cache['OrnateChestLarge'] = 1000.0`，覆盖了正确的实体生成率 25.0。

### 问题 2：`_compute_group_drop_rates` 取 max 而非 sum

原函数对容器类实体取单件物品的最大概率（`best_rate = max(w / _shared / _rate_total)`），
而非累加所有独立 lootdrop 的总概率，导致数值远低于实际。

## 修改内容

### 文件：`api/src/collector.py`

#### 1. 新增 `_compute_container_drop_rates()` 函数（第1506行）

专门用于容器类 props 的聚合爆率计算，与原 `_compute_group_drop_rates` 的区别：

| 维度 | 原函数 | 新函数 |
|------|--------|--------|
| 计算方式 | `max(w/_shared/_rate_total)` 取单件物品最大值 | `1 - Π(1 - P_ld)^drop_count` 累加所有独立 lootdrop |
| 适用场景 | 怪物/物品详情页（单件物品的爆率） | 容器类 props（至少掉落一件物品的概率） |
| 结果范围 | 各模式下单个物品的爆率（偏低） | 至少掉落一件物品的概率（接近游戏实际） |

#### 2. Props 段 spawn_rate 改用精确 pair 查找（第2080行）

```python
# 改前：被 spawner_keyword 命名空间污染
_sr = _spawn_rate_cache.get(_pname, 0.0)

# 改后：从 _entity_spawners 获取该实体的所有生成器，取精确 pair 的最大值
_sr_list = [_spawn_rate_detail.get((sk, _pname), 0) for sk in _entity_spawners.get(_pname, set())]
_sr = max(_sr_list) if _sr_list else 0.0
```

#### 3. Props 段 drop_rates 改用新函数（第2083行）

`_compute_group_drop_rates(_ldg_id, _g)` → `_compute_container_drop_rates(_ldg_id, _g)`

## 效果对比（OrnateChestLarge / Inferno 分组）

| 指标 | 改前 | 改后 | 说明 |
|------|------|------|------|
| `spawn_rate` | 1000.0 ❌ | 25.0 ✅ | 来自 `(ChestSpecial, OrnateChestLarge)` |
| `drop_rates.PVE` | 3.0% | 35.945% | 各模式正确聚合适配 |
| `drop_rates.普通` | 10.0% | 95.188% | |
| `drop_rates.豪客赛` | 22.5% | 99.971% | 豪客赛几乎必出 |

## 未修复项（仍需单独计划）

| 项目 | 问题 | 方案编号 |
|------|------|----------|
| Lootdrop 页坐标 `spawn_rate` | 部分坐标默认 100（因 keyword 与 original_keyword 不匹配） | B |
| Monsters 段 `_spawn_rate_cache` | 与 Props 段相同的命名空间污染问题 | D |
| `_spawn_rate_cache` 命名空间分离 | 整体重构，分离 entity_name 和 spawner_keyword | A |
| Items 段 `_spawn_rate_cache` | 同上 | A |

## 验证步骤

1. 运行 `cd api && python main.py`
2. 检查 `data/json/props/OrnateChestLarge.json` 中 `group_drop_info` 各分组的 `spawn_rate` 是否为 25.0
3. 检查 `drop_rates` 是否为合理的聚合值（豪客赛接近 100%）
4. 运行 `cd web && npm run build && npx vite preview --port 8080`
5. 访问 `/props/OrnateChestLarge/` 确认显示正确
