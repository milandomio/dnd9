# Blindfall Pit Probability Calculation Record

## 1. Executive Summary

The probability of `Blindfall Pit` is not a fixed value stored in a single
configuration field. It is derived from three layers of Crypt random-dungeon
assets:

1. The `Dungeon` asset selects one of its referenced layouts.
2. The selected `DungeonLayout` may provide a `Rare` module slot.
3. The Crypt rare-module pool selects one rare module.

For the Crypt 5x5 N_Solo mode, the calculation is:

```text
P(Blindfall Pit before map coverage)
= P(layout contains a Rare slot)
  x P(Blindfall Pit is selected from the Rare module pool)
= (2 / 40) x (1 / 5)
= 1%
```

The `0.84%` value shown by the current page is the effective probability
after applying the CenterTower coverage correction. It must not be treated as
the source of the base `1%` probability:

```text
P(effective Blindfall Pit appearance)
= 1% x (25 - 2 x 2) / 25
= 1% x 21 / 25
= 0.84%
```

### Result at a glance

| Stage                                      | Formula         |  Result |
| ------------------------------------------ | --------------- | ------: |
| Layout-level Rare opportunity              | `2 / 40`        |    `5%` |
| Blindfall Pit selection from the Rare pool | `1 / 5`         |   `20%` |
| Base module appearance probability         | `5% x 20%`      |    `1%` |
| CenterTower coverage correction            | `(25 - 4) / 25` |   `84%` |
| Effective module appearance probability    | `1% x 21 / 25`  | `0.84%` |

## 2. Scope and Primary Input

This record describes the Crypt 5x5 random-dungeon calculation, using the
N_Solo dungeon asset as the primary verification sample.

The calculation starts at:

```text
Data/Generated/V2/Dungeon/Dungeon/Id_Dungeon_RandomCrypt_N_Solo.json
```

The relevant fields are:

```text
Properties.LayoutSize = 5
Properties.Layouts = [Crypt_5x5_01 ... Crypt_5x5_40]
Properties.ModuleType = EDCDungeonModuleType::Crypt
Properties.NumMaxRares = 1
Properties.LevelAsset = Crypt_5x5_R_P
```

Every value in the final formula must be rechecked if these assets change.
The numbers `2`, `40`, `5`, `5`, `2`, and `2` are derived values or asset
fields, not arbitrary constants.

## 3. End-to-End Calculation Chain

The following is the complete derivation for `Crypt_BlindfallPit` in
Crypt 5x5 N_Solo mode.

### Step 1: Read the dungeon's layout references

`N_Solo.Properties.Layouts` references 40 Crypt 5x5 layout assets:

```text
Id_DungeonLayout_Crypt_5x5_01.json
...
Id_DungeonLayout_Crypt_5x5_40.json
```

The denominator of the layout-level probability is therefore `40`, provided
that all referenced layouts are equally likely. The exported JSON does not
expose an alternative layout weight field.

### Step 2: Count layouts that contain a Rare slot

For every referenced `DungeonLayout`, inspect:

```text
Properties.Slots[].SlotTypes[].SlotType
```

The current result is:

```text
_01: 1 Rare slot
_02: 1 Rare slot
_03 ... _40: 0 Rare slots
```

Thus, 2 of the 40 layouts provide a rare-module opportunity:

```text
P(layout provides a Rare opportunity)
= 2 / 40
= 5%
```

The current layout statistics are:

| Metric                                    |         Value |
| ----------------------------------------- | ------------: |
| Referenced Crypt 5x5 layouts              |          `40` |
| Layouts containing at least one Rare slot |           `2` |
| Total Rare slots                          |           `2` |
| Rare slots per qualifying layout          |           `1` |
| `NumMaxRares`                             |           `1` |
| Layout-level Rare opportunity             | `2 / 40 = 5%` |

Because every qualifying layout currently has exactly one Rare slot and
`NumMaxRares = 1`, the number of qualifying layouts can be used as the
numerator for the current model.

### Step 3: Apply `NumMaxRares`

The dungeon asset contains:

```text
Properties.NumMaxRares = 1
```

Under the current asset structure, this means that a run can perform at most
one rare-module draw. It also matches the current layout data: each layout
that contains a Rare slot contains only one such slot.

This assumption must be revisited if any of the following changes:

