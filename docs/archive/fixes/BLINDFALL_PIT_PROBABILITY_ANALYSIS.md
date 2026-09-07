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

## 最大同时存在数量

每个 ObjectLinker 独立从自己的子池中抽选 1 种实体类型，**选中的类型只在该 linker 的 1 个 spawn 点生成**（即 linker 的多个 spawn 点中随机选 1 个放置），**不是所有 spawn 点都出**。

因此某实体同时存在的最大数量 = 包含该实体的 linker 数量：

| 实体 | 所在 linker | 同时最大 | 计算 |
|------|-------------|---------|------|
| 骷髅冠军 | C_3(3点选1), C_11(1点选1) | **2** | 最多从 C_3 出 1 个(3 位置随机选 1) + C_11 出 1 个 |
| GrimveilCloak | C_1~C_11 全部 6 个 linker | **6** | 每个 linker 各 1 位置 → 最多 6 |
| 阴森帷幕披风 | C_1~C_11 全部 6 个 linker | **6** | 同 GrimveilCloak |

> 注：之前的"骷髅冠军最多 4 个"是错误结论，误将 C_3 的 3 个 spawn 位置算作独立出怪，实际每个 linker 只选 1 位置生成。

## 子池信息提取与显示链路

### 数据流

```
DB (spawners 表) → api/src/db/repositories/coordinates.py
  → api/src/collector.py (翻译实体名)
  → api/src/translator.py::build_coord_out (输出到 JSON)
  → data/json/monsters|items|props/*.json (coord 内联)
  → 前端 DetailPage.tsx (按 sub_group_parent 分组渲染)
```

### 步骤拆解

1. **SQL 查询** (`coordinates.py:get_sub_group_pool_info`)
   ```sql
   SELECT map_base, json_filename, group_parent, sub_group_parent,
          COUNT(DISTINCT original_keyword) as pool_size,
          GROUP_CONCAT(DISTINCT original_keyword) as keywords
   FROM spawners
   WHERE group_parent != '' AND sub_group_parent != '' AND has_lootdrop = 1
   GROUP BY map_base, json_filename, group_parent, sub_group_parent
   ```
   按 `(map, file, group_parent, sub_group_parent)` 分组，统计各 ObjectLinker 子池内的独立实体种类数和实体名列表。

2. **名称翻译** (`collector.py`)
   用 `entity_classification` 判断实体类型（monster/props/item），取出对应 `translation_key` 调用 `NameResolver.resolve()`，得到中文显示名。GrimveilCloak→阴森帷幕披风等。

3. **JSON 注入** (`translator.py:build_coord_out`)
   每个 coord 的 `sub_pool_size`（子池实体种类数）和 `sub_pool_names`（翻译后的实体名列表）随 `coords[]` 字段写入实体详情 JSON。

4. **前端分组渲染** (`DetailPage.tsx`)
   ```tsx
   const linkerGroups = new Map</* sub_group_parent → {coords, poolSize, poolNames} */>();
   for (const c of mapCoords) {
     const sgp = c.sub_group_parent, gp = c.group_parent;
     if (!sgp || !gp) continue;
     // 按 `${gp}::${sgp}` 分组
   }
   // 每组显示: (entityName1、entityName2、...poolSize种选uniquePos · uniquePos点选1)
   ```

   效果：`(骷髅冠军、阴森帷幕披风2种选3 · 3点选1)`

### 关键字段

| 字段 | 来源 | 含义 |
|------|------|------|
| `sub_group_parent` | search_engine → spawners 表 | ObjectLinker 名称（如 BP_GameObjectLinker_C_3） |
| `sub_pool_size` | SQL COUNT(DISTINCT original_keyword) | 该 linker 子池的实体种类数 |
| `sub_pool_names` | SQL GROUP_CONCAT + NameResolver 翻译 | 子池内所有实体的翻译名列表 |
| `uniquePos` | 前端按 (x,y,z) 去重 | 该实体在此 linker 中的 spawn 位置数 |

