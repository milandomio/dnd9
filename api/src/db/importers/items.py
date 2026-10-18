import json
from collections import Counter

from config import ITEM_DIR

from .._helpers import extract_item_name, load_json_dir

_TYPE_TRANSLATION_PREFIX = "Text_Code_DCDataBlueprintLibrary_Type_Item_"
_SUBTYPE_FIELDS = {
    "Armor": "ArmorType",
    "Accessory": "AccessoryType",
    "Utility": "UtilityType",
    "Misc": "MiscType",
}


def _tag_name(value) -> str:
    return value.get("TagName", "") if isinstance(value, dict) else ""


def _tag_translation_key(tag_name: str) -> str:
    prefix = "Type.Item."
    if not tag_name.startswith(prefix):
        return ""
    path = tag_name.removeprefix(prefix).replace(".", "_")
    return f"{_TYPE_TRANSLATION_PREFIX}{path}" if path else ""


def _item_type_metadata(properties: dict) -> tuple[str, str, list[str]]:
    item_type = str(properties.get("ItemType", "")).removeprefix("EItemType::")
    category_key = f"{_TYPE_TRANSLATION_PREFIX}Category_{item_type}" if item_type else ""

    raw_values = []
    if item_type == "Weapon":
        raw_values = properties.get("WeaponTypes", []) or []
    elif item_type in _SUBTYPE_FIELDS:
        raw_value = properties.get(_SUBTYPE_FIELDS[item_type])
        if raw_value:
            raw_values = [raw_value]

    subtype_keys = []
    for raw_value in raw_values:
        key = _tag_translation_key(_tag_name(raw_value))
        if key and key not in subtype_keys:
            subtype_keys.append(key)
    return item_type, category_key, subtype_keys


def _slot_key(properties: dict) -> str:
    """Equip slot of the item (``Type.Item.Slot.Head`` -> its translation key).

    Armour uses it for the body part (head / hands / chest / legs / foot), while
    weapons only carry Primary/Secondary, which says nothing about the weapon.
    """
    return _tag_translation_key(_tag_name(properties.get("SlotType")))


def _rarity_from_properties(properties: dict) -> str:
    rarity = properties.get("RarityType")
    tag = _tag_name(rarity)
    return tag.rsplit(".", 1)[-1] if tag else ""


class ItemsImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM item_entities")
        files = load_json_dir(ITEM_DIR)
        variant_counts: Counter = Counter()
        seen: set[str] = set()
        rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = ""
            if "Name" in props:
                name_key = (props["Name"] or {}).get("Key", "")
            item_name = extract_item_name(raw_name)
            variant_counts[item_name] += 1
            if item_name not in seen:
                seen.add(item_name)
                item_type, category_key, subtype_keys = _item_type_metadata(props)
                rows.append(
                    (
                        item_name,
                        raw_name,
                        name_key,
                        "",
                        item_type,
                        category_key,
                        json.dumps(subtype_keys, ensure_ascii=False, separators=(",", ":")),
                        _slot_key(props),
                    )
                )
        deduped = [r[:4] + (variant_counts.get(r[0], 1),) + r[4:] for r in rows]
        c.executemany(
            "INSERT OR REPLACE INTO item_entities (item_name, raw_name, translation_key, category, variant_count, item_type, item_category_key, item_subtype_keys, item_slot_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            deduped,
        )
        self._rebuild_fts("items_fts")
        self.conn.commit()
        return len(deduped)

    def import_lights(self) -> int:
        """Persist items that carry both FuelSeconds and LightAreaRadius.

        One row per quality variant so the 【灯】 page can show each tier's exact
        burn time and light radius. Exact duplicates (same item, rarity, fuel and
        radius) are collapsed so a legacy suffix-less base asset does not shadow a
        real tier.
        """
        c = self.conn.cursor()
        c.execute("DELETE FROM light_items")
        files = load_json_dir(ITEM_DIR)
        rows = []
        seen: set[tuple] = set()
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            props = data_list[0].get("Properties", {}) or {}
            fuel = props.get("FuelSeconds")
            radius = props.get("LightAreaRadius")
            if not isinstance(fuel, (int, float)) or not isinstance(radius, (int, float)):
                continue
            item_name = extract_item_name(raw_name)
            rarity = _rarity_from_properties(props)
            key = (item_name, rarity, float(fuel), float(radius))
            if key in seen:
                continue
            seen.add(key)
            rows.append((raw_name, item_name, rarity, float(fuel), float(radius)))
        c.executemany(
            "INSERT OR REPLACE INTO light_items (raw_name, item_name, rarity, fuel_seconds, light_area_radius) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def _rebuild_fts(self, fts_table: str):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
        self.conn.commit()