- `NumMaxRares` is no longer `1`.
- A layout contains multiple Rare slots.
- The game runtime distributes multiple Rare slots using a rule not visible
  in the exported JSON.

### Step 4: Build the Crypt rare-module pool

Do not infer rare-pool membership from a module name prefix. Inspect every
Crypt `DungeonModule` asset and retain only modules satisfying both
conditions:

```text
Properties.ModuleType == "EDCDungeonModuleType::Crypt"
Properties.bIsRare == true
```

The current Crypt rare-module pool contains five modules:

```text
BlindfallPit
LightlessChamber_01
LightlessTomb_01
MadCorridors
TorchboundVault
```

The corresponding asset files are:

```text
Id_DungeonModule_Crypt_BlindfallPit.json
Id_DungeonModule_Crypt_LightlessChamber_01.json
Id_DungeonModule_Crypt_LightlessTomb_01.json
Id_DungeonModule_Crypt_MadCorridors.json
Id_DungeonModule_Crypt_TorchboundVault.json
```

No rare-module weight or priority field is exposed in the current assets.
Therefore, the current calculation treats this as a uniform pool:

```text
P(Blindfall Pit | Rare draw)
= 1 / count(Crypt modules where bIsRare == true)
= 1 / 5
= 20%
```

### Step 5: Calculate the base module probability

Combine the layout opportunity with the rare-pool selection probability:

```text
P(Blindfall Pit before map coverage)
= 5% x 20%
= 1%
```

This is the base probability of selecting `Blindfall Pit` before accounting
for a map cell covered by `CenterTower`.

### Step 6: Apply the CenterTower coverage correction

The dungeon has a layout size of `5`, so the random grid contains:

```text
grid cell count = 5 x 5 = 25
```

The relevant CenterTower module asset is:

```text
Data/Generated/V2/Dungeon/DungeonModule/Id_DungeonModule_CenterTower.json
```

Its current size is:

```text
Properties.Size = {X: 2, Y: 2}
```

The associated high-roller sublevel is:

```text
SubLevelAssetD_HR = .../CenterTower/CenterTower_HR_D
```

The CenterTower covers four cells:

```text
covered cell count = 2 x 2 = 4
effective Blindfall Pit cells = 25 - 4 = 21
```

Assuming the rare module is uniformly placed across the 25-cell grid, the
coverage correction is:

```text
P(survives CenterTower coverage)
= 21 / 25
= 84%
```

### Step 7: Calculate the final effective probability

Apply the coverage correction to the base module probability:

```text
P(effective Blindfall Pit appearance)
= 1% x 21 / 25
= 0.84%
```

## 4. Combined Formula

The complete formula can be written as follows:

```text
P(effective Blindfall Pit appearance)
= 100%
  x (number of N_Solo layouts containing a Rare slot
     / total number of N_Solo layout references)
  x (1 / number of Crypt rare modules)
  x ((N_Solo.LayoutSize^2
      - CenterTower.Size.X x CenterTower.Size.Y)
     / N_Solo.LayoutSize^2)

= 100%
  x (2 / 40)
  x (1 / 5)
  x ((5^2 - 2 x 2) / 5^2)

= 0.84%
```

The leading `100%` is the probability conversion base. It is not a fixed
probability read from the `N_Solo` asset.

## 5. Source Asset Chain

### Dungeon to layout statistics

```text
Dungeon
  -> Id_Dungeon_RandomCrypt_N_Solo.json
  -> Properties.Layouts[]
  -> Id_DungeonLayout_Crypt_5x5_01.json ... _40.json
  -> Properties.Size
  -> Properties.Slots[].SlotTypes[].SlotType
  -> Rare-slot statistics
```

### Dungeon to maximum rare draws

```text
Dungeon
  -> Properties.NumMaxRares
  -> Maximum number of rare-module draws per run
```

### DungeonModule to rare-pool membership

```text
DungeonModule
  -> Id_DungeonModule_Crypt_BlindfallPit.json
  -> Properties.ModuleType == Crypt
  -> Properties.bIsRare == true
  -> Crypt rare-module pool membership
```

### CenterTower coverage correction

```text
DungeonModule
  -> Id_DungeonModule_CenterTower.json
  -> Properties.Size = {X: 2, Y: 2}
  -> SubLevelAssetD_HR = .../CenterTower/CenterTower_HR_D
  -> 4 covered cells in the 5x5 grid
```

## 6. Asset Verification Details

