"""Lootdrop index and detail file generation, extracted from collector.py."""

import json
import re
from pathlib import Path

from config import TRANSLATION_ALIAS_MAP, superhoard_translation_key
from label_type import (
    GOLDCHEST_FAMILY,
    GOLDCHEST_SPECIAL,
    LABEL_TYPE_SUFFIX,
    classify_label,
)
from translator import (
    HARD_SUFFIX_RE,
    QUALITY_RE,
    UNIQUE_SUFFIX_RE,
    VARIANT_RE,
    base_monster_name,
)

# Back-compat aliases for enrichment / external imports
_classify_label = classify_label
_LABEL_TYPE_SUFFIX = LABEL_TYPE_SUFFIX

_NO_SCORE = -1

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

MAX_COORDS_PER_PAGE = 3000

# Translation suffixes used when matching base entity for legend ref
_LEGEND_STRIP_SUFFIXES = ("(可能上锁)", "(特殊)", "(随机)")


def _strip_legend_suffixes(trans: str) -> str:
    base = trans
    for s in _LEGEND_STRIP_SUFFIXES:
        base = base.replace(s, "")
    if base.endswith("组"):
        base = base[:-1]
    return base.strip()


def _resolve_legend_ref(
    trans: str,
    entity_name: str,
    monsters_out: list[dict],
    entity_page_map: dict[str, str] | None,
) -> str | None:
    """Resolve ref page for a gdi-only legend entry. Prefer entity_page_map, then exact base match."""
    # special GoldChest legend → dedicated props page
    if "(特殊)" in trans and ("黄金宝箱" in trans or entity_name in GOLDCHEST_FAMILY):
        if entity_page_map and GOLDCHEST_SPECIAL in entity_page_map:
            return entity_page_map[GOLDCHEST_SPECIAL]
        return f"props/{GOLDCHEST_SPECIAL}"
    if entity_page_map and entity_name:
        page = entity_page_map.get(entity_name) or entity_page_map.get(base_monster_name(entity_name))
        if page:
            return page
    base = _strip_legend_suffixes(trans)
    if not base:
        return None
    for m in monsters_out:
        if m.get("translation") != base:
            continue
        if m.get("ref"):
            return m["ref"]
        en = m.get("entity_name", m.get("name", ""))
        if entity_page_map and en:
            page = entity_page_map.get(en) or entity_page_map.get(base_monster_name(en))
            if page:
                return page
        if en:
            return f"coords/{base_monster_name(en)}"
    return None


def _ensure_gdi_monster_entries(
    monsters_out: list[dict],
    group_drop_info: dict[str, list[dict]],
    entity_page_map: dict[str, str] | None = None,
    max_scores: dict[str, float] | None = None,
    valid_translations: set[str] | None = None,
) -> list[dict]:
    """Ensure every group_drop_info translation has a monsters entry (legend / 参考爆率).

    Orphans appear after coord budget trim or variant spawner filter drops the real entry.
    Virtual entries carry empty coords and optional ref; frontend only needs matching translation.
    """
    existing = {m["translation"] for m in monsters_out}
    for _g_entries in group_drop_info.values():
        for _entry in _g_entries:
            _trans = _entry["translation"]
            if _trans in existing:
                continue
            if valid_translations is not None and _trans not in valid_translations:
                continue
            _en = _entry.get("_entity_name") or ""
            _ref = _resolve_legend_ref(_trans, _en, monsters_out, entity_page_map)
            _virtual: dict = {
                "name": _en or _trans,
                "entity_name": _en or _trans,
                "translation": _trans,
                "translation_key": _entry.get("translation_key", ""),
                "color": _MONSTER_COLORS[len(monsters_out) % len(_MONSTER_COLORS)],
                "coords": [],
                "_source_kind": _entry.get("_source_kind", "direct"),
            }
            if _ref:
                _virtual["ref"] = _ref
                _virtual["coord_count"] = 0
            if max_scores is not None:
                _virtual["max_score"] = max_scores.get(_trans, _NO_SCORE)
            else:
                _virtual["max_score"] = round(
                    _entry.get("spawn_rate", 0) * _entry.get("drop_rates", {}).get("豪客赛", 0) / 100, 4
                )
            monsters_out.append(_virtual)
            existing.add(_trans)
    return monsters_out


_SUFFIX_NUM_RE = re.compile(r"_(\d{4})$")

_FALLBACK_RARITY = {
    "1001": "Poor",
    "2001": "Common",
    "3001": "Uncommon",
    "4001": "Rare",
    "5001": "Epic",
    "6001": "Legend",
    "7001": "Unique",
    "8001": "Artifact",
}


def _get_variant_rarity(item_name: str, suffixes: list[str], translations: dict[str, str]) -> dict[str, dict]:
    """Resolve rarity from the variant suffix and DB-backed translation map."""
    result: dict[str, dict] = {}
    for suffix in suffixes:
        rarity_name = _FALLBACK_RARITY.get(suffix)
        if rarity_name:
            key = f"Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_{rarity_name}"
            result[suffix] = {"name": translations.get(key, rarity_name), "translation_key": key}
    return result


def _detail_variant_suffixes(entry: dict, drop_engine) -> list[str]:
    item_name = entry["name"]
    base_name = item_name.removesuffix("_8001")
    suffixes = sorted(drop_engine.get_existing_variant_suffixes(base_name))
    if item_name.endswith("_8001"):
        return suffixes
    return [suffix for suffix in suffixes if suffix != "8001"]


def _artifact_translation_key(item_name: str, translations: dict[str, str]) -> str:
    """Resolve an artifact key exclusively from the DB-backed translation map."""
    expected_key = f"Text_DesignData_Item_Item_{item_name}"
    return expected_key if expected_key in translations else ""


