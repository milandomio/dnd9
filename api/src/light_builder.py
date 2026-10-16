"""Export light-source items (FuelSeconds + LightAreaRadius) for the 【灯】 page.

The importer stores one row per quality variant in ``light_items``; this export
only reads the DB, so CI builds (which have no game extract) stay DB-only.
Names come from ``item_entities`` translation keys; the zh-Hans label is embedded
because the default language does not load the locale dictionary on the client.
"""

import json
from pathlib import Path

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


def _sort_key(entry: dict) -> tuple:
    return (
        entry["name"],
        RARITY_ORDER.get(entry["rarity"], 99),
        entry["fuel_seconds"],
        entry["light_area_radius"],
    )


def build_and_save_lights(rows, environment_rows, items, resolve_name, output_dir: Path) -> dict:
    """Build ``lights.json`` from DB rows. Returns the payload."""
    meta = {r["item_name"]: r for r in items}
    entries: list[dict] = []
    for row in rows:
        name = row["item_name"]
        item = meta.get(name, {})
        translation_key = item.get("translation_key", "")
        entries.append(
            {
                "name": name,
                "translation": resolve_name(name, translation_key, "item"),
                "translation_key": translation_key,
                "raw_name": row["raw_name"],
                "rarity": row["rarity"],
                "fuel_seconds": row["fuel_seconds"],
                "light_area_radius": row["light_area_radius"],
            }
        )
    entries.sort(key=_sort_key)

    environment: list[dict] = []
    for row in environment_rows:
        name = row["item_name"]
        translation_key = row["translation_key"]
        environment.append(
            {
                "name": name,
                "translation": resolve_name(name, translation_key, "props"),
                "translation_key": translation_key,
                "raw_name": row["raw_name"],
                "fuel_seconds": row["fuel_seconds"],
                "fuel_seconds_max": row["fuel_seconds_max"],
                "only_in_swarm": bool(row["only_in_swarm"]),
            }
        )
    environment.sort(key=lambda entry: (entry["name"], entry["raw_name"]))

    payload = {
        "count": len({entry["name"] for entry in entries}),
        "items": entries,
        "environment_count": len({entry["translation_key"] for entry in environment}),
        "environment": environment,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "lights.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return payload
