# Plan: Merge Monster Quality Variant Spawn Rates

## Problem

在 lootdrop 详情页（如 `lootdrops/RangerHood_6001/`）的 `group_drop_info` 中，幽鬼（Wraith）的 `spawn_rate` 显示为 45%。

但实际上，该 spawner keyword (`Wraith`) 下同时存在多个质量变体（_Common、_Elite、_Nightmare），它们共享同一组刷怪点，互斥生成。Wraith_Common max=45%、Wraith_Elite max=35%、Wraith_Nightmare max=33%，综合概率应为 sum ≈ 100%，而非 max=45%。

## Root Cause

### `lootdrop_builder.py`
- `build_loot_index()` lines 273-285：对怪物名称按 base 去重（`QUALITY_RE.sub("", mn)`），只保留一个变体
- `build_and_save_lootdrop_details()` line 454-455：spawn_rate 使用 `max(spawn_rate_cache.get(...))`，取最大单体概率，未合并同 spawner keyword 下所有质量变体的概率

### `enrichment.py`
- Lines 139-144：怪物章节同样使用 `max(spawn_rate_cache.get(...))` 或前缀模糊匹配取 max，未做合并

### `drop_rate.py`
- 缺少一个方法来自动检测质量变体并合并 spawn_rate

## Data Example

DB `spawner_entries` for keyword `Wraith`:

| entity_name | spawn_rate |
|---|---|
| Wraith_Common | 45.0 (max) |
| Wraith_Elite | 35.0 (max) |
| Wraith_Nightmare | 33.33 (max) |

Current result: `spawn_rate_cache["Wraith"] = 45.0`（因为 spawner_keyword 也是 "Wraith"）
Expected: combined = 45+35+33 ≈ 100 (per spawner keyword, sum of all variants at that keyword)

## Changes

### 1. `drop_rate.py` — Add `get_combined_spawn_rate()` method

Add to `DropRateEngine` class:

```python
QUALITY_VARIANT_SUFFIXES = ["", "_Common", "_Elite", "_Nightmare", "_Unique"]

def get_quality_variants(self, entity_name: str) -> list[str]:
    """Generate quality variant names for a given entity.
    E.g. 'Wraith' → ['Wraith', 'Wraith_Common', 'Wraith_Elite', 'Wraith_Nightmare', 'Wraith_Unique']
    """
    from translator import base_monster_name, QUALITY_RE
    base = base_monster_name(entity_name)
    return [base + s for s in self.QUALITY_VARIANT_SUFFIXES]

def get_combined_spawn_rate(self, entity_name: str) -> float:
    """Sum spawn rates across all quality variants sharing spawner keywords.
    
    For each spawner keyword used by any variant of this entity, sums the
    spawn_rate_detail for all quality variants. Returns the max across keywords.
    Falls back to spawn_rate_cache if no quality variants share spawners.
    """
    base_rate = self._spawn_rate_cache.get(entity_name, 0.0)
    variants = self.get_quality_variants(entity_name)
    
    # Collect all spawner keywords across all quality variants
    all_sk: set[str] = set()
    for v in variants:
        all_sk.update(self._entity_spawners.get(v, set()))
    
    if not all_sk:
        return base_rate
    
    best_total = 0.0
    for sk in all_sk:
        total = sum(self._spawn_rate_detail.get((sk, v), 0.0) for v in variants)
        if total > best_total:
            best_total = total
    
    return best_total if best_total > 0.0 else base_rate
```

### 2. `lootdrop_builder.py` — Use `get_combined_spawn_rate()`

In `build_and_save_lootdrop_details()`, line 454-455, change:

```python
# OLD (line 454-455):
else:
    _sr = max(spawn_rate_cache.get(_bn, 100) for _bn in (_m_data.get("_bases") or {_en}))

# NEW:
else:
    _sr = drop_engine.get_combined_spawn_rate(_en)
    if _sr <= 0:
        _sr = max(spawn_rate_cache.get(_bn, 100) for _bn in (_m_data.get("_bases") or {_en}))
```

### 3. `enrichment.py` — Use `get_combined_spawn_rate()` in monsters section

In `enrich_all_entities()`, lines 139-144, change:

```python
# OLD:
sr = spawn_rate_cache.get(mname, 0.0)
if not sr:
    lower = mname.lower()
    for k, v in spawn_rate_cache.items():
        if k.lower().startswith(lower + "_") or k.lower() == lower:
            sr = max(sr, v)

# NEW:
sr = drop_engine.get_combined_spawn_rate(mname)
if not sr:
    sr = spawn_rate_cache.get(mname, 0.0)
```

### 4. `enrichment.py` — Pass `drop_engine` to `enrich_all_entities`

`enrich_all_entities()` already receives `drop_engine` as first parameter. The new code uses `drop_engine.get_combined_spawn_rate()`. No signature change needed.

## Verification

1. Run `python main.py` in api/
2. Check `data/json/lootdrops/RangerHood_6001.json` — 幽鬼 spawn_rate should change from 45 to ~100
3. Check `data/json/monsters/Wraith.json` — group_drop_info spawn_rate should change similarly
4. Start web and verify display

## Effect Summary

| Entity | Before | After | Reason |
|--------|--------|-------|--------|
| Wraith (幽鬼) in Crypt | 45% | ~100% | Sum of Wraith_Common+_Elite+_Nightmare |
| Other monsters without quality variants | unchanged | unchanged | Not affected by merge logic |

## Edge Cases

- **Entity name already has quality suffix** (e.g., "Wraith_Common"): `get_quality_variants()` strips via `base_monster_name()`, then re-applies all suffixes → correct set
- **No quality variants exist**: `all_sk` will be empty → falls back to `spawn_rate_cache`
- **100% base rate**: already correct, merge won't change it
- **Monsters also in props**: Not affected — props use separate `_has_locked` code path
