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
                    )
                )
        deduped = [r[:4] + (variant_counts.get(r[0], 1),) + r[4:] for r in rows]
        c.executemany(
            "INSERT OR REPLACE INTO item_entities (item_name, raw_name, translation_key, category, variant_count, item_type, item_category_key, item_subtype_keys) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            deduped,
        )
        self._rebuild_fts("items_fts")
        self.conn.commit()
        return len(deduped)

    def _rebuild_fts(self, fts_table: str):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
        self.conn.commit()
