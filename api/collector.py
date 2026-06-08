import json
import re
from collections import defaultdict
from pathlib import Path

from config import DB_PATH, OUTPUT_DIR
from db_manager import DatabaseManager
from search_engine import build_all_matches

_VARIANT_RE = re.compile(r"^(.+)_\d{4}$")


def run():
    print("=" * 50)
    print("  DarkFindV5 - Data Collector")
    print("=" * 50)

    db = DatabaseManager(DB_PATH)

    # 1. Import translations
    print("\n[1/7] Importing translations...")
    count = db.import_translations()
    print(f"  -> {count} translations loaded")

    # 2. Import items
    print("[2/7] Importing items...")
    count = db.import_items()
    print(f"  -> {count} item entities")

    # 3. Import monsters
    print("[3/7] Importing monsters...")
    count = db.import_monsters()
    print(f"  -> {count} monster entities")

    # 4. Import props
    print("[4/7] Importing props...")
    count = db.import_props()
    print(f"  -> {count} props entities")

    # 5. Import dungeon modules
    print("[5/7] Importing dungeon modules...")
    count = db.import_dungeon_modules()
    print(f"  -> {count} dungeon modules")

    # 6. Import lootdrops (with raw variant names)
    print("[6/7] Importing lootdrop relationships...")
    count = db.import_lootdrops()
    print(f"  -> {count} lootdrop relationships")

    # 7. Build spawner matches via search engine
    print("[7/7] Building spawner matches...")
    items = db.get_item_entities()
    monsters = db.get_monster_entities()
    props = db.get_props_entities()
    search_terms = [r["item_name"] for r in items] + [r["monster_name"] for r in monsters] + [r["asset_name"] for r in props]
    matches, spawners = build_all_matches(search_terms)
    print(f"  -> {len(spawners)} spawners, {len(matches)} matched terms")

    # Store matches in DB
    c = db.connect()
    c.execute("DELETE FROM spawners")
    c.execute("DELETE FROM search_term_matches")
    for idx, s in enumerate(spawners):
        c.execute(
            "INSERT INTO spawners (id, keyword, original_keyword, spawner_type, x, y, z, json_filename, version, map_base) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (idx + 1, s["keyword"], s.get("original_keyword", ""), s["spawner_type"], s["x"], s["y"], s["z"], s["json_filename"], s.get("version", ""), s.get("map_base", "")),
        )
    for term, spawner_ids in matches.items():
        rows = [(term, sid + 1) for sid in spawner_ids]
        c.executemany(
            "INSERT OR IGNORE INTO search_term_matches (search_term, spawner_id) VALUES (?, ?)",
            rows,
        )
    db.connect().commit()

    # ─── Export JSON ───
    print("\nExporting JSON files...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    translations = db.get_translations_map()

    def t(key: str) -> str:
        if not key:
            return ""
        if key in translations:
            return translations[key]
        suffix = key.rsplit("_", 1)[-1]
        return translations.get(suffix, suffix)

    # ── Build merged lootdrop map with variant family merging ──
    loot_raw = db.get_lootdrop_relationships()
    loot_map: dict[str, set[str]] = {}
    for r in loot_raw:
        loot_map.setdefault(r["item_name"], set()).add(r["monster_name"])

    # detect variant families (_\d{4} suffix, ≥2 members)
    families: dict[str, list[str]] = {}
    for item_name in loot_map:
        m = _VARIANT_RE.match(item_name)
        if m:
            base = m.group(1)
            families.setdefault(base, []).append(item_name)
    families = {k: sorted(v) for k, v in families.items() if len(v) >= 2}
    skip_variants: set[str] = set()
    for variants in families.values():
        skip_variants.update(variants)

    # merge: base_name → union of all monsters from its variants
    merged_loot: dict[str, list[str]] = {}
    for item_name, monster_set in loot_map.items():
        m = _VARIANT_RE.match(item_name)
        base = m.group(1) if m else item_name
        merged_loot.setdefault(base, set()).update(monster_set)
    merged_loot = {k: sorted(v) for k, v in merged_loot.items()}
    print(f"  variant families merged: {len(families)} ({len(skip_variants)} variants skipped)")
    print(f"  unique items after merge: {len(merged_loot)}")

    # ── items.json: only items with coordinates, using merged loot ──
    items_data = []
    for r in items:
        name = r["item_name"]
        if name in skip_variants:
            continue
        coords = db.get_item_coordinates(name)
        if not coords:
            continue
        items_data.append({
            "name": name,
            "translation": t(r["translation_key"]),
            "category": r["category"],
            "monsters": merged_loot.get(name, []),
            "coords": [
                {"x": c["x"], "y": c["y"], "z": c["z"], "map": c["map_base"], "file": c["json_filename"], "version": c["version"]}
                for c in coords
            ],
        })
    _save("items.json", items_data)

    # ── monsters.json: only monsters with coordinates ──
    monsters_data = []
    for r in monsters:
        coords = db.get_item_coordinates(r["monster_name"])
        if not coords:
            continue
        monsters_data.append({
            "name": r["monster_name"],
            "translation": t(r["translation_key"]),
            "coords": [
                {"x": c["x"], "y": c["y"], "z": c["z"], "map": c["map_base"], "file": c["json_filename"], "version": c["version"]}
                for c in coords
            ],
        })
    _save("monsters.json", monsters_data)

    # ── props.json: only props with coordinates ──
    props_data = []
    for r in props:
        coords = db.get_item_coordinates(r["asset_name"])
        if not coords:
            continue
        props_data.append({
            "name": r["asset_name"],
            "translation": t(r["translation_key"]),
            "coords": [
                {"x": c["x"], "y": c["y"], "z": c["z"], "map": c["map_base"], "file": c["json_filename"], "version": c["version"]}
                for c in coords
            ],
        })
    _save("props.json", props_data)

    # ── dungeon_modules.json ──
    modules = db.get_dungeon_modules()
    modules_data = [{
        "name": r["module_name"],
        "translation": t(r["translation_key"]),
        "group": r["module_group"],
        "size_x": r["size_x"],
        "size_y": r["size_y"],
        "sl_base_name": r["sl_base_name"],
    } for r in modules]
    _save("dungeon_modules.json", modules_data)

    # ── lootdrops.json ──
    loot_out = []
    for item_name, monster_names in merged_loot.items():
        for mon in monster_names:
            loot_out.append({"item_name": item_name, "monster_name": mon})
    _save("lootdrops.json", loot_out)

    # ── index.json: page index ──
    index_data = [
        {"page": "items", "label": "物品表", "count": len(items_data)},
        {"page": "monsters", "label": "怪物表", "count": len(monsters_data)},
        {"page": "props", "label": "实体表", "count": len(props_data)},
        {"page": "dungeon_modules", "label": "模块表", "count": len(modules_data)},
        {"page": "lootdrops", "label": "掉落关系", "count": len(loot_out)},
    ]
    _save("index.json", index_data)

    print(f"\n[DONE] Output written to {OUTPUT_DIR}")
    for entry in index_data:
        print(f"  {entry['page']}: {entry['count']}")

    db.close()


def _save(filename: str, data: list):
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
