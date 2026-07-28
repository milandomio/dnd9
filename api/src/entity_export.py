"""Entity export functions (items, monsters, props) extracted from collector.py."""

import json
from pathlib import Path

from label_type import GOLDCHEST_SPECIAL, LABEL_TYPE_SUFFIX
from translator import (
    ORE_ITEM_COORD_RE,
    ORE_QUALITY_RE,
    QUALITY_RE,
    build_coord_out,
    filter_coords,
    ore_quality_key,
)


def _save(output_dir: Path, filename: str, data: list | dict):
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_items(
    items: list[dict],
    merged_loot: dict[str, list[str]],
    all_coords: dict[str, list[dict]],
    resolve_name,
    skip_variants: set[str],
    coord_variant_count: dict,
    item_names: set[str],
    output_dir: Path,
    map_to_module: dict | None = None,
    item_coord_chain_map: dict[str, set[str]] | None = None,
    sub_pool_info: dict | None = None,
) -> list[dict]:
    """Export items index + individual detail files. Returns items_index."""
    items_index = []
    for r in items:
        name = r["item_name"]
        if name in skip_variants:
            continue
        _mons = merged_loot.get(name, [])
        if _mons and "Ground" not in _mons:
            continue
        coords = filter_coords(all_coords.get(name, []), item_names)
        if not coords:
            m = ORE_ITEM_COORD_RE.match(name)
            if m:
                coords = filter_coords(all_coords.get(m.group(1) + "Ore", []), item_names)
        if not coords and item_coord_chain_map:
            for spawner_kw in item_coord_chain_map.get(name, []):
                _raw = all_coords.get(spawner_kw, [])
                if _raw:
                    coords = _raw
                    break
        if not coords:
            continue
        translation = resolve_name(name, r["translation_key"], "item")
        variant_count = r.get("variant_count", 1)
        items_index.append(
            {
                "name": name,
                "translation": translation,
                "translation_key": r["translation_key"],
                "category": r["category"],
                "variant_count": variant_count,
                "monsters": merged_loot.get(name, []),
                "coordCount": len(coords),
            }
        )
        entity_data = {
            "name": name,
            "translation": translation,
            "translation_key": r["translation_key"],
            "category": r["category"],
            "variant_count": variant_count,
            "monsters": merged_loot.get(name, []),
            "coords": [build_coord_out(c, coord_variant_count, map_to_module, sub_pool_info) for c in coords],
        }
        _save(output_dir, f"items/{name}.json", entity_data)
    _save(output_dir, "items.json", items_index)
    return items_index


def export_monsters(
    monsters: list[dict],
    all_coords: dict[str, list[dict]],
    resolve_name,
    coord_variant_count: dict,
    monster_names: set[str],
    output_dir: Path,
    map_to_module: dict | None = None,
    sub_pool_info: dict | None = None,
) -> list[dict]:
    """Export monsters index + individual detail files. Returns monsters_index."""
    _monsters_by_name: dict[str, dict] = {r["monster_name"]: r for r in monsters}
    monsters_by_translation: dict[str, list[dict]] = {}
    for r in monsters:
        translation = resolve_name(r["monster_name"], r["translation_key"], "monster")
        # 翻译失败（返回原始名）且有质量后缀时，改用基础怪物的翻译作为分组键
        if translation == r["monster_name"] and QUALITY_RE.search(r["monster_name"]):
            base = QUALITY_RE.sub("", r["monster_name"])
            if base != r["monster_name"]:
                br = _monsters_by_name.get(base)
                if br:
                    if br["translation_key"]:
                        bt = resolve_name(br["monster_name"], br["translation_key"], "monster")
                        if bt != br["monster_name"]:
                            translation = bt
                    else:
                        translation = base
        monsters_by_translation.setdefault(translation, []).append(r)

    monsters_index = []
    for translation, group in monsters_by_translation.items():
        canonical = next((r for r in group if r["translation_key"]), group[0])
        seen_coords: set[tuple] = set()
        merged_coords_list = []
        for r in group:
            coords = filter_coords(all_coords.get(r["monster_name"], []), monster_names)
            for c in coords:
                key = (c["x"], c["y"], c["z"], c["map_base"], c["json_filename"])
                if key not in seen_coords:
                    seen_coords.add(key)
                    merged_coords_list.append(c)
        if not merged_coords_list:
            continue
        monsters_index.append(
            {
                "name": canonical["monster_name"],
                "translation": translation,
                "translation_key": canonical["translation_key"],
                "coordCount": len(merged_coords_list),
            }
        )
        entity_data = {
            "name": canonical["monster_name"],
            "translation": translation,
            "translation_key": canonical["translation_key"],
            "coords": [
                build_coord_out(c, coord_variant_count, map_to_module, sub_pool_info) for c in merged_coords_list
            ],
        }
        _save(output_dir, f"monsters/{canonical['monster_name']}.json", entity_data)
    _save(output_dir, "monsters.json", monsters_index)
    return monsters_index


