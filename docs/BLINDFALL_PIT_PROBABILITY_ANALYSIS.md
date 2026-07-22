# Crypt_BlindfallPit 模块出现概率分析

> 分析日期：2026-07-22
> 更新日期：2026-07-22（补充阴森帷幕披风完整掉落链路）
> 数据来源：`DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Dungeon/` 游戏解包 JSON + `spawners`/`lootdrop_groups`/`mutually_exclusive_groups` DB 表

## 背景

推算 Crypt 5x5 地图（废墟2层·地穴）中出现 **盲坑（Crypt_BlindfallPit）** 稀有模块的概率，以及该模块内 **阴森帷幕披风（GrimveilCloak）** 的完整掉落概率。

## 游戏内译名对照

| 英文名 | 游戏中译 |
|-------|---------|
| Crypt | 废墟2层（地穴） |
| Crypt_BlindfallPit | 盲坑 |
| Crypt_LightlessChamber_01 | 无光密室 |
| Crypt_LightlessTomb_01 | 无光陵墓 |
| Crypt_MadCorridors | 失心长廊 |
| Crypt_TorchboundVault | 炬封宝库 |
| GrimveilCloak | 阴森帷幕披风 |

## 数据源结构

```
Dungeon (Id_Dungeon_RandomCrypt_*)
  ├── Layouts[] → DungeonLayout (Id_DungeonLayout_Crypt_5x5_*)
  │     └── Slots[].SlotTypes[].SlotType (Escape/Boss/Rare/Key/Altar/...)
  └── ModuleType: Crypt → DungeonModule (Id_DungeonModule_Crypt_*)
        └── bIsRare: true/false
```

**关键：** 布局文件只定义 slot 类型，模块分配在游戏编译代码中完成（JSON 中 `"Module": null`、`"Rotation": "None"`）。概率基于可用稀有模块数量推算。

## 第一层：盲坑模块出现概率（~1%）

### 布局验证

经逐槽核查 40 个 5x5 布局文件：

| 维度 | 数值 |
|------|------|
| 5x5 布局总数 | **40** (`Id_DungeonLayout_Crypt_5x5_01` ~ `_40`) |
| 含 Rare 槽的布局 | **2**（01: slot 20, 02: slot 18） |
| 含多个 Rare 槽的布局 | **0**（不存在双 Rare 槽布局） |
| Rare 槽总数 | **2**（2 个布局各 1 个） |
| Rare 槽布局占比 | **2/40 = 5%** |

**用户提及的双 Rare 槽场景在 Crypt 5x5 中不存在**，每局最多只有 1 次稀有模块抽取机会。

### 稀有模块池

| 维度 | 数值 |
|------|------|
| 稀有模块总数 | **5**（全为 1x1） |
| 稀有模块列表 | 盲坑、无光密室、无光陵墓、失心长廊、炬封宝库 |
| 每局最大稀有模块数 | **1** (`NumMaxRares: 1`) |
| 选中盲坑概率 | **1/5 = 20%** |

### 盲坑出现概率

```
P(盲坑出现) = P(带Rare槽布局) × P(稀有池选中盲坑)
            = (2/40) × (1/5)
            = 1%
```

## 第二层：盲坑内的冲突生成（11 种选 1）

盲坑模块的地图文件 `Crypt_BlindfallPit_D.json` 中，有一个互斥生成组 `BP_GameSpawnerGroup_C_8`。组内 11 种实体在坐标 (810, -10, -1600) 冲突生成，每局仅选 1 种。

| # | 实体 | 类型 | DB 行数 |
|:---:|------|:---:|:---:|
| 1 | 阴森帷幕披风（GrimveilCloak） | lootdrop | 6 |
| 2 | 宝藏堆（Hoard01_3） | props | 3 |
| 3 | 金矿（Ore_GoldOre，4 种稀有度合并） | props | 8 |
| 4 | 骷髅弓箭手（SkeletonArcher） | monster | 5 |
| 5 | 骷髅斧兵（SkeletonAxeman） | monster | 2 |
| 6 | 骷髅冠军（SkeletonChampion） | monster | 4 |
| 7 | 骷髅弩手（SkeletonCrossbowman） | monster | 5 |
| 8 | 骷髅卫兵（装死）（SkeletonGuardmanFromFakeDeath） | monster | 56 |
| 9 | 骷髅长枪兵（SkeletonSpearman） | monster | 4 |
| 10 | 骷髅双手剑士（SkeletonSwordman） | monster | 4 |
| 11 | 幽鬼（Wraith） | monster | 4 |

