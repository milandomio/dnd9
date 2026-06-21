"""Entity export functions (items, monsters, props) extracted from collector.py."""

import json
from pathlib import Path

from translator import (
    ORE_ITEM_COORD_RE,
    ORE_QUALITY_RE,
    QUALITY_RE,
    build_coord_out,
    filter_coords,
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
) -> list[dict]:
    """Export items index + individual detail files. Returns items_index."""
    items_index = []
    for r in items:
        name = r["item_name"]
        if name in skip_variants:
            continue
        coords = filter_coords(all_coords.get(name, []), item_names)
        # Try ore name cleaning: GoldOres → GoldOre
        if not coords:
            m = ORE_ITEM_COORD_RE.match(name)
            if m:
                coords = filter_coords(all_coords.get(m.group(1) + "Ore", []), item_names)
        if not coords:
            continue
        translation = resolve_name(name, r["translation_key"], "item")
        variant_count = r.get("variant_count", 1)
        items_index.append(
            {
                "name": name,
                "translation": translation,
                "category": r["category"],
                "variant_count": variant_count,
                "monsters": merged_loot.get(name, []),
                "coordCount": len(coords),
            }
        )
        _save(
            output_dir,
            f"items/{name}.json",
            {
                "name": name,
                "translation": translation,
                "category": r["category"],
                "variant_count": variant_count,
                "monsters": merged_loot.get(name, []),
                "coords": [build_coord_out(c, coord_variant_count) for c in coords],
            },
        )
    _save(output_dir, "items.json", items_index)
    return items_index


def export_monsters(
    monsters: list[dict],
    all_coords: dict[str, list[dict]],
    resolve_name,
    coord_variant_count: dict,
    monster_names: set[str],
    output_dir: Path,
) -> list[dict]:
    """Export monsters index + individual detail files. Returns monsters_index."""
    monsters_by_translation: dict[str, list[dict]] = {}
    for r in monsters:
        translation = resolve_name(r["monster_name"], r["translation_key"], "monster")
        # 翻译失败（返回原始名）且有质量后缀时，改用基础怪物的翻译作为分组键
        if translation == r["monster_name"] and QUALITY_RE.search(r["monster_name"]):
            base = QUALITY_RE.sub("", r["monster_name"])
            if base != r["monster_name"]:
                for br in monsters:
                    if br["monster_name"] == base:
                        if br["translation_key"]:
                            bt = resolve_name(br["monster_name"], br["translation_key"], "monster")
                            if bt != br["monster_name"]:
                                translation = bt
                        else:
                            translation = base
                        break
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
                "coordCount": len(merged_coords_list),
            }
        )
        _save(
            output_dir,
            f"monsters/{canonical['monster_name']}.json",
            {
                "name": canonical["monster_name"],
                "translation": translation,
                "coords": [build_coord_out(c, coord_variant_count) for c in merged_coords_list],
            },
        )
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
) -> list[dict]:
    """Export props index + individual detail files. Returns props_index."""
    from translator import ore_quality_key

    props_index = []
    props_by_translation: dict[str, list[dict]] = {}
    for r in sorted(props, key=lambda r: ore_quality_key(r["asset_name"])):
        translation = resolve_name(r["asset_name"], r["translation_key"], "props")
        # Ore quality variants without translation: normalize to base ore name
        if translation == r["asset_name"]:
            m = ORE_QUALITY_RE.match(r["asset_name"])
            if m:
                translation = m.group(1) if m.group(1).startswith("Ore_") else "Ore_" + m.group(1)
        props_by_translation.setdefault(translation, []).append(r)
    for translation, group in props_by_translation.items():
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

        props_index.append(
            {
                "name": name_key,
                "translation": translation,
                "coordCount": len(merged_coords),
                "type": entity_type,
            }
        )
        _save(
            output_dir,
            f"props/{name_key}.json",
            {
                "name": name_key,
                "translation": translation,
                "coords": [build_coord_out(c, coord_variant_count) for c in merged_coords],
            },
        )
    _save(output_dir, "props.json", props_index)
    return props_index