### 子池分组（Blindfall Pit 全量）

| Linker | 子池实体 | 种数 | spawner 数 |
|--------|----------|------|-----------|
| C_1 | 宝藏堆, 金矿脉, 阴森帷幕披风 | 3 | 12 |
| C_3 | 骷髅冠军, 阴森帷幕披风 | 2 | 4 |
| C_5 | 幽鬼, 阴森帷幕披风 | 2 | 4 |
| C_7 | 骷髅斧手, GuardsmanFromFakeDeath, 骷髅长枪兵, 骷髅双手剑士, 阴森帷幕披风 | 5 | 65 |
| C_9 | 骷髅弓箭手, 骷髅弩手, 阴森帷幕披风 | 3 | 9 |
| C_11 | 骷髅弓箭手, 骷髅冠军, 骷髅弩手, 骷髅长枪兵, 骷髅双手剑士, 幽鬼, 阴森帷幕披风 | 7 | 7 |

## 共生池 vs 冲突池（互斥与共存）

### 区分标准

ObjectLinker（BP_GameObjectLinker_C）在游戏中有两种语义，通过 `group_parent` 字段区分：

| 类型 | 条件 | 含义 | 显示 |
|------|------|------|------|
| **冲突池（互斥）** | `group_parent != ''` | Linker 是 BP_GameSpawnerGroup_C 的子级，多个实体竞争同一刷怪槽，N 种中选 M 种 | `(名1、名2、...N种选M)` |
| **共生池（共存）** | `group_parent == ''` 且 `sub_group_parent != ''` | Linker 直接挂在场景中，所含实体全部同时存在，无互斥关系 | 不标注，同普通坐标点 |

### 代码三层过滤

共生池在数据管线和前端的**三层检查**中均被正确过滤，不会产生子池标注文字：

1. **SQL 查询**（`coordinates.py:get_sub_group_pool_info`）：
   ```sql
   WHERE group_parent != '' AND sub_group_parent != '' AND has_lootdrop = 1
   ```
   共生池 `group_parent` 为空 → 不会被聚合统计

2. **JSON 注入**（`translator.py:build_coord_out`）：
   ```python
   if sub_pool_info and _sgp:
       key = (c["map_base"], c["json_filename"], _gp, _sgp)
       spi = sub_pool_info.get(key)
       if spi and spi[0] > 0:
           out["sub_pool_size"] = spi[0]
           out["sub_pool_names"] = spi[1]
   ```
   共生池未进入 `sub_pool_info` → `spi = None` → `sub_pool_size`/`sub_pool_names` 不注入

3. **前端条件**（`DetailPage.tsx`）：
   ```tsx
   const sgp = c.sub_group_parent, gp = c.group_parent;
   if (!sgp || !gp) continue;
   ```
   共生池 `gp` 为空字符串 → `!gp` 为 `true` → continue 跳过渲染

### 分布统计

| 类型 | JSON 文件数 | 示例 |
|------|-----------|------|
| 冲突池（有 `group_parent`） | 11 | `Crypt_BlindfallPit_D.json` |
| 共生池（无 `group_parent`） | 41 | `Firedeep_MagmaFalls_D.json` |

共生池的典型场景是 Boss 房（如 Firedeep_MagmaFalls 的赤焰巨像 + 地面宝箱+矿石+药水共存）、宝藏房（CaveMaze 的独眼巨人+卓越宝箱+饰品等）、以及各类固定布局的特殊模块。

## 对比

| 版本 | GrimveilCloak 点数 | 标签 | 说明 |
|------|-------------------|------|------|
| 修复前 | 1 | 11种选1 | 6 个 ObjectLinker 被去重合并，groupCount=1 |
| 修复后 | 6 | 11种选6 | 使用 sub_group_parent 去重，groupCount=6 |
| 实际游戏 | 1 物理点 | 6 子组独立抽选 | 引擎去重，最多 1 个 |
