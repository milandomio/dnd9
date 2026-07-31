# Blindfall Pit 概率计算记录

## 结论

Blindfall Pit 的基础模块出现概率不是固定配置，而是由 Crypt 随机地牢的 Dungeon、DungeonLayout 和 DungeonModule 三层资产共同推导：

```text
P(Blindfall Pit)
= P(抽中含 Rare 槽的布局)
  × P(Rare 模块池抽中 Blindfall Pit)
= (2 / 40) × (1 / 5)
= 1%
```

当前页面显示的 `0.84%` 是在上述布局概率之后增加中心塔覆盖修正得到的有效出现概率，不应替代基础 `1%` 的来源：

```text
P(有效出现)
= 1% × (25 - 2 × 2) / 25
= 1% × 21 / 25
= 0.84%
```

## N_Solo 端到端计算链

以下链路是本记录的主计算路径，起点固定为：

```text
Data/Generated/V2/Dungeon/Dungeon/Id_Dungeon_RandomCrypt_N_Solo.json
```

从该文件读取：

```text
Properties.LayoutSize = 5
Properties.Layouts = [Crypt_5x5_01 ... Crypt_5x5_40]
Properties.ModuleType = EDCDungeonModuleType::Crypt
Properties.NumMaxRares = 1
Properties.LevelAsset = Crypt_5x5_R_P
```

随后按以下顺序推导，任何一步的源数据变化都必须重新计算后续结果：

```text
1. N_Solo.Properties.Layouts
   -> 40 个 Id_DungeonLayout_Crypt_5x5_*.json

2. 每个 DungeonLayout.Properties.Slots[].SlotTypes[].SlotType
   -> _01 有 1 个 Rare
   -> _02 有 1 个 Rare
   -> _03 ... _40 有 0 个 Rare
   -> 2 / 40 个布局提供稀有模块槽

3. N_Solo.Properties.NumMaxRares = 1
   -> 每局最多执行 1 次稀有模块抽取
   -> 当前每个含 Rare 布局只有 1 个 Rare 槽
   -> 布局层稀有机会 = 2 / 40 = 5%

4. N_Solo.Properties.ModuleType = Crypt
   -> 扫描 DungeonModule 资产
   -> 保留 ModuleType=Crypt 且 bIsRare=true
   -> 得到 5 个稀有模块：
      BlindfallPit, LightlessChamber_01, LightlessTomb_01,
      MadCorridors, TorchboundVault

5. 稀有模块池没有权重字段
   -> 按均匀抽取处理
   -> P(BlindfallPit | Rare 抽取) = 1 / 5 = 20%

6. 基础模块概率
   -> 5% × 20% = 1%

7. N_Solo.Properties.LayoutSize = 5
   -> 5 × 5 = 25 个地图格

8. Id_DungeonModule_CenterTower.json.Properties.Size = {X: 2, Y: 2}
   -> CenterTower_HR_D 覆盖 2 × 2 = 4 个地图格
   -> BlindfallPit 有效落点 = 25 - 4 = 21 个地图格

9. 最终有效概率
   -> 1% × 21 / 25
   -> 0.84%
```

合并写成一个公式：

```text
P(BlindfallPit 有效出现)
= 100%
  × (N_Solo 中含 Rare 的布局数 / N_Solo.Layouts 总数)
  × (1 / Crypt 稀有模块数)
  × ((N_Solo.LayoutSize² - CenterTower.Size.X × CenterTower.Size.Y)
     / N_Solo.LayoutSize²)

= 100%
  × (2 / 40)
  × (1 / 5)
  × ((5² - 2 × 2) / 5²)

= 0.84%
```

这里的 `100%` 是概率换算基数，不是从 `N_Solo` 读取的固定概率；`2`、`40`、`5`、`5`、`2`、`2` 均必须由后续资产字段重新统计或读取。

## 原始文件链

```text
Dungeon
  -> Id_Dungeon_RandomCrypt_N_Solo.json
  -> Properties.Layouts[]
  -> Id_DungeonLayout_Crypt_5x5_01.json ... _40.json
  -> Properties.Size / Properties.Slots[].SlotTypes[].SlotType
  -> Rare 槽统计

Dungeon
  -> Properties.NumMaxRares
  -> 每局最多抽取的稀有模块数量

DungeonModule
  -> Id_DungeonModule_Crypt_BlindfallPit.json
  -> Properties.ModuleType == Crypt
  -> Properties.bIsRare == true
  -> 稀有模块池成员
```

### Dungeon 资产

Crypt 5x5 的随机 Dungeon 资产位于：

```text
Data/Generated/V2/Dungeon/Dungeon/
```

需要核对的文件为：

