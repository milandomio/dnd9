import json
import re
from collections import defaultdict
from pathlib import Path

from config import DB_PATH, OUTPUT_DIR, HARDCODED_TRANSLATIONS, MODULE_DISPLAY_OVERRIDE, MODULE_NAME_OVERRIDE, MODULE_OFFSET_MAP, TRANSLATION_ALIAS_MAP
from db_manager import DatabaseManager
from search_engine import build_all_matches
from layout_utils import load_all_layout_rotations
from quest_collector import run_quest_extraction

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

    def resolve_name(name: str, translation_key: str, scope: str = "item") -> str:
        if translation_key and translation_key in translations:
            return translations[translation_key]
        alias_name = TRANSLATION_ALIAS_MAP.get(name, name)
        if alias_name != name:
            for prefix in [
                "Text_DesignData_Item_Item_",
                "Text_DesignData_Monster_Monster_",
                "Text_DesignData_Props_Props_",
                "Text_DesignData_Dungeon_DungeonModule_",
            ]:
                alias_key = prefix + alias_name
                if alias_key in translations:
                    return translations[alias_key]
        if name in HARDCODED_TRANSLATIONS:
            return HARDCODED_TRANSLATIONS[name]
        if scope == "module" and name in MODULE_NAME_OVERRIDE:
            return MODULE_NAME_OVERRIDE[name]
        return name

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

    # ── items: index + individual files ──
    items_index = []
    for r in items:
        name = r["item_name"]
        if name in skip_variants:
            continue
        coords = db.get_item_coordinates(name)
        if not coords:
            continue
        translation = resolve_name(name, r["translation_key"], "item")
        items_index.append({
            "name": name,
            "translation": translation,
            "category": r["category"],
            "monsters": merged_loot.get(name, []),
            "coordCount": len(coords),
        })
        _save(f"items/{name}.json", {
            "name": name,
            "translation": translation,
            "category": r["category"],
            "monsters": merged_loot.get(name, []),
            "coords": [
                {"x": c["x"], "y": c["y"], "z": c["z"], "map": c["map_base"], "file": c["json_filename"], "version": c["version"], "label": c["original_keyword"]}
                for c in coords
            ],
        })
    _save("items.json", items_index)

    # ── monsters: index + individual files ──
    monsters_index = []
    for r in monsters:
        coords = db.get_item_coordinates(r["monster_name"])
        if not coords:
            continue
        translation = resolve_name(r["monster_name"], r["translation_key"], "monster")
        monsters_index.append({
            "name": r["monster_name"],
            "translation": translation,
            "coordCount": len(coords),
        })
        _save(f"monsters/{r['monster_name']}.json", {
            "name": r["monster_name"],
            "translation": translation,
            "coords": [
                {"x": c["x"], "y": c["y"], "z": c["z"], "map": c["map_base"], "file": c["json_filename"], "version": c["version"], "label": c["original_keyword"]}
                for c in coords
            ],
        })
    _save("monsters.json", monsters_index)

    # ── props: index + individual files (merged by translation) ──
    props_index = []
    props_by_translation: dict[str, list[dict]] = {}
    for r in props:
        translation = resolve_name(r["asset_name"], r["translation_key"], "props")
        props_by_translation.setdefault(translation, []).append(r)
    for translation, group in props_by_translation.items():
        merged_coords = []
        for r in group:
            coords = db.get_item_coordinates(r["asset_name"])
            merged_coords.extend(coords)
        if not merged_coords:
            continue
        name_key = group[0]["asset_name"]
        props_index.append({
            "name": name_key,
            "translation": translation,
            "coordCount": len(merged_coords),
        })
        _save(f"props/{name_key}.json", {
            "name": name_key,
            "translation": translation,
            "coords": [
                {"x": c["x"], "y": c["y"], "z": c["z"], "map": c["map_base"], "file": c["json_filename"], "version": c["version"], "label": c["original_keyword"]}
                for c in merged_coords
            ],
        })
    _save("props.json", props_index)

    # ── dungeon_modules.json ──
    module_rotations = load_all_layout_rotations()
    modules = db.get_dungeon_modules()
    art_root = Path(__file__).parent.parent.parent / "Output" / "Exports" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Art" / "DungeonModuleMapImage"
    modules_map: dict[str, dict] = {}
    for r in modules:
        override = MODULE_DISPLAY_OVERRIDE.get(r["module_name"], {})
        sx = override.get("size_x", r["size_x"])
        sy = override.get("size_y", r["size_y"])
        custom_range = override.get("range", 0)
        offset_x, offset_y = MODULE_OFFSET_MAP.get(r["module_name"], (0, 0))
        rotate = module_rotations.get(r["sl_base_name"], 1)
        sl = r["sl_base_name"]
        img_name = _resolve_img(art_root, r["module_group"], sl)
        modules_map[r["module_name"]] = {
            "name": r["module_name"],
            "translation": resolve_name(r["module_name"], r["translation_key"], "module"),
            "group": r["module_group"],
            "size_x": sx,
            "size_y": sy,
            "sl_base_name": sl,
            "img_name": img_name,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "rotate": rotate,
            "range": custom_range,
        }
    for override_name, override_translation in MODULE_NAME_OVERRIDE.items():
        if override_name not in modules_map:
            modules_map[override_name] = {
                "name": override_name,
                "translation": override_translation,
                "group": "",
                "size_x": 1,
                "size_y": 1,
                "sl_base_name": override_name,
                "img_name": _resolve_img(art_root, "", override_name),
                "offset_x": 0,
                "offset_y": 0,
                "rotate": 1,
                "range": 0,
            }
    modules_data = sorted(modules_map.values(), key=lambda x: x["name"])
    _save("dungeon_modules.json", modules_data)

    # ── lootdrops.json (grouped by item for list page) ──
    items_lookup = {r["item_name"]: r for r in items}
    monsters_lookup = {r["monster_name"]: r for r in monsters}
    loot_index = []
    for item_name, monster_names in merged_loot.items():
        item_row = items_lookup.get(item_name)
        translation = resolve_name(item_name, item_row["translation_key"] if item_row else None, "item") if item_row else (resolve_name(item_name, None, "item") or item_name)
        mon_translations = []
        for m in sorted(monster_names):
            mon_row = monsters_lookup.get(m)
            mon_translations.append(resolve_name(m, mon_row["translation_key"] if mon_row else None, "monster") if mon_row else (resolve_name(m, None, "monster") or m))
        loot_index.append({
            "name": item_name,
            "translation": translation,
            "monsters": sorted(monster_names),
            "monster_translations": mon_translations,
        })
    loot_index.sort(key=lambda x: x["translation"] or x["name"])
    _save("lootdrops.json", loot_index)

    # ── lootdrops detail files ──
    _MONSTER_COLORS = ["#E74C3C","#3498DB","#2ECC71","#F39C12","#9B59B6","#1ABC9C","#E67E22","#2980B9","#27AE60","#D35400","#8E44AD","#16A085","#C0392B","#2C3E50","#7F8C8D","#FF6B35","#00BFFF","#FFD700","#FF69B4","#32CD32","#FF4500","#9370DB","#00FA9A","#DC143C","#00CED1"]
    monster_coord_cache: dict[str, list] = {}
    for entry in loot_index:
        item_name = entry["name"]
        monsters_out = []
        for i, m_name in enumerate(entry["monsters"]):
            if m_name not in monster_coord_cache:
                monster_coord_cache[m_name] = db.get_item_coordinates(m_name)
            coords = monster_coord_cache[m_name]
            if not coords:
                continue
            m_trans = entry["monster_translations"][entry["monsters"].index(m_name)]
            monsters_out.append({
                "name": m_name,
                "translation": m_trans,
                "color": _MONSTER_COLORS[i % len(_MONSTER_COLORS)],
                "coords": [
                    {"x": c["x"], "y": c["y"], "z": c["z"], "map": c["map_base"], "file": c["json_filename"], "version": c["version"]}
                    for c in coords
                ],
            })
        if monsters_out:
            _save(f"lootdrops/{item_name}.json", {
                "name": item_name,
                "translation": entry["translation"],
                "monsters": monsters_out,
            })

    # ── Quest extraction ──
    print("\nExtracting quest data...")
    explore_count, quest_items_count, quest_npc_count = run_quest_extraction()

    # ── index.json: page index ──
    index_data = [
        {"page": "items", "label": "物品表", "count": len(items_index)},
        {"page": "monsters", "label": "怪物表", "count": len(monsters_index)},
        {"page": "props", "label": "实体表", "count": len(props_index)},
        {"page": "lootdrops", "label": "掉落表", "count": len(loot_index)},
        {"page": "explore", "label": "探索地点表", "count": explore_count},
        {"page": "quest_items", "label": "任务物品表", "count": quest_items_count},
        {"page": "quest_npc", "label": "任务NPC表", "count": quest_npc_count},
    ]
    _save("index.json", index_data)

    print(f"\n[DONE] Output written to {OUTPUT_DIR}")
    for entry in index_data:
        print(f"  {entry['page']}: {entry['count']}")

    db.close()


def _resolve_img(art_root: Path, group: str, sl: str) -> str:
    if not art_root.exists() or not group:
        return sl
    group_dir = art_root / group
    if not group_dir.exists():
        return sl
    png = group_dir / f"{sl}.png"
    if png.exists():
        return sl
    for p in group_dir.iterdir():
        if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl.lower():
            return p.stem
    tail = sl.split("_", 1)[-1] if "_" in sl else sl
    png = group_dir / f"{tail}.png"
    if png.exists():
        return tail
    for p in group_dir.iterdir():
        if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == tail.lower():
            return p.stem
    return sl


def _save(filename: str, data: list | dict):
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
