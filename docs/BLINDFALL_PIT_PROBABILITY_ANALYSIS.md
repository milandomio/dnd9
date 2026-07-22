# Crypt_BlindfallPit 模块出现概率分析

> 分析日期：2026-07-22
> 数据来源：`DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Dungeon/` 游戏解包 JSON

## 背景

用户需要推算游戏中 Crypt 5x5 地图（废墟2层·地穴）中出现 `Crypt_BlindfallPit` 稀有模块的概率。

## 数据源结构

模块出现概率由三层配置决定：

```
Dungeon (Id_Dungeon_RandomCrypt_*)
  ├── Layouts[] → DungeonLayout (Id_DungeonLayout_Crypt_5x5_*)
  │     └── Slots[].SlotTypes[].SlotType (Escape/Boss/Rare/Key/Altar/...)
  └── ModuleType: Crypt → DungeonModule (Id_DungeonModule_Crypt_*)
        └── bIsRare: true/false
```

**关键：** 布局文件只定义 slot 类型，模块分配在游戏编译代码中完成（JSON 中 `"Module": null`、`"Rotation": "None"`）。概率基于可用稀有模块数量推算。

## 完整概率推算

### 步骤 1：布局选中带 Rare 槽

| 维度 | 数值 |
|------|------|
| 5x5 布局总数 | **40** (`Id_DungeonLayout_Crypt_5x5_01` ~ `_40`) |
| 含 Rare 槽的布局 | **2**（01: slot 20, 02: slot 18） |
| Rare 槽布局占比 | **2/40 = 5%** |

假设 40 个布局等概率选择（数据中无权重字段）。

### 步骤 2：稀有模块池中选中 BlindfallPit

| 维度 | 数值 |
|------|------|
| Crypt 稀有模块总数 | **5**（全为 1x1） |
| 稀有模块列表 | BlindfallPit、LightlessChamber_01、LightlessTomb_01、MadCorridors、TorchboundVault |
| 每个布局的 Rare 槽位数 | **1**（每个布局只有一个 Rare slot） |
| 每局最大稀有模块数 | **1** (`NumMaxRares: 1`) |
| 选中 BlindfallPit 概率 | **1/5 = 20%** |

假设 5 个稀有模块等概率选择（模块 JSON 中无权重/优先级字段）。

### 步骤 3：综合概率

```
P(出现 BlindfallPit) = P(选中带Rare槽布局) × P(稀有池选中BlindfallPit)
                     = (2/40) × (1/5)
                     = 2/200
                     = 1%
```

## 各模式对比

| 模式 | LayoutSize | 布局数 | NumMaxRares | 含Rare槽布局数 | BlindfallPit 概率 |
|------|-----------|-------|-------------|---------------|-----------------|
| N (普通) Solo/Duo/Trio | 5 | 40 | 1 | 2 | **~1%** |
| HR (豪客赛) Solo/Duo/Trio | 5 | 40 | 1 | 2 | **~1%** |
| A (冒险者) | 5 | 40 | 1 | 2 | **~1%** |
| AHR | 5 | 40 | 1 | 2 | **~1%** |
| S2R (逆袭赛) | **4** | **10** | **无** | **0** | **0%（不存在）** |

> **注意：** 所有 Crypt 5x5 模式（N/HR/A/AHR）共用同一份布局列表和同一套地图文件（`Crypt_5x5_R_P`），概率完全相同。

## S2R 特殊性

S2R 使用独立的 `Crypt_4x4_HR_R_P` 地图文件和 10 个 4x4 布局。4x4 布局中**没有任何 Rare 槽位**，因此 BlindfallPit 不可能在 S2R 中出现。

## 限制条件

1. **模块分配算法未知**：最终的模块选择逻辑在 Unreal Engine Blueprint/C++ 中实现，未被导出为 JSON。以上推算假设均匀随机分布。
2. **无权重数据**：布局选择和模块选择均无权重/优先级字段，无法排除加权随机分配的可能性。
3. **布局复用**：`Crypt_5x5_R_P` 同时是 Rare Pool 和 HR 地图文件（文件名中 `_R_` 含义可能为 "Random" 而非 "Rare"），HR 模式仅通过 `FloorRule` 和 `DefaultDungeonGrade` 区分。