```text
Id_Dungeon_RandomCrypt_N_Solo.json
Id_Dungeon_RandomCrypt_N_Duo.json
Id_Dungeon_RandomCrypt_N_Trio.json
Id_Dungeon_RandomCrypt_HR_Solo.json
Id_Dungeon_RandomCrypt_HR_Duo.json
Id_Dungeon_RandomCrypt_HR_Trio.json
Id_Dungeon_RandomCrypt_A.json
Id_Dungeon_RandomCrypt_AHR.json
```

以 `Id_Dungeon_RandomCrypt_N_Solo.json` 为主校验样本：

```text
Properties.LayoutSize = 5
Properties.LevelAsset = .../Maps/Dungeon/Layouts/Crypt_5x5_R_P
Properties.Layouts = 40 个 Crypt_5x5 布局引用
Properties.ModuleType = Crypt
Properties.NumMaxRares = 1
```

其他 Crypt 5x5 模式应复核 `Layouts`、`NumMaxRares` 和 `LevelAsset` 是否仍一致；不能只根据文件名推断结果。

Crypt S2R 使用：

```text
Id_Dungeon_RandomCrypt_S2R.json
```

它引用 Crypt 4x4 布局，原始核查结果为 10 个布局且没有 `Rare` 槽，因此 Blindfall Pit 在该模式下的布局概率为 `0`。

### DungeonLayout 资产

布局资产位于：

```text
Data/Generated/V2/Dungeon/DungeonLayout/
```

Crypt 5x5 的引用范围为：

```text
Id_DungeonLayout_Crypt_5x5_01.json
...
Id_DungeonLayout_Crypt_5x5_40.json
```

每个文件读取以下字段：

```text
Properties.Size.X
Properties.Size.Y
Properties.Slots[]
Properties.Slots[].SlotTypes[]
Properties.Slots[].SlotTypes[].SlotType
```

统计规则：

1. 只统计 Dungeon 资产 `Properties.Layouts[]` 实际引用的布局，不要用目录中所有同名文件替代引用列表。
2. 校验每个布局的 `Size` 是否等于 Dungeon 的 `LayoutSize`。
3. 在每个布局的所有 `Slots[].SlotTypes[]` 中统计 `SlotType == "EDCDungeonLayoutSlotType::Rare"`。
4. 当前原始结果为 `_01` 和 `_02` 各 1 个 Rare 槽，其余 38 个布局为 0。
5. 当前每个含 Rare 槽布局只有 1 个 Rare 槽，且 `NumMaxRares = 1`，所以“含 Rare 槽布局数”就是“本局获得稀有模块抽取机会”的分子。

当前布局统计表：

| 项目 | 数值 |
|---|---:|
| Crypt 5x5 布局总数 | 40 |
| 含 Rare 槽布局数 | 2 |
| Rare 槽总数 | 2 |
| 每个含 Rare 布局的 Rare 槽数 | 1 |
| `NumMaxRares` | 1 |
| 布局层概率 | `2 / 40 = 5%` |

### DungeonModule 资产

模块资产位于：

```text
Data/Generated/V2/Dungeon/DungeonModule/
```

稀有池不能用模块名称前缀猜测，必须读取每个 Crypt 模块的属性：

```text
Properties.ModuleType == "EDCDungeonModuleType::Crypt"
Properties.bIsRare == true
```

原始稀有模块池为：

```text
Id_DungeonModule_Crypt_BlindfallPit.json
Id_DungeonModule_Crypt_LightlessChamber_01.json
Id_DungeonModule_Crypt_LightlessTomb_01.json
Id_DungeonModule_Crypt_MadCorridors.json
Id_DungeonModule_Crypt_TorchboundVault.json
```

每个模块的 `Properties.Size` 当前均为 `1x1`。原始核查结果：Crypt 稀有模块总数为 5，资产中没有暴露额外权重或优先级字段，因此按均匀池计算：

```text
P(Rare 模块池抽中 Blindfall Pit)
= 1 / count(Crypt 模块中 bIsRare == true)
= 1 / 5
= 20%
```

如果未来出现 `Rare` 模块权重字段，或游戏资产/解包数据暴露非均匀选择参数，必须停止使用 `1 / 稀有模块数量`，改为按该权重归一化。

## 可重复计算路径

布局文件变更后，按以下顺序重新计算，禁止直接修改前端概率常量：

### 1. 确定模式和布局引用

读取对应 `Id_Dungeon_RandomCrypt_*.json`：

```text
layout_size = Properties.LayoutSize
layout_refs = Properties.Layouts
num_max_rares = Properties.NumMaxRares
module_type = Properties.ModuleType
```

将 `Layouts[].AssetPathName` 的末段转换为 `Data/Generated/V2/Dungeon/DungeonLayout/` 下的 JSON 文件名，并确认文件全部存在。