**坐标验证：** DB 中阴森帷幕披风有 6 条 spawner 记录，但全部位于**同一个坐标** (810, -10, -1600, z=-1600)。所谓"6 个坐标"系将 6 条 DB 行误认为 6 个不同坐标。

**选中概率：** **1/11 ≈ 9.09%**

## 第三层：阴森帷幕披风的掉落率（2.5%）

### 掉落组

`spawner_entries` 中 `keyword='GrimveilCloak'` 仅关联一个掉落组：

```
spawner_entries.GrimveilCloak → lootdrop_group_id = ID_LootdropGroup_GrimveilCloak
  → lootdrop_id = ID_Lootdrop_GrimveilCloak
    → item_name = GrimveilCloak_5001 (luck_grade=5, drop_count=1)
```

**没有任何其他物品共享此掉落组。** 若掉落 roll 失败，该位置不出特殊物品。

### 爆率权重（Crypt HR，dungeon_grade 3022）

| luck_grade | 权重 | 占比 | 产出 |
|:---:|---:|---:|------|
| 0 | 9750 | **97.5%** | 无特殊掉落（基础垃圾/金币） |
| 5 | 250 | **2.5%** | 阴森帷幕披风 |
| 1-4, 6-8 | 0 | 0% | 无 |

**掉落概率：** 250/10000 = **2.5%**

## 综合概率

### 公式

```
P(拿到披风) = P(盲坑出现) × P(选中披风容器) × P(容器出披风)
```

### 三种难度对比

| 层级 | 通用 | PVE | 普通 | 豪客赛 | 逆袭赛 |
|:---|:---:|:---:|:---:|:---:|:---:|
| ① 盲坑出现 | 1% | 同左 | 同左 | 同左 | **0%**（S2R 无 Rare） |
| ② 11 种选 1 | 1/11 | 同左 | 同左 | 同左 | — |
| ③ 掉落率 | — | 0.25% | 1.25% | **2.5%** | 2.5% |
| **综合概率** | — | **1/440,000** | **1/88,000** | **1/44,000** | **0** |
| 约等于 | — | 每 44 万局 1 个 | 每 8.8 万局 1 个 | **每 4.4 万局 1 个** | 无 |

豪客赛详细计算：

```
P(盲坑出现) × P(选中披风) × P(掉落)
= 1/100 × 1/11 × 2.5%
= 1/100 × 1/11 × 25/1000
= 25 / 1,100,000
= 1 / 44,000
≈ 0.00227%
```

### 一次完整的生成流程

```
进入废墟2层（地穴）5x5
  └→ 40 种布局抽 1
       └→ 2/40 = 5% → 带 Rare 槽的布局
            └→ 5 个稀有模块抽 1
                 └→ 1/5 = 20% → 盲坑（非盲坑则本局结束）
                      └→ 盲坑内 11 种生成物冲突
                           └→ 1/11 ≈ 9% → 阴森帷幕披风容器
                                └→ 容器掉落 roll
                                     ├─ 2.5% → 出披风 ✓
                                     └─ 97.5% → 无特殊掉落 ✗
```

## 各模式对比

| 模式 | LayoutSize | 布局数 | NumMaxRares | 含 Rare 槽布局数 | 盲坑概率 |
|------|-----------|-------|:-----------:|:---------------:|:-------:|
| N（普通）Solo/Duo/Trio | 5 | 40 | 1 | 2 | **1%** |
| HR（豪客赛）Solo/Duo/Trio | 5 | 40 | 1 | 2 | **1%** |
| A（冒险者） | 5 | 40 | 1 | 2 | **1%** |
| AHR | 5 | 40 | 1 | 2 | **1%** |
| S2R（逆袭赛） | **4** | **10** | **无** | **0** | **0%** |

> 所有 Crypt 5x5 模式（N/HR/A/AHR）共用同一份布局列表和地图文件（`Crypt_5x5_R_P`），概率完全相同。

## S2R 特殊性

S2R 使用独立的 `Crypt_4x4_HR_R_P` 地图文件和 10 个 4x4 布局，4x4 布局中**没有任何 Rare 槽位**，盲坑和披风均不可能出现。

## 限制条件

1. **模块分配算法未知**：稀有模块和布局的选择逻辑在 Unreal Engine C++ 中实现，未被导出为 JSON。以上推算假设均匀随机分布。
2. **无权重数据**：布局选择和模块选择均无权重/优先级字段。
3. **游戏版本**：数据基于当前游戏解包版本，后续更新可能改变布局配置或掉落权重。
