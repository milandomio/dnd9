import json
import re
from collections import defaultdict
from pathlib import Path

from config import DB_PATH, OUTPUT_DIR, GAME_ROOT, GROUP_TO_ART_DIR, HARDCODED_TRANSLATIONS, MODULE_DISPLAY_OVERRIDE, MODULE_NAME_OVERRIDE, MODULE_OFFSET_MAP, TRANSLATION_ALIAS_MAP
from db_manager import DatabaseManager
from search_engine import build_all_matches
from layout_utils import load_all_layout_rotations
from quest_collector import run_quest_extraction

_VARIANT_RE = re.compile(r"^(.+)_\d{4}$")
_HARD_SUFFIX_RE = re.compile(r"_(Hard|VeryHard)$")
_UNIQUE_SUFFIX_RE = re.compile(r"Unique$")


def run():
    print("=" * 50)
    print("  DarkFindV5 - Data Collector")
    print("=" * 50)

    db = DatabaseManager(DB_PATH)

    game_available = GAME_ROOT.exists()

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
    else:
        print("\n[SKIP] Game data not found, using existing DB")

    # 后续步骤从 DB 读取（无论是否导入，DB 中都有数据）
    items = db.get_item_entities()
    monsters = db.get_monster_entities()
    props = db.get_props_entities()

    # ─── Export JSON ───
    print("\nExporting JSON files...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    translations = db.get_translations_map()

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

        # Final fallback: if nothing matched and the only candidate was a placeholder,
        # keep the placeholder so the frontend shows RareModule_1x1.webp.
        # Only when Art was searched (not_found) AND sl == module_name (single source) AND MapImage was a placeholder.
        if not img_name or img_name in PLACEHOLDERS:
            img_name = module_name or ''
        elif art_status == 'not_found' and img_name == module_name == sl and map_image in PLACEHOLDERS:
            img_name = map_image
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
            # Try item lookup (item names used as drop sources)
            item_row = items_lookup.get(m)
            if item_row:
                mon_translations.append(resolve_name(m, item_row["translation_key"], "item"))
                continue
            # Generic fallback
            mon_translations.append(resolve_name(m, None, "monster") or m)
        variant_count = item_row.get("variant_count", 1) if item_row else 1
        # Merge _Hard/_VeryHard/Unique variants in loot_index too
        merged_names: list[str] = []
        merged_translations: list[str] = []
        seen_bases: set[str] = set()
        for mn, mt in zip(monster_names, mon_translations):
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
            if m_name not in monster_coord_cache:
                coords_list = db.get_item_coordinates(m_name)
                if not coords_list:
                    alias = TRANSLATION_ALIAS_MAP.get(m_name)
                    if alias:
                        coords_list = db.get_item_coordinates(alias)
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
    _generate_quest_items_groups(db, merged_loot, resolve_name)

    # ── index.json: page index ──
    qg_path = OUTPUT_DIR / "quest_items_groups.json"
    qg = json.loads(qg_path.read_text()) if qg_path.exists() else []
    index_data = [
        {"page": "items", "label": "物品表", "count": len(items_index)},
        {"page": "monsters", "label": "怪物表", "count": len(monsters_index)},
        {"page": "props", "label": "实体表", "count": len(props_index)},
        {"page": "lootdrops", "label": "掉落表", "count": len(loot_index)},
        {"page": "explore", "label": "探索地点表", "count": explore_count},
        {"page": "quest_items", "label": "任务物品表", "count": len(qg)},
        {"page": "quest_npc", "label": "任务NPC表", "count": quest_npc_count},
    ]
    _save("index.json", index_data)

    print(f"\n[DONE] Output written to {OUTPUT_DIR}")
    for entry in index_data:
        print(f"  {entry['page']}: {entry['count']}")

    db.close()


def _generate_quest_items_groups(db, merged_loot, resolve_name):
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

        icoords = db.get_item_coordinates(item_name)
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
            mtrans = resolve_name(mn, None, "monster")
            mcoords = db.get_item_coordinates(mn)
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
                    }
                    ci += 1
                else:
                    if item_name not in groups[mt]["entities"][ek]["quest_items"]:
                        groups[mt]["entities"][ek]["quest_items"].append(item_name)
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
    return sl, 'not_found'


def _save(filename: str, data: list | dict):
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