### 6.1 Dungeon assets

The Crypt random-dungeon assets are located at:

```text
Data/Generated/V2/Dungeon/Dungeon/
```

The modes that should be checked are:

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

Use `Id_Dungeon_RandomCrypt_N_Solo.json` as the primary sample and verify:

```text
Properties.LayoutSize = 5
Properties.LevelAsset = .../Maps/Dungeon/Layouts/Crypt_5x5_R_P
Properties.Layouts = 40 Crypt 5x5 layout references
Properties.ModuleType = Crypt
Properties.NumMaxRares = 1
```

The other Crypt 5x5 modes must be checked independently for `Layouts`,
`NumMaxRares`, and `LevelAsset`. Do not infer equivalence from file names.

Crypt S2R uses:

```text
Id_Dungeon_RandomCrypt_S2R.json
```

It references Crypt 4x4 layouts. The original verification found 10 layouts
and no Rare slots, so the layout-level Blindfall Pit probability for that
mode is `0` under the current data.

### 6.2 DungeonLayout assets

The layout assets are located at:

```text
Data/Generated/V2/Dungeon/DungeonLayout/
```

The referenced Crypt 5x5 range is:

```text
Id_DungeonLayout_Crypt_5x5_01.json
...
Id_DungeonLayout_Crypt_5x5_40.json
```

Read these fields from each referenced layout:

```text
Properties.Size.X
Properties.Size.Y
Properties.Slots[]
Properties.Slots[].SlotTypes[]
Properties.Slots[].SlotTypes[].SlotType
```

Verification rules:

1. Count only layouts actually referenced by `Dungeon.Properties.Layouts[]`.
   Do not replace the reference list with every similarly named file in the
   directory.
2. Verify that each layout's `Size` matches the dungeon `LayoutSize`.
3. Count `SlotType == "EDCDungeonLayoutSlotType::Rare"` across all
   `Slots[].SlotTypes[]` entries.
4. The current result is one Rare slot in `_01`, one in `_02`, and zero in the
   remaining 38 layouts.
5. Because each qualifying layout currently has one Rare slot and
   `NumMaxRares = 1`, the qualifying-layout count is the numerator for the
   current layout-level model.

### 6.3 DungeonModule assets

The module assets are located at:

```text
Data/Generated/V2/Dungeon/DungeonModule/
```

Rare-pool membership must be determined from properties:

```text
Properties.ModuleType == "EDCDungeonModuleType::Crypt"
Properties.bIsRare == true
```

The five currently verified modules are:

| Asset                       | Module type | `bIsRare` | Size  |
| --------------------------- | ----------- | --------- | ----- |
| `Crypt_BlindfallPit`        | `Crypt`     | `true`    | `1x1` |
| `Crypt_LightlessChamber_01` | `Crypt`     | `true`    | `1x1` |
| `Crypt_LightlessTomb_01`    | `Crypt`     | `true`    | `1x1` |
| `Crypt_MadCorridors`        | `Crypt`     | `true`    | `1x1` |
| `Crypt_TorchboundVault`     | `Crypt`     | `true`    | `1x1` |

The current assets expose no additional weight or priority field. Therefore:

```text
P(Blindfall Pit | Rare draw) = 1 / 5 = 20%
```

If a future asset exposes rare-module weights, or the unpacked data reveals a
non-uniform selection parameter, replace the uniform formula with normalized
weights. Do not continue using `1 / rare module count` without verification.

## 7. Reproducible Recalculation Procedure

When layout or module assets change, recalculate from source data. Do not
modify a frontend probability constant directly.

### 7.1 Select the mode and resolve layout references

Read the relevant `Id_Dungeon_RandomCrypt_*.json` asset:

```text
layout_size = Properties.LayoutSize
layout_refs = Properties.Layouts
num_max_rares = Properties.NumMaxRares
module_type = Properties.ModuleType
```

Convert the final segment of each `Layouts[].AssetPathName` into the matching
JSON filename under:

```text
Data/Generated/V2/Dungeon/DungeonLayout/
```

Confirm that every referenced layout file exists before counting anything.

### 7.2 Recalculate the layout-level probability

For every resolved layout:

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

Under the current game-data assumptions:

```text
P(rare-module opportunity)
= rare_layout_count / layout_count
```

Do not apply this formula without confirming the runtime semantics if any of
the following is true:

