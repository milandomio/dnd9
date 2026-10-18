"""Export tavern crafting recipes for the 【工匠】 page.

The importer stores one row per StockCraft recipe in ``craft_recipes``; this
export only reads the DB, so CI builds (which have no game extract) stay DB-only.
Names come from ``item_entities`` translation keys; the zh-Hans label is embedded
because the default language does not load the locale dictionary on the client.

Recipes are ordered by merchant, then by folded output item (so every quality
tier of one item sits together), then by rarity: the page groups consecutive
rows with the same item name.
"""

import json
from pathlib import Path

from db.importers.crafts import INGOT_MERCHANT

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


def _resolve_item(name: str, item_meta: dict[str, dict], resolve_name) -> tuple[str, str]:
    """(translation, translation_key) for a folded item name."""
    translation_key = item_meta.get(name, {}).get("translation_key", "")
    if not translation_key:
        translation_key = f"Text_DesignData_Item_Item_{name}"
    return resolve_name(name, translation_key, "item"), translation_key


def build_and_save_crafts(
    merchants,
    recipes,
    items,
    resolve_name,
    output_dir: Path,
) -> dict:
    """Build ``crafts.json`` from DB rows. Returns the payload."""
    item_meta = {r["item_name"]: r for r in items}
    merchant_order = {row["merchant_name"]: row["sort_order"] for row in merchants}

    entries: list[dict] = []
    for row in recipes:
        name = row["output_item_name"]
        translation, translation_key = _resolve_item(name, item_meta, resolve_name)
        requirements = []
        for requirement in json.loads(row["requirements_json"] or "[]"):
            req_translation, req_translation_key = _resolve_item(requirement["name"], item_meta, resolve_name)
            requirements.append(
                {
                    "name": requirement["name"],
                    "raw_name": requirement["raw_name"],
                    "translation": req_translation,
                    "translation_key": req_translation_key,
                    "rarity": requirement.get("rarity", ""),
                    "amount": requirement.get("amount", 1),
                }
            )
        entries.append(
            {
                "merchant": row["merchant_name"],
                "recipe_id": row["recipe_id"],
                "unique_id": row["unique_id"],
                "name": name,
                "raw_name": row["output_raw_name"],
                "translation": translation,
                "translation_key": translation_key,
                "rarity": row["output_rarity"],
                "requirements": requirements,
            }
        )

    entries.sort(
        key=lambda entry: (
            merchant_order.get(entry["merchant"], 0),
            entry["merchant"],
            entry["name"],
            RARITY_ORDER.get(entry["rarity"], 99),
            entry["unique_id"],
        )
    )

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
                "item_count": len({entry["name"] for entry in owned}),
                "recipe_count": len(owned),
            }
        )

    payload = {
        "count": len(merchant_entries),
        "item_count": len({(entry["merchant"], entry["name"]) for entry in entries}),
        "recipe_count": len(entries),
        "ingot_merchant": INGOT_MERCHANT,
        "merchants": merchant_entries,
        "recipes": entries,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "crafts.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return payload
