import json
import os
import re
from collections import defaultdict
from pathlib import Path

from config import (
    DB_PATH, GAME_JSON, ITEM_DIR, MONSTER_DIR, PROPS_DIR,
    DUNGEON_MODULE_DIR, LOOTDROP_DIR, LOOTDROP_GROUP_DIR,
    SPAWNER_DIR, MAPS_DIR, LAYOUT_DIR,
    OUTPUT_DIR, GAME_ROOT, GROUP_TO_ART_DIR,
    HARDCODED_TRANSLATIONS, MODULE_DISPLAY_OVERRIDE,
    MODULE_NAME_OVERRIDE, MODULE_OFFSET_MAP, TRANSLATION_ALIAS_MAP,
    IMG_SRC,
)
from db_manager import DatabaseManager
from search_engine import build_all_matches
from layout_utils import load_all_layout_rotations
from quest_collector import run_quest_extraction

_VARIANT_RE = re.compile(r"^(.+)_\d{4}$")
_HARD_SUFFIX_RE = re.compile(r"_(Hard|VeryHard)$")
_UNIQUE_SUFFIX_RE = re.compile(r"Unique$")
_QUALITY_RE = re.compile(r"_(Common|Elite|Nightmare|Unique)$")
_ORE_QUALITY_RE = re.compile(r"^(?:Ore_)?(.+?)(?:_(?:High|Med|Low|VeryLow|Random))$")

# Props 目录中的 _Dummy 实体同时也是怪物
_DUMMY_AS_MONSTER = {
    "LivingArmor", "LivingStatue",
    "LivingArmor_Elite", "LivingArmor_Nightmare",
    "LivingStatue_Elite", "LivingStatue_Nightmare",
}


def _build_entity_classification(translations: dict[str, str] | None = None) -> dict[str, dict]:
    """Scan source dirs and return { normalized_name: { types: [str], translation_key: str } }.
    Provides ground truth classification, supporting entities that exist in multiple categories.
    """
    from db_manager import _extract_item_name, _extract_monster_name, _extract_props_name
    classification: dict[str, dict] = {}
    seen_lower: dict[str, str] = {}

    def _key_valid(tk: str) -> bool:
        """key 非空且能在翻译表中解析才视为有效"""
        if not tk:
            return False
        if translations is not None:
            return tk in translations
        return tk.startswith("Text_DesignData_")

    def _scan_dir(directory, prefix_strip_fn, type_label):
        from pathlib import Path
        if not Path(directory).exists():
            return
        for fp in sorted(Path(directory).glob("*.json")):
            raw_name = fp.stem
            name = prefix_strip_fn(raw_name)
            if not name:
                continue
            try:
                with open(fp) as f:
                    data = json.load(f)
            except Exception:
                continue
            if not data:
                continue
            entry = data[0]
            props = (entry.get("Properties") or {}) or {}
            tk = (props.get("Name") or {}).get("Key", "") or ""
            key = name.lower()
            if key not in seen_lower:
                seen_lower[key] = name
                classification[name] = {"types": [type_label], "translation_key": tk}
            else:
                existing_name = seen_lower[key]
                existing = classification[existing_name]
                if type_label not in existing["types"]:
                    existing["types"].append(type_label)
                existing_tk = existing["translation_key"]
                if not _key_valid(existing_tk) and _key_valid(tk):
                    existing["translation_key"] = tk

    _scan_dir(ITEM_DIR, lambda r: _extract_item_name(r), "item")
    _scan_dir(MONSTER_DIR, lambda r: _extract_monster_name(r), "monster")
    _scan_dir(PROPS_DIR, lambda r: _extract_props_name(r), "props")

    # _Dummy 实体同时也是怪物，补全 monster 翻译键
    for name in _DUMMY_AS_MONSTER:
        if name in classification:
            if "monster" not in classification[name]["types"]:
                classification[name]["types"].append("monster")
            if not classification[name]["translation_key"]:
                base = _QUALITY_RE.sub("", name)
                if base != name:
                    monster_key = "Text_DesignData_Monster_Monster_" + base
                    classification[name]["translation_key"] = monster_key
        else:
            base = _QUALITY_RE.sub("", name)
            monster_key = "Text_DesignData_Monster_Monster_" + base
            classification[name] = {"types": ["props", "monster"], "translation_key": monster_key}

    return classification


