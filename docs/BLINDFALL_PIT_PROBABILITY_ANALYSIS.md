# Crypt_BlindfallPit Module Appearance Probability Analysis

> Analysis Date: 2026-07-22
> Updated: 2026-07-22 (GrimveilCloak full drop chain added)
> Data Source: `DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/Dungeon/` game unpacked JSON + `spawners`/`lootdrop_groups`/`mutually_exclusive_groups` DB tables

## Background

Calculate the probability of encountering the **Blindfall Pit (Crypt_BlindfallPit)** rare module in the Crypt 5x5 map (Ruins Floor 2 · Crypt), and the full drop probability of **GrimveilCloak** within that module.

## Name Reference

| English | Notes |
|---------|-------|
| Crypt | Ruins Floor 2 (Crypt) |
| Crypt_BlindfallPit | Blindfall Pit |
| Crypt_LightlessChamber_01 | Lightless Chamber |
| Crypt_LightlessTomb_01 | Lightless Tomb |
| Crypt_MadCorridors | Mad Corridors |
| Crypt_TorchboundVault | Torchbound Vault |
| GrimveilCloak | Grimveil Cloak |

## Data Source Structure

```
Dungeon (Id_Dungeon_RandomCrypt_*)
  ├── Layouts[] → DungeonLayout (Id_DungeonLayout_Crypt_5x5_*)
  │     └── Slots[].SlotTypes[].SlotType (Escape/Boss/Rare/Key/Altar/...)
  └── ModuleType: Crypt → DungeonModule (Id_DungeonModule_Crypt_*)
        └── bIsRare: true/false
```

**Key point:** Layout files only define slot types; module assignment is handled in game compiled code (JSON contains `"Module": null`, `"Rotation": "None"`). Probabilities are derived from the number of available rare modules.

## Layer 1: Blindfall Pit Module Appearance Probability (~1%)

### Layout Verification

After checking all slots across 40 5x5 layout files:

| Dimension | Value |
|-----------|-------|
| Total 5x5 layouts | **40** (`Id_DungeonLayout_Crypt_5x5_01` ~ `_40`) |
| Layouts with Rare slot(s) | **2** (01: slot 20, 02: slot 18) |
| Layouts with multiple Rare slots | **0** (no dual-Rare-slot layout exists) |
| Total Rare slots | **2** (2 layouts, 1 each) |
| Layouts with Rare slot ratio | **2/40 = 5% |

**The dual-Rare-slot scenario mentioned by users does not exist in Crypt 5x5** — at most 1 rare module draw per run.

### Rare Module Pool

| Dimension | Value |
|-----------|-------|
| Total rare modules | **5** (all 1x1) |
| Rare module list | Blindfall Pit, Lightless Chamber, Lightless Tomb, Mad Corridors, Torchbound Vault |
| Max rare modules per run | **1** (`NumMaxRares: 1`) |
| Probability of Blindfall Pit being selected | **1/5 = 20%** |

### Blindfall Pit Appearance Probability

```
P(Blindfall Pit appears) = P(Layout with Rare slot) × P(Rare pool selects Blindfall Pit)
                         = (2/40) × (1/5)
                         = 1%
```

## Layer 2: Mutually Exclusive Spawns Inside Blindfall Pit (1 of 11)

The Blindfall Pit module map file `Crypt_BlindfallPit_D.json` contains a mutually exclusive spawn group `BP_GameSpawnerGroup_C_8`. 11 entities compete at coordinate (810, -10, -1600), only 1 selected per run.

| # | Entity | Type | DB rows |
|:-:|--------|:----:|:-------:|
| 1 | GrimveilCloak | lootdrop | 6 |
| 2 | Hoard01_3 | props | 3 |
| 3 | Ore_GoldOre (4 rarities merged) | props | 8 |
| 4 | SkeletonArcher | monster | 5 |
| 5 | SkeletonAxeman | monster | 2 |
| 6 | SkeletonChampion | monster | 4 |
| 7 | SkeletonCrossbowman | monster | 5 |
| 8 | SkeletonGuardmanFromFakeDeath | monster | 56 |
| 9 | SkeletonSpearman | monster | 4 |
| 10 | SkeletonSwordman | monster | 4 |
| 11 | Wraith | monster | 4 |

