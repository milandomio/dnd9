"""Lootdrop index and detail file generation, extracted from collector.py."""

import json
from pathlib import Path

from config import TRANSLATION_ALIAS_MAP
from translator import (
    HARD_SUFFIX_RE,
    QUALITY_RE,
    UNIQUE_SUFFIX_RE,
    VARIANT_RE,
    base_monster_name,
)

_MONSTER_COLORS = [
    "#E74C3C",
    "#3498DB",
    "#2ECC71",
    "#F39C12",
    "#9B59B6",
    "#1ABC9C",
    "#E67E22",
    "#2980B9",
    "#27AE60",
    "#D35400",
    "#8E44AD",
    "#16A085",
    "#C0392B",
    "#2C3E50",
    "#7F8C8D",
    "#FF6B35",
    "#00BFFF",
    "#FFD700",
    "#FF69B4",
    "#32CD32",
    "#FF4500",
    "#9370DB",
    "#00FA9A",
    "#DC143C",
    "#00CED1",
]


def _classify_label(label: str, entity_name: str) -> str:
    if not label:
        return "direct"
    en_base = QUALITY_RE.sub("", entity_name)
    if label == en_base or label.startswith(en_base + "_"):
        return "direct"
    if "Random" in label:
        return "random"
    if "Special" in label or "ChestLarge" in label:
        return "special"
    return "other"


_LABEL_TYPE_SUFFIX = {
    "direct": "",
    "special": "(特殊)",
    "random": "(随机)",
    "other": "",
}


def _save(output_dir: Path, filename: str, data: list | dict):
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_merged_loot_map(db) -> tuple[dict[str, list[str]], set[str], dict[str, int]]:
    """Build merged lootdrop map with variant family merging.

    Returns:
        (merged_loot, skip_variants, variant_override)
    """
    loot_raw = db.get_lootdrop_relationships()
    loot_map: dict[str, set[str]] = {}
    for r in loot_raw:
        loot_map.setdefault(r["item_name"], set()).add(r["monster_name"])

    # detect variant families (_\d{4} suffix, >=2 members)
    families: dict[str, list[str]] = {}
    for item_name in loot_map:
        m = VARIANT_RE.match(item_name)
        if m:
            base = m.group(1)
            families.setdefault(base, []).append(item_name)
    families = {k: sorted(v) for k, v in families.items() if len(v) >= 2}
    skip_variants: set[str] = set()
    for variants in families.values():
        skip_variants.update(variants)

    # merge: base_name -> union of all monsters from its variants
    merged_loot: dict[str, list[str]] = {}
    for item_name, monster_set in loot_map.items():
        m = VARIANT_RE.match(item_name)
        base = m.group(1) if m else item_name
        merged_loot.setdefault(base, set()).update(monster_set)
    merged_loot = {k: sorted(v) for k, v in merged_loot.items()}
    print(f"  variant families merged: {len(families)} ({len(skip_variants)} variants skipped)")
    print(f"  unique items after merge: {len(merged_loot)}")

    # split _8001 variants: keep as own entry (monsters are shared with base)
    variant_override: dict[str, int] = {}
    for base, variants in list(families.items()):
        _8001 = [v for v in variants if v.endswith("_8001")]
        if not _8001:
            continue
        v8001 = _8001[0]
        skip_variants.discard(v8001)
        merged_loot[v8001] = sorted(loot_map.get(v8001, []))
        variant_override[base] = len(variants) - 1
    # Also handle _8001 items that were merged into base (other variants stripped at import)
    _8001_split = 0
    for item_name in list(loot_map):
        if not item_name.endswith("_8001"):
            continue
        if item_name in merged_loot:
            continue
        base = item_name.removesuffix("_8001")
        if base in merged_loot:
            merged_loot[item_name] = sorted(loot_map[item_name])
            _8001_split += 1
            if base not in variant_override:
                cur = (
                    db.connect()
                    .execute("SELECT variant_count FROM item_entities WHERE item_name = ?", (base,))
                    .fetchone()
                )
                if cur:
                    variant_override[base] = cur[0] - 1
    if _8001_split:
        print(f"  _8001 variants split (from loot_map): {_8001_split} bases affected")

    # Inject SuperHoard spawners as separate monster entries
    superhoard_map: dict[str, list[str]] = {}
    for row in (
        db.connect()
        .execute(
            "SELECT DISTINCT spawner_keyword, entity_name FROM spawner_entries WHERE entity_name IN ('Hoard01_9', 'HoardChest01') AND spawner_keyword != entity_name"
        )
        .fetchall()
    ):
        sk, en = row
        superhoard_map.setdefault(en, []).append(sk)
    for mons in merged_loot.values():
        for en, sks in superhoard_map.items():
            if en in mons:
                for sk in sks:
                    if sk not in mons:
                        mons.append(sk)
    merged_loot = {k: sorted(v) for k, v in merged_loot.items()}

    return merged_loot, skip_variants, variant_override


