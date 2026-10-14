"""Export Goblin Smuggler (InGameMerchant) shop data to frontend JSON.

Layout mirrors the dungeon-module pages: one index file listing every region,
plus a per-region detail file holding the merchant's stock.

Region ordering and labels come from the existing dungeon-group helpers so the
shop pages read the same region names as the module pages (哥布林洞穴 / 寒冰洞穴 /
废墟地穴).
"""

import json
from pathlib import Path

from consumable_effects import resolve_item_effects
from monster_drops_builder import fold_item_page

# Merchant variant regions -> the single dungeon-floor label that names that
# region to players (matching the in-game map names, not the module-group
# composite label like "废墟2层（地穴）").
REGION_LABEL_KEY = {
    "Crypts": "Text_UI_WB_DungeonSlot_TheCrypts_2ndFloor",
    "Goblin": "Text_UI_WB_DungeonSlot_GoblinCave_1stFloor",
    "IceCavern": "Text_UI_WB_DungeonSlot_IceCavern_1stFloor",
}

# Region display order on the index page.
REGION_ORDER = ["Crypts", "Goblin", "IceCavern"]

DIFFICULTY_ORDER = ["N", "HR"]

# Item quality suffix -> rarity key, matching the lootdrop pages.
SUFFIX_RARITY = {
    "1001": "Poor",
    "2001": "Common",
    "3001": "Uncommon",
    "4001": "Rare",
    "5001": "Epic",
    "6001": "Legend",
    "7001": "Unique",
    "8001": "Artifact",
}

# Slot 8 and 9 hold byte-identical pools (the game rolls the same material table
# twice); they are merged into one row group so the table is not duplicated.
MATERIAL_SLOT_GROUP = (8, 9)


def _slot_label(difficulty: str, slot: int) -> str:
    return f"{difficulty}_{slot:02d}"