def _possible_variant_suffixes(entry: dict) -> list[str]:
    """Return game-defined quality suffixes, including qualities with no drop weight."""
    if entry["name"].endswith("_8001"):
        return ["8001"]
    match = _SUFFIX_NUM_RE.search(entry.get("raw_name", ""))
    if not match:
        return []
    first_num = int(match.group(1))
    count = entry.get("variant_count", 1)
    return [str(first_num + 1000 * i).zfill(4) for i in range(count)]


def _source_id(entity_name: str, source_kind: str) -> str:
    canonical_name = base_monster_name(entity_name.replace("_Locked", ""))
    if not canonical_name:
        raise ValueError("lootdrop source has no entity_name")
    return f"{canonical_name}:{source_kind}"


def _save(output_dir: Path, filename: str, data: list | dict, compact: bool = False):
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if compact:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(data, f, ensure_ascii=False, indent=2)


def build_merged_loot_map(db) -> tuple[dict[str, list[str]], set[str]]:
    """Build merged lootdrop map with variant family merging.

    Returns:
        (merged_loot, skip_variants)
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

    # split _8001 artifacts: keep as own entry (monsters are shared with base)
    for _, variants in list(families.items()):
        _8001 = [v for v in variants if v.endswith("_8001")]
        if not _8001:
            continue
        v8001 = _8001[0]
        skip_variants.discard(v8001)
        merged_loot[v8001] = sorted(loot_map.get(v8001, []))
    for item_name in list(loot_map):
        if not item_name.endswith("_8001"):
            continue
        if item_name in merged_loot:
            continue
        base = item_name.removesuffix("_8001")
        if base in merged_loot:
            merged_loot[item_name] = sorted(loot_map[item_name])

    # Inject SuperHoard spawners as separate monster entries.
    superhoard_map: dict[str, list[str]] = {}
    for row in (
        db.connect()
        .execute(
            "SELECT DISTINCT spawner_keyword, entity_name FROM spawner_entries "
            "WHERE entity_name IN ('Hoard01_9', 'HoardChest01', 'HoardChest01_9') "
            "AND spawner_keyword != entity_name"
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

    return merged_loot, skip_variants


def build_loot_index(
    merged_loot: dict[str, list[str]],
    items: list[dict],
    monsters: list[dict],
    entity_class: dict,
    resolve_name,
    translations: dict[str, str],
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
        mon_translations: list[str] = []
        mon_translation_keys: list[str] = []
        for m in sorted(monster_names):
            cls = entity_class.get(m)
            if cls and "item" in cls["types"]:
                item_row_m = items_lookup.get(m)
                if item_row_m:
                    _tk = item_row_m["translation_key"]
                    mon_translations.append(resolve_name(m, _tk, "item"))
                    mon_translation_keys.append(_tk)
                    continue
                _tk = cls.get("translation_key", "")
                if _tk:
                    mon_translations.append(resolve_name(m, _tk, "item"))
                    mon_translation_keys.append(_tk)
                    continue
            elif cls and "props" in cls["types"]:
                _tk = cls.get("translation_key", "") or superhoard_translation_key(m) or ""
                mon_translations.append(resolve_name(m, _tk if _tk.startswith("Text_") else None, "props"))
                mon_translation_keys.append(_tk)
                continue
            mon_row = monsters_lookup.get(m)
            if mon_row:
                _tk = mon_row["translation_key"]
                mon_translations.append(resolve_name(m, _tk, "monster"))
                mon_translation_keys.append(_tk)
                continue
            # Try stripping _Hard/_VeryHard suffix
            base = HARD_SUFFIX_RE.sub("", m) if HARD_SUFFIX_RE.search(m) else m
            if base != m:
                mon_row = monsters_lookup.get(base)
                if mon_row:
                    _tk = mon_row["translation_key"]
                    mon_translations.append(resolve_name(base, _tk, "monster"))
                    mon_translation_keys.append(_tk)
                    continue
            # Try stripping trailing Unique
            base2 = UNIQUE_SUFFIX_RE.sub("", base) if UNIQUE_SUFFIX_RE.search(base) else base
            if base2 != base:
                mon_row = monsters_lookup.get(base2)
                if mon_row:
                    _tk = mon_row["translation_key"]
                    mon_translations.append(resolve_name(base2, _tk, "monster"))
                    mon_translation_keys.append(_tk)
                    continue
            # Try entity_class translation key as fallback
            if cls and cls.get("translation_key"):
                _tk = cls["translation_key"]
                mon_translations.append(resolve_name(m, _tk, cls["types"][0]))
                mon_translation_keys.append(_tk)
                continue
            # Try stripping _Locked suffix and resolving the base name
            locked_name = m.removesuffix("_Locked")
            if locked_name != m:
                locked_trans = resolve_name(locked_name, None, "props")
                if locked_trans != locked_name:
                    mon_translations.append(locked_trans)
                    mon_translation_keys.append("")
                    continue
            # SuperHoard* synthetic key (no Game.json)
            _sh_tk = superhoard_translation_key(m)
            if _sh_tk:
                mon_translations.append(resolve_name(m, None, "props") or m)
                mon_translation_keys.append(_sh_tk)
                continue
            # Generic fallback
            mon_translations.append(resolve_name(m, None, "monster") or m)
            mon_translation_keys.append("")
        variant_count = item_row.get("variant_count", 1) if item_row else 1
        translation_key = (
            _artifact_translation_key(item_name, translations)
            if item_name.endswith("_8001")
            else item_row.get("translation_key", "") if item_row else ""
        )
        if not translation_key and item_name.endswith("_8001"):
            base_row = items_lookup.get(item_name.removesuffix("_8001"))
            if base_row:
                translation_key = base_row.get("translation_key", "")
        # Merge _Hard/_VeryHard/Unique variants in loot_index too
        merged_names: list[str] = []
        merged_translations: list[str] = []
        merged_translation_keys: list[str] = []
        seen_bases: set[str] = set()
        for mn, mt, mtk in zip(monster_names, mon_translations, mon_translation_keys, strict=False):
            if mn == item_name:
                continue
            b = HARD_SUFFIX_RE.sub("", mn)
            b = QUALITY_RE.sub("", b)
            b = UNIQUE_SUFFIX_RE.sub("", b)
            if b not in seen_bases:
                seen_bases.add(b)
                merged_names.append(mn)
                merged_translations.append(mt)
                merged_translation_keys.append(mtk)
        raw_name = item_row.get("raw_name", "") if item_row else ""
        entry: dict = {
            "name": item_name,
            "translation": translation,
            "translation_key": translation_key,
            "variant_count": variant_count,
            "raw_name": raw_name,
            "monsters": sorted(merged_names),
            "monster_translations": merged_translations,
            "monster_translation_keys": merged_translation_keys,
        }
        loot_index.append(entry)
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
    map_to_module: dict | None = None,
    translations: dict[str, str] | None = None,
    entity_page_map: dict[str, str] | None = None,
    used_translation_keys: set[str] | None = None,
    lootdrop_group_info_out: dict[str, dict[str, list[dict]]] | None = None,
) -> dict[str, float]:
    """Build and save lootdrop detail files. Returns item_max_score."""
    map_base_to_group = drop_engine.map_base_to_group
    spawn_rate_cache = drop_engine.spawn_rate_cache
    spawn_rate_detail = drop_engine.spawn_rate_detail
    spawn_rate_by_mode = drop_engine.spawn_rate_by_mode
    entity_spawners = drop_engine.entity_spawners
    entity_page_map_ci = {name.casefold(): page for name, page in (entity_page_map or {}).items()}
    available_entity_pages = set((entity_page_map or {}).values())

    def _ref_is_available(candidate: str | None) -> bool:
        if not candidate:
            return False
        if candidate in available_entity_pages:
            return True
        return (output_dir / f"{candidate}.json").is_file()

    spawner_public_entities: dict[str, set[str]] = {}
    for entity_name, spawner_names in entity_spawners.items():
        canonical_name = base_monster_name(entity_name.replace("_Locked", ""))
        if not ((entity_page_map or {}).get(canonical_name) or entity_page_map_ci.get(canonical_name.casefold())):
            continue
        for spawner_name in spawner_names:
            spawner_public_entities.setdefault(spawner_name.casefold(), set()).add(canonical_name)

    def _public_source_entity(entity_name: str) -> str:
        canonical_name = base_monster_name(entity_name.replace("_Locked", ""))
        if (entity_page_map or {}).get(canonical_name) or entity_page_map_ci.get(canonical_name.casefold()):
            return canonical_name
        candidates = spawner_public_entities.get(entity_name.casefold(), set())
        return next(iter(candidates)) if len(candidates) == 1 else canonical_name

    item_max_score: dict[str, float] = {}
    item_valid_names: dict[str, set[str]] = {}
    item_hr100: dict[str, bool] = {}
    item_variant_suffixes: dict[str, list[str]] = {}
    # monsters table alone misses props/chests; merge entity_class (items+monsters+props)
    m_tk_map = {r["monster_name"]: r.get("translation_key", "") for r in (monsters or [])}
    for _ec_name, _ec in (entity_class or {}).items():
        _ec_tk = (_ec or {}).get("translation_key") or ""
        if _ec_tk and not m_tk_map.get(_ec_name):
            m_tk_map[_ec_name] = _ec_tk

    detail_count = 0
    detail_total = len(loot_index)
    if log_fn:
        log_fn(f"[JSON] lootdrop detail loop starting: {detail_total} items")

    for entry in loot_index:
        item_name = entry["name"]
        variant_suffixes = _detail_variant_suffixes(entry, drop_engine)
        is_variant_family = len(variant_suffixes) > 1 and not item_name.endswith("_8001")
        merged: dict[str, dict] = {}
        _entry_mtk = entry.get("monster_translation_keys") or []
        for _i, m_name in enumerate(entry["monsters"]):
            if m_name == item_name:
                continue
            coords = all_coords.get(m_name, [])
            _coord_key = m_name if coords else None
            if not coords:
                _m_base = QUALITY_RE.sub("", m_name)
                if _m_base != m_name:
                    coords = all_coords.get(_m_base, [])
                    if coords:
                        _coord_key = _m_base
            if not coords:
                alias = TRANSLATION_ALIAS_MAP.get(m_name)
                if alias:
                    coords = all_coords.get(alias, [])
                    if coords:
                        _coord_key = alias
            if not coords:
                alt_keywords = og_to_keywords.get(m_name, set())
                for _ak in sorted(alt_keywords):
                    _c = all_coords.get(_ak, [])
                    if _c:
                        coords = _c
                        _coord_key = _ak
                        break
            _valid_sk = entity_spawners.get(m_name, set())
            if _valid_sk:
                coords = [
                    c for c in coords if c.get("keyword", "") in _valid_sk or c.get("original_keyword", "") in _valid_sk
                ]
            if not coords:
                continue
            m_trans = entry["monster_translations"][_i]
            # Prefer loot_index keys (already resolved), then maps, then entity_class / SuperHoard
            m_tk = _entry_mtk[_i] if _i < len(_entry_mtk) else ""
            if not m_tk:
                m_tk = m_tk_map.get(m_name, "")
            if not m_tk:
                m_tk = ((entity_class or {}).get(m_name) or {}).get("translation_key", "") or ""
            if not m_tk:
                m_tk = superhoard_translation_key(m_name) or ""
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
                _merge_key = f"{m_trans}|{_type}"
                # special GoldChest → synthetic entity page
                _bucket_name = m_name
                _bucket_ck = _coord_key
                if _type == "special" and m_name in GOLDCHEST_FAMILY:
                    _bucket_name = GOLDCHEST_SPECIAL
                    _bucket_ck = GOLDCHEST_SPECIAL
                _existing = merged.get(_merge_key)
                if _existing is not None:
                    _existing["_bases"].add(base)
                    if is_locked:
                        _existing["_has_locked"] = True
                else:
                    merged[_merge_key] = {
                        "name": _bucket_name,
                        "entity_name": _bucket_name,
                        "translation": _type_trans,
                        "translation_key": m_tk,
                        "color": _MONSTER_COLORS[len(merged) % len(_MONSTER_COLORS)],
                        "coords": [],
                        "_has_locked": False,
                        "_bases": {base, m_name, _bucket_name},
                        "_coord_key": _bucket_ck,
                        "_source_kind": _type,
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
                    _gp = _c.get("group_parent", "")
                    if _gp:
                        coord_out["group_parent"] = _gp
                    _vc_info = coord_variant_count.get((_c["map_base"], _c["json_filename"], _gp))
                    if _vc_info and _vc_info[0] > 1:
                        coord_out["variant_count"] = _vc_info[0]
                        coord_out["variant_names"] = _vc_info[1]
                    # rate entity: synthetic special uses real keyword on coord
                    _rate_en = _c.get("keyword") or m_name
                    if _c.get("keyword") != _c.get("original_keyword", ""):
                        _pair = (_c["original_keyword"], _rate_en)
                        _sr = spawn_rate_detail.get(_pair, 0) if _pair else spawn_rate_cache.get(_rate_en, 0)
                    else:
                        _sr = spawn_rate_cache.get(_rate_en, 0)
                    _qm = re.search(r"_(VeryLow|Low|Med|High)$", _c.get("keyword", "")) or re.search(
                        r"_(VeryLow|Low|Med|High)$", _c.get("original_keyword", "")
                    )
                    if _qm:
                        coord_out["quality"] = _qm.group(1)
                    coord_out["spawn_rate"] = _sr
                    merged[_merge_key]["coords"].append(coord_out)

        # GoldChest_special: coords live under synthetic key after all_coords split;
        # inject when this item drops any GoldChest family entity.
        _entry_mons = set(entry.get("monsters") or [])
        if _entry_mons & {"GoldChest", "GoldChest_UnderSea", GOLDCHEST_SPECIAL}:
            _gc_sp_coords = all_coords.get(GOLDCHEST_SPECIAL) or []
            if _gc_sp_coords:
                _gc_merge_key = None
                for _mk, _md in merged.items():
                    if _md.get("translation", "").endswith("(特殊)") and (
                        _md.get("entity_name") in GOLDCHEST_FAMILY or "黄金宝箱" in _md.get("translation", "")
                    ):
                        _gc_merge_key = _mk
                        break
                if _gc_merge_key is None:
                    # find base translation from family entries or resolve
                    _gc_base_trans = "黄金宝箱"
                    for _md in merged.values():
                        if _md.get("entity_name") in ("GoldChest", "GoldChest_UnderSea"):
                            _t = _md.get("translation", "")
                            for _suf in ("(特殊)", "(随机)", "组", "(可能上锁)"):
                                _t = _t.replace(_suf, "")
                            if _t:
                                _gc_base_trans = _t
                                break
                    _gc_tk = m_tk_map.get("GoldChest", "") or m_tk_map.get("GoldChest_UnderSea", "")
                    _gc_merge_key = f"{_gc_base_trans}|special"
                    merged[_gc_merge_key] = {
                        "name": GOLDCHEST_SPECIAL,
                        "entity_name": GOLDCHEST_SPECIAL,
                        "translation": _gc_base_trans + _LABEL_TYPE_SUFFIX["special"],
                        "translation_key": _gc_tk,
                        "color": _MONSTER_COLORS[len(merged) % len(_MONSTER_COLORS)],
                        "coords": [],
                        "_has_locked": False,
                        "_bases": {GOLDCHEST_SPECIAL, "GoldChest_UnderSea"},
                        "_coord_key": GOLDCHEST_SPECIAL,
                        "_source_kind": "special",
                    }
                else:
                    merged[_gc_merge_key]["name"] = GOLDCHEST_SPECIAL
                    merged[_gc_merge_key]["entity_name"] = GOLDCHEST_SPECIAL
                    merged[_gc_merge_key]["_coord_key"] = GOLDCHEST_SPECIAL
                _seen_sp = {(c["x"], c["y"], c["z"], c.get("file")) for c in merged[_gc_merge_key]["coords"]}
                for _c in _gc_sp_coords:
                    _raw_label = _c.get("original_keyword") or _c.get("keyword", "")
                    _k = (_c["x"], _c["y"], _c["z"], _c.get("json_filename"))
                    if _k in _seen_sp:
                        continue
                    _seen_sp.add(_k)
                    _rate_en = _c.get("keyword") or "GoldChest_UnderSea"
                    if _c.get("keyword") != _c.get("original_keyword", ""):
                        _sr = spawn_rate_detail.get((_c["original_keyword"], _rate_en), 0)
                    else:
                        _sr = spawn_rate_cache.get(_rate_en, 0)
                    if _sr <= 0:
                        _sr = spawn_rate_detail.get((_raw_label, "GoldChest_UnderSea"), 0) or 17.5
                    coord_out = {
                        "x": _c["x"],
                        "y": _c["y"],
                        "z": _c["z"],
                        "yaw": _c.get("yaw", 0),
                        "map": _c["map_base"],
                        "file": _c["json_filename"],
                        "version": _c["version"],
                        "label": _raw_label,
                        "spawn_rate": _sr,
                    }
                    _gp = _c.get("group_parent", "")
                    if _gp:
                        coord_out["group_parent"] = _gp
                    merged[_gc_merge_key]["coords"].append(coord_out)

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
                _en = _m_data.get("entity_name", _m_data["name"])
                # synthetic special: rates keyed under real entity GoldChest_UnderSea
                _rate_en = "GoldChest_UnderSea" if _en == GOLDCHEST_SPECIAL else _en
                _dr = drop_engine.get_group_drop_rates(item_name, _rate_en, _g)
                if not _dr:
                    _dr = (
                        drop_engine.get_group_drop_rates(item_name, "GoldChest", _g)
                        if _en == GOLDCHEST_SPECIAL
                        else None
                    )
                if not _dr:
                    _dr = {"PVE": 0, "普通": 0, "豪客赛": 0}
                _coord_labels = {_c["label"] for _c in _m_data["coords"] if _c.get("label")}
                if _has_locked:
                    _locked_name = (
                        _rate_en.replace("_UnderSea", "_Locked_UnderSea")
                        if "_UnderSea" in _rate_en
                        else _rate_en + "_Locked"
                    )
                    _common_sks = (
                        _coord_labels & entity_spawners.get(_rate_en, set()) & entity_spawners.get(_locked_name, set())
                    )
                    _best_rate = 0
                    for _sk in _common_sks:
                        _ul_sr = spawn_rate_detail.get((_sk, _rate_en), 0)
                        _l_sr = spawn_rate_detail.get((_sk, _locked_name), 0)
                        _rate = _ul_sr + _l_sr
                        if _rate > _best_rate:
                            _best_rate = _rate
                    _sr = _best_rate if _best_rate > 0 else drop_engine.get_combined_spawn_rate(_rate_en)
                    if _sr <= 0:
                        _sr = max(spawn_rate_cache.get(_bn, 100) for _bn in (_m_data.get("_bases") or {_rate_en}))
                else:
                    _sr_via_label = 0
                    _rate_ens = ("GoldChest_UnderSea", "GoldChest") if _en == GOLDCHEST_SPECIAL else (_rate_en,)
                    for _cl in _coord_labels:
                        for _re in _rate_ens:
                            _pair_sr = spawn_rate_detail.get((_cl, _re), 0)
                            if _pair_sr > _sr_via_label:
                                _sr_via_label = _pair_sr
                    _sr = _sr_via_label if _sr_via_label > 0 else drop_engine.get_combined_spawn_rate(_rate_en)
                    if _sr <= 0 and _en == GOLDCHEST_SPECIAL:
                        _sr = 17.5
                    if _sr <= 0:
                        _sr = max(spawn_rate_cache.get(_bn, 100) for _bn in (_m_data.get("_bases") or {_rate_en}))
                _sr = round(_sr, 4)
                _en_mode_rates = spawn_rate_by_mode.get(("", _rate_en), {}) or spawn_rate_by_mode.get(("", _en), {})
                _sr_by_mode: dict[str, float] = {}
                if _en_mode_rates:
                    for _mn in ("PVE", "普通", "豪客赛"):
                        if _mn in _en_mode_rates:
                            _sr_by_mode[_mn] = _en_mode_rates[_mn]
                _has_varied_spawn = len(set(_sr_by_mode.values())) > 1
                _group_drop_info.setdefault(_g, []).append(
                    {
                        "translation": _m_data["translation"],
                        "translation_key": _m_data.get("translation_key", ""),
                        "spawn_rate": _sr,
                        "drop_rates": _dr,
                        # keep real entity for variant drop lookup; synthetic stays as special id
                        "_variant": _en if _en == GOLDCHEST_SPECIAL else _m_data.get("entity_name", _m_data["name"]),
                        "_source_kind": _m_data.get("_source_kind", "direct"),
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
                _prio = {"Elite": 3, "Nightmare": 2, "Common": 1}.get(_m.group(1) if _m else "", _NO_SCORE)
                if _trans not in _best or _prio > _best[_trans].get("_q_prio", _NO_SCORE):
                    _best[_trans] = _entry
                    _best[_trans]["_q_prio"] = _prio
            _g_list[:] = list(_best.values())
            for _entry in _g_list:
                _entry["_entity_name"] = _entry.pop("_variant", "")
                _entry.pop("_q_prio", None)
        # Sort by spawn_rate * drop_rate descending
        for _g_list in _group_drop_info.values():
            _g_list.sort(key=lambda x: x["spawn_rate"] * x["drop_rates"].get("豪客赛", 0), reverse=True)

        # Build valid translation-group pairs from all entries (keep even if 豪客赛=0)
        _valid_tg: set[tuple[str, str]] = set()
        for _g, _entries in _group_drop_info.items():
            for e in _entries:
                _valid_tg.add((e["translation"], _g))
        _valid_translations: set[str] = {e["translation"] for e_set in _group_drop_info.values() for e in e_set}
        for _base_key in list(merged.keys()):
            _trans = merged[_base_key]["translation"]
            if _trans not in _valid_translations:
                del merged[_base_key]
                continue
            merged[_base_key]["coords"] = [
                c for c in merged[_base_key]["coords"] if (_trans, map_base_to_group.get(c["map"], "")) in _valid_tg
            ]

        # Compute per-coord score (using entity-level spawn_rate from group_drop_info)
        _hk_lookup: dict[str, dict[str, float]] = {}
        _sr_lookup: dict[str, dict[str, float]] = {}
        for _g, _entries in _group_drop_info.items():
            for _entry in _entries:
                _hkl = _hk_lookup.setdefault(_entry["translation"], {})
                _hkl[_g] = _entry["drop_rates"].get("豪客赛", 0)
                _srl = _sr_lookup.setdefault(_entry["translation"], {})
                _srl[_g] = _entry["spawn_rate"]
        for _base_data in merged.values():
            _trans = _base_data["translation"]
            _hk_map = _hk_lookup.get(_trans, {})
            _sr_map = _sr_lookup.get(_trans, {})
            for _c in _base_data["coords"]:
                _g = map_base_to_group.get(_c["map"], "")
                _hk = _hk_map.get(_g, 0)
                _sr = _sr_map.get(_g, 100)
                _score = _sr * _hk / 100
                _c["score"] = round(_score, 4)
        merged = {k: v for k, v in merged.items() if v["coords"]}
        for _v in merged.values():
            _bases = _v.pop("_bases", None)
            if _bases and len(_bases) > 1:
                _v["_multi_base"] = True
        monsters_out = list(merged.values())
        # gdi 子类图例：无坐标时仍保留 monsters 条目（预算/变体后再跑一遍）
        monsters_out = _ensure_gdi_monster_entries(monsters_out, _group_drop_info, entity_page_map)

        # MERGE: Merge "组" suffix entries into their base translations
        # e.g. "黄金宝箱组" (5 coords) → merge into "黄金宝箱" (2 coords) → "黄金宝箱" (7 coords)
        for _m in list(monsters_out):
            _trans = _m.get("translation", "")
            if _trans.endswith("组") and _m.get("coords"):
                _base_trans = _trans[:-1]
                for _base in monsters_out:
                    if _base is not _m and _base.get("translation") == _base_trans:
                        _base["coords"].extend(_m["coords"])
                        if _m.get("_coord_key") and not _base.get("_coord_key"):
                            _base["_coord_key"] = _m["_coord_key"]
                        monsters_out.remove(_m)
                        break

        # P005: Coordinate ref optimization — inline coords for type-split entities
        _type_suffixes = {"(特殊)", "(随机)", "组"}
        _split_entities: set[str] = set()
        for _m in monsters_out:
            _trans = _m.get("translation", "")
            if any(_s in _trans for _s in _type_suffixes):
                _split_entities.add(_m.get("entity_name", _m["name"]))
        if entity_page_map and not is_variant_family:
            for _m in monsters_out:
                _en = _m.get("entity_name", _m["name"])
                # GoldChest_special: always ref dedicated props page when available
                if _en == GOLDCHEST_SPECIAL:
                    _m.pop("_coord_key", None)
                    _rp = entity_page_map.get(GOLDCHEST_SPECIAL)
                    if _rp and _m.get("coords") is not None:
                        _m["ref"] = _rp
                        _m["coord_count"] = len(_m.get("coords") or [])
                        del _m["coords"]
                    continue
                if _en in _split_entities:
                    _m.pop("_coord_key", None)
                    continue
                if _m.pop("_multi_base", None):
                    _m.pop("_coord_key", None)
                    continue
                _ck = _m.pop("_coord_key", None)
                ref_page = (entity_page_map.get(_ck) if _ck else None) or entity_page_map.get(_en)
                if ref_page:
                    _filtered_count = len(_m["coords"])
                    _total_count = len(all_coords.get(_ck, [])) if _ck else 0
                    # Keep filtered coords inline when they are a small fraction of
                    # the full entity coord set (severe reduction like 2/87 or 10/112).
                    # This avoids showing irrelevant spawn points from the shared ref file.
                    # The threshold (50%) ensures common cases like 50/87 still use ref.
                    if _total_count > 0 and _filtered_count < _total_count * 0.5:
                        pass  # keep filtered coords inline
                    else:
                        _m["ref"] = ref_page
                        _m["coord_count"] = _filtered_count
                        del _m["coords"]
        # Pre-compute max score per monster translation
        _max_scores: dict[str, float] = {}
        for _g_list in _group_drop_info.values():
            for _entry in _g_list:
                _trans = _entry["translation"]
                _score = round(_entry["spawn_rate"] * _entry["drop_rates"].get("豪客赛", 0) / 100, 4)
                if _trans not in _max_scores or _score > _max_scores[_trans]:
                    _max_scores[_trans] = _score
        for _m in monsters_out:
            _m["max_score"] = _max_scores.get(_m["translation"], _NO_SCORE)
        # Remove monsters whose group_drop_info entries all have zero rates
        _trans_with_any_rate: set[str] = {
            _e["translation"]
            for _g_entries in _group_drop_info.values()
            for _e in _g_entries
            if any(v > 0 for v in _e["drop_rates"].values())
        }
        if _trans_with_any_rate:
            monsters_out = [_m for _m in monsters_out if _m["translation"] in _trans_with_any_rate]
        # Limit total coords to MAX_COORDS_PER_PAGE (sort by max_score desc)
        # P005: Handle referenced entities (no inline coords)
        # 0 坐标 / 仅 ref 条目始终保留（图例 + 参考爆率），不被 budget break 丢掉
        _total_coords = sum(len(_m.get("coords", [])) for _m in monsters_out)
        if _total_coords > MAX_COORDS_PER_PAGE:
            monsters_out.sort(key=lambda x: x.get("max_score", _NO_SCORE), reverse=True)
            _kept = []
            _budget = MAX_COORDS_PER_PAGE
            for _m in monsters_out:
                _coord_count = len(_m.get("coords", []))
                if _coord_count == 0:
                    _kept.append(_m)
                    continue
                if _budget <= 0:
                    continue
                if _coord_count <= _budget:
                    _kept.append(_m)
                    _budget -= _coord_count
                else:
                    _trimmed = dict(_m)
                    _trimmed["coords"] = _m["coords"][:_budget]
                    _kept.append(_trimmed)
                    _budget = 0
            monsters_out = _kept
        # 预算裁切后补齐 gdi 孤儿（遵守零爆率过滤）
        monsters_out = _ensure_gdi_monster_entries(
            monsters_out,
            _group_drop_info,
            entity_page_map,
            _max_scores,
            _trans_with_any_rate if _trans_with_any_rate else None,
        )
        if monsters_out:
            if used_translation_keys is not None:
                _item_tk = entry.get("translation_key")
                if _item_tk:
                    used_translation_keys.add(_item_tk)
                used_translation_keys.update(_m["translation_key"] for _m in monsters_out if _m.get("translation_key"))
                used_translation_keys.update(
                    _e["translation_key"]
                    for _g_entries in _group_drop_info.values()
                    for _e in _g_entries
                    if _e.get("translation_key")
                )
            detail = {
                "name": item_name,
                "translation": entry["translation"],
                "translation_key": entry.get("translation_key", ""),
                "monsters": monsters_out,
                "group_drop_info": _group_drop_info,
            }
            if variant_suffixes:
                if is_variant_family:
                    _vs_out = [s for s in variant_suffixes if s != "8001"]
                    detail["variant_suffixes"] = _vs_out
                    item_variant_suffixes[item_name] = _vs_out
                if translations:
                    detail["variant_rarity"] = _get_variant_rarity(item_name, variant_suffixes, translations)
                    if used_translation_keys is not None:
                        used_translation_keys.update(
                            _rarity["translation_key"] for _rarity in detail["variant_rarity"].values()
                        )

            if is_variant_family:
                sources: dict[str, dict] = {}
                source_ids_by_translation: dict[str, set[str]] = {}
                unresolved_refs: list[str] = []
                for _source in monsters_out:
                    _en = _source.get("entity_name", _source.get("name", ""))
                    _public_en = _public_source_entity(_en)
                    _kind = _source.get("_source_kind", "direct")
                    _sid = _source_id(_public_en, _kind)
                    _coord_key = _source.get("_coord_key")
                    _ref_candidates = [_source.get("ref")]
                    if entity_page_map:
                        _ref_candidates.extend(
                            [
                                entity_page_map.get(_coord_key) if _coord_key else None,
                                entity_page_map_ci.get(_coord_key.casefold()) if _coord_key else None,
                                entity_page_map.get(_en),
                                entity_page_map_ci.get(_en.casefold()),
                                entity_page_map.get(_public_en),
                                entity_page_map_ci.get(_public_en.casefold()),
                            ]
                        )
                    _ref_candidates.append(
                        _resolve_legend_ref(_source.get("translation", ""), _en, monsters_out, entity_page_map)
                    )
                    _ref = next(
                        (candidate for candidate in _ref_candidates if _ref_is_available(candidate)),
                        None,
                    )
                    if not _ref:
                        unresolved_refs.append(f"{_sid} ({_en}, ref={_ref or 'missing'})")
                        continue
                    _source_out = {
                        "name": _source.get("name", _en),
                        "entity_name": _public_en,
                        "translation": _source["translation"],
                        "translation_key": _source.get("translation_key", ""),
                        "color": _source["color"],
                        "ref": _ref,
                    }
                    _existing_source = sources.get(_sid)
                    if _existing_source and _existing_source != _source_out:
                        raise RuntimeError(f"lootdrop source_id collision for {item_name}: {_sid}")
                    sources[_sid] = _source_out
                    source_ids_by_translation.setdefault(_source["translation"], set()).add(_sid)

                # Legacy legend completion deduplicates by translated text. Restore
                # distinct logical sources directly from stable GDI identity.
                for _g_entries in _group_drop_info.values():
                    for _gdi_source in _g_entries:
                        _en = _gdi_source.get("_entity_name", "")
                        _public_en = _public_source_entity(_en)
                        _kind = _gdi_source.get("_source_kind", "direct")
                        _sid = _source_id(_public_en, _kind)
                        if _sid in sources:
                            continue
                        _ref_candidates = []
                        if entity_page_map:
                            _ref_candidates.extend(
                                [
                                    entity_page_map.get(_en),
                                    entity_page_map_ci.get(_en.casefold()),
                                    entity_page_map.get(_public_en),
                                    entity_page_map_ci.get(_public_en.casefold()),
                                ]
                            )
                        _ref_candidates.append(
                            _resolve_legend_ref(_gdi_source["translation"], _en, monsters_out, entity_page_map)
                        )
                        _ref = next(
                            (candidate for candidate in _ref_candidates if _ref_is_available(candidate)),
                            None,
                        )
                        if not _ref:
                            unresolved_refs.append(f"{_sid} ({_en}, ref=missing)")
                            continue
                        sources[_sid] = {
                            "name": _public_en,
                            "entity_name": _public_en,
                            "translation": _gdi_source["translation"],
                            "translation_key": _gdi_source.get("translation_key", ""),
                            "color": _MONSTER_COLORS[len(sources) % len(_MONSTER_COLORS)],
                            "ref": _ref,
                        }
                        source_ids_by_translation.setdefault(_gdi_source["translation"], set()).add(_sid)
                if unresolved_refs:
                    raise RuntimeError(
                        f"lootdrop sources without public refs for {item_name}: " + ", ".join(unresolved_refs)
                    )

                variants: dict[str, dict] = {}
                used_source_ids: set[str] = set()
                for suffix in detail["variant_suffixes"]:
                    variant_name = f"{item_name}_{suffix}"
                    luck_grade = int(suffix[0]) if suffix and suffix[0].isdigit() else 0
                    variant_gdi: dict[str, list[dict]] = {}
                    for _g, _entries in _group_drop_info.items():
                        v_entries = []
                        for _entry in _entries:
                            _en = _entry.get("_entity_name", _entry["translation"])
                            _rate_en = "GoldChest_UnderSea" if _en == GOLDCHEST_SPECIAL else _en
                            _vdr = drop_engine.get_variant_group_drop_rates(
                                luck_grade, _rate_en, _g, item_name=variant_name
                            )
                            if not _vdr:
                                _vdr = drop_engine.get_variant_group_drop_rates(
                                    luck_grade, "GoldChest", _g, item_name=variant_name
                                )
                            if not _vdr:
                                _vdr = {"PVE": 0, "普通": 0, "豪客赛": 0}
                            if _vdr.get("豪客赛", 0) <= 0:
                                continue
                            _sid = _source_id(_public_source_entity(_en), _entry.get("_source_kind", "direct"))
                            if _sid not in sources:
                                _translation_ids = source_ids_by_translation.get(_entry["translation"], set())
                                if len(_translation_ids) == 1:
                                    _sid = next(iter(_translation_ids))
                            if _sid not in sources:
                                raise RuntimeError(
                                    f"lootdrop variant source mismatch for {variant_name}: "
                                    f"{_entry['translation']} ({_en})"
                                )
                            v_entry = {
                                "source_id": _sid,
                                "spawn_rate": _entry["spawn_rate"],
                                "drop_rates": _vdr,
                            }
                            if _entry.get("spawn_rates"):
                                v_entry["spawn_rates"] = _entry["spawn_rates"]
                            v_entries.append(v_entry)
                            used_source_ids.add(_sid)
                        if v_entries:
                            variant_gdi[_g] = v_entries
                    variants[suffix] = {"group_drop_info": variant_gdi}
                    if log_fn:
                        _variant_groups = len(variant_gdi)
                        _variant_sources = len({e["source_id"] for entries in variant_gdi.values() for e in entries})
                        _variant_max = max(
                            (
                                round(e["spawn_rate"] * e["drop_rates"].get("豪客赛", 0) / 100, 4)
                                for entries in variant_gdi.values()
                                for e in entries
                            ),
                            default=0.0,
                        )
                        log_fn(
                            f"[JSON] {variant_name}: sources={_variant_sources}, "
                            f"groups={_variant_groups}, max_score={_variant_max}"
                        )
                    stale_variant = output_dir / "lootdrops" / f"{variant_name}.json"
                    stale_variant.unlink(missing_ok=True)

                detail["sources"] = {sid: source for sid, source in sources.items() if sid in used_source_ids}
                detail["variants"] = variants
                detail.pop("monsters", None)
                detail.pop("group_drop_info", None)
                if not detail["sources"] or not detail["variants"]:
                    raise RuntimeError(f"empty merged lootdrop family: {item_name}")
            # Clean internal keys from group_drop_info before saving base detail
            for _g_list in _group_drop_info.values():
                for _e in _g_list:
                    _e.pop("_entity_name", None)
                    _e.pop("_source_kind", None)
            if lootdrop_group_info_out is not None and not is_variant_family:
                lootdrop_group_info_out[item_name] = _group_drop_info
            if not is_variant_family:
                for _monster in monsters_out:
                    for _internal_key in ("_coord_key", "_multi_base", "_source_kind"):
                        _monster.pop(_internal_key, None)
            _save(output_dir, f"lootdrops/{item_name}.json", detail, compact=True)
            item_max_score[item_name] = max(_max_scores.values(), default=0.0)
            item_valid_names[item_name] = {_m["name"] for _m in monsters_out}
            _has_hr100 = any(
                e.get("drop_rates", {}).get("豪客赛", 0) >= 100.0 and e.get("spawn_rate", 0) < 5.0
                for _gl in _group_drop_info.values()
                for e in _gl
            )
            item_hr100[item_name] = _has_hr100
        detail_count += 1
        if detail_count % 100 == 0 and log_fn:
            log_fn(f"[JSON] lootdrops detail: {detail_count}/{detail_total}")
    if log_fn:
        log_fn(f"[JSON] lootdrops detail files DONE -> {detail_count} items")

    # Update lootdrops.json index with max_score, hr100, variant_suffixes and filtered monsters
    for _entry in loot_index:
        _iname = _entry["name"]
        _entry["max_score"] = item_max_score.get(_iname, 0.0)
        if item_hr100.get(_iname):
            _entry["hr100"] = True
        _vs = item_variant_suffixes.get(_iname)
        if _vs:
            _possible = _possible_variant_suffixes(_entry)
            _entry["variant_suffixes"] = _vs
            _entry["variant_count"] = len(_vs)
            _unavailable = [suffix for suffix in _possible if suffix not in _vs and suffix != "8001"]
            if _unavailable:
                _entry["unavailable_variant_suffixes"] = _unavailable
        _valid = item_valid_names.get(_iname)
        if _valid:
            _filtered = [
                (mn, mt, mtk)
                for mn, mt, mtk in zip(
                    _entry["monsters"],
                    _entry["monster_translations"],
                    _entry["monster_translation_keys"],
                    strict=True,
                )
                if mn in _valid
            ]
            if _filtered:
                _entry["monsters"], _entry["monster_translations"], _entry["monster_translation_keys"] = map(
                    list, zip(*_filtered, strict=True)
                )
    _save(output_dir, "lootdrops.json", loot_index)

    return item_max_score