def build_loot_index(
    merged_loot: dict[str, list[str]],
    items: list[dict],
    monsters: list[dict],
    entity_class: dict,
    resolve_name,
    variant_override: dict[str, int],
) -> list[dict]:
    """Build lootdrops.json index (grouped by item for list page)."""
    items_lookup = {r["item_name"]: r for r in items}
    monsters_lookup = {r["monster_name"]: r for r in monsters}
    loot_index = []
    for item_name, monster_names in merged_loot.items():
        item_row = items_lookup.get(item_name)
        if item_row is None and item_name.endswith("_8001"):
            item_row = items_lookup.get(item_name.removesuffix("_8001"))
        translation = (
            resolve_name(
                item_name,
                None if item_name.endswith("_8001") else item_row.get("translation_key"),
                "item",
            )
            if item_row
            else (resolve_name(item_name, None, "item") or item_name)
        )
        mon_translations = []
        for m in sorted(monster_names):
            cls = entity_class.get(m)
            if cls and "item" in cls["types"]:
                item_row_m = items_lookup.get(m)
                if item_row_m:
                    mon_translations.append(resolve_name(m, item_row_m["translation_key"], "item"))
                    continue
                tk = cls.get("translation_key", "")
                if tk:
                    mon_translations.append(resolve_name(m, tk, "item"))
                    continue
            elif cls and "props" in cls["types"]:
                mon_translations.append(resolve_name(m, cls.get("translation_key", ""), "props"))
                continue
            # Try direct monster lookup
            mon_row = monsters_lookup.get(m)
            if mon_row:
                mon_translations.append(resolve_name(m, mon_row["translation_key"], "monster"))
                continue
            # Try stripping _Hard/_VeryHard suffix
            base = HARD_SUFFIX_RE.sub("", m) if HARD_SUFFIX_RE.search(m) else m
            if base != m:
                mon_row = monsters_lookup.get(base)
                if mon_row:
                    mon_translations.append(resolve_name(base, mon_row["translation_key"], "monster"))
                    continue
            # Try stripping trailing Unique
            base2 = UNIQUE_SUFFIX_RE.sub("", base) if UNIQUE_SUFFIX_RE.search(base) else base
            if base2 != base:
                mon_row = monsters_lookup.get(base2)
                if mon_row:
                    mon_translations.append(resolve_name(base2, mon_row["translation_key"], "monster"))
                    continue
            # Try entity_class translation key as fallback
            if cls and cls.get("translation_key"):
                mon_translations.append(resolve_name(m, cls["translation_key"], cls["types"][0]))
                continue
            # Try stripping _Locked suffix and resolving the base name
            locked_name = m.removesuffix("_Locked")
            if locked_name != m:
                locked_trans = resolve_name(locked_name, None, "props")
                if locked_trans != locked_name:
                    mon_translations.append(locked_trans)
                    continue
            # Generic fallback
            mon_translations.append(resolve_name(m, None, "monster") or m)
        variant_count = variant_override.get(item_name, item_row.get("variant_count", 1) if item_row else 1)
        # Merge _Hard/_VeryHard/Unique variants in loot_index too
        merged_names: list[str] = []
        merged_translations: list[str] = []
        seen_bases: set[str] = set()
        for mn, mt in zip(monster_names, mon_translations, strict=False):
            if mn == item_name:
                continue
            b = HARD_SUFFIX_RE.sub("", mn)
            b = QUALITY_RE.sub("", b)
            b = UNIQUE_SUFFIX_RE.sub("", b)
            if b not in seen_bases:
                seen_bases.add(b)
                merged_names.append(mn)
                merged_translations.append(mt)
        loot_index.append(
            {
                "name": item_name,
                "translation": translation,
                "variant_count": variant_count,
                "monsters": sorted(merged_names),
                "monster_translations": merged_translations,
            }
        )
    loot_index.sort(key=lambda x: x["translation"] or x["name"])
    return loot_index