### 2. 重新统计布局层

对 `layout_refs` 逐个读取布局文件：

```text
layout_count = len(layout_refs)
rare_layout_count = 0
rare_slot_total = 0

for layout in layout_refs:
    assert layout.Properties.Size == (layout_size, layout_size)
    rare_slots = count(
        slot_type == "EDCDungeonLayoutSlotType::Rare"
        for slot in layout.Properties.Slots
        for slot_type in slot.SlotTypes[].SlotType
    )
    rare_slot_total += rare_slots
    if rare_slots > 0:
        rare_layout_count += 1
```

在当前游戏规则成立时使用：

```text
P(有稀有模块机会) = rare_layout_count / layout_count
```

如果出现以下任一情况，不能直接套用该公式，必须先确认游戏抽取语义：

```text
rare_slot_total != rare_layout_count
num_max_rares != 1
同一布局存在多个 Rare 槽
布局列表存在明确权重
```

原因是布局 JSON 只描述槽位，不描述 Unreal 运行时如何在多个槽位之间分配稀有模块。

### 3. 重新统计稀有模块池

读取 `Properties.ModuleType` 匹配的所有 DungeonModule 资产，筛选：

```text
module.Properties.ModuleType == "EDCDungeonModuleType::Crypt"
module.Properties.bIsRare == true
```

然后计算：

```text
rare_module_count = len(rare_modules)
P(Blindfall Pit | 稀有模块抽取) = 1 / rare_module_count
```

目标模块必须通过其 `Name` 或资产文件名精确匹配 `Crypt_BlindfallPit`，不能使用显示名 `Blindfall Pit` 反查。

### 4. 计算基础概率

```text
base_rate_percent
= 100
  × (rare_layout_count / layout_count)
  × (1 / rare_module_count)
```

当前代入：

```text
100 × (2 / 40) × (1 / 5)
= 1%
```

### 5. 计算中心塔覆盖后的有效概率

中心塔不是基础 `1%` 的来源，而是地图落槽后的覆盖修正。相关资产链为：

```text
Data/Generated/V2/Dungeon/DungeonModule/Id_DungeonModule_CenterTower.json
  -> Properties.Size = {X: 2, Y: 2}
  -> SubLevelAssetD_HR = .../CenterTower/CenterTower_HR_D
```

在 Crypt 5x5 网格中：

```text
grid_cell_count = layout_size × layout_size = 25
covered_cell_count = center_tower.Properties.Size.X × center_tower.Properties.Size.Y = 4
effective_rate_percent
= base_rate_percent × (grid_cell_count - covered_cell_count) / grid_cell_count
= 1% × 21 / 25
= 0.84%
```

该覆盖公式只有在中心塔确实覆盖同一 5x5 随机网格、且稀有模块在 25 格中均匀落点时成立；如果布局尺寸、中心塔尺寸、中心塔出现条件或落点规则改变，应重新核验，不能只替换数字。

## 重要限制

1. `DungeonLayout` 的 `Module` 当前为 `null`，布局资产只提供槽类型；具体稀有模块分配逻辑在 Unreal 运行时/编译代码中，JSON 未暴露选择权重。
2. `Maps/Dungeon/Layouts/Crypt_5x5_R_P.json` 是 `LevelAsset` 的关卡布局文件，不是 40 个随机布局的概率表；不能用其中的模块引用替代 `Dungeon.Properties.Layouts[]`。
3. `bIsRare` 是稀有池成员判定，不能把所有 `ModuleType=Crypt` 的模块都放入稀有池。
4. `NumMaxRares` 决定当前“每局最多一次稀有抽取”的前提；该字段变化时必须重新判断概率模型。
5. 当前 `1/5` 是在没有权重字段时的均匀池假设，不代表已从 Unreal 二进制中证明了运行时一定均匀。
6. 历史原始记录为提交 `501d7b59` 的 `docs/BLINDFALL_PIT_PROBABILITY_ANALYSIS.md`；后续 `4a469816` 只增加中心塔覆盖修正，没有改变布局层 `2/40` 与稀有池 `1/5` 的原始推导。

## 变更检查清单

布局或模块资产更新后，至少记录以下结果：

```text
[ ] Dungeon 资产引用的布局数量
[ ] LayoutSize 与每个布局 Size
[ ] 每个布局的 Rare 槽数量及 Rare 布局列表
[ ] NumMaxRares
[ ] Crypt + bIsRare 模块列表
[ ] 是否存在模块权重/优先级字段
[ ] 基础概率公式和代入值
[ ] 中心塔尺寸、覆盖格数和有效概率
[ ] N/HR/A/AHR/S2R 各模式是否仍共享该结论
```
