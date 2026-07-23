# Crypt_BlindfallPit_D 变体组概率分析

## 组结构

| 元素 | 数量 |
|------|------|
| BP_GameSpawnerGroup_C | 1（BP_GameSpawnerGroup_C_8） |
| BP_GameObjectLinker_C | 6（C_1, C_3, C_5, C_7, C_9, C_11） |
| BP_ObjectLinkWithTriggerBox_C | 6（C_0~C_5） |
| 变体池（variant_count） | 11 种实体 |
| BP_GameSpawner_C（组内） | 43 |

## 算法验证

### sub_group_parent 追踪

`search_engine.py::sub_group_root_to_name` 正确识别两种 ObjectLinker 作为子组根：

- `BP_GameObjectLinker_C` → 传给 spawner
- `BP_ObjectLinkWithTriggerBox_C` → 传给 spawner

每个 spawner 的 `_resolve_world_loc` 结果中正确携带 `sub_group_name`，最终存入 DB 的 `sub_group_parent` 字段。

### 坐标去重 key

原：`(x, y, z, json_filename)` → 6 个同位置 ObjectLinker 被合并为 1 点

现：`(x, y, z, json_filename, group_parent, sub_group_parent)` → 正确区分

**验证**：GrimveilCloak x=810,y=-10,z=-1600:
- 旧去重：6 条 → 1 条
- 新去重：6 条（各 ObjectLinker 分别保留）

### groupCount 前端计算

```tsx
// DetailPage.tsx
const varGps = [...new Set(
  mapCoords.map((c) =>
    c.group_parent && c.sub_group_parent
      ? `${c.group_parent}::${c.sub_group_parent}`
      : (c.group_parent ?? '')
  ).filter(Boolean)
)];
const groupCount = varGps.length || 1;
```

**等价于**：统计该变体组中 unique `(group_parent, sub_group_parent)` 对数。

## 变体机制

当玩家进入触发区域时，每个 `BP_GameObjectLinker_C` 独立从变体池中选择 1 种实体并召唤。

### 11 种实体分布（Crypt_BlindfallPit_D）

| 实体 | 出现 ObjectLinker | 总刷怪点数 |
|------|-------------------|-----------|
| GrimveilCloak | C_1, C_3, C_5, C_7, C_9, C_11（全 6） | 6×1 |
| SkeletonChampion | C_3(×3), C_11(×1) | 4 |
| Hoard01_3 | C_1(×3) | 3 |
| Ore_GoldOre | C_1(×8) | 8 |
| SkeletonArcher | C_9(×4), C_11(×1) | 5 |
| SkeletonCrossbowman | C_9(×4), C_11(×1) | 5 |
| SkeletonSpearman | C_7(×3), C_11(×1) | 4 |
| SkeletonSwordman | C_7(×3), C_11(×1) | 4 |
| SkeletonAxeman | C_7(×2) | 2 |
| SkeletonGuardsmanFromFakeDeath | C_7(×56) | 56 |
| Wraith | C_5(×3), C_11(×1) | 4 |

### ObjectLinker 主题分区

| ObjectLinker | 标签 | 关联实体 |
|-------------|------|---------|
| C_1 | Hoard | 宝箱/金矿类（3 种） |
| C_3 | MonsterA | 精英近战 |
| C_5 | MonsterB | 幽鬼 |
| C_7 | MonsterC | 杂兵近战群（56 装死卫兵） |
| C_9 | MonsterD | 远程兵 |
| C_11 | MonsterE | 混合全品种 |

### 爆率计算

由于 `BP_GameObjectLinker_C` 是互斥、独立、均匀的选择，没有额外权重信息时假设每 ObjectLinker 从完整 11 种池中均匀选择：

| 指标 | 公式 | 值 |
|------|------|-----|
| 单次选择特定实体的概率 | 1/11 | 9.09% |
| 至少出现一次的概率 | 1 - (10/11)^6 | 43.53% |
| 恰好出现 k 次的概率 | C(6,k) × (1/11)^k × (10/11)^(6-k) | k=0: 56.47%, k=1: 33.86%, k=2: 8.47%, k=3: 1.13% |
| 期望出现次数 | 6/11 | 0.545 |

**限制**：此计算假设每 ObjectLinker 从全部 11 种中等概率选取。实际游戏中各 ObjectLinker 的权重由 `DCGameObjectLink` 决定，受蓝图逻辑影响，未暴露在导出 JSON 中。前端显示的"11种选M"使用的 M = 该实体出现的 unique `(group_parent, sub_group_parent)` 对数，并非总 ObjectLinker 数 6。

## 概率修正：GrimveilCloak 物品 vs 怪物实体

旧分析把两个东西混在一起了，需要区分：

### 场景 A：GrimveilCloak 怪物直接生成（变体池中的实体）

GrimveilCloak 本身就是 11 种变体之一。当某个 ObjectLinker 选中它时，直接在其坐标点生成 GrimveilCloak 怪物。

| 版本 | 点数 | 单次选中的概率 | P(至少出 1 只) |
|------|------|--------------|---------------|
| 修复前 | 1（6 Linker 被合并） | 1/11 = 9.09% | 9.09% |
| 修复后 | 6（各 Linker 独立） | 每 Linker 1/11，6 次独立 | **1 - (10/11)^6 = 43.53%** ⬆ 4.8× |

**结论**：修复后 GrimveilCloak 怪物出现概率从 9% 暴涨到 43.5%，每次进 BlindfallPit 有近一半概率见到它。

### 场景 B：GrimveilCloak 物品直接生成（修正后的 1/9,200 分析）

GrimveilCloak **物品本身**就是变体池中的直接生成物（`group_drop_info` 实体名 = "阴森帷幕披风"），不是通过容器间接掉落。它有 6 个坐标点（对应 6 个 ObjectLinker），`spawn_rate=100`（选中即生成），`drop_rates` 控制物品的品质/模式系数。

| 阶段 | 旧理解（1 次抽选） | 新理解（6 次独立） | 变化 |
|------|-------------------|-------------------|------|
| 模块概率 | 1/100 | 1/100 | 不变 |
| 实体选中 | 11 选 1 → 1/11 = 9.09% | 6 次独立，P(至少 1 中) = 1−(10/11)^6 = **43.53%** | ⬆ 4.8× |
| 物品品质系数 | 2.5%（豪客赛） | 2.5%（豪客赛） | 不变 |
| **总计（豪客赛）** | **1/44,000** | **1/9,191** | **⬆ 4.8×** |

若模块概率为 1/200（5x5 层 × 稀有模块比例未精确验证）：**1/18,382**。

### 关键映射总结

| 你要的东西 | 对应的变体实体 | 修复影响 | 新概率（豪客赛） |
|-----------|--------------|---------|----------------|
| GrimveilCloak **物品**（直接拾取） | 变体池 GrimveilCloak | ⬆ 涨 4.8× | **≈1/9,200** 每次进 BlindfallPit |
| GrimveilCloak **怪物**（可见实体，同实体） | 变体池 GrimveilCloak | ⬆ 涨 4.8× | **43.5%** 可见 |

## 对比

| 版本 | GrimveilCloak 点数 | 标签 | 说明 |
|------|-------------------|------|------|
| 修复前 | 1 | 11种选1 | 6 个 ObjectLinker 被去重合并，groupCount=1 |
| 修复后 | 6 | 11种选6 | 使用 sub_group_parent 去重，groupCount=6 |
| 实际游戏 | 1 物理点 | 11种各 ObjectLinker 独立选 | 6 次独立抽选，可重复，GrimveilCloak 会重叠 |
