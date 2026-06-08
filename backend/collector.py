import json
from pathlib import Path

from config import DB_PATH, OUTPUT_DIR
from db_manager import DatabaseManager
from search_engine import build_all_matches


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

    # 6. Import lootdrops
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

    # ── items.json: items with coordinates ──
    items_with_matches = db.get_items_with_matches()
    items_data = []
    for r in items_with_matches:
        coords = db.get_item_coordinates(r["item_name"])
        item = {
            "name": r["item_name"],
            "translation": t(r["translation_key"]),
            "category": r["category"],
            "monsters": r["monster_names"],
            "coords": [
                {
                    "x": c["x"],
                    "y": c["y"],
                    "z": c["z"],
                    "map": c["map_base"],
                    "file": c["json_filename"],
                    "version": c["version"],
                }
                for c in coords
            ],
        }
        items_data.append(item)
    _save("items.json", items_data)

    # ── monsters.json ──
    monsters_data = [{"name": r["monster_name"], "translation": t(r["translation_key"])} for r in monsters]
    _save("monsters.json", monsters_data)

    # ── props.json ──
    props_data = [{"name": r["asset_name"], "translation": t(r["translation_key"])} for r in props]
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
    loot = db.get_lootdrop_relationships()
    _save("lootdrops.json", loot)

    # ── index.json: page index ──
    index_data = [
        {"page": "items", "label": "物品表", "count": len(items_data)},
        {"page": "monsters", "label": "怪物表", "count": len(monsters_data)},
        {"page": "props", "label": "实体表", "count": len(props_data)},
        {"page": "dungeon_modules", "label": "模块表", "count": len(modules_data)},
        {"page": "lootdrops", "label": "掉落关系", "count": len(loot)},
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
