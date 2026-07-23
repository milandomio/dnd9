import json
import os
import re
from pathlib import Path

from config import (
    DB_PATH,
    DUNGEON_MODULE_DIR,
    GAME_JSON,
    GAME_ROOT,
    ITEM_DIR,
    LAYOUT_DIR,
    LOG_DIR,
    LOOTDROP_DIR,
    LOOTDROP_GROUP_DIR,
    LOOTDROP_RATE_DIR,
    MAPS_DIR,
    MONSTER_DIR,
    OUTPUT_DIR,
    PROPS_DIR,
    SPAWNER_DIR,
)
from db_manager import DatabaseManager
from drop_rate import DropRateEngine
from enrichment import enrich_all_entities
from entity_export import export_items, export_monsters, export_props
from image_utils import sync_webp_images
from index_export import build_and_save_indexes, generate_quest_items_groups, save_quest_data
from lootdrop_builder import (
    build_and_save_lootdrop_details,
    build_loot_index,
    build_merged_loot_map,
)
from module_builder import (
    build_and_save_module_coords,
    build_and_save_modules_data,
    build_map_mappings,
    build_modules_map,
)
from pipeline import Pipeline
from quest_collector import run_quest_extraction
from search_engine import extract_all_spawners, load_all_spawner_data
from translator import NameResolver, build_coord_out, resolve_group_label

_SOURCE_PATHS = [
    GAME_JSON,
    ITEM_DIR,
    MONSTER_DIR,
    PROPS_DIR,
    DUNGEON_MODULE_DIR,
    LOOTDROP_DIR,
    LOOTDROP_GROUP_DIR,
    LOOTDROP_RATE_DIR,
    SPAWNER_DIR,
    MAPS_DIR,
    LAYOUT_DIR,
]


def _get_newest_mtime(paths: list[Path]) -> float:
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
            for dirpath, _dirnames, filenames in os.walk(p):
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
    if not db_path.exists():
        return True
    db_mtime = db_path.stat().st_mtime
    latest_source = _get_newest_mtime(_SOURCE_PATHS)
    return db_mtime < latest_source


