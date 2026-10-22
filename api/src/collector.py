import json
import time
from datetime import datetime, timezone

from config import (
    DB_PATH,
    LOG_DIR,
    OUTPUT_DIR,
)
from craft_builder import build_and_save_crafts
from db_freshness import has_usable_database
from db_manager import DatabaseManager
from drop_rate import DropRateEngine
from enrichment import enrich_all_entities
from entity_export import export_items, export_monsters, export_props
from image_utils import sync_webp_images
from index_export import build_and_save_indexes, generate_quest_items_groups, save_quest_data
from label_type import GOLDCHEST_SPECIAL, split_goldchest_special_coords
from light_builder import build_and_save_lights
from locale_builder import build_locale_files
from lootdrop_builder import (
    build_and_save_lootdrop_details,
    build_loot_index,
    build_merged_loot_map,
)
from merchant_builder import REGION_LABEL_KEY, build_shop_data, save_shop_data
from module_builder import (
    build_and_save_module_coords,
    build_and_save_modules_data,
    build_map_mappings,
    build_modules_map,
)
from monster_drops_builder import attach_loot_pools, load_drop_rows
from pipeline import Pipeline
from quest_collector import run_quest_extraction
from search_engine import load_all_spawner_data
from search_index_builder import build_search_index_files
from translator import (
    RESOLVE_STRIP_RE,
    NameResolver,
    build_coord_out,
    resolve_group_label,
    resolve_translation_key,
)


def _resolve_group_display(group: str, translations: dict[str, str]) -> str:
    """Construct Chinese display string from group name, for JSON fallback."""
    result = resolve_group_label(group)
    if not result:
        return group
    base = translations.get(result["slot_key"], group)
    floor = result["floor"]
    sub_key = result["sub_key"]
    if sub_key:
        sub_name = translations.get(sub_key, "")
        return f"{base}{floor}层（{sub_name}）"
    return f"{base}{floor}层"