**Coordinate verification:** GrimveilCloak has 6 spawner records in DB, but all point to **the same coordinate** (810, -10, -1600, z=-1600). The notion of "6 coordinates" mistakenly interprets 6 DB rows as 6 distinct coordinates.

**Selection probability:** **1/11 ≈ 9.09%**

## Layer 3: GrimveilCloak Drop Rate (2.5%)

### Drop Group

`spawner_entries` with `keyword='GrimveilCloak'` links to a single drop group:

```
spawner_entries.GrimveilCloak → lootdrop_group_id = ID_LootdropGroup_GrimveilCloak
  → lootdrop_id = ID_Lootdrop_GrimveilCloak
    → item_name = GrimveilCloak_5001 (luck_grade=5, drop_count=1)
```

**No other item shares this drop group.** If the drop roll fails, no special item drops at this location.

### Drop Weights (Crypt HR, dungeon_grade 3022)

| luck_grade | Weight | Share | Result |
|:----------:|------:|:----:|--------|
| 0 | 9750 | **97.5%** | No special drop (basic junk/gold) |
| 5 | 250 | **2.5%** | GrimveilCloak |
| 1-4, 6-8 | 0 | 0% | None |

**Drop probability:** 250/10000 = **2.5%**

## Combined Probability

### Formula

```
P(obtain cloak) = P(Blindfall Pit appears) × P(cloak container selected) × P(container drops cloak)
```

### Comparison Across Modes

| Layer | Normal | PVE | Normal | HR | S2R |
|:------|:------:|:---:|:------:|:--:|:---:|
| ① Blindfall Pit appears | 1% | Same | Same | Same | **0%** (S2R has no Rare) |
| ② 1 of 11 selected | 1/11 | Same | Same | Same | — |
| ③ Drop rate | — | 0.25% | 1.25% | **2.5%** | 2.5% |
| **Combined probability** | — | **1/440,000** | **1/88,000** | **1/44,000** | **0** |
| ≈ | — | 1 per 440K runs | 1 per 88K runs | **1 per 44K runs** | None |

HR detailed calculation:

```
P(Blindfall Pit appears) × P(cloak selected) × P(drop)
= 1/100 × 1/11 × 2.5%
= 1/100 × 1/11 × 25/1000
= 25 / 1,100,000
= 1 / 44,000
≈ 0.00227%
```

### Complete Spawn Flow

```
Enter Crypt (Ruins Floor 2) 5x5
  └→ 1 of 40 layouts drawn
       └→ 2/40 = 5% → Layout with Rare slot
            └→ 1 of 5 rare modules drawn
                 └→ 1/5 = 20% → Blindfall Pit (otherwise, run ends)
                      └→ 11 mutually exclusive spawns
                           └→ 1/11 ≈ 9% → GrimveilCloak container
                                └→ Container drop roll
                                     ├─ 2.5% → Cloak drops ✓
                                     └─ 97.5% → No special drop ✗
```

## Mode Comparison

| Mode | LayoutSize | Layouts | NumMaxRares | Layouts with Rare slot | Blindfall Pit probability |
|------|-----------|---------|:-----------:|:---------------------:|:------------------------:|
| N (Normal) Solo/Duo/Trio | 5 | 40 | 1 | 2 | **1%** |
| HR (High Roller) Solo/Duo/Trio | 5 | 40 | 1 | 2 | **1%** |
| A (Adventurer) | 5 | 40 | 1 | 2 | **1%** |
| AHR | 5 | 40 | 1 | 2 | **1%** |
| S2R (Starter to Ritual) | **4** | **10** | **None** | **0** | **0%** |

> All Crypt 5x5 modes (N/HR/A/AHR) share the same layout list and map file (`Crypt_5x5_R_P`), with identical probabilities.

## S2R Specifics

S2R uses its own `Crypt_4x4_HR_R_P` map file and 10 4x4 layouts. 4x4 layouts **have no Rare slots**, making both Blindfall Pit and GrimveilCloak impossible.

## Limitations

1. **Module allocation algorithm unknown:** Rare module and layout selection logic is implemented in Unreal Engine C++ and not exported to JSON. The analysis assumes uniform random distribution.
2. **No weight data:** Neither layout selection nor module selection has weight/priority fields.
3. **Game version:** Data is based on the current game unpacked version. Future updates may alter layout configuration or drop weights.