def run():
    print("=" * 50)
    print("  DarkFindV5 - Data Collector")
    print("=" * 50)

    pipe = Pipeline(LOG_DIR)
    db = None

    try:

        pipe.log("checking DB staleness...")
        db_stale = _is_db_stale(DB_PATH)
        if db_stale and DB_PATH.exists():
            DB_PATH.unlink()
        pipe.log(f"DB stale={db_stale}, creating DatabaseManager...")
        db = DatabaseManager(DB_PATH)
        pipe.log("DatabaseManager ready")

        game_available = GAME_ROOT.exists() and db_stale

        pipe.log("get_entity_classification START")
        entity_class = db.get_entity_classification()
        pipe.log(f"get_entity_classification DONE -> {len(entity_class)}")

        if game_available:
            with pipe.phase("import_translations", 11) as ctx:
                count = db.import_translations()
                ctx.set_result(f"{count}")

            with pipe.phase("import_items", 11) as ctx:
                count = db.import_items()
                ctx.set_result(f"{count}")

            with pipe.phase("import_monsters", 11) as ctx:
                count = db.import_monsters()
                ctx.set_result(f"{count}")

            with pipe.phase("import_props", 11) as ctx:
                count = db.import_props()
                ctx.set_result(f"{count}")

            with pipe.phase("import_dungeon_modules", 11) as ctx:
                count = db.import_dungeon_modules()
                ctx.set_result(f"{count}")

            with pipe.phase("get_monster_name_map", 11) as ctx:
                monster_name_map = db.get_monster_name_map()
                ctx.set_result(f"{len(monster_name_map)}")

            with pipe.phase("load_all_spawner_data", 11) as ctx:
                spawner_has_lootdrop, spawner_multi_entity, spawner_monster_map = load_all_spawner_data(
                    monster_name_map
                )
                ctx.set_result(
                    f"has_lootdrop={len(spawner_has_lootdrop)}, multi_entity={len(spawner_multi_entity)}, monster_map={len(spawner_monster_map)}"
                )

            with pipe.phase("import_lootdrops", 11) as ctx:
                count = db.import_lootdrops(spawner_monster_map)
                ctx.set_result(f"{count}")

            with pipe.phase("extract_and_store_spawners", 11):
                spawners = extract_all_spawners(
                    has_lootdrop_map=spawner_has_lootdrop, multi_entity_spawners=spawner_multi_entity
                )
                pipe.log(f"extract_all_spawners DONE -> {len(spawners)} spawners")
                c = db.connect()
                c.execute("BEGIN")
                c.execute("DELETE FROM spawners")
                spawner_rows = [
                    (
                        idx + 1,
                        s["keyword"],
                        s.get("original_keyword", ""),
                        s["spawner_type"],
                        1 if s.get("has_lootdrop", False) else 0,
                        s["x"],
                        s["y"],
                        s["z"],
                        s.get("yaw", 0),
                        s["json_filename"],
                        s.get("version", ""),
                        s.get("map_base", ""),
                        s.get("group_parent", ""),
                        s.get("sub_group_parent", ""),
                    )
                    for idx, s in enumerate(spawners)
                ]
                c.executemany(
                    "INSERT INTO spawners (id, keyword, original_keyword, spawner_type, has_lootdrop, x, y, z, yaw, json_filename, version, map_base, group_parent, sub_group_parent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    spawner_rows,
                )
                db.connect().commit()
                pipe.log("spawners stored in DB")
                added = db.import_spawner_fallback_entities()
                pipe.log(f"import_spawner_fallback_entities DONE -> {added}")
                # ╔══════════════════════════════════════════════════════════════╗
                # ║  CRITICAL: entity_class MUST be rebuilt here!              ║
                # ║  Do NOT move/remove this line without user confirmation.   ║
                # ║  Moving it causes:                                         ║
                # ║  - Spawner fallback entities (HoardChest01_3, etc.)        ║
                # ║    missing from entity_class → translation fails           ║
                # ║  - Lootdrop pages show wrong category buttons              ║
                # ║  - Category merge breaks → coords lost                    ║
                # ║  - Multiple silent data corruption cascades               ║
                # ╚══════════════════════════════════════════════════════════════╝
                entity_class = db.get_entity_classification()
                cur2 = db.connect().cursor()
                cur2.execute("DELETE FROM mutually_exclusive_groups")
                cur2.execute("""
                    SELECT s.group_parent, s.map_base, s.json_filename, s.keyword,
                           COUNT(*) as cnt
                    FROM spawners s
                    WHERE s.group_parent != ''
                    GROUP BY s.group_parent, s.map_base, s.json_filename, s.keyword
                    HAVING cnt > 1
                """)
                group_rows = []
                for row in cur2.fetchall():
                    group_rows.append(
                        (
                            row["map_base"],
                            row["json_filename"],
                            row["group_parent"],
                            row["keyword"],
                            row["cnt"],
                        )
                    )
                cur2.executemany(
                    "INSERT INTO mutually_exclusive_groups (map_base, json_filename, group_name, search_term, spawner_count) VALUES (?, ?, ?, ?, ?)",
                    group_rows,
                )
                db.connect().commit()
                pipe.log(f"mutually_exclusive_groups DONE -> {len(group_rows)} groups")

            with pipe.phase("quest_extraction", 11) as ctx:
                explore_data, quest_items_data, quest_npcs_data = run_quest_extraction(
                    entity_classification=entity_class
                )
                ctx.set_result(
                    f"explore={len(explore_data)}, items={len(quest_items_data)}, npcs={len(quest_npcs_data)}"
                )
                db.import_explore_targets(explore_data)
                db.import_quest_items(quest_items_data)
                db.import_quest_npcs(quest_npcs_data)
                pipe.log("quest data imported to DB")

            with pipe.phase("import_lootdrop_rates", 11):
                db.import_spawner_entries()
                db.import_lootdrop_groups()
                db.import_lootdrop_rate_items()
                db.import_lootdrop_rate_weights()
        else:
            if not GAME_ROOT.exists():
                print("\n[SKIP] Game data not found, using existing DB")
            else:
                print("\n[SKIP] DB is up to date (newest source file older than DB), using existing DB")

        pipe.log("[JSON] loading entities from DB...")
        items = db.get_item_entities()
        monsters = db.get_monster_entities()
        props = db.get_props_entities()
        pipe.log(f"[JSON] entities loaded: items={len(items)}, monsters={len(monsters)}, props={len(props)}")
        pipe.log("[JSON] get_all_coordinates START")
        all_coords = db.get_all_coordinates()
        pipe.log(f"[JSON] get_all_coordinates DONE -> {len(all_coords)} entity keys")
        _coord_variant_count = db.get_coord_variant_counts()
        pipe.log(f"[JSON] get_coord_variant_counts DONE -> {len(_coord_variant_count)} variant groups")
        _sub_pool_info_raw = db.get_sub_group_pool_info()
        pipe.log(f"[JSON] get_sub_group_pool_info DONE -> {len(_sub_pool_info_raw)} sub-groups")

        _og_to_keywords: dict[str, set[str]] = {}
        for _kw, _clist in all_coords.items():
            for _c in _clist:
                _og = _c.get("original_keyword", "")
                if _og and _og != _kw and _og not in all_coords:
                    _og_to_keywords.setdefault(_og, set()).add(_kw)

        _props_spawner_info: dict[str, dict] = {}
        for row in (
            db.connect()
            .execute("SELECT DISTINCT keyword, spawner_type, has_lootdrop FROM spawners WHERE spawner_type = 'props'")
            .fetchall()
        ):
            _props_spawner_info[row["keyword"]] = {
                "spawner_type": row["spawner_type"],
                "has_lootdrop": row["has_lootdrop"],
            }

        _item_names = {r["item_name"] for r in items}
        _monster_names = {r["monster_name"] for r in monsters}
        _prop_names = {r["asset_name"] for r in props}

        print("\nExporting JSON files...")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        if GAME_ROOT.exists():
            pipe.log("[JSON] syncing webp images...")
            sync_webp_images(pipe.log)

        translations = db.get_translations_map()

        resolver = NameResolver(translations)

        _monsters_lookup = {r["monster_name"]: r for r in monsters}
        for _vkey, (_vcnt, _vraw) in list(_coord_variant_count.items()):
            if _vraw:
                _vtr: list[str] = []
                for _kw in _vraw:
                    _cls = entity_class.get(_kw, {})
                    _mrow = _monsters_lookup.get(_kw)
                    if _mrow:
                        _vtr.append(resolver.resolve(_kw, _mrow["translation_key"], "monster"))
                    elif _cls and "props" in _cls.get("types", []):
                        _vtr.append(resolver.resolve(_kw, _cls.get("translation_key", ""), "props"))
                    else:
                        _vtr.append(resolver.resolve(_kw, None, "props") or _kw)
                _coord_variant_count[_vkey] = (_vcnt, _vtr)

        _sub_pool_info: dict[tuple[str, str, str, str], tuple[int, list[str]]] = {}
        for _sp_key, (_sp_cnt, _sp_raw_names) in _sub_pool_info_raw.items():
            _sp_tr: list[str] = []
            for _kw in _sp_raw_names:
                _cls = entity_class.get(_kw, {})
                _mrow = _monsters_lookup.get(_kw)
                if _mrow:
                    _sp_tr.append(resolver.resolve(_kw, _mrow["translation_key"], "monster"))
                elif _cls and "props" in _cls.get("types", []):
                    _sp_tr.append(resolver.resolve(_kw, _cls.get("translation_key", ""), "props"))
                else:
                    _sp_tr.append(resolver.resolve(_kw, None, "props") or _kw)
            _sub_pool_info[_sp_key] = (_sp_cnt, _sp_tr)

        pipe.log("[JSON] building merged lootdrop map...")
        merged_loot, skip_variants = build_merged_loot_map(db)

        pipe.log("[JSON] building item→spawner coord chain map...")
        _variant_re = re.compile(r"_\d{4}$")
        item_coord_chain_map: dict[str, set[str]] = {}
        for _row in (
            db.connect()
            .execute(
                "SELECT DISTINCT lri.item_name, se.spawner_keyword "
                "FROM lootdrop_rate_items lri "
                "JOIN lootdrop_groups lg ON lri.lootdrop_id = lg.lootdrop_id "
                "JOIN spawner_entries se ON lg.group_id = se.lootdrop_group_id"
            )
            .fetchall()
        ):
            _base = _variant_re.sub("", _row["item_name"])
            item_coord_chain_map.setdefault(_base, set()).add(_row["spawner_keyword"])
        pipe.log(f"[JSON] item_coord_chain_map DONE -> {len(item_coord_chain_map)} item keys")

        pipe.log("[JSON] building modules_map...")
        modules = db.get_dungeon_modules()
        modules_map = build_modules_map(db, resolver.resolve)
        map_to_module, module_to_maps = build_map_mappings(modules_map)
        # 注入分组显示名
        for _mod in modules_map.values():
            _g = _mod.get("group", "")
            _mod["group_display"] = resolve_group_label(_g, translations)

        # P005: Build ENTITY_PAGE_MAP for coord reference
        entity_page_map: dict[str, str] = {}

        with pipe.step("items export") as ctx:
            items_index = export_items(
                items,
                merged_loot,
                all_coords,
                resolver.resolve,
                skip_variants,
                _coord_variant_count,
                _item_names,
                OUTPUT_DIR,
                map_to_module,
                item_coord_chain_map,
                _sub_pool_info,
            )
            # P005: Build from actual exported files, not raw DB data
            for e in items_index:
                entity_page_map[e["name"]] = f"items/{e['name']}"
            ctx.set_result(f"{len(items_index)} items")

        with pipe.step("monsters export") as ctx:
            monsters_index = export_monsters(
                monsters,
                all_coords,
                resolver.resolve,
                _coord_variant_count,
                _monster_names,
                OUTPUT_DIR,
                map_to_module,
                _sub_pool_info,
            )
            for e in monsters_index:
                entity_page_map[e["name"]] = f"monsters/{e['name']}"
            ctx.set_result(f"{len(monsters_index)} monsters")

        with pipe.step("props export") as ctx:
            props_index = export_props(
                props,
                all_coords,
                resolver.resolve,
                _props_spawner_info,
                _coord_variant_count,
                _prop_names,
                OUTPUT_DIR,
                map_to_module,
                _sub_pool_info,
            )
            for e in props_index:
                entity_page_map[e["name"]] = f"props/{e['name']}"
            ctx.set_result(f"{len(props_index)} props")

        # P005: Ensure all all_coords keys have ref files
        # Covers orphan entities + case-variant keys (e.g. DwarfHandcannoneer)
        _orphan_count = 0
        for _entity_name, _coords in all_coords.items():
            if _entity_name in entity_page_map:
                continue
            if not _coords:
                continue
            coord_data = [build_coord_out(c, _coord_variant_count, map_to_module, _sub_pool_info) for c in _coords]
            _save(f"coords/{_entity_name}.json", coord_data)
            entity_page_map[_entity_name] = f"coords/{_entity_name}"
            _orphan_count += 1
        if _orphan_count:
            pipe.log(f"[JSON] orphan coord files: {_orphan_count}")

        pipe.log(f"[JSON] ENTITY_PAGE_MAP built: {len(entity_page_map)} entities")

        with pipe.step("dungeon_modules export") as ctx:
            merged_coords = build_and_save_module_coords(
                db, modules_map, map_to_module, resolver.resolve, items, monsters, props, OUTPUT_DIR
            )
            modules_data = build_and_save_modules_data(modules_map, module_to_maps, merged_coords, OUTPUT_DIR)
            ctx.set_result(f"{len(modules_data)} modules")

        pipe.log("[JSON] preloading drop rate data...")
        drop_engine = DropRateEngine()
        drop_engine.preload(db, modules_data)
        pipe.log("[JSON] preloaded drop rate data via DropRateEngine")

        with pipe.step("lootdrops") as ctx:
            loot_index = build_loot_index(merged_loot, items, monsters, entity_class, resolver.resolve)
            _save("lootdrops.json", loot_index)
            ctx.set_result(f"{len(loot_index)} items")

        build_and_save_lootdrop_details(
            loot_index,
            drop_engine,
            all_coords,
            resolver.resolve,
            _og_to_keywords,
            _coord_variant_count,
            entity_class,
            monsters,
            OUTPUT_DIR,
            pipe.log,
            map_to_module,
            translations,
            entity_page_map,
        )
        pipe.log("[JSON] lootdrops detail files DONE")

        enrich_all_entities(drop_engine, loot_index, OUTPUT_DIR, pipe.log)

        with pipe.step("quest data export") as ctx:
            print("\nExporting quest data from DB...")
            explore_count, quest_items_count, quest_npc_count, quest_npcs_data = save_quest_data(db, OUTPUT_DIR)
            print(f"  explore: {explore_count}, quest items: {quest_items_count}, quest NPCs: {quest_npc_count}")
            ctx.set_result(f"explore={explore_count}, items={quest_items_count}, npcs={quest_npc_count}")

        with pipe.step("quest_items_groups"):
            generate_quest_items_groups(
                db,
                merged_loot,
                resolver.resolve,
                all_coords,
                modules,
                OUTPUT_DIR,
                group_label_resolver=lambda g: resolve_group_label(g, translations),
            )

        with pipe.step("search_index") as ctx:
            index_data = build_and_save_indexes(
                items_index,
                monsters_index,
                props_index,
                loot_index,
                modules_data,
                explore_count,
                quest_items_count,
                quest_npc_count,
                quest_npcs_data,
                OUTPUT_DIR,
                group_label_resolver=lambda g: resolve_group_label(g, translations),
            )
            ctx.set_result("DONE")

        print(f"\n[DONE] Output written to {OUTPUT_DIR}")
        for entry in index_data:
            if "page" in entry:
                print(f"  {entry['page']}: {entry['count']}")

    finally:
        if db:
            db.close()
        pipe.close()
    return pipe.timer


def _save(filename: str, data: list | dict):
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