def build_shop_data(
    merchant_data: dict[str, list[dict]],
    translations: dict[str, str],
    item_index: dict[str, dict],
    region_labels: dict[str, str],
    effect_index: dict[str, dict] | None = None,
    item_ability_dir: Path | None = None,
) -> dict[str, object]:
    """Assemble the index + per-region shop payloads.

    ``item_index`` maps an item page name to ``{"page", "translation",
    "translation_key"}`` so items link to their lootdrop detail page.

    Merchants also carry resolved ``display`` / ``greeting`` values: the default
    language does not load the locale dictionary on the client, so anything the
    UI must show in zh-Hans has to travel inside the JSON.
    """
    # Consumables keep their numbers in gameplay-effect assets rather than in the
    # item JSON, so resolve them once for every item the shop sells.
    item_effects: dict[str, dict] = {}
    if effect_index and item_ability_dir:
        sold = {row["item_name"] for row in merchant_data["stock"]}
        item_effects = resolve_item_effects(sold, effect_index, item_ability_dir)

    merchants = {}
    for m in merchant_data["merchants"]:
        entry = dict(m)
        entry["display"] = translations.get(m["translation_key"], m["merchant_name"])
        entry["greeting"] = translations.get(m["greeting_key"], "")
        merchants[m["merchant_name"]] = entry
    variants = merchant_data["variants"]
    stock = merchant_data["stock"]

    by_variant: dict[str, list[dict]] = {}
    for row in stock:
        by_variant.setdefault(row["variant_id"], []).append(row)

    # Group rows per region so cross-region exclusives can be detected. Compare
    # by folded item name: Ruby_4001 and Ruby_7001 are the same item at different
    # quality tiers, so a tier difference alone is not a region exclusive.
    region_items: dict[str, set[str]] = {}
    for variant in variants:
        region = variant["region"]
        for row in by_variant.get(variant["variant_id"], []):
            region_items.setdefault(region, set()).add(fold_item_page(row["item_name"])[0])

    regions: list[dict] = []
    detail_by_region: dict[str, dict] = {}

    for region in sorted(
        {v["region"] for v in variants},
        key=lambda r: REGION_ORDER.index(r) if r in REGION_ORDER else len(REGION_ORDER),
    ):
        other_items: set[str] = set()
        for other, names in region_items.items():
            if other != region:
                other_items |= names

        difficulties: list[dict] = []
        for difficulty in DIFFICULTY_ORDER:
            variant_id = next(
                (v["variant_id"] for v in variants if v["region"] == region and v["difficulty"] == difficulty),
                "",
            )
            if not variant_id:
                continue
            rows = by_variant.get(variant_id, [])

            # Per-slot weight totals. A slot rolls once, so an item's chance is
            # its rate divided by the total rate of the pool it belongs to.
            slot_totals: dict[int, int] = {}
            for row in rows:
                slot_totals[row["slot_index"]] = slot_totals.get(row["slot_index"], 0) + row["item_rate"]

            # Group rows into display slots. Slots 8 and 9 hold identical pools
            # (the game rolls the same material table twice), so they share one
            # display slot; an item's chance is then the union over both rolls.
            slots: dict[str, dict] = {}
            for row in rows:
                slot_index = row["slot_index"]
                display_slot = MATERIAL_SLOT_GROUP[0] if slot_index in MATERIAL_SLOT_GROUP else slot_index
                entry = slots.setdefault(_slot_label(difficulty, display_slot), {"slot": display_slot, "items": {}})
                existing = entry["items"].get(row["item_name"])
                if existing is not None:
                    # Second roll of the same pool: accumulate the combined odds
                    # instead of dropping the duplicate.
                    existing["_miss"] *= 1 - (
                        row["item_rate"] / slot_totals[slot_index] if slot_totals[slot_index] else 0
                    )
                    continue
                # Entity detail pages are keyed by the folded item name
                # (HealingPotion_5001 -> HealingPotion); artifacts (_8001) keep
                # their suffix.
                page, suffix = fold_item_page(row["item_name"])
                item_meta = item_index.get(page, item_index.get(row["item_name"], {}))
                translation = item_meta.get("translation", "")
                translation_key = item_meta.get("translation_key", "")
                if not translation:
                    # Shop-only goods (LuckPotion) never appear in the lootdrop
                    # index, so fall back to the official Game.json item key.
                    fallback_key = f"Text_DesignData_Item_Item_{page}"
                    if fallback_key in translations:
                        translation = translations[fallback_key]
                        translation_key = fallback_key
                total = slot_totals.get(slot_index, 0)
                chance = row["item_rate"] / total if total else 0.0
                entry["items"][row["item_name"]] = {
                    "name": row["item_name"],
                    "page": item_meta.get("page", page),
                    "translation": translation,
                    "translation_key": translation_key,
                    "price": row["price"],
                    "currency": row["currency"],
                    "count": row["item_count"],
                    "stock": row["stock"],
                    "rate": row["item_rate"],
                    "slot_total": total,
                    "chance": chance,
                    "rarity": SUFFIX_RARITY.get(suffix or "", ""),
                    "map_exclusive": page not in other_items,
                    "effect": item_effects.get(row["item_name"]),
                    "_miss": 1 - chance,
                }

            ordered = sorted(slots.items(), key=lambda kv: kv[1]["slot"])
            for _, entry in ordered:
                items = list(entry["items"].values())
                for item in items:
                    # Fold the per-roll misses into the final chance, then drop
                    # the scratch field so it never reaches the JSON payload.
                    item["chance"] = 1 - item.pop("_miss")
                items.sort(key=lambda i: (-(i["price"] or 0), i["name"]))
                entry["items"] = items
                entry["chance_total"] = sum(i["chance"] for i in items)
            # Per-difficulty totals. Counted by folded base name so the number
            # matches what the page renders; the raw count differs because the
            # same item appears at several quality tiers (Ruby_4001/5001/6001).
            difficulty_pages = {fold_item_page(row["item_name"])[0] for row in rows}
            difficulty_exclusive = sorted(name for name in difficulty_pages if name not in other_items)
            difficulties.append(
                {
                    "difficulty": difficulty,
                    "variant_id": variant_id,
                    "slots": [entry for _, entry in ordered],
                    "item_count": len({row["item_name"] for row in rows}),
                    "base_item_count": len(difficulty_pages),
                    "exclusive_count": len(difficulty_exclusive),
                }
            )

        exclusive = sorted(name for name in region_items.get(region, set()) if name not in other_items)
        label_key = REGION_LABEL_KEY.get(region, "")
        # Card count across difficulties (HR usually has a few more tiers). The
        # list page and the detail header both show this, so they never disagree;
        # `base_item_count` is the folded, de-duplicated figure.
        card_count = max((d["item_count"] for d in difficulties), default=0)
        region_base_count = max((d["base_item_count"] for d in difficulties), default=0)
        regions.append(
            {
                "region": region,
                "label_key": label_key,
                "display": region_labels.get(region, region),
                "item_count": card_count,
                "base_item_count": region_base_count,
                "exclusive_count": len(exclusive),
            }
        )
        detail_by_region[region] = {
            "region": region,
            "label_key": label_key,
            "display": region_labels.get(region, region),
            "merchant": merchants.get("GoblinSmuggler", {}),
            "exclusive_count": len(exclusive),
            "total_items": card_count,
            "base_item_count": region_base_count,
            "difficulties": difficulties,
        }

    payload = {
        "merchants": list(merchants.values()),
        "regions": regions,
    }
    return {"index": payload, "details": detail_by_region}


def save_shop_data(data: dict[str, object], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    index = data["index"]
    (output_dir / "dungeon_shops.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    details: dict[str, dict] = data["details"]  # type: ignore[assignment]
    detail_dir = output_dir / "dungeon_shops"
    detail_dir.mkdir(parents=True, exist_ok=True)
    for region, payload in details.items():
        (detail_dir / f"{region}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
    return index
