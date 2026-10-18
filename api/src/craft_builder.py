"""Export tavern crafting recipes for the 【工匠】 page.

The importer stores one row per StockCraft recipe in ``craft_recipes``; this
export only reads the DB, so CI builds (which have no game extract) stay DB-only.
Names come from ``item_entities`` translation keys; the zh-Hans label is embedded
because the default language does not load the locale dictionary on the client.

Recipes are grouped by the material that identifies their family, so recipes
built from the same thing sit together instead of one section per item:

* ``SilverPowder`` -> the seven 【纯银】 weapons of the Weaponsmith;
* ``IronIngots``  -> the six iron-only weaponsmith items;
* ``BlueSapphire + ArcaneEssence`` -> the Goldsmith's sapphire jewellery;
* the synthetic 【矿类】 tab (pure ore/coin refining) is a single group.

Equipment NPCs (Armourer, Weaponsmith, Tailor, Leathersmith) are classified with
the item taxonomy the 【掉落表】 page uses instead: every material family there
holds a single item, so the sections are the game's item category plus the worn
body part (护甲 / 头部 …) or, for weapons, the weapon subtype (武器 / 剑 …). A
weapon the game files under several weapon types (a staff is both a mace and a
staff) is listed under each of them, exactly like the 【掉落表】 page does.

Two safety nets keep the headings useful:

* a material group that would hold a single item falls back to the item name,
  because a material heading over one card groups nothing;
* an item whose quality tiers consume *different* materials (SurgicalKit)
  cannot sit in one material group without splitting the tiers apart, so it
  keeps its own item group.
"""

import json
from pathlib import Path

from db.importers.crafts import ORE_MERCHANT

RARITY_ORDER = {
    "Poor": 0,
    "Common": 1,
    "Uncommon": 2,
    "Rare": 3,
    "Epic": 4,
    "Legend": 5,
    "Unique": 6,
    "Artifact": 7,
}

#: Raw currencies are shared by dozens of unrelated recipes (:95 recipes), so a
#: material group only uses them when they are the *only* material.
_CURRENCIES = frozenset({"SilverCoin", "GoldCoins"})

#: Equipment NPCs whose items the page classifies with the 【掉落表】 taxonomy
#: instead of by material: armour by the body part it is worn on (head / hands /
#: chest / legs / foot) and weapons by their subtype (sword / axe / bow ...).
_EQUIPMENT_MERCHANTS = frozenset({"Armourer", "Tailor", "Leathersmith", "Weaponsmith"})

#: Item types whose section is the body part the item is worn on. Weapons only
#: carry Primary/Secondary as their slot, so they are grouped by subtype instead.
_PART_ITEM_TYPES = frozenset({"Armor"})

#: Prefix of the item type tag keys (``…_Type_Item_Slot_Head``); it stops the
#: ancestor lookup of ``_key_label`` from walking out of the tag namespace.
_TYPE_TAG_PREFIX = "Text_Code_DCDataBlueprintLibrary_Type_Item_"

#: Section order of the item categories, mirroring the 【掉落表】 page.
_CATEGORY_ORDER = ("Utility", "Misc", "Accessory", "Armor", "Weapon")

#: Separator between the parts of a composite group key.
_GROUP_SEPARATOR = "\u001f"


def _signature(requirements: list[dict]) -> tuple[str, ...]:
    """The material names that identify a recipe family, sorted."""
    names = [requirement["name"] for requirement in requirements]
    distinctive = [name for name in names if name not in _CURRENCIES]
    return tuple(sorted(set(distinctive or names)))


def _category_name(category_key: str) -> str:
    """``..._Type_Item_Category_Armor`` -> ``Armor``."""
    return category_key.rsplit("_Category_", 1)[-1]


def _part_keys(entry: dict) -> list[str]:
    """Keys of the section parts: body part for armour, subtype for the rest."""
    if entry["item_type"] in _PART_ITEM_TYPES and entry["slot_key"]:
        return [entry["slot_key"]]
    return entry["subtype_keys"]


def _category_rank(group: str) -> int:
    """【掉落表】 category order, used as the secondary section sort key."""
    category = _category_name(group.split(_GROUP_SEPARATOR)[0])
    return _CATEGORY_ORDER.index(category) if category in _CATEGORY_ORDER else len(_CATEGORY_ORDER)


def _order_equipment_sections(entries: list[dict]) -> None:
    """Sort the equipment sections: most items first, then the 【掉落表】 order.

    The section key is prefixed with a zero padded index because the payload is
    sorted by group key, which keeps the biggest part of the tab on top.
    """
    section_items: dict[tuple[str, str], set[str]] = {}
    for entry in entries:
        if entry.get("group_kind") != "category":
            continue
        section_items.setdefault((entry["merchant"], entry["group"]), set()).add(entry["name"])

    by_merchant: dict[str, dict[str, tuple[int, int]]] = {}
    for (merchant, group), items in section_items.items():
        by_merchant.setdefault(merchant, {})[group] = (-len(items), _category_rank(group))

    for sections in by_merchant.values():
        ordered = sorted(sections, key=lambda group: (sections[group], group))
        for index, group in enumerate(ordered):
            sections[group] = index

    for entry in entries:
        index = by_merchant.get(entry["merchant"], {}).get(entry.get("group", ""))
        if index is not None:
            entry["group"] = f"{index:02d}{_GROUP_SEPARATOR}{entry['group']}"


