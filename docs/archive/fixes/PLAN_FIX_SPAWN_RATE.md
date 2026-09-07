# 修复记录：Props 详情页 Spawn Rate & Drop Rates

## 问题

`/props/OrnateChestLarge/` 页面显示的参考爆率中：
- `spawn_rate: 1000.0`（应为 25.0）
- `drop_rates: {PVE: 3.0, 普通: 10.0, 豪客赛: 22.5}`（聚合计算错误）
- 未显示上锁变体的生成概率
- 未按生成器关键词类型（特殊/随机）分别标注

## 根因

### 问题 1：`_spawn_rate_cache` 命名空间污染

`drop_rate.py`（原 `collector.py`）用同一个 dict 同时以 `spawner_keyword` 和 `entity_name` 做 key。
DB 中 `(spawner_keyword='OrnateChestLarge', entity_name='FlatChestLarge', spawn_rate=1000.0)` 导致
`_spawn_rate_cache['OrnateChestLarge'] = 1000.0`，覆盖了正确的实体生成率 25.0。

### 问题 2：`_compute_group_drop_rates` 取 max 而非 sum

原函数对容器类实体取单件物品的最大概率（`best_rate = max(w / _shared / _rate_total)`），
而非累加所有独立 lootdrop 的总概率，导致数值远低于实际。

### 问题 3：`_ld_rate_items` dict 覆盖导致 luck_grade 丢失

`_ld_rate_items` 以 `{lootdrop_id: {item_name: (luck_grade, drop_count)}}` 存储。
同一 item 在同个 lootdrop 中有多行不同 luck_grade（如 `GoldCoins` 在 `ID_Lootdrop_Drop_Trinkets` 有 lg1-7 七行），
dict 只保留最后一行。在 `ID_Droprate_HighRate_1023` 中只有 lg5 有非零权重 750，
导致 `id_prob = 750/10000 = 0.075`（正确应为 `(5250+4000+750)/10000 = 1.0`）。
**这是长期存在的已知限制，影响所有爆率页面。35.945% 是当前代码的正确输出。**

## 修改内容

### 文件：`api/src/drop_rate.py`（原 `collector.py`）

#### 1. 新增 `_compute_container_drop_rates()` 函数

专门用于容器类 props 的聚合爆率计算，与原 `_compute_group_drop_rates` 的区别：

| 维度 | 原函数 | 新函数 |
|------|--------|--------|
| 计算方式 | `max(w/_shared/_rate_total)` 取单件物品最大值 | `1 - Π(1 - P_ld)^drop_count` 累加所有独立 lootdrop |
| 适用场景 | 怪物/物品详情页（单件物品的爆率） | 容器类 props（至少掉落一件物品的概率） |
| 结果范围 | 各模式下单个物品的爆率（偏低） | 至少掉落一件物品的概率（接近游戏实际） |

#### 2. Props 段 spawn_rate 改用精确 pair 查找

```python
# 改前：被 spawner_keyword 命名空间污染
_sr = _spawn_rate_cache.get(_pname, 0.0)

# 改后：从 _entity_spawners 获取该实体的所有生成器，取精确 pair 的最大值
_sr_list = [_spawn_rate_detail.get((sk, _pname), 0) for sk in _entity_spawners.get(_pname, set())]
_sr = max(_sr_list) if _sr_list else 0.0
```

#### 3. Props 段 drop_rates 改用新函数

`_compute_group_drop_rates(_ldg_id, _g)` → `_compute_container_drop_rates(_ldg_id, _g)`

#### 4. 上锁变体合并 + 按关键词类型分组

Props `group_drop_info` 段重写为：
- 按 entity variant（regular / _Locked / _UnderSea / _Locked_UnderSea）收集所有生成器关键词
- 对每个关键词，用 `_classify_label()` 分类为 `direct` / `special` / `random`，加上 `_label_type_suffix` 后缀（`(特殊)` / `(随机)`）
- 上锁变体共享相同关键词时，生成率求和，标注 `(可能上锁)`
- UnderSea 和非 UnderSea 用 `(is_undersea, type)` 复合键分离，UnderSea 条目加 `(海底)` 前缀
- 同一 type 多个关键词取最大生成率

示例输出（OrnateChestLarge / Inferno）：

| 条目 | 生成率 | 说明 |
|------|--------|------|
| 狮头宝箱(特殊)(可能上锁) | 50% | ChestSpecial: 25+25 |
| 狮头宝箱(随机)(可能上锁) | 3.44% | OrnateChestLargeRandom: 2.41+1.03 |
| (海底)狮头宝箱(特殊)(可能上锁) | 32.5% | ChestSpecial_UnderSea: 15+17.5 |
| (海底)狮头宝箱(随机)(可能上锁) | 100% | OrnateChestLargeRandom_UnderSea: 71.05+28.95 |
| (海底)狮头宝箱 | 100% | OrnateChestLarge_UnderSea: 100 |

## 效果对比（OrnateChestLarge / Inferno 分组 / 随机类型）

| 指标 | 改前 | 改后 | 说明 |
|------|------|------|------|
| `spawn_rate`（随机） | 1000.0 ❌ | 3.44% ✅ | 分子 50000 / 分母 1,450,040（OrnateChestLargeRandom spawner 总池） |
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
| `_ld_rate_items` dict 覆盖 | 多 luck_grade 物品只保留最后一行，导致部分爆率偏低 | E |

## 验证步骤

1. 运行 `cd api && python main.py`
2. 检查 `data/json/props/OrnateChestLarge.json` 中 `group_drop_info`：
   - 包含 `狮头宝箱(特殊)(可能上锁)` 等 5 个条目
   - 各条目 `spawn_rate` 正确聚合（特殊 50、随机 3.44 等）
   - `drop_rates` 合理（豪客赛接近 100%）
3. 运行 `cd web && npm run build && npx vite preview --port 8080`
4. 访问 `/props/OrnateChestLarge/` 确认多条目显示正确
5. 检查 `/props/OrnateChestMedium/` 等同类页面的显示一致性