def run(
    import_required: bool = False,
    db_path=DB_PATH,
    source_manifest: dict | None = None,
):
    print("=" * 50)
    print("  DarkFindV5 - Data Collector")
    print("=" * 50)

    pipe = Pipeline(LOG_DIR)
    db = None

    try:

        pipe.log("creating DatabaseManager...")
        db = DatabaseManager(db_path, initialize_schema=import_required)
        pipe.log("DatabaseManager ready")
        pipe.log(f"[DB] mode={'full import' if import_required else 'DB-only'}")

        pipe.log("get_entity_classification START")
        entity_class = db.get_entity_classification()
        pipe.log(f"get_entity_classification DONE -> {len(entity_class)}")

        if import_required:
            with pipe.phase("import_translations", 12) as ctx:
                count = db.import_translations()
                ctx.set_result(f"{count}")

            with pipe.phase("import_items", 12) as ctx:
                count = db.import_items()
                ctx.set_result(f"{count}")

            with pipe.phase("import_monsters", 12) as ctx:
                count = db.import_monsters()
                ctx.set_result(f"{count}")

            with pipe.phase("import_props", 12) as ctx:
                count = db.import_props()
                ctx.set_result(f"{count}")

            with pipe.phase("import_dungeon_modules", 12) as ctx:
                count = db.import_dungeon_modules()
                ctx.set_result(f"{count}")

            with pipe.phase("import_ingame_merchants", 12) as ctx:
                counts = db.import_ingame_merchants()
                ctx.set_result(
                    f"{counts['merchants']} merchants, {counts['variants']} variants, {counts['stock']} stock rows"
                )

            # Craft recipes come first: their outputs (the Protection potions)
            # are part of the item set the effect importer resolves, so
            # ``craft_recipes`` must already be populated when it runs.
            with pipe.phase("import_craft_recipes", 12) as ctx:
                counts = db.import_craft_recipes()
                ctx.set_result(f"{counts['merchants']} merchants, {counts['recipes']} recipes")

            with pipe.phase("import_item_effects", 12) as ctx:
                count = db.import_item_effects()
                ctx.set_result(f"{count} items")

            with pipe.phase("import_light_items", 12) as ctx:
                count = db.import_light_items()
                ctx.set_result(f"{count} light variants")

            with pipe.phase("import_item_properties", 12) as ctx:
                counts = db.import_item_properties()
                ctx.set_result(f"{counts['items']} items, {counts['pools']} random pools")

            with pipe.phase("import_environment_lights", 12) as ctx:
                count = db.import_environment_lights()
                ctx.set_result(f"{count} environment props")

            with pipe.phase("import_spawner_entries", 12) as ctx:
                count = db.import_spawner_entries()
                ctx.set_result(f"{count}")

            with pipe.phase("get_monster_name_map", 12) as ctx:
                monster_name_map = db.get_monster_name_map()
                ctx.set_result(f"{len(monster_name_map)}")

            with pipe.phase("load_all_spawner_data", 12) as ctx:
                spawner_has_lootdrop, spawner_multi_entity, spawner_monster_map = load_all_spawner_data(
                    db, monster_name_map
                )
                ctx.set_result(
                    f"has_lootdrop={len(spawner_has_lootdrop)}, multi_entity={len(spawner_multi_entity)}, monster_map={len(spawner_monster_map)}"
                )

            with pipe.phase("import_lootdrops", 12) as ctx:
                count = db.import_lootdrops(spawner_monster_map)
                ctx.set_result(f"{count}")

            with pipe.phase("extract_and_store_spawners", 12):
                spawners = db.extract_spawners(
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
                        1 if s.get("is_container", False) else 0,
                    )
                    for idx, s in enumerate(spawners)
                ]
                c.executemany(
                    "INSERT INTO spawners (id, keyword, original_keyword, spawner_type, has_lootdrop, x, y, z, yaw, json_filename, version, map_base, group_parent, sub_group_parent, is_container) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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

            with pipe.phase("quest_extraction", 12) as ctx:
                explore_data, quest_items_data, quest_npcs_data = run_quest_extraction(
                    db, entity_classification=entity_class
                )
                ctx.set_result(
                    f"explore={len(explore_data)}, items={len(quest_items_data)}, npcs={len(quest_npcs_data)}"
                )
                db.import_explore_targets(explore_data)
                db.import_quest_items(quest_items_data)
                db.import_quest_npcs(quest_npcs_data)
                pipe.log("quest data imported to DB")

            with pipe.phase("import_lootdrop_rates", 12):
                db.import_lootdrop_groups()
                db.import_lootdrop_rate_items()
                db.import_lootdrop_rate_weights()
            if source_manifest is None:
                raise RuntimeError("full import requires a source manifest")
            db.connect().commit()
            if not has_usable_database(db.db_path):
                raise RuntimeError("full import did not produce a usable database")
            db.set_pipeline_meta(
                {
                    "schema_version": source_manifest["schema_version"],
                    "generator_version": source_manifest["generator_version"],
                    "source_manifest": json.dumps(source_manifest, sort_keys=True, separators=(",", ":")),
                    "source_latest_mtime_ns": str(source_manifest["latest_mtime_ns"]),
                    "import_completed_at": datetime.now(timezone.utc).isoformat(),
                    "import_complete": "1",
                }
            )
        pipe.log("[JSON] loading entities from DB...")
        items = db.get_item_entities()
        monsters = db.get_monster_entities()
        props = db.get_props_entities()
        pipe.log(f"[JSON] entities loaded: items={len(items)}, monsters={len(monsters)}, props={len(props)}")
        pipe.log("[JSON] get_all_coordinates START")
        all_coords = db.get_all_coordinates()
        pipe.log(f"[JSON] get_all_coordinates DONE -> {len(all_coords)} entity keys")
        _gc_n = split_goldchest_special_coords(all_coords)
        if _gc_n:
            pipe.log(f"[JSON] GoldChest_special split -> {_gc_n} special coords")
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
        if GOLDCHEST_SPECIAL in all_coords:
            _prop_names.add(GOLDCHEST_SPECIAL)
            # synthetic props row for export / entity_class consumers
            if not any(r["asset_name"] == GOLDCHEST_SPECIAL for r in props):
                _gc_tk = next(
                    (r["translation_key"] for r in props if r["asset_name"] in ("GoldChest", "GoldChest_UnderSea")),
                    "Text_DesignData_Props_Props_GoldenChest",
                )
                props = list(props) + [
                    {
                        "asset_name": GOLDCHEST_SPECIAL,
                        "raw_name": f"Id_Props_{GOLDCHEST_SPECIAL}",
                        "translation_key": _gc_tk,
                    }
                ]
            entity_class[GOLDCHEST_SPECIAL] = {
                "types": ["props"],
                "translation_key": next(
                    (r["translation_key"] for r in props if r["asset_name"] == GOLDCHEST_SPECIAL),
                    "Text_DesignData_Props_Props_GoldenChest",
                ),
            }

        print("\nExporting JSON files...")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        pipe.log("[JSON] checking delivered webp images...")
        sync_webp_images(pipe.log)

        translations = db.get_translations_map()

        resolver = NameResolver(translations)

        _monsters_lookup = {r["monster_name"]: r for r in monsters}
        _props_lookup = {r["asset_name"]: r for r in props}

        def _pool_entry(_kw: str) -> dict[str, str]:
            """Translate a spawner keyword into a {translation_key, name} entry."""
            _cls = entity_class.get(_kw, {})
            _mrow = _monsters_lookup.get(_kw) or _monsters_lookup.get(_kw.replace("Guardsman", "Guardman"))
            if "FromFakeDeath" in _kw:
                _tk = "ui.pool.skeleton_guard_fake_death"
                _name = resolver.resolve(_kw, None, "props") or _kw
            elif _mrow:
                _tk = _mrow["translation_key"]
                _name = resolver.resolve(_kw, _tk, "monster")
            elif _kw == "Ore_GoldOre":
                _tk = _props_lookup["Ore_GoldOre_VeryLow"]["translation_key"]
                _name = resolver.resolve(_kw, _tk, "props")
            elif _cls:
                _cls_types = _cls.get("types", [])
                if "props" in _cls_types:
                    _tk = _cls.get("translation_key", "")
                    _name = resolver.resolve(_kw, _tk, "props")
                elif "item" in _cls_types:
                    _tk = _cls.get("translation_key", "")
                    _name = resolver.resolve(_kw, _tk, "item")
                else:
                    _tk = ""
                    _name = resolver.resolve(_kw, None, "props") or _kw
            else:
                _tk = ""
                _name = resolver.resolve(_kw, None, "props") or _kw
            return {"translation_key": resolve_translation_key(_kw, _tk), "name": _name}

        for _vkey, (_vcnt, _vraw) in list(_coord_variant_count.items()):
            if _vraw:
                _vtr: list[dict] = []
                for _kw in _vraw:
                    _cls = entity_class.get(_kw, {})
                    _mrow = _monsters_lookup.get(_kw) or _monsters_lookup.get(_kw.replace("Guardsman", "Guardman"))
                    if "FromFakeDeath" in _kw:
                        tk = "ui.pool.skeleton_guard_fake_death"
                        _vtr.append({"translation_key": tk, "name": resolver.resolve(_kw, None, "props") or _kw})
                    elif _mrow:
                        tk = _mrow["translation_key"]
                        _vtr.append({"translation_key": tk, "name": resolver.resolve(_kw, tk, "monster")})
                    elif _cls and "props" in _cls.get("types", []):
                        tk = _cls.get("translation_key", "")
                        _vtr.append({"translation_key": tk, "name": resolver.resolve(_kw, tk, "props")})
                    else:
                        _vtr.append(
                            {
                                "translation_key": resolve_translation_key(_kw),
                                "name": resolver.resolve(_kw, None, "props") or _kw,
                            }
                        )
                _coord_variant_count[_vkey] = (_vcnt, _vtr)

        _sub_pool_info: dict[tuple[str, str, str, str], tuple[int, list[dict[str, str]], int]] = {}
        for _sp_key, (_sp_cnt, _sp_raw_names) in _sub_pool_info_raw.items():
            _sub_pool_info[_sp_key] = (_sp_cnt, [_pool_entry(_kw) for _kw in _sp_raw_names], 0)

        _parent_pool_sizes: dict[tuple[str, str, str], int] = {}
        for _map_base, _filename, _group_parent, _sub_group_parent in _sub_pool_info:
            _parent_key = (_map_base, _filename, _group_parent)
            _parent_pool_sizes[_parent_key] = _parent_pool_sizes.get(_parent_key, 0) + 1
        for _sp_key, (_sp_cnt, _sp_entries, _) in _sub_pool_info.items():
            _sub_pool_info[_sp_key] = (
                _sp_cnt,
                _sp_entries,
                _parent_pool_sizes[_sp_key[:3]],
            )

        # Same-point candidate pools: several entities placed on the exact same
        # coordinate are mutually exclusive (only one of them is spawned there).
        # Quality/grade variants of one entity (Ore_IronOre_Low / _High, ...) are
        # collapsed so only real alternatives are listed.
        _point_pools_raw = db.get_coord_point_pools()
        pipe.log(f"[JSON] get_coord_point_pools DONE -> {len(_point_pools_raw)} same-point pools")
        _point_pools: dict[tuple[str, str, float, float, float], tuple[int, list[dict[str, str]]]] = {}
        for _pp_key, (_pp_cnt, _pp_raw_names) in _point_pools_raw.items():
            _by_base: dict[str, str] = {}
            for _kw in sorted(_pp_raw_names):
                _base = RESOLVE_STRIP_RE.sub("", _kw) or _kw
                _by_base.setdefault(_base, _kw)
            if len(_by_base) < 2:
                continue
            _entries: list[dict[str, str]] = []
            _seen_names: set[str] = set()
            for _kw in _by_base.values():
                _entry = _pool_entry(_kw)
                if _entry["name"] in _seen_names:
                    continue
                _seen_names.add(_entry["name"])
                _entries.append(_entry)
            if len(_entries) < 2:
                continue
            _point_pools[_pp_key] = (len(_entries), _entries)

        pipe.log("[JSON] building merged lootdrop map...")
        merged_loot, skip_variants = build_merged_loot_map(db)

        pipe.log("[JSON] building modules_map...")
        modules = db.get_dungeon_modules()
        modules_map = build_modules_map(db, resolver.resolve, module_rotations=None)
        map_to_module, module_to_maps = build_map_mappings(modules_map)
        # 注入分组显示名
        for _mod in modules_map.values():
            _g = _mod.get("group", "")
            result = resolve_group_label(_g)
            if result:
                _mod["group_key"] = result["slot_key"]
                _mod["group_floor"] = result["floor"]
                _mod["group_sub_key"] = result["sub_key"]
            else:
                _mod["group_key"] = _g
                _mod["group_floor"] = 1
                _mod["group_sub_key"] = None
            _mod["group_display"] = _resolve_group_display(_g, translations)

        with pipe.step("dungeon_modules export") as ctx:
            merged_coords = build_and_save_module_coords(
                db, modules_map, map_to_module, resolver.resolve, items, monsters, props, OUTPUT_DIR, _point_pools
            )
            modules_data = build_and_save_modules_data(modules_map, module_to_maps, merged_coords, OUTPUT_DIR)
            ctx.set_result(f"{len(modules_data)} modules")

        pipe.log("[JSON] preloading drop rate data...")
        drop_engine = DropRateEngine()
        drop_engine.preload(db, modules_data)
        pipe.log("[JSON] preloaded drop rate data via DropRateEngine")

        with pipe.step("item coord chain map") as ctx:
            item_coord_chain_map = drop_engine.base_item_spawners
            ctx.set_result(f"{len(item_coord_chain_map)} item keys")

        # P005: Build ENTITY_PAGE_MAP for coord reference
        entity_page_map: dict[str, str] = {}
        entity_data_by_type: dict[str, dict[str, dict]] = {
            "items": {},
            "monsters": {},
            "props": {},
        }
        session_spawn_limits = db.get_session_spawn_limits()

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
                entity_data_by_type["items"],
                _point_pools,
            )
            # P005: Build from actual exported entities, not raw DB data
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
                entity_data_by_type["monsters"],
                session_spawn_limits,
                _point_pools,
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
                entity_data_by_type["props"],
                _point_pools,
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
            coord_data = [
                build_coord_out(c, _coord_variant_count, map_to_module, _sub_pool_info, _point_pools) for c in _coords
            ]
            _save(f"coords/{_entity_name}.json", coord_data)
            entity_page_map[_entity_name] = f"coords/{_entity_name}"
            _orphan_count += 1
        if _orphan_count:
            pipe.log(f"[JSON] orphan coord files: {_orphan_count}")

        pipe.log(f"[JSON] ENTITY_PAGE_MAP built: {len(entity_page_map)} entities")

        with pipe.step("lootdrops") as ctx:
            _lootdrop_started = time.perf_counter()
            loot_index = build_loot_index(
                merged_loot,
                items,
                monsters,
                entity_class,
                resolver.resolve,
                translations,
            )
            for entry in loot_index:
                entry["translation_key"] = resolve_translation_key(entry["name"], entry.get("translation_key"))
                entry["monster_translation_keys"] = [
                    resolve_translation_key(name, key)
                    for name, key in zip(
                        entry.get("monsters", []),
                        entry.get("monster_translation_keys", []),
                        strict=False,
                    )
                ]
            _save("lootdrops.json", loot_index)
            ctx.set_result(f"{len(loot_index)} items")
            pipe.log(f"[PERF] lootdrops index: {time.perf_counter() - _lootdrop_started:.3f}s")

        used_translation_keys: set[str] = set()
        for _entry in loot_index:
            _category_key = _entry.get("item_category_key", "")
            if _category_key:
                used_translation_keys.add(_category_key)
            used_translation_keys.update(_entry.get("item_subtype_keys") or [])
        lootdrop_group_info_by_item: dict[str, dict[str, list[dict]]] = {}
        _lootdrop_details_started = time.perf_counter()
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
            used_translation_keys,
            lootdrop_group_info_by_item,
            _point_pools,
        )
        pipe.log(f"[PERF] lootdrops details: {time.perf_counter() - _lootdrop_details_started:.3f}s")
        pipe.log("[JSON] lootdrops detail files DONE")

        _drop_rows_started = time.perf_counter()
        loot_pool_rows = load_drop_rows(db, drop_engine)
        pipe.log(
            f"[PERF] loot pool rows: {len(loot_pool_rows)} rows " f"({time.perf_counter() - _drop_rows_started:.3f}s)"
        )

        _monster_drops_started = time.perf_counter()
        _monster_drops_n = attach_loot_pools(
            entity_data_by_type["monsters"],
            db,
            translations,
            drop_engine,
            rows=loot_pool_rows,
        )
        pipe.log(
            f"[JSON] monster loot_pools: {_monster_drops_n} monsters "
            f"({time.perf_counter() - _monster_drops_started:.3f}s)"
        )

        _props_drops_started = time.perf_counter()
        _props_drops_n = attach_loot_pools(
            entity_data_by_type["props"],
            db,
            translations,
            drop_engine,
            fold_quality=False,
            rows=loot_pool_rows,
        )
        pipe.log(
            f"[JSON] props loot_pools: {_props_drops_n} props " f"({time.perf_counter() - _props_drops_started:.3f}s)"
        )

        with pipe.step("dungeon shops export") as ctx:
            region_labels = {region: translations.get(key, region) for region, key in REGION_LABEL_KEY.items()}
            # Shop rows carry quality-suffixed names (HealingPotion_5001) while
            # the detail page uses the folded name (HealingPotion); index the
            # already-resolved lootdrop labels by page so items link and label.
            shop_item_index = {
                entry["name"]: {
                    "page": entry["name"],
                    "translation": entry.get("translation", ""),
                    "translation_key": entry.get("translation_key", ""),
                }
                for entry in loot_index
            }
            shop_data = build_shop_data(
                db.get_ingame_merchants(),
                translations,
                shop_item_index,
                region_labels,
            )
            save_shop_data(shop_data, OUTPUT_DIR)
            ctx.set_result(f"{len(shop_data['index']['regions'])} regions")

        with pipe.step("lights export") as ctx:
            lights_payload = build_and_save_lights(
                db.get_light_items(),
                db.get_environment_lights(),
                items,
                resolver.resolve,
                OUTPUT_DIR,
            )
            light_count = lights_payload["count"]
            ctx.set_result(
                f"{light_count} light items, {len(lights_payload['items'])} variants, "
                f"{len(lights_payload['environment'])} environment props"
            )

        with pipe.step("crafts export") as ctx:
            craft_data = db.get_craft_data()
            # Reuse the effect summaries already resolved for the shop export:
            # both pages read the same DB table, so there is no second query.
            shop_merchant_data = db.get_ingame_merchants()
            crafts_payload = build_and_save_crafts(
                craft_data["merchants"],
                craft_data["recipes"],
                items,
                resolver.resolve,
                OUTPUT_DIR,
                item_properties=db.get_item_properties(),
                property_pools=db.get_item_property_pools(),
                item_effects=shop_merchant_data["effects"],
            )
            craft_count = crafts_payload["count"]
            ctx.set_result(
                f"{craft_count} merchants, {crafts_payload['group_count']} groups, "
                f"{crafts_payload['recipe_count']} recipes"
            )

        _lootdrop_enrichment_started = time.perf_counter()
        enrich_all_entities(
            drop_engine,
            loot_index,
            entity_data_by_type,
            lootdrop_group_info_by_item,
            OUTPUT_DIR,
            pipe.log,
        )
        pipe.log(f"[PERF] lootdrops enrichment: {time.perf_counter() - _lootdrop_enrichment_started:.3f}s")

        with pipe.step("quest data export") as ctx:
            print("\nExporting quest data from DB...")
            quest_items_count, quest_npc_count, quest_npcs_data = save_quest_data(db, OUTPUT_DIR)
            print(f"  quest items: {quest_items_count}, quest NPCs: {quest_npc_count}")
            ctx.set_result(f"items={quest_items_count}, npcs={quest_npc_count}")

        with pipe.step("quest_items_groups"):
            generate_quest_items_groups(
                db,
                merged_loot,
                resolver.resolve,
                all_coords,
                modules,
                OUTPUT_DIR,
                group_label_resolver=lambda g: _resolve_group_display(g, translations),
            )

        with pipe.step("search_index") as ctx:
            index_data = build_and_save_indexes(
                items_index,
                monsters_index,
                props_index,
                loot_index,
                modules_data,
                quest_items_count,
                quest_npc_count,
                quest_npcs_data,
                OUTPUT_DIR,
                group_label_resolver=lambda g: _resolve_group_display(g, translations),
                shop_index=shop_data["index"],
                light_count=light_count,
                crafts_payload=crafts_payload,
            )
            ctx.set_result("DONE")

        with pipe.step("locale export") as ctx:
            locale_langs = build_locale_files(db, OUTPUT_DIR, used_translation_keys)
            search_index_langs = build_search_index_files(db, OUTPUT_DIR)
            ctx.set_result(f"locale={len(locale_langs)}, search_index={len(search_index_langs)} languages")

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