def _key_label(resolve_name, key: str) -> dict:
    """Label for a raw game translation key (item category / subtype / slot).

    Some tags are one level deeper than the game's translations, e.g.
    ``..._Type_Item_Utility_Installable_Trap`` has no string of its own while its
    parent ``..._Type_Item_Utility_Installable`` (部署品) describes it, so an
    untranslated key falls back to its closest translated ancestor.
    """
    candidate = key
    while candidate:
        translation = resolve_name("", candidate, "item")
        if translation:
            # The tag may be one level deeper than the game's strings, so the label
            # points at the closest ancestor key that every language translates.
            return {"name": key, "translation": translation, "translation_key": candidate}
        parent = candidate.rsplit("_", 1)[0]
        candidate = parent if parent != candidate and parent.startswith(_TYPE_TAG_PREFIX) else ""
    return {"name": key, "translation": "", "translation_key": key}


def _property_entries(rows: list[dict], resolve_name, with_chance: bool) -> list[dict]:
    """Label stat rows for the client: display name plus the rolled range.

    ``ratio`` marks the percentage stats (raw 20 -> 2%), matching the in-game
    tooltip; rows without it are flat numbers.
    """
    total = sum(row.get("rate") or 0 for row in rows) or 1
    entries = []
    for row in rows:
        label = _key_label(resolve_name, row.get("key") or "")
        entry = {
            "type": row.get("type", ""),
            "translation": label["translation"],
            "translation_key": label["translation_key"],
            "min": row.get("min", 0),
            "max": row.get("max", 0),
        }
        if row.get("ratio"):
            entry["ratio"] = row["ratio"]
        if with_chance:
            entry["chance"] = round((row.get("rate") or 0) / total, 4)
        entries.append(entry)
    return entries


def _craft_properties(
    raw_name: str,
    item_properties: dict[str, dict],
    property_pools: dict[str, list[dict]],
    resolve_name,
) -> dict:
    """Stat lines shown under the materials of one crafted item.

    ``primary`` stats are fixed; ``random`` names the pool the item's extra
    enchantment slots draw from. Pools are shared by every item of one equipment
    slot, so the payload keeps them once (``property_pools``) and recipes only
    carry the reference.
    """
    stored = item_properties.get(raw_name)
    if not stored:
        return {}
    primary = _property_entries(stored.get("primary") or [], resolve_name, with_chance=False)
    pool_name = stored.get("secondary_pool") or ""
    rolls = int(stored.get("secondary_rolls") or 0)
    if not primary and not rolls:
        return {}
    entry: dict = {"primary": primary}
    if pool_name and property_pools.get(pool_name):
        entry["random"] = {"rolls": rolls, "pool": pool_name}
    return entry


class _ItemLabel:
    """Resolves a folded item name to (translation, translation_key)."""

    def __init__(self, items, resolve_name):
        self.meta = {row["item_name"]: row for row in items}
        self.resolve = resolve_name

    def __call__(self, name: str) -> dict:
        translation_key = self.meta.get(name, {}).get("translation_key", "")
        if not translation_key:
            translation_key = f"Text_DesignData_Item_Item_{name}"
        return {
            "name": name,
            "translation": self.resolve(name, translation_key, "item"),
            "translation_key": translation_key,
        }

    def subtype_keys(self, name: str) -> list[str]:
        """Item category / subtype keys of a folded item name (may be empty)."""
        row = self.meta.get(name, {})
        try:
            subtypes = json.loads(row.get("item_subtype_keys", "[]") or "[]")
        except json.JSONDecodeError:
            subtypes = []
        return [key for key in subtypes if isinstance(key, str) and key]