def export_props(
    props: list[dict],
    all_coords: dict[str, list[dict]],
    resolve_name,
    props_spawner_info: dict[str, dict],
    coord_variant_count: dict,
    prop_names: set[str],
    output_dir: Path,
    map_to_module: dict | None = None,
    sub_pool_info: dict | None = None,
) -> list[dict]:
    """Export props index + individual detail files. Returns props_index."""
    props_index = []
    props_by_translation: dict[tuple[str, bool], list[dict]] = {}
    for r in sorted(props, key=lambda r: ore_quality_key(r["asset_name"])):
        # synthetic special page exported separately (must not merge under 黄金宝箱)
        if r["asset_name"] == GOLDCHEST_SPECIAL:
            continue
        translation = resolve_name(r["asset_name"], r["translation_key"], "props")
        # Ore quality variants without translation: normalize to base ore name
        if translation == r["asset_name"]:
            m = ORE_QUALITY_RE.match(r["asset_name"])
            if m:
                translation = m.group(1) if m.group(1).startswith("Ore_") else "Ore_" + m.group(1)
        has_lootdrop = bool((props_spawner_info.get(r["asset_name"]) or {}).get("has_lootdrop"))
        props_by_translation.setdefault((translation, has_lootdrop), []).append(r)
    for (translation, _has_lootdrop), group in props_by_translation.items():
        merged_coords = []
        seen_coords: set[tuple] = set()
        for r in group:
            coords = filter_coords(all_coords.get(r["asset_name"], []), prop_names, is_prop=True)
            for c in coords:
                key = (c["x"], c["y"], c["z"], c["map_base"], c["json_filename"])
                if key not in seen_coords:
                    seen_coords.add(key)
                    merged_coords.append(c)
        # Also try matching via cleaned ore name
        if not merged_coords:
            for r in group:
                m = ORE_QUALITY_RE.match(r["asset_name"])
                if m:
                    coords = filter_coords(all_coords.get(m.group(1), []), prop_names, is_prop=True)
                    for c in coords:
                        key = (c["x"], c["y"], c["z"], c["map_base"], c["json_filename"])
                        if key not in seen_coords:
                            seen_coords.add(key)
                            merged_coords.append(c)
                    if merged_coords:
                        break
        if not merged_coords:
            continue
        # For merged ore quality variants, use English base ore name as key
        name_key = group[0]["asset_name"]
        if len(group) > 1:
            m = ORE_QUALITY_RE.match(name_key)
            if m:
                name_key = m.group(1)

        # Determine entity type: decoration (no lootdrop in spawner_data) or props
        entity_type = "props"
        for r in group:
            asset = r["asset_name"]
            info = props_spawner_info.get(asset)
            if info and info["has_lootdrop"] == 0:
                entity_type = "decoration"
                break

        canonical_prop = group[0]
        props_index.append(
            {
                "name": name_key,
                "translation": translation,
                "translation_key": canonical_prop["translation_key"],
                "coordCount": len(merged_coords),
                "type": entity_type,
            }
        )
        entity_data = {
            "name": name_key,
            "translation": translation,
            "translation_key": canonical_prop["translation_key"],
            "coords": [build_coord_out(c, coord_variant_count, map_to_module, sub_pool_info) for c in merged_coords],
        }
        _save(output_dir, f"props/{name_key}.json", entity_data)

    # GoldChest_special: synthetic page (Special-generator coords only)
    _gc_special_coords = all_coords.get(GOLDCHEST_SPECIAL) or []
    if _gc_special_coords:
        _gc_tk = ""
        for r in props:
            if r["asset_name"] in ("GoldChest", "GoldChest_UnderSea"):
                _gc_tk = r.get("translation_key") or ""
                break
        _gc_base_trans = resolve_name("GoldChest", _gc_tk, "props") if _gc_tk else "黄金宝箱"
        _gc_special_trans = _gc_base_trans + LABEL_TYPE_SUFFIX["special"]
        _built = [build_coord_out(c, coord_variant_count, map_to_module, sub_pool_info) for c in _gc_special_coords]
        props_index.append(
            {
                "name": GOLDCHEST_SPECIAL,
                "translation": _gc_special_trans,
                "translation_key": _gc_tk,
                "coordCount": len(_built),
                "type": "props",
            }
        )
        _save(
            output_dir,
            f"props/{GOLDCHEST_SPECIAL}.json",
            {
                "name": GOLDCHEST_SPECIAL,
                "translation": _gc_special_trans,
                "translation_key": _gc_tk,
                "coords": _built,
            },
        )

    _save(output_dir, "props.json", props_index)
    return props_index