```text
rare_slot_total != rare_layout_count
num_max_rares != 1
one layout contains multiple Rare slots
the layout list exposes explicit weights
```

The reason is that layout JSON describes slot structure, but does not expose
how Unreal runtime code allocates rare modules among multiple slots.

### 7.3 Recalculate the rare-module pool

Read all `DungeonModule` assets matching the dungeon's module type and keep
only modules satisfying:

```text
module.Properties.ModuleType == "EDCDungeonModuleType::Crypt"
module.Properties.bIsRare == true
```

Then calculate:

```text
rare_module_count = len(rare_modules)
P(Blindfall Pit | Rare draw) = 1 / rare_module_count
```

Match the target module by its `Name` or asset filename, such as
`Crypt_BlindfallPit`. Do not reverse-match it from the display name
`Blindfall Pit`.

### 7.4 Recalculate the base probability

```text
base_rate_percent
= 100
   x (rare_layout_count / layout_count)
   x (1 / rare_module_count)
```

Current substitution:

```text
100 x (2 / 40) x (1 / 5)
= 1%
```

### 7.5 Recalculate the effective probability

The CenterTower is not the source of the base `1%`. It is a coverage
correction applied after the rare module has been assigned to the random-grid
slots.

```text
grid_cell_count
= layout_size x layout_size
= 25

covered_cell_count
= center_tower.Properties.Size.X
   x center_tower.Properties.Size.Y
= 4

effective_rate_percent
= base_rate_percent
   x (grid_cell_count - covered_cell_count)
   / grid_cell_count
= 1% x 21 / 25
= 0.84%
```

This correction is valid only if all of the following remain true:

- CenterTower covers the same 5x5 random grid.
- The rare module is uniformly distributed across the 25 cells.
- CenterTower appears under the assumed mode and condition.
- The CenterTower footprint is represented by its `2x2` asset size.

If the layout size, CenterTower size, appearance condition, or placement rule
changes, verify the model again instead of replacing numbers in the formula.

## 8. Assumptions and Limitations

1. `DungeonLayout.Properties.Module` is currently `null`. Layout assets expose
   slot types, but not the runtime assignment of a specific rare module.
2. `Maps/Dungeon/Layouts/Crypt_5x5_R_P.json` is the level-layout asset pointed
   to by `LevelAsset`. It is not a probability table for the 40 random
   layouts, so its module references must not replace
   `Dungeon.Properties.Layouts[]`.
3. `bIsRare` identifies membership in the rare pool. Do not place every
   `ModuleType=Crypt` module into that pool.
4. `NumMaxRares` supports the current one-rare-draw model. Any change to this
   field requires a new probability interpretation.
5. The current `1/5` calculation assumes a uniform rare-module pool because
   no weight field is exposed. It does not prove from Unreal binaries that the
   runtime selection is uniform.
6. The original detailed variant and item-drop analysis is recorded in commit
   `501d7b59` and `docs/BLINDFALL_PIT_PROBABILITY_ANALYSIS.md`. Commit
   `4a469816` added the CenterTower coverage correction without changing the
   original `2/40` layout factor or `1/5` rare-pool factor.

## 9. Recalculation Checklist

After any layout or module asset update, record at least:

```text
[ ] Number of layouts referenced by the Dungeon asset
[ ] LayoutSize and Size for every referenced layout
[ ] Rare-slot count for every layout and the list of Rare layouts
[ ] NumMaxRares
[ ] Crypt modules where bIsRare is true
[ ] Presence or absence of module weights or priorities
[ ] Base-probability formula and substituted values
[ ] CenterTower size, covered cells, and effective probability
[ ] Whether N, HR, A, AHR, and S2R modes still share the conclusion
```

## 10. Terminology

| Term                    | Meaning                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------ |
| `Dungeon`               | Random-dungeon mode asset that references layouts and defines mode-level properties. |
| `DungeonLayout`         | Layout asset containing the map size and module slot types.                          |
| `DungeonModule`         | Module asset that can be selected for a dungeon slot.                                |
| `Rare slot`             | A layout slot whose type is `EDCDungeonLayoutSlotType::Rare`.                        |
| `Rare module pool`      | Crypt modules with `ModuleType=Crypt` and `bIsRare=true`.                            |
| `Base probability`      | Probability before the CenterTower coverage correction.                              |
| `Effective probability` | Base probability after removing CenterTower-covered cells.                           |
