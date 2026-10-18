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

Equipment NPCs (Armourer/Smith/Tailor/Leathersmith) are classified with the same
item taxonomy the 【掉落表】 page uses instead: every material family there holds
a single item, so the sections are the game's item category + subtype (护甲 /
板甲…), which is what a player looks for.

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

#: Equipment NPCs that each craft one armour class, so a material family never
#: merges anything: they are classified by item category + subtype instead (the
#: same taxonomy as the 【掉落表】 page).
_CATEGORY_MERCHANTS = frozenset({"Armourer", "Tailor", "Leathersmith"})

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


def _key_label(resolve_name, key: str) -> dict:
    """Label for a raw game translation key (item category / subtype)."""
    return {"name": key, "translation": resolve_name("", key, "item"), "translation_key": key}


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
) -> dict:
    """Build ``crafts.json`` from DB rows. Returns the payload."""
    label = _ItemLabel(items, resolve_name)
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

    for entry in entries:
        merchant = entry["merchant"]
        if kinds.get(merchant) == "ores":
            # One 【矿类】 group for every pure refining recipe.
            entry["group"] = ORE_MERCHANT
            entry["group_kind"] = "ores"
            entry["group_parts"] = []
        elif merchant in _CATEGORY_MERCHANTS and entry["category_key"] and entry["subtype_keys"]:
            # Equipment NPCs: classify by item category + subtype like 【掉落表】.
            category = _category_name(entry["category_key"])
            order = _CATEGORY_ORDER.index(category) if category in _CATEGORY_ORDER else len(_CATEGORY_ORDER)
            entry["group"] = _GROUP_SEPARATOR.join([str(order), entry["category_key"], *entry["subtype_keys"]])
            entry["group_kind"] = "category"
            entry["group_category"] = _key_label(resolve_name, entry["category_key"])
            entry["group_parts"] = [_key_label(resolve_name, key) for key in entry["subtype_keys"]]
        elif (merchant, entry["name"]) in split_items or len(family_items[(merchant, entry["signature"])]) == 1:
            # Grouping would not merge anything, so the item names the section.
            entry["group"] = entry["name"]
            entry["group_kind"] = "item"
            entry["group_parts"] = [label(entry["name"])]
        else:
            entry["group"] = " + ".join(entry["signature"])
            entry["group_kind"] = "material"
            entry["group_parts"] = [label(material) for material in entry["signature"]]

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
                "recipe_count": len(owned),
            }
        )

    payload = {
        "count": len(merchant_entries),
        "group_count": len({(entry["merchant"], entry["group"]) for entry in entries}),
        "item_count": len({(entry["merchant"], entry["name"]) for entry in entries}),
        "recipe_count": len(entries),
        "ores_merchant": ORE_MERCHANT,
        "merchants": merchant_entries,
        "recipes": entries,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "crafts.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return payload