def build_and_save_crafts(
    merchants,
    recipes,
    items,
    resolve_name,
    output_dir: Path,
    item_properties: dict[str, dict] | None = None,
    property_pools: dict[str, list[dict]] | None = None,
) -> dict:
    """Build ``crafts.json`` from DB rows. Returns the payload."""
    label = _ItemLabel(items, resolve_name)
    item_properties = item_properties or {}
    property_pools = property_pools or {}
    merchant_order = {row["merchant_name"]: row["sort_order"] for row in merchants}
    kinds = {row["merchant_name"]: row["kind"] for row in merchants}

    entries: list[dict] = []
    for row in recipes:
        name = row["output_item_name"]
        requirements = json.loads(row["requirements_json"] or "[]")
        entry = {
            "merchant": row["merchant_name"],
            "recipe_id": row["recipe_id"],
            "unique_id": row["unique_id"],
            "name": name,
            "raw_name": row["output_raw_name"],
            "rarity": row["output_rarity"],
            "requirements": [dict(requirement, **label(requirement["name"])) for requirement in requirements],
        }
        entry.update(label(name))
        entry["signature"] = _signature(requirements)
        entry["category_key"] = label.meta.get(name, {}).get("item_category_key", "")
        entry["subtype_keys"] = label.subtype_keys(name)
        entry["item_type"] = label.meta.get(name, {}).get("item_type", "")
        entry["slot_key"] = label.meta.get(name, {}).get("item_slot_key", "")
        properties = _craft_properties(row["output_raw_name"], item_properties, property_pools, resolve_name)
        if properties:
            entry["properties"] = properties
        entries.append(entry)

    # Items whose tiers need different materials keep an item group so every
    # quality tier of one item still renders together.
    signatures: dict[tuple[str, str], set[tuple[str, ...]]] = {}
    for entry in entries:
        signatures.setdefault((entry["merchant"], entry["name"]), set()).add(entry["signature"])
    split_items = {key for key, found in signatures.items() if len(found) > 1 and kinds.get(key[0]) != "ores"}

    # A material group is only worth its heading when it actually merges items.
    family_items: dict[tuple[str, tuple[str, ...]], set[str]] = {}
    for entry in entries:
        if kinds.get(entry["merchant"]) == "ores" or (entry["merchant"], entry["name"]) in split_items:
            continue
        family_items.setdefault((entry["merchant"], entry["signature"]), set()).add(entry["name"])

    grouped: list[dict] = []
    for entry in entries:
        merchant = entry["merchant"]
        if kinds.get(merchant) == "ores":
            # One 【矿类】 group for every pure refining recipe.
            entry["group"] = ORE_MERCHANT
            entry["group_kind"] = "ores"
            entry["group_parts"] = []
            grouped.append(entry)
        elif merchant in _EQUIPMENT_MERCHANTS and entry["category_key"] and _part_keys(entry):
            # Equipment NPCs: classify by item category + part, like 【掉落表】.
            # An item that belongs to several weapon types is listed with each of
            # them, exactly like the 【掉落表】 page does.
            for part in _part_keys(entry):
                clone = dict(entry)
                clone["group"] = _GROUP_SEPARATOR.join([entry["category_key"], part])
                clone["group_kind"] = "category"
                clone["group_category"] = _key_label(resolve_name, entry["category_key"])
                clone["group_parts"] = [_key_label(resolve_name, part)]
                grouped.append(clone)
        else:
            if (merchant, entry["name"]) in split_items or len(family_items[(merchant, entry["signature"])]) == 1:
                # Grouping would not merge anything, so the item names the section.
                entry["group"] = entry["name"]
                entry["group_kind"] = "item"
                entry["group_parts"] = [label(entry["name"])]
            else:
                entry["group"] = " + ".join(entry["signature"])
                entry["group_kind"] = "material"
                entry["group_parts"] = [label(material) for material in entry["signature"]]
            grouped.append(entry)

    entries = grouped
    _order_equipment_sections(entries)

    entries.sort(
        key=lambda entry: (
            merchant_order.get(entry["merchant"], 0),
            entry["merchant"],
            entry["group"],
            entry["name"],
            RARITY_ORDER.get(entry["rarity"], 99),
            entry["unique_id"],
        )
    )
    for entry in entries:
        entry.pop("signature")
        entry.pop("category_key")
        entry.pop("subtype_keys")
        entry.pop("item_type")
        entry.pop("slot_key")

    merchant_entries = []
    for row in merchants:
        merchant_name = row["merchant_name"]
        owned = [entry for entry in entries if entry["merchant"] == merchant_name]
        if not owned:
            continue
        merchant_entries.append(
            {
                "name": merchant_name,
                "kind": row["kind"],
                "translation_key": row["translation_key"],
                "display": (
                    resolve_name(merchant_name, row["translation_key"], "merchant") if row["translation_key"] else ""
                ),
                "group_count": len({entry["group"] for entry in owned}),
                "item_count": len({entry["name"] for entry in owned}),
                "recipe_count": len({entry["recipe_id"] for entry in owned}),
            }
        )

    payload = {
        "count": len(merchant_entries),
        "group_count": len({(entry["merchant"], entry["group"]) for entry in entries}),
        "item_count": len({(entry["merchant"], entry["name"]) for entry in entries}),
        "recipe_count": len({entry["recipe_id"] for entry in entries}),
        "ores_merchant": ORE_MERCHANT,
        # Random stat pools, once per pool asset instead of once per recipe.
        "property_pools": {
            pool_name: _property_entries(property_pools[pool_name], resolve_name, with_chance=True)
            for pool_name in dict.fromkeys(
                (entry.get("properties") or {}).get("random", {}).get("pool") for entry in entries
            )
            if pool_name
        },
        "merchants": merchant_entries,
        "recipes": entries,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "crafts.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return payload
