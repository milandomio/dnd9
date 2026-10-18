"""Export tavern crafting recipes for the 【工匠】 page.

The importer stores one row per StockCraft recipe in ``craft_recipes``; this
export only reads the DB, so CI builds (which have no game extract) stay DB-only.
Names come from ``item_entities`` translation keys; the zh-Hans label is embedded
because the default language does not load the locale dictionary on the client.

Recipes are grouped by the material that identifies their family, so recipes
built from the same thing sit together instead of one section per item:

* ``SilverPowder`` -> the seven 【纯银】 weapons of the Weaponsmith;
* ``IronIngots``  -> the nine iron-only weaponsmith items;
* ``BlueSapphire + ArcaneEssence`` -> the Goldsmith's sapphire jewellery;
* the synthetic 【矿类】 tab (pure ore/coin refining) is a single group.

An item whose quality tiers consume *different* materials (SurgicalKit) cannot
sit in one material group without splitting the tiers apart, so it keeps its own
item group; the same holds for every other multi-tier item as a safety net.
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


def _signature(requirements: list[dict]) -> tuple[str, ...]:
    """The material names that identify a recipe family, sorted."""
    names = [requirement["name"] for requirement in requirements]
    distinctive = [name for name in names if name not in _CURRENCIES]
    return tuple(sorted(set(distinctive or names)))


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
        entries.append(entry)

    # Items whose tiers need different materials keep an item group so every
    # quality tier of one item still renders together.
    signatures: dict[tuple[str, str], set[tuple[str, ...]]] = {}
    for entry in entries:
        signatures.setdefault((entry["merchant"], entry["name"]), set()).add(entry["signature"])
    split_items = {key for key, found in signatures.items() if len(found) > 1 and kinds.get(key[0]) != "ores"}

    for entry in entries:
        if kinds.get(entry["merchant"]) == "ores":
            # One 【矿类】 group for every pure refining recipe.
            entry["group"] = ORE_MERCHANT
            entry["group_parts"] = []
        elif (entry["merchant"], entry["name"]) in split_items:
            entry["group"] = entry["name"]
            entry["group_parts"] = [label(entry["name"])]
        else:
            entry["group"] = " + ".join(entry["signature"])
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