def build_and_save_lootdrop_details(
    loot_index: list[dict],
    drop_engine,
    all_coords: dict,
    resolve_name,
    og_to_keywords: dict[str, set[str]],
    coord_variant_count: dict,
    entity_class: dict,
    monsters: list[dict],
    output_dir: Path,
    log_fn=None,
    modules_map: dict | None = None,
    map_to_module: dict | None = None,
) -> dict[str, float]:
    """Build and save lootdrop detail files. Returns item_max_score."""
    map_base_to_group = drop_engine.map_base_to_group
    spawn_rate_cache = drop_engine.spawn_rate_cache
    spawn_rate_detail = drop_engine.spawn_rate_detail
    spawn_rate_by_mode = drop_engine.spawn_rate_by_mode
    entity_spawners = drop_engine.entity_spawners

    item_max_score: dict[str, float] = {}
    detail_count = 0
    detail_total = len(loot_index)
    if log_fn:
        log_fn(f"[JSON] lootdrop detail loop starting: {detail_total} items")

    for entry in loot_index:
        item_name = entry["name"]
        merged: dict[str, dict] = {}
        for _i, m_name in enumerate(entry["monsters"]):
            if m_name == item_name:
                continue
            coords = all_coords.get(m_name, [])
            if not coords:
                _m_base = QUALITY_RE.sub("", m_name)
                if _m_base != m_name:
                    coords = all_coords.get(_m_base, [])
            if not coords:
                alias = TRANSLATION_ALIAS_MAP.get(m_name)
                if alias:
                    coords = all_coords.get(alias, [])
            if not coords:
                alt_keywords = og_to_keywords.get(m_name, set())
                for _ak in sorted(alt_keywords):
                    _c = all_coords.get(_ak, [])
                    if _c:
                        coords = _c
                        break
            _valid_sk = entity_spawners.get(m_name, set())
            if _valid_sk:
                coords = [
                    c for c in coords if c.get("keyword", "") in _valid_sk or c.get("original_keyword", "") in _valid_sk
                ]
            if not coords:
                continue
            m_trans = entry["monster_translations"][_i]
            base = base_monster_name(m_name)
            locked_base = m_name.replace("_Locked", "")
            is_locked = locked_base != m_name
            if is_locked:
                base = base_monster_name(locked_base)
            coords_by_type: dict[str, list[dict]] = {}
            for _c in coords:
                _t = _classify_label(_c.get("original_keyword", ""), m_name)
                coords_by_type.setdefault(_t, []).append(_c)
            for _type, _typed_coords in coords_by_type.items():
                _suffix = _LABEL_TYPE_SUFFIX.get(_type, "")
                _type_trans = m_trans + _suffix if _suffix else m_trans
                _use_suffix = _suffix != ""
                _merge_key = f"{m_trans}|{_type}"
                _existing = merged.get(_merge_key)
                if _existing is not None:
                    _existing["_bases"].add(base)
                    if is_locked:
                        _existing["_has_locked"] = True
                else:
                    merged[_merge_key] = {
                        "name": m_name,
                        "entity_name": m_name,
                        "translation": _type_trans,
                        "color": _MONSTER_COLORS[len(merged) % len(_MONSTER_COLORS)],
                        "coords": [],
                        "_has_locked": False,
                        "_bases": {base, m_name},
                    }
                if is_locked:
                    merged[_merge_key]["_has_locked"] = True
                for _c in _typed_coords:
                    _raw_label = _c.get("original_keyword") or _c.get("keyword", "")
                    coord_out = {
                        "x": _c["x"],
                        "y": _c["y"],
                        "z": _c["z"],
                        "yaw": _c.get("yaw", 0),
                        "map": _c["map_base"],
                        "file": _c["json_filename"],
                        "version": _c["version"],
                        "label": _raw_label,
                    }
                    _vc_info = coord_variant_count.get(
                        (_c["map_base"], _c["json_filename"], _c.get("group_parent", ""))
                    )
                    if _vc_info and _vc_info[0] > 1:
                        coord_out["variant_count"] = _vc_info[0]
                        coord_out["variant_names"] = _vc_info[1]
                    if _c.get("keyword") != _c.get("original_keyword", ""):
                        _pair = (_c["keyword"], m_name)
                        _sr = spawn_rate_detail.get(_pair, 100) if _pair else spawn_rate_cache.get(m_name, 100)
                    else:
                        _sr = spawn_rate_cache.get(m_name, 100)
                    coord_out["spawn_rate"] = _sr
                    merged[_merge_key]["coords"].append(coord_out)
        # Compute per-group drop rates
        _group_drop_info: dict[str, list[dict]] = {}
        for _base, _m_data in merged.items():
            _has_locked = _m_data.get("_has_locked", False)
            _seen_groups: set[str] = set()
            for _c in _m_data["coords"]:
                _g = map_base_to_group.get(_c["map"], "")
                if _g:
                    _seen_groups.add(_g)
            for _g in _seen_groups:
                _dr = drop_engine.get_group_drop_rates(item_name, _m_data.get("entity_name", _m_data["name"]), _g)
                if not _dr:
                    _dr = {"PVE": 0, "普通": 0, "豪客赛": 0}
                _en = _m_data.get("entity_name", _m_data["name"])
                if _has_locked:
                    _locked_name = (
                        _en.replace("_UnderSea", "_Locked_UnderSea") if "_UnderSea" in _en else _en + "_Locked"
                    )
                    _common_sks = entity_spawners.get(_en, set()) & entity_spawners.get(_locked_name, set())
                    _best_rate = 0
                    for _sk in _common_sks:
                        _ul_sr = spawn_rate_detail.get((_sk, _en), 0)
                        _l_sr = spawn_rate_detail.get((_sk, _locked_name), 0)
                        _rate = _ul_sr + _l_sr
                        if _rate > _best_rate:
                            _best_rate = _rate
                    _sr = (
                        _best_rate
                        if _best_rate > 0
                        else max(spawn_rate_cache.get(_bn, 100) for _bn in (_m_data.get("_bases") or {_en}))
                    )
                else:
                    _sr = max(spawn_rate_cache.get(_bn, 100) for _bn in (_m_data.get("_bases") or {_en}))
                _en_mode_rates = spawn_rate_by_mode.get(("", _en), {})
                _sr_by_mode: dict[str, float] = {}
                if _en_mode_rates:
                    for _mn in ("PVE", "普通", "豪客赛"):
                        if _mn in _en_mode_rates:
                            _sr_by_mode[_mn] = _en_mode_rates[_mn]
                _has_varied_spawn = len(set(_sr_by_mode.values())) > 1
                _group_drop_info.setdefault(_g, []).append(
                    {
                        "translation": _m_data["translation"],
                        "spawn_rate": _sr,
                        "drop_rates": _dr,
                        "_variant": _m_data.get("entity_name", _m_data["name"]),
                    }
                )
                if _has_varied_spawn:
                    _group_drop_info[_g][-1]["spawn_rates"] = _sr_by_mode
        # Deduplicate coords and update translation for locked-merged entries
        for _base_data in merged.values():
            if _base_data.pop("_has_locked", False):
                _old = _base_data["translation"]
                _base_data["translation"] += "(可能上锁)"
                for _g_list in _group_drop_info.values():
                    for _entry in _g_list:
                        if _entry["translation"] == _old:
                            _entry["translation"] = _base_data["translation"]
                _bn = _base_data.get("entity_name", _base_data["name"])
                _ln = _bn.replace("_UnderSea", "_Locked_UnderSea") if "_UnderSea" in _bn else _bn + "_Locked"
                _common = entity_spawners.get(_bn, set()) & entity_spawners.get(_ln, set())
                _combined_rate = 0
                for _sk in _common:
                    _ul = spawn_rate_detail.get((_sk, _bn), 0)
                    _ll = spawn_rate_detail.get((_sk, _ln), 0)
                    _r = _ul + _ll
                    if _r > _combined_rate:
                        _combined_rate = _r
                seen: set[tuple] = set()
                deduped = []
                for _c in _base_data["coords"]:
                    _k = (_c["x"], _c["y"], _c["z"], _c["file"])
                    if _k not in seen:
                        seen.add(_k)
                        deduped.append(_c)
                _base_data["coords"] = deduped
        # Quality variant dedup: keep highest priority (Elite > Nightmare > Common)
        for _g_list in _group_drop_info.values():
            _best: dict[str, dict] = {}
            for _entry in _g_list:
                _trans = _entry["translation"]
                _m = QUALITY_RE.search(_entry.get("_variant", ""))
                _prio = {"Elite": 3, "Nightmare": 2, "Common": 1}.get(_m.group(1) if _m else "", -1)
                if _trans not in _best or _prio > _best[_trans].get("_q_prio", -1):
                    _best[_trans] = _entry
                    _best[_trans]["_q_prio"] = _prio
            _g_list[:] = list(_best.values())
            for _entry in _g_list:
                _entry.pop("_variant", None)
                _entry.pop("_q_prio", None)
        # Sort by spawn_rate * drop_rate descending
        for _g_list in _group_drop_info.values():
            _g_list.sort(key=lambda x: x["spawn_rate"] * x["drop_rates"].get("豪客赛", 0), reverse=True)

        # Compute per-coord score
        _hk_lookup: dict[str, dict[str, float]] = {}
        for _g, _entries in _group_drop_info.items():
            for _entry in _entries:
                _hkl = _hk_lookup.setdefault(_entry["translation"], {})
                _hkl[_g] = _entry["drop_rates"].get("豪客赛", 0)
        for _base_data in merged.values():
            _trans = _base_data["translation"]
            _hk_map = _hk_lookup.get(_trans, {})
            for _c in _base_data["coords"]:
                _g = map_base_to_group.get(_c["map"], "")
                _hk = _hk_map.get(_g, 0)
                _score = (_c.get("spawn_rate", 0) or 0) * _hk / 100
                _c["score"] = round(_score, 4)
        merged = {k: v for k, v in merged.items() if v["coords"]}
        for _v in merged.values():
            _v.pop("_bases", None)
        monsters_out = list(merged.values())
        # Pre-compute max score per monster translation
        _max_scores: dict[str, float] = {}
        for _g_list in _group_drop_info.values():
            for _entry in _g_list:
                _trans = _entry["translation"]
                _score = round(_entry["spawn_rate"] * _entry["drop_rates"].get("豪客赛", 0) / 100, 4)
                if _trans not in _max_scores or _score > _max_scores[_trans]:
                    _max_scores[_trans] = _score
        for _m in monsters_out:
            _m["max_score"] = _max_scores.get(_m["translation"], -1)
        if monsters_out:
            detail = {
                "name": item_name,
                "translation": entry["translation"],
                "monsters": monsters_out,
                "group_drop_info": _group_drop_info,
            }
            # Inline module data for all referenced maps
            if modules_map and map_to_module:
                inline: dict[str, dict] = {}
                for _m in monsters_out:
                    for _c in _m["coords"]:
                        _mb = _c["map"]
                        if _mb in inline:
                            continue
                        _mn = map_to_module.get(_mb, _mb)
                        _mod = modules_map.get(_mn)
                        if _mod:
                            inline[_mb] = {
                                "rotate": _mod["rotate"],
                                "offset_x": _mod["offset_x"],
                                "offset_y": _mod["offset_y"],
                                "size_x": _mod["size_x"],
                                "size_y": _mod["size_y"],
                                "range": _mod["range"],
                                "group": _mod["group"],
                                "translation": _mod["translation"],
                                "img_name": _mod["img_name"],
                                "sl_base_name": _mod["sl_base_name"],
                            }
                if inline:
                    detail["_modules"] = inline
            _save(output_dir, f"lootdrops/{item_name}.json", detail)
            item_max_score[item_name] = max(_max_scores.values(), default=0.0)
        elif item_name == "BloodsapBlade":
            if log_fn:
                log_fn(
                    f"[DEBUG] BloodsapBlade: merged={ {k: v.get('translation','?') for k, v in merged.items()} }, group_drop_info={ {g: len(v) for g, v in _group_drop_info.items()} }"
                )
                for _i, m_name in enumerate(entry["monsters"]):
                    log_fn(f"[DEBUG]   monster: {m_name}, trans={entry['monster_translations'][_i]}")
                    coords = all_coords.get(m_name, [])
                    log_fn(f"[DEBUG]     all_coords direct: {len(coords)}")
                    _m_base = QUALITY_RE.sub("", m_name)
                    if _m_base != m_name:
                        coords2 = all_coords.get(_m_base, [])
                        log_fn(f"[DEBUG]     all_coords base '{_m_base}': {len(coords2)}")
                    _valid_sk = entity_spawners.get(m_name, set())
                    log_fn(f"[DEBUG]     _valid_sk: {_valid_sk}")
        detail_count += 1
        if detail_count % 100 == 0 and log_fn:
            log_fn(f"[JSON] lootdrops detail: {detail_count}/{detail_total}")
    if log_fn:
        log_fn(f"[JSON] lootdrops detail files DONE -> {detail_count} items")

    # Update lootdrops.json index with max_score
    for _entry in loot_index:
        _iname = _entry["name"]
        _entry["max_score"] = item_max_score.get(_iname, 0.0)
    _save(output_dir, "lootdrops.json", loot_index)

    return item_max_score
