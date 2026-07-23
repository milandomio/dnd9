# Crypt_BlindfallPit_D 变体组概率分析

## 组结构

| 元素 | 数量 |
|------|------|
| BP_GameSpawnerGroup_C | 1（BP_GameSpawnerGroup_C_8） |
| BP_GameObjectLinker_C（子组） | 6（C_1, C_3, C_5, C_7, C_9, C_11） |
| BP_ObjectLinkWithTriggerBox_C | 6（C_0~C_5） |
| 全组实体种类（variant_count） | 11 种 |
| BP_GameSpawner_C（组内） | 43 |

## 变体机制（核心结构）

**不是"11种选6"**——6 个 ObjectLinker 各自有独立的子池，并联独立抽选：

```
C_1 (Hoard)    → {Hoard01(×3), Ore_GoldOre(×8), GrimveilCloak(×1)}          ← 3 种, 12 spawner
C_3 (MonsterA) → {SkeletonChampion(×3), GrimveilCloak(×1)}                   ← 2 种, 4 spawner
C_5 (MonsterB) → {Wraith(×3), GrimveilCloak(×1)}                             ← 2 种, 4 spawner
C_7 (MonsterC) → {SkeletonAxeman(×2), GuardsmanFromFakeDeath(×56),
                   SkeletonSpearman(×3), SkeletonSwordman(×3),
                   GrimveilCloak(×1)}                                          ← 5 种, 65 spawner
C_9 (MonsterD) → {SkeletonArcher(×4), SkeletonCrossbowman(×4),
                   GrimveilCloak(×1)}                                          ← 3 种, 9 spawner
C_11 (MonsterE) → {SkeletonArcher(×1), SkeletonChampion(×1),
                    SkeletonCrossbowman(×1), SkeletonSpearman(×1),
                    SkeletonSwordman(×1), Wraith(×1),
                    GrimveilCloak(×1)}                                         ← 7 种, 7 spawner
```

**variant_count=11** 只是全组实体种类的汇总，不是子池大小。各子池范围从 2~7 种不等。

## 引擎行为

同位置同实体只生成 1 次（引擎去重）。即使多个 ObjectLinker 同时选中同一实体，也只产生 1 个实例。幽鬼、GrimveilCloak 等均遵循此规则。

**6 个坐标点**的父级偏移精确抵消，全部算术对齐至同一世界坐标 (810, −10, −1600)，物理上只有 1 个点。

## ObjectLinker 主题分区

| ObjectLinker | 标签 | 关联实体 | 子池大小 |
|-------------|------|---------|---------|
| C_1 | Hoard | Hoard01、Ore_GoldOre、GrimveilCloak | 3 种 |
| C_3 | MonsterA | SkeletonChampion、GrimveilCloak | 2 种 |
| C_5 | MonsterB | Wraith、GrimveilCloak | 2 种 |
| C_7 | MonsterC | SkeletonAxeman、GuardsmanFromFakeDeath、SkeletonSpearman、SkeletonSwordman、GrimveilCloak | 5 种 |
| C_9 | MonsterD | SkeletonArcher、SkeletonCrossbowman、GrimveilCloak | 3 种 |
| C_11 | MonsterE | SkeletonArcher、SkeletonChampion、SkeletonCrossbowman、SkeletonSpearman、SkeletonSwordman、Wraith、GrimveilCloak | 7 种 |
| **GrimveilCloak** | 全部 6 个子组 | 每个子组都有 1 个 GC spawner | 6/6 |

## 精确爆率链（以 GrimveilCloak 物品为例）

各子组抽选权重未在导出 JSON 中暴露（由蓝图 `DCGameObjectLink` 控制），以下按**子池内均匀选 1** 假设。

### 各子组出 GC 的概率

| 子组 | P(该组选中 GC) | 说明 |
|------|--------------|------|
| C_1 | 1/3 = 33.33% | 3 种中抽 1 |
| C_3 | 1/2 = 50% | 2 种中抽 1 |
| C_5 | 1/2 = 50% | 2 种中抽 1 |
| C_7 | 1/5 = 20% | 5 种中抽 1 |
| C_9 | 1/3 = 33.33% | 3 种中抽 1 |
| C_11 | 1/7 = 14.29% | 7 种中抽 1 |

P(至少 1 组选中 GC) = 1 − P(全部 6 组都不中)
= 1 − (2/3 × 1/2 × 1/2 × 4/5 × 2/3 × 6/7)
= 1 − (2/3 × 1/2 × 1/2 × 4/5 × 2/3 × 6/7)

```
= 1 − 96/1260
= 1 − 0.0762
= 0.9238 = 92.38%
```

这个概率远高于简化假设（43.53%），因为各子池比 11 小得多，GC 在每个子池里的占比都很高。

### 完整链（豪客赛）

| 阶段 | 概率 |
|------|------|
| 模块层: BlindfallPit 出现 | 1/100 |
| 子组层: P(≥1 组选中 GC) | 92.38%（精确子池）vs 43.53%（简化 1/11） |
| 物品层: pickup 掉率 | 2.5% |
| **总计** | **≈1/432（精确）** vs ≈1/9,191（简化） |

若模块概率为 1/200：**≈1/865（精确）** vs ≈1/18,382（简化）。

前端目前使用简化公式 `1−(10/11)^6`，因为各子池权重未经确认。精确值高了约 21 倍。

## 算法验证

### sub_group_parent 追踪

`search_engine.py::sub_group_root_to_name` 正确识别两种 ObjectLinker 作为子组根：
- `BP_GameObjectLinker_C` → 传给 spawner
- `BP_ObjectLinkWithTriggerBox_C` → 传给 spawner

### 坐标去重 key

原：`(x, y, z, json_filename)` → 6 个同位置 ObjectLinker 被合并为 1 点
现：`(x, y, z, json_filename, group_parent, sub_group_parent)` → 正确区分

### groupCount 前端计算

```tsx
const varGps = [...new Set(
  mapCoords.map((c) =>
    c.group_parent && c.sub_group_parent
      ? `${c.group_parent}::${c.sub_group_parent}`
      : (c.group_parent ?? '')
  ).filter(Boolean)
)];
const groupCount = varGps.length || 1;
```

### adjRate 公式

```tsx
const adjRate = (v: number) =>
  hasVariant
    ? +(v * (1 - (1 - 1 / forcedVcN) ** groupCount)).toFixed(4)
    : v;
```

`forcedVcN` = variant_count（默认 11），`groupCount` = unique sub_group_parent 数。

前端使用简化假设（每子组从完整 11 种均匀抽），精确值需子池权重数据支撑。

## 对比

| 版本 | GrimveilCloak 点数 | 标签 | 说明 |
|------|-------------------|------|------|
| 修复前 | 1 | 11种选1 | 6 个 ObjectLinker 被去重合并，groupCount=1 |
| 修复后 | 6 | 11种选6 | 使用 sub_group_parent 去重，groupCount=6 |
| 实际游戏 | 1 物理点 | 6 子组独立抽选 | 引擎去重，最多 1 个 |