_SOURCE_PATHS = [
    GAME_JSON, ITEM_DIR, MONSTER_DIR, PROPS_DIR,
    DUNGEON_MODULE_DIR, LOOTDROP_DIR, LOOTDROP_GROUP_DIR,
    SPAWNER_DIR, MAPS_DIR, LAYOUT_DIR,
]


def _get_newest_mtime(paths: list[Path]) -> float:
    """Return the newest modification time across all files in given paths."""
    newest = 0.0
    for p in paths:
        if not p.exists():
            continue
        if p.is_file():
            try:
                mtime = p.stat().st_mtime
                if mtime > newest:
                    newest = mtime
            except OSError:
                continue
        elif p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p):
                for fn in filenames:
                    try:
                        fp = Path(dirpath) / fn
                        mtime = fp.stat().st_mtime
                        if mtime > newest:
                            newest = mtime
                    except OSError:
                        continue
    return newest


def _is_db_stale(db_path: Path) -> bool:
    """Return True if DB is missing or older than any source file."""
    if not db_path.exists():
        return True
    db_mtime = db_path.stat().st_mtime
    latest_source = _get_newest_mtime(_SOURCE_PATHS)
    return db_mtime < latest_source


def run():
    print("=" * 50)
    print("  DarkFindV5 - Data Collector")
    print("=" * 50)

    db_stale = _is_db_stale(DB_PATH)
    if db_stale and DB_PATH.exists():
        DB_PATH.unlink()
    db = DatabaseManager(DB_PATH)

    game_available = GAME_ROOT.exists() and db_stale

    if game_available:
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
        _search_term_set: set[str] = set()
        for r in items:
            _search_term_set.add(r["item_name"])
        for r in monsters:
            _search_term_set.add(r["monster_name"])
        for r in props:
            name = r["asset_name"]
            m = _ORE_QUALITY_RE.match(name)
            if m:
                _search_term_set.add(m.group(1))
            _search_term_set.add(name)
        search_terms = sorted(_search_term_set)
        # Clean ore item names: GoldOres → GoldOre (add stripped form for spawner matching)
        _ORE_ITEM_STRIP_RE = re.compile(r"^(Cobalt|Copper|FrostStone|Gold|Iron|Obsidian|Rubysilver|Tidestone)Ores$")
        for t in list(search_terms):
            m = _ORE_ITEM_STRIP_RE.match(t)
            if m:
                _search_term_set.add(m.group(1) + "Ore")
        search_terms = sorted(_search_term_set)
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
    else:
        if not GAME_ROOT.exists():
            print("\n[SKIP] Game data not found, using existing DB")
        else:
            print("\n[SKIP] DB is up to date (newest source file older than DB), using existing DB")

    # 后续步骤从 DB 读取（无论是否导入，DB 中都有数据）
    items = db.get_item_entities()
    monsters = db.get_monster_entities()
    props = db.get_props_entities()
    all_coords = db.get_all_coordinates()

    # ─── Export JSON ───
    print("\nExporting JSON files...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    translations = db.get_translations_map()

    _RESOLVE_STRIP_RE = re.compile(r"_(?:\d+|Common|Elite|Nightmare|Hard|VeryHard|Unique)$")

    def resolve_name(name: str, translation_key: str, scope: str = "item") -> str:
        if translation_key and translation_key in translations:
            return translations[translation_key]
        alias_name = TRANSLATION_ALIAS_MAP.get(name, name)
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
        # 剥离末尾数字/难度后缀后重试兜底翻译
        stripped = _RESOLVE_STRIP_RE.sub("", name)
        if stripped != name and stripped in HARDCODED_TRANSLATIONS:
            return HARDCODED_TRANSLATIONS[stripped]
        if scope == "module":
            if name in MODULE_NAME_OVERRIDE:
                return MODULE_NAME_OVERRIDE[name]
            for group_prefix in [
                "Firedeep_", "Inferno_", "Crypt_", "Ruins_", "GoblinCave_",
                "Goblin_", "IceCavern_", "IceCave_", "IceAbyss_",
                "ShipGraveyard_", "Shipgraveyard_", "Swamp_", "Cave_",
            ]:
                if name.startswith(group_prefix):
                    stripped = name[len(group_prefix):]
                    if stripped:
                        alias_key = "Text_DesignData_Dungeon_DungeonModule_" + stripped
                        if alias_key in translations:
                            return translations[alias_key]
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
    _ORE_ITEM_COORD_RE = re.compile(r"^(Cobalt|Copper|FrostStone|Gold|Iron|Obsidian|Rubysilver|Tidestone)Ores$")
    items_index = []
    for r in items:
        name = r["item_name"]
        if name in skip_variants:
            continue
        coords = all_coords.get(name, [])
        # Try ore name cleaning: GoldOres → GoldOre
        if not coords:
            m = _ORE_ITEM_COORD_RE.match(name)
            if m:
                coords = all_coords.get(m.group(1) + "Ore", [])
        if not coords:
            continue
        translation = resolve_name(name, r["translation_key"], "item")
        variant_count = r.get("variant_count", 1)
        items_index.append({
            "name": name,
            "translation": translation,
            "category": r["category"],
            "variant_count": variant_count,
            "monsters": merged_loot.get(name, []),
            "coordCount": len(coords),
        })
        _save(f"items/{name}.json", {
            "name": name,
            "translation": translation,
            "category": r["category"],
            "variant_count": variant_count,
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
        coords = all_coords.get(r["monster_name"], [])
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
    _ORE_QUALITY_ORDER = {"VeryLow": 0, "Low": 1, "Med": 2, "High": 3}
    def _ore_quality_key(r):
        m = re.search(r"_(High|Med|Low|VeryLow)$", r["asset_name"])
        return _ORE_QUALITY_ORDER.get(m.group(1), 99) if m else 99
    props_index = []
    props_by_translation: dict[str, list[dict]] = {}
    for r in sorted(props, key=_ore_quality_key):
        translation = resolve_name(r["asset_name"], r["translation_key"], "props")
        props_by_translation.setdefault(translation, []).append(r)
    for translation, group in props_by_translation.items():
        merged_coords = []
        for r in group:
            coords = all_coords.get(r["asset_name"], [])
            merged_coords.extend(coords)
        # Also try matching via cleaned ore name
        if not merged_coords:
            for r in group:
                m = _ORE_QUALITY_RE.match(r["asset_name"])
                if m:
                    coords = all_coords.get(m.group(1), [])
                    merged_coords.extend(coords)
                    if merged_coords:
                        break
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
    art_root = Path(__file__).parent.parent.parent.parent / "Output" / "Exports" / "DungeonCrawler" / "Content" / "DungeonCrawler" / "Data" / "Art" / "DungeonModuleMapImage"
    modules_map: dict[str, dict] = {}
    for r in modules:
        override = MODULE_DISPLAY_OVERRIDE.get(r["module_name"], {})
        sx = override.get("size_x", r["size_x"])
        sy = override.get("size_y", r["size_y"])
        custom_range = override.get("range", 0)
        offset_x, offset_y = MODULE_OFFSET_MAP.get(r["module_name"], (0, 0))
        rot1 = module_rotations.get(r["module_name"])
        rotate = rot1 if rot1 is not None else module_rotations.get(r["sl_base_name"], 1)
        sl = r["sl_base_name"]
        map_image = r.get("map_image_name", "")
        module_name = r["module_name"]
        PLACEHOLDERS = ('RareModule_1x1', 'UnderConstruction_1x1')

        def _try_resolve(name: str):
            """Return (resolved_name, status). status: 'found'|'not_found'|'no_art'."""
            resolved, status = _resolve_img(art_root, r["module_group"], name)
            if resolved in PLACEHOLDERS:
                return resolved, status  # placeholder — don't accept
            return resolved, status

        img_name, art_status = _try_resolve(sl)

        # Priority logic:
        # 1. sl_base_name (SubLevelAsset) — always primary
        # 2. module_name — only when Art dir exists AND sl was not found
        # 3. MapImage — last resort
        if art_status == 'no_art':
            # No Art dir → sl is the best guess (matches webp in img/ dir)
            # BUT if MapImage is a placeholder, the module's own image might differ from sl
            if map_image in PLACEHOLDERS and module_name != sl:
                candidate, c_status = _try_resolve(module_name)
                if c_status in ('no_art', 'found'):
                    img_name = candidate
        elif art_status == 'not_found':
            # Art dir exists but no match for sl → try module_name (may differ)
            if module_name != sl:
                candidate, c_status = _try_resolve(module_name)
                if c_status == 'found':
                    img_name = candidate
                elif c_status == 'not_found':
                    pass  # neither found; keep sl
        else:
            # 'found' → sl had an exact match in Art; use it
            pass

        # If result is still a placeholder, try MapImage
        if img_name in PLACEHOLDERS and map_image and map_image not in PLACEHOLDERS:
            candidate, _ = _try_resolve(map_image)
            if candidate not in PLACEHOLDERS:
                img_name = candidate

        # Fallback: strip variant suffixes (_D, _A, _S) from module_name and check IMG_SRC for .webp
        if art_status in ('not_found', 'no_art') and img_name not in PLACEHOLDERS:
            if not (IMG_SRC / f"{img_name}.webp").exists() and module_name:
                stripped = re.sub(r"_[A-Z]$", "", module_name)
                if stripped != module_name and (IMG_SRC / f"{stripped}.webp").exists():
                    img_name = stripped

        # Final fallback: if nothing matched and the only candidate was a placeholder,
        # keep the placeholder so the frontend shows RareModule_1x1.webp.
        # Only when Art was searched (not_found) AND sl == module_name (single source) AND MapImage was a placeholder.
        if not img_name or img_name in PLACEHOLDERS:
            img_name = module_name or ''
        elif art_status == 'not_found' and img_name == module_name == sl and map_image in PLACEHOLDERS:
            img_name = map_image
        has_img = (IMG_SRC / f"{img_name}.webp").exists()
        modules_map[r["module_name"]] = {
            "name": r["module_name"],
            "translation": resolve_name(r["module_name"], r["translation_key"], "module"),
            "group": r["module_group"],
            "size_x": sx,
            "size_y": sy,
            "sl_base_name": sl,
            "img_name": img_name,
            "has_img": has_img,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "rotate": rotate,
            "range": custom_range,
        }
    for override_name, override_translation in MODULE_NAME_OVERRIDE.items():
        if override_name not in modules_map:
            resolved_name, _ = _resolve_img(art_root, "", override_name)
            modules_map[override_name] = {
                "name": override_name,
                "translation": override_translation,
                "group": "",
                "size_x": 1,
                "size_y": 1,
                "sl_base_name": override_name,
                "img_name": resolved_name,
                "has_img": (IMG_SRC / f"{resolved_name}.webp").exists(),
                "offset_x": 0,
                "offset_y": 0,
                "rotate": 1,
                "range": 0,
            }
    modules_data = sorted(modules_map.values(), key=lambda x: x["name"])
    # Filter out debug/test/resize variants (they're not real playable modules)
    _DEBUG_VARIANT_RE = re.compile(r"_(?:Resize|Test|BossTest|DistantView)$")
    modules_data = [m for m in modules_data if not _DEBUG_VARIANT_RE.search(m["name"])]
    _save("dungeon_modules.json", modules_data)

    # ── dungeon_module_coords: per-module entity coordinates ──
    # Build entity classification index from source directories (ground truth type)
    entity_class = _build_entity_classification(translations)
    _save("entity_index.json", [
        {"name": n, "types": v["types"], "translation_key": v["translation_key"]}
        for n, v in sorted(entity_class.items())
    ])

    # Build translation lookup from DB entity tables (covers all names including props variants)
    trans_lookup = {}
    for r in items:
        trans_lookup[r["item_name"]] = resolve_name(r["item_name"], r["translation_key"], "item")
    for r in monsters:
        trans_lookup[r["monster_name"]] = resolve_name(r["monster_name"], r["translation_key"], "monster")
    for r in props:
        trans_lookup[r["asset_name"]] = resolve_name(r["asset_name"], r["translation_key"], "props")

    _MODULE_COLORS = [
        "#E74C3C","#3498DB","#2ECC71","#F39C12","#9B59B6","#1ABC9C",
        "#E67E22","#2980B9","#27AE60","#D35400","#8E44AD","#16A085",
        "#C0392B","#2C3E50","#7F8C8D","#FF6B35","#00BFFF","#FFD700",
        "#FF69B4","#32CD32","#FF4500","#9370DB","#00FA9A","#DC143C",
        "#00CED1",
    ]
    rows = db.connect().execute("SELECT keyword, spawner_type, x, y, z, version, map_base FROM spawners ORDER BY map_base, keyword").fetchall()
    module_coords: dict[str, dict] = {}
    color_idx = 0
    for row in rows:
        mb = row["map_base"]
        if not mb:
            continue
        if mb not in module_coords:
            module_coords[mb] = {"map_base": mb, "entities": {}}
        ek = row["keyword"]
        if ek not in module_coords[mb]["entities"]:
            cls = entity_class.get(ek, {})
            st = row["spawner_type"]
            mapped_st = "item" if st == "lootdrop" else st
            if cls:
                types = cls.get("types", [])
                entity_type = mapped_st if mapped_st in types else types[0]
            else:
                entity_type = mapped_st
            translation = trans_lookup.get(ek) or resolve_name(ek, None, entity_type)
            module_coords[mb]["entities"][ek] = {
                "name": ek,
                "translation": translation,
                "type": entity_type,
                "color": _MODULE_COLORS[color_idx % len(_MODULE_COLORS)],
                "coords": [],
            }
            color_idx += 1
        module_coords[mb]["entities"][ek]["coords"].append({
            "x": row["x"], "y": row["y"], "z": row["z"], "version": row["version"] or "",
        })
    for mb, data in module_coords.items():
        entities_out = list(data["entities"].values())
        _save(f"dungeon_modules_coords/{mb}.json", {
            "map_base": mb,
            "entities": entities_out,
        })
    print(f"  module coords: {len(module_coords)} modules with coordinates")

    # ── lootdrops.json (grouped by item for list page) ──
    items_lookup = {r["item_name"]: r for r in items}
    monsters_lookup = {r["monster_name"]: r for r in monsters}
    loot_index = []
    for item_name, monster_names in merged_loot.items():
        item_row = items_lookup.get(item_name)
        translation = resolve_name(item_name, item_row["translation_key"] if item_row else None, "item") if item_row else (resolve_name(item_name, None, "item") or item_name)
        mon_translations = []
        for m in sorted(monster_names):
            cls = entity_class.get(m)
            if cls and "item" in cls["types"]:
                item_row = items_lookup.get(m)
                if item_row:
                    mon_translations.append(resolve_name(m, item_row["translation_key"], "item"))
                    continue
                tk = cls.get("translation_key", "")
                if tk:
                    mon_translations.append(resolve_name(m, tk, "item"))
                    continue
            elif cls and "props" in cls["types"]:
                mon_translations.append(resolve_name(m, cls.get("translation_key", ""), "props"))
                continue
            # Try direct monster lookup
            mon_row = monsters_lookup.get(m)
            if mon_row:
                mon_translations.append(resolve_name(m, mon_row["translation_key"], "monster"))
                continue
            # Try stripping _Hard/_VeryHard suffix → base monster lookup
            base = _HARD_SUFFIX_RE.sub("", m) if _HARD_SUFFIX_RE.search(m) else m
            if base != m:
                mon_row = monsters_lookup.get(base)
                if mon_row:
                    mon_translations.append(resolve_name(base, mon_row["translation_key"], "monster"))
                    continue
            # Try stripping trailing Unique → base monster lookup (e.g. FrostImpUnique → FrostImp)
            base2 = _UNIQUE_SUFFIX_RE.sub("", base) if _UNIQUE_SUFFIX_RE.search(base) else base
            if base2 != base:
                mon_row = monsters_lookup.get(base2)
                if mon_row:
                    mon_translations.append(resolve_name(base2, mon_row["translation_key"], "monster"))
                    continue
            # Try entity_class translation key as fallback
            if cls and cls.get("translation_key"):
                mon_translations.append(resolve_name(m, cls["translation_key"], cls["types"][0]))
                continue
            # Generic fallback
            mon_translations.append(resolve_name(m, None, "monster") or m)
        variant_count = item_row.get("variant_count", 1) if item_row else 1
        # Merge _Hard/_VeryHard/Unique variants in loot_index too
        merged_names: list[str] = []
        merged_translations: list[str] = []
        seen_bases: set[str] = set()
        for mn, mt in zip(monster_names, mon_translations):
            # Skip self-referencing
            if mn == item_name:
                continue
            base = _HARD_SUFFIX_RE.sub("", mn)
            base = _UNIQUE_SUFFIX_RE.sub("", base)
            if base not in seen_bases:
                seen_bases.add(base)
                merged_names.append(mn)
                merged_translations.append(mt)
        loot_index.append({
            "name": item_name,
            "translation": translation,
            "variant_count": variant_count,
            "monsters": sorted(merged_names),
            "monster_translations": merged_translations,
        })
    loot_index.sort(key=lambda x: x["translation"] or x["name"])
    _save("lootdrops.json", loot_index)

    # ── lootdrops detail files ──
    _MONSTER_COLORS = ["#E74C3C","#3498DB","#2ECC71","#F39C12","#9B59B6","#1ABC9C","#E67E22","#2980B9","#27AE60","#D35400","#8E44AD","#16A085","#C0392B","#2C3E50","#7F8C8D","#FF6B35","#00BFFF","#FFD700","#FF69B4","#32CD32","#FF4500","#9370DB","#00FA9A","#DC143C","#00CED1"]
    monster_coord_cache: dict[str, list] = {}
    _HARD_RE = re.compile(r"_(Hard|VeryHard)$")
    _SUFFIX_RE = re.compile(r"Unique$")

    def _base_monster_name(name: str) -> str:
        """Strip _Hard/_VeryHard/Unique suffix to get base name."""
        base = _HARD_RE.sub("", name)
        base = _SUFFIX_RE.sub("", base)
        return base

    for entry in loot_index:
        item_name = entry["name"]
        # Build merged monsters: base_name → {name, translation, coords}
        merged: dict[str, dict] = {}
        for i, m_name in enumerate(entry["monsters"]):
            # Skip self-referencing: item dropping itself (e.g. GoldOres → GoldOres)
            if m_name == item_name:
                continue
            if m_name not in monster_coord_cache:
                coords_list = all_coords.get(m_name, [])
                if not coords_list:
                    alias = TRANSLATION_ALIAS_MAP.get(m_name)
                    if alias:
                        coords_list = all_coords.get(alias, [])
                monster_coord_cache[m_name] = coords_list
            coords = monster_coord_cache[m_name]
            if not coords:
                continue
            m_trans = entry["monster_translations"][entry["monsters"].index(m_name)]
            base = _base_monster_name(m_name)
            if base not in merged:
                merged[base] = {
                    "name": base,
                    "translation": m_trans,
                    "color": _MONSTER_COLORS[len(merged) % len(_MONSTER_COLORS)],
                    "coords": [],
                }
            for c in coords:
                merged[base]["coords"].append({
                    "x": c["x"], "y": c["y"], "z": c["z"],
                    "map": c["map_base"], "file": c["json_filename"], "version": c["version"],
                    "label": c.get("original_keyword", ""),
                })
        monsters_out = list(merged.values())
        if monsters_out:
            _save(f"lootdrops/{item_name}.json", {
                "name": item_name,
                "translation": entry["translation"],
                "monsters": monsters_out,
            })

    # ── Quest extraction ──
    print("\nExtracting quest data...")
    explore_count, quest_items_count, quest_npc_count = run_quest_extraction()

    # ── Quest items groups (with coordinates) ──
    _generate_quest_items_groups(db, merged_loot, resolve_name, all_coords)

    # ── index.json: page index ──
    qg_path = OUTPUT_DIR / "quest_items_groups.json"
    qg = json.loads(qg_path.read_text()) if qg_path.exists() else []
    index_data = [
        {"_comment": "该文件由 api/src/collector.py 自动生成，请勿手动编辑。如需修改，请编辑 collector.py 中的 index_data 列表。"},
        {"page": "items", "label": "物品表", "count": len(items_index)},
        {"page": "monsters", "label": "怪物表", "count": len(monsters_index)},
        {"page": "props", "label": "实体表", "count": len(props_index)},
        {"page": "lootdrops", "label": "掉落表", "count": len(loot_index)},
        {"page": "explore", "label": "探索地点表", "count": explore_count},
        {"page": "quest_items", "label": "任务物品表", "count": len(qg)},
        {"page": "quest_npc", "label": "任务NPC表", "count": quest_npc_count},
        {"page": "dungeon_modules", "label": "地图模块表", "count": len(modules_data)},
    ]
    _save("index.json", index_data)

    print(f"\n[DONE] Output written to {OUTPUT_DIR}")
    for entry in index_data:
        if "page" in entry:
            print(f"  {entry['page']}: {entry['count']}")

    db.close()


def _generate_quest_items_groups(db, merged_loot, resolve_name, all_coords):
    quest_items_path = OUTPUT_DIR / "quest_items.json"
    if not quest_items_path.exists():
        return
    with open(quest_items_path) as f:
        quest_items = json.load(f)

    # Build map_base -> module_group lookup
    mods = db.get_dungeon_modules()
    map_to_group = {}
    for m in mods:
        g = m.get("module_group", "") or ""
        if g:
            map_to_group[m["module_name"]] = g
            if m.get("sl_base_name"):
                map_to_group[m["sl_base_name"]] = g

    item_names = sorted(set(qi["item_name"] for qi in quest_items))
    quest_map = {}
    for qi in quest_items:
        quest_map.setdefault(qi["item_name"], []).append(qi)

    _COLORS = [
        "#E74C3C","#3498DB","#2ECC71","#E67E22","#9B59B6","#1ABC9C",
        "#F39C12","#2980B9","#D35400","#C0392B","#7F8C8D","#27AE60",
        "#16A085","#8E44AD","#2C3E50","#F1C40F",
    ]

    groups = {}
    ci = 0
    for item_name in item_names:
        info_list = quest_map.get(item_name, [])
        trans = info_list[0]["item_translation"] if info_list else item_name

        icoords = all_coords.get(item_name, [])
        mnames = merged_loot.get(item_name, [])
        for c in icoords:
            mb = c["map_base"]
            mt = map_to_group.get(mb, "")
            if not mt:
                continue
            groups.setdefault(mt, {"group":mt,"entities":{}})
            ek = f"item::{item_name}"
            if ek not in groups[mt]["entities"]:
                groups[mt]["entities"][ek] = {
                    "name": item_name, "translation": trans, "type": "item",
                    "color": _COLORS[ci % len(_COLORS)], "coords": [],
                    "quest_npcs": [{"npc_name":qi["npc_name"],"npc_name_cn":qi["npc_name_cn"],"quest_number":qi["quest_number"],"count":qi["count"]} for qi in info_list],
                }
                ci += 1
            groups[mt]["entities"][ek]["coords"].append({
                "x":c["x"],"y":c["y"],"z":c["z"],"map":mb,
                "file":c["json_filename"],"version":c["version"],
            })
        for mn in sorted(mnames):
            if mn == item_name:
                continue
            mtrans = resolve_name(mn, None, "monster")
            mcoords = all_coords.get(mn, [])
            for c in mcoords:
                mb = c["map_base"]
                mt = map_to_group.get(mb, "")
                if not mt:
                    continue
                groups.setdefault(mt, {"group":mt,"entities":{}})
                ek = f"monster::{mn}"
                if ek not in groups[mt]["entities"]:
                    groups[mt]["entities"][ek] = {
                        "name": mn, "translation": mtrans, "type": "monster",
                        "color": _COLORS[ci % len(_COLORS)], "coords": [],
                        "quest_items": [item_name],
                        "_seen_coords": set(),
                    }
                    ci += 1
                else:
                    if item_name not in groups[mt]["entities"][ek]["quest_items"]:
                        groups[mt]["entities"][ek]["quest_items"].append(item_name)
                coord_key = (c["x"], c["y"], c["z"], mb, c["json_filename"])
                if coord_key not in groups[mt]["entities"][ek]["_seen_coords"]:
                    groups[mt]["entities"][ek]["_seen_coords"].add(coord_key)
                    groups[mt]["entities"][ek]["coords"].append({
                        "x":c["x"],"y":c["y"],"z":c["z"],"map":mb,
                        "file":c["json_filename"],"version":c["version"],
                    })

    GROUP_LABELS = {
        "Crypt":"废墟2层地牢","FireDeep":"哥布林洞穴2层","GoblinCave":"哥布林洞穴1层",
        "IceAbyss":"冰图2层","IceCavern":"冰图1层","Inferno":"废墟3层炼狱",
        "Ruins":"废墟1层","ShipGraveyard":"水图",
    }
    groups_index = []
    for gname in sorted(groups):
        g = groups[gname]
        g["group_display"] = GROUP_LABELS.get(gname, gname)
        entities = list(g["entities"].values())
        for e in entities:
            e.pop("_seen_coords", None)
        pos_count = sum(len(e["coords"]) for e in entities)
        groups_index.append({
            "group": gname, "group_display": g["group_display"],
            "entity_count": len(entities), "position_count": pos_count,
        })
        _save(f"quest_items_groups/{gname}.json", {
            "group": gname, "group_display": g["group_display"],
            "entities": entities,
        })
    _save("quest_items_groups.json", groups_index)
    print(f"  quest items groups: {len(groups_index)}")


def _resolve_img(art_root: Path, group: str, sl: str):
    """Return (resolved_name, status).
    status: 'found' (exact match in Art), 'not_found' (Art dir searched, no match),
            'no_art' (Art dir doesn't exist for this group).
    """
    if not art_root.exists() or not group:
        return sl, 'no_art'
    art_dir_name = GROUP_TO_ART_DIR.get(group, group)
    group_dir = art_root / art_dir_name
    if not group_dir.exists():
        return sl, 'no_art'
    # Try exact match (case-insensitive)
    png = group_dir / f"{sl}.png"
    if png.exists():
        return sl, 'found'
    for p in group_dir.iterdir():
        if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl.lower():
            return p.stem, 'found'
    # Try tail match (part after first underscore)
    tail = sl.split("_", 1)[-1] if "_" in sl else sl
    png = group_dir / f"{tail}.png"
    if png.exists():
        return tail, 'found'
    for p in group_dir.iterdir():
        if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == tail.lower():
            return p.stem, 'found'
    # Try stripping numeric suffix (_01, _02 etc.)
    import re
    sl_stripped = re.sub(r"_\d{2,4}$", "", sl)
    if sl_stripped != sl:
        for p in group_dir.iterdir():
            if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl_stripped.lower():
                return p.stem, 'found'
        tail_stripped = re.sub(r"_\d{2,4}$", "", tail)
        if tail_stripped != tail:
            for p in group_dir.iterdir():
                if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == tail_stripped.lower():
                    return p.stem, 'found'
    # Try stripping _Center / _Corner / _Passage suffix (keep trailing _NN)
    sl_center_stripped = re.sub(r"_(?:Center|Corner|Passage)(?=_\d|$)", "", sl)
    if sl_center_stripped != sl:
        for p in group_dir.iterdir():
            if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl_center_stripped.lower():
                return p.stem, 'found'
    # Try stripping _Resize / _Test / _BossTest / _DistantView debug suffixes
    sl_debug_stripped = re.sub(r"_(?:Resize|Test|BossTest|DistantView)$", "", sl)
    if sl_debug_stripped != sl:
        for p in group_dir.iterdir():
            if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl_debug_stripped.lower():
                return p.stem, 'found'
    # Try numeric prefix match: after stripping _\d{2,4}$, find any file starting with the stripped prefix
    if sl_stripped != sl:
        prefix = sl_stripped.lower()
        for p in group_dir.iterdir():
            if p.suffix.lower() in (".png", ".webp") and p.stem.lower().startswith(prefix):
                return p.stem, 'found'
    return sl, 'not_found'


def _save(filename: str, data: list | dict):
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
