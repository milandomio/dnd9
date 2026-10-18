"""Resolve item stat lines (armour rating, damage, ...) from ItemProperty assets.

Item assets carry no numbers of their own: each one points at a ``PrimaryProperty``
asset plus a list of ``SecondaryProperties`` slots, and those hold one row per stat
with the exact range the item rolls:

    Id_Item_FrostlightAketon_5001
      -> PrimaryProperty Id_ItemProperty_Primary_FrostlightAketon_5001
           ArmorRating 19~20, MaxHealthAdd 3, MagicRegistance 41, ...
      -> SecondaryProperties [Id_ItemProperty_Secondary_Chest] x 3
           three random rolls, all drawing from one shared pool

Each row names an ``ItemPropertyType`` asset that owns the stat's display key and
its ``ValueRatio``: a ratio of 0.001 marks the percentage stats, so an ``Action
Speed`` row of 20 reads as ``2%`` — which is exactly what the game and the wiki
show — while types without a ratio are flat numbers (armour rating 19, move
speed -30, physical weapon damage 17).

Only the import phase may read the game extract and CI has none, so the resolved
summary is persisted (see ``db/importers/item_properties.py``) and read back by
the DB-only 【工匠】 export.
"""

import json
from pathlib import Path

# ``Type.Item.Property.Effect.ArmorRating`` -> the game's own display string.
_TAG_TRANSLATION_PREFIX = "Text_Code_DCDataBlueprintLibrary_Type_Item_"


def _load(path: Path) -> list | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _tag_translation_key(tag_name: str) -> str:
    prefix = "Type.Item."
    if not tag_name.startswith(prefix):
        return ""
    path = tag_name.removeprefix(prefix).replace(".", "_")
    return f"{_TAG_TRANSLATION_PREFIX}{path}" if path else ""


def _asset_stem(asset_path_name: str) -> str:
    """``/Game/.../Id_ItemProperty_Secondary_Chest.Id_ItemProperty_Secondary_Chest``
    -> ``Id_ItemProperty_Secondary_Chest``."""
    return asset_path_name.rsplit("/", 1)[-1].split(".", 1)[0]


def _number(value) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value) if float(value).is_integer() else float(value)


def build_property_type_index(type_dir: Path) -> dict[str, dict]:
    """Map an ItemPropertyType asset name to its display key and value ratio.

    ``Id_ItemPropertyType_Effect_ActionSpeed`` -> ``{"key": "..._Effect_ActionSpeed",
    "ratio": 0.001}``. Types without ``ValueRatio`` are flat numbers.
    """
    index: dict[str, dict] = {}
    if not type_dir.exists():
        return index
    for fp in sorted(type_dir.glob("*.json")):
        data = _load(fp)
        if not data:
            continue
        props = (data[0] or {}).get("Properties") or {}
        ratio = props.get("ValueRatio")
        index[fp.stem] = {
            "key": _tag_translation_key((props.get("PropertyType") or {}).get("TagName", "")),
            "ratio": float(ratio) if isinstance(ratio, (int, float)) and not isinstance(ratio, bool) else 0.0,
        }
    return index


def property_rows(asset_path_name: str, property_dir: Path, type_index: dict[str, dict]) -> list[dict]:
    """Stat rows of one ItemProperty asset, decorated with display key + ratio.

    ``rate`` only means something inside a random pool; primary rows carry 0.
    """
    data = _load(property_dir / f"{_asset_stem(asset_path_name)}.json")
    if not data:
        return []
    rows: list[dict] = []
    for block in data:
        for item in (block.get("Properties") or {}).get("ItemPropertyItemArray") or []:
            type_stem = _asset_stem((item.get("PropertyTypeId") or {}).get("AssetPathName", ""))
            minimum = _number(item.get("MinValue"))
            maximum = _number(item.get("MaxValue"))
            if not type_stem or minimum is None or maximum is None:
                continue
            meta = type_index.get(type_stem, {})
            rows.append(
                {
                    "type": type_stem.removeprefix("Id_ItemPropertyType_"),
                    "key": meta.get("key", ""),
                    "ratio": meta.get("ratio", 0.0),
                    "min": minimum,
                    "max": maximum,
                    "rate": int(item.get("PropertyRate") or 0),
                }
            )
    return rows


def resolve_item_properties(
    item_dir: Path, property_dir: Path, type_dir: Path
) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    """Resolve every item asset into ``(items, pools)``.

    ``items`` maps a raw item name (``FrostlightAketon_5001``) to
    ``{"primary": [row, ...], "secondary_pool": asset_name, "secondary_rolls": n}``.
    ``pools`` maps a pool asset name to its rows, so many items can share one
    pool without the export repeating it per item.
    """
    type_index = build_property_type_index(type_dir)
    items: dict[str, dict] = {}
    pools: dict[str, list[dict]] = {}
    if not item_dir.exists():
        return items, pools
    for fp in sorted(item_dir.glob("*.json")):
        data = _load(fp)
        if not data:
            continue
        props = (data[0] or {}).get("Properties") or {}
        primary_ref = (props.get("PrimaryProperty") or {}).get("AssetPathName", "")
        secondary_refs = [
            ref.get("AssetPathName", "") for ref in props.get("SecondaryProperties") or [] if isinstance(ref, dict)
        ]
        primary = []
        if primary_ref:
            primary = [
                {k: v for k, v in row.items() if k != "rate"}
                for row in property_rows(primary_ref, property_dir, type_index)
            ]
        pool_name = _asset_stem(secondary_refs[0]) if secondary_refs else ""
        rolls = len([ref for ref in secondary_refs if ref])
        for ref in secondary_refs:
            stem = _asset_stem(ref)
            if stem and stem not in pools:
                pools[stem] = property_rows(ref, property_dir, type_index)
        if not primary and not (pool_name and pools.get(pool_name)):
            continue
        items[fp.stem.removeprefix("Id_Item_")] = {
            "primary": primary,
            "secondary_pool": pool_name,
            "secondary_rolls": rolls,
        }
    return items, pools
