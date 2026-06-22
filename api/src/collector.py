import json
import os
from pathlib import Path

from config import (
    DB_PATH,
    DUNGEON_MODE_NAMES,
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
    MODULE_GROUP_FLOOR_SUFFIXES,
    MONSTER_DIR,
    OUTPUT_DIR,
    PROPS_DIR,
    SPAWNER_DIR,
)
from db_manager import DatabaseManager
from drop_rate import DropRateEngine, _round_rate
from entity_export import export_items, export_monsters, export_props
from index_export import build_and_save_indexes, generate_quest_items_groups, save_quest_data
from layout_utils import load_all_layout_rotations
from lootdrop_builder import (
    _LABEL_TYPE_SUFFIX,
    _classify_label,
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
from pipeline_timer import PipelineTimer
from quest_collector import run_quest_extraction
from search_engine import extract_all_spawners, load_all_spawner_data
from translator import (
    NameResolver,
)

_log_file = None


def _log(msg: str):
    from datetime import datetime

    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if _log_file:
        _log_file.write(line + "\n")
        _log_file.flush()


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
    """Return True if DB is missing or older than any source file."""
    if not db_path.exists():
        return True
    db_mtime = db_path.stat().st_mtime
    latest_source = _get_newest_mtime(_SOURCE_PATHS)
    return db_mtime < latest_source


def _ue_asset_base_name(asset_path: str) -> str:
    """Extract base name from UE asset path like '/Game/.../Id_Foo.Id_Foo' → 'Id_Foo'."""
    if not asset_path:
        return ""
    part = asset_path.rsplit("/", 1)[-1]
    if "." in part:
        part = part.split(".")[0]
    return part


def run():
    global _log_file
    print("=" * 50)
    print("  DarkFindV5 - Data Collector")
    print("=" * 50)

    timer = PipelineTimer(log_dir=LOG_DIR)

    # Open real-time log file
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime

    _log_file = open(  # noqa: SIM115
        LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", "w", encoding="utf-8"
    )

    _log("checking DB staleness...")
    db_stale = _is_db_stale(DB_PATH)
    if db_stale and DB_PATH.exists():
        DB_PATH.unlink()
    _log(f"DB stale={db_stale}, creating DatabaseManager...")
    db = DatabaseManager(DB_PATH)
    _log("DatabaseManager ready")

    game_available = GAME_ROOT.exists() and db_stale

    _log("get_entity_classification START")
    entity_class = db.get_entity_classification()
    _log(f"get_entity_classification DONE -> {len(entity_class)}")

    if game_available:
        # 1. Import translations
        timer.start_step("[DB] translations")
        _log("[1/9] import_translations START")
        count = db.import_translations()
        _log(f"[1/9] import_translations DONE -> {count}")

        # 2. Import items
        timer.start_step("[DB] items")
        _log("[2/9] import_items START")
        count = db.import_items()
        _log(f"[2/9] import_items DONE -> {count}")

        # 3. Import monsters
        timer.start_step("[DB] monsters")
        _log("[3/9] import_monsters START")
        count = db.import_monsters()
        _log(f"[3/9] import_monsters DONE -> {count}")

        # 4. Import props
        timer.start_step("[DB] props")
        _log("[4/9] import_props START")
        count = db.import_props()
        _log(f"[4/9] import_props DONE -> {count}")

        # 5. Import dungeon modules
        timer.start_step("[DB] dungeon modules")
        _log("[5/9] import_dungeon_modules START")
        count = db.import_dungeon_modules()
        _log(f"[5/9] import_dungeon_modules DONE -> {count}")

        # 6. Import lootdrops (with raw variant names)
        timer.start_step("[DB] lootdrop relationships")
        _log("[6/9] get_monster_name_map START")
        monster_name_map = db.get_monster_name_map()
        _log(f"[6/9] get_monster_name_map DONE -> {len(monster_name_map)}")
        _log("[6/9] load_all_spawner_data START")
        spawner_has_lootdrop, spawner_multi_entity, spawner_monster_map = load_all_spawner_data(monster_name_map)
        _log(
            f"[6/9] load_all_spawner_data DONE -> has_lootdrop={len(spawner_has_lootdrop)}, multi_entity={len(spawner_multi_entity)}, monster_map={len(spawner_monster_map)}"
        )
        _log("[6/9] import_lootdrops START")
        count = db.import_lootdrops(spawner_monster_map)
        _log(f"[6/9] import_lootdrops DONE -> {count}")

        # 7. Build spawner matches via direct keyword matching (no AC automaton)
        timer.start_step("[DB] spawner matches")
        _log("[7/9] extract_all_spawners START")
        spawners = extract_all_spawners(
            has_lootdrop_map=spawner_has_lootdrop, multi_entity_spawners=spawner_multi_entity
        )
        _log(f"[7/9] extract_all_spawners DONE -> {len(spawners)} spawners")

        # Store spawners in DB
        _log("[7/9] storing spawners in DB...")
        c = db.connect()
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
            )
            for idx, s in enumerate(spawners)
        ]
        c.executemany(
            "INSERT INTO spawners (id, keyword, original_keyword, spawner_type, has_lootdrop, x, y, z, yaw, json_filename, version, map_base, group_parent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            spawner_rows,
        )
        db.connect().commit()
        _log("[7/9] spawners stored in DB")

        # 7.5. Add spawner fallback entities
        _log("[7.5/9] import_spawner_fallback_entities START")
        added = db.import_spawner_fallback_entities()
        _log(f"[7.5/9] import_spawner_fallback_entities DONE -> {added}")

        # 7.6. Build mutually_exclusive_groups table
        _log("[7.6/9] building mutually_exclusive_groups...")
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
        _log(f"[7.6/9] mutually_exclusive_groups DONE -> {len(group_rows)} groups")

        # 8. Quest extraction
        timer.start_step("[DB] quest extraction")
        _log("[8/9] run_quest_extraction START")
        explore_data, quest_items_data, quest_npcs_data = run_quest_extraction(entity_classification=entity_class)
        _log(
            f"[8/9] run_quest_extraction DONE -> explore={len(explore_data)}, items={len(quest_items_data)}, npcs={len(quest_npcs_data)}"
        )
        _log("[8/9] importing quest data to DB...")
        db.import_explore_targets(explore_data)
        db.import_quest_items(quest_items_data)
        db.import_quest_npcs(quest_npcs_data)
        _log("[8/9] quest data imported to DB")

        # 9. Import lootdrop rate data (爆率)
        timer.start_step("[DB] lootdrop rate data")
        _log("[9/9] import_spawner_entries START")
        count = db.import_spawner_entries()
        _log(f"[9/9] import_spawner_entries DONE -> {count}")
        _log("[9/9] import_lootdrop_groups START")
        count = db.import_lootdrop_groups()
        _log(f"[9/9] import_lootdrop_groups DONE -> {count}")
        _log("[9/9] import_lootdrop_rate_items START")
        count = db.import_lootdrop_rate_items()
        _log(f"[9/9] import_lootdrop_rate_items DONE -> {count}")
        _log("[9/9] import_lootdrop_rate_weights START")
        count = db.import_lootdrop_rate_weights()
        _log(f"[9/9] import_lootdrop_rate_weights DONE -> {count}")
    else:
        if not GAME_ROOT.exists():
            print("\n[SKIP] Game data not found, using existing DB")
        else:
            print("\n[SKIP] DB is up to date (newest source file older than DB), using existing DB")

    # 后续步骤从 DB 读取（无论是否导入，DB 中都有数据）
    _log("[JSON] loading entities from DB...")
    items = db.get_item_entities()
    monsters = db.get_monster_entities()
    props = db.get_props_entities()
    _log(f"[JSON] entities loaded: items={len(items)}, monsters={len(monsters)}, props={len(props)}")
    _log("[JSON] get_all_coordinates START")
    all_coords = db.get_all_coordinates()
    _log(f"[JSON] get_all_coordinates DONE -> {len(all_coords)} entity keys")
    _coord_variant_count = db.get_coord_variant_counts()
    _log(f"[JSON] get_coord_variant_counts DONE -> {len(_coord_variant_count)} variant groups")

    # Build original_keyword → keyword mapping for multi-entity spawner resolution
    # (e.g. "Jellyfish" → {Jellyfish_Tiny, Jellyfish_Small, Jellyfish_Medium, Jellyfish_Large})
    _og_to_keywords: dict[str, set[str]] = {}
    for _kw, _clist in all_coords.items():
        for _c in _clist:
            _og = _c.get("original_keyword", "")
            if _og and _og != _kw and _og not in all_coords:
                _og_to_keywords.setdefault(_og, set()).add(_kw)

    # Query spawner info for props (spawner_type, has_lootdrop) to determine entity type
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

    # Entity name sets for coord type filtering (prevents cross-type contamination)
    _item_names = {r["item_name"] for r in items}
    _monster_names = {r["monster_name"] for r in monsters}
    _prop_names = {r["asset_name"] for r in props}

    # ─── Export JSON ───
    print("\nExporting JSON files...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    translations = db.get_translations_map()

    resolver = NameResolver(translations)

    # ── Build merged lootdrop map with variant family merging ──
    _log("[JSON] building merged lootdrop map...")
    merged_loot, skip_variants, _variant_override = build_merged_loot_map(db)

    # ── items: index + individual files ──
    timer.start_step("[JSON] items")
    _log("[JSON] items export START")
    items_index = export_items(
        items, merged_loot, all_coords, resolver.resolve, skip_variants, _coord_variant_count, _item_names, OUTPUT_DIR
    )
    _log(f"[JSON] items export DONE -> {len(items_index)} items")

    # ── monsters: index + individual files (merged by translation) ──
    timer.start_step("[JSON] monsters")
    _log("[JSON] monsters export START")
    monsters_index = export_monsters(
        monsters, all_coords, resolver.resolve, _coord_variant_count, _monster_names, OUTPUT_DIR
    )
    _log(f"[JSON] monsters export DONE -> {len(monsters_index)} monsters")

    # ── props: index + individual files (merged by translation) ──
    timer.start_step("[JSON] props")
    _log("[JSON] props export START")
    props_index = export_props(
        props, all_coords, resolver.resolve, _props_spawner_info, _coord_variant_count, _prop_names, OUTPUT_DIR
    )
    _log(f"[JSON] props export DONE -> {len(props_index)} props")

    # ── dungeon_modules.json ──
    timer.start_step("[JSON] dungeon modules")
    _log("[JSON] dungeon_modules export START")
    module_rotations = load_all_layout_rotations()
    modules = db.get_dungeon_modules()
    modules_map = build_modules_map(db, resolver.resolve, module_rotations)
    map_to_module, module_to_maps = build_map_mappings(modules_map)
    merged_coords = build_and_save_module_coords(
        db, modules_map, map_to_module, resolver.resolve, items, monsters, props, OUTPUT_DIR
    )
    modules_data = build_and_save_modules_data(modules_map, module_to_maps, merged_coords, OUTPUT_DIR)
    _log(f"[JSON] dungeon_modules export DONE -> {len(modules_data)} modules")

    # ── lootdrops.json (grouped by item for list page) ──
    timer.start_step("[JSON] lootdrops")
    _log("[JSON] lootdrops export START")
    loot_index = build_loot_index(merged_loot, items, monsters, entity_class, resolver.resolve, _variant_override)
    _save("lootdrops.json", loot_index)
    _log(f"[JSON] lootdrops index DONE -> {len(loot_index)} items")

    # ── lootdrops detail files ──
    _log("[JSON] lootdrops detail files START")
    _log("[JSON] preloading drop rate data...")
    drop_engine = DropRateEngine()
    drop_engine.preload(db, modules_data)
    _map_base_to_group = drop_engine.map_base_to_group
    _spawner_ldg = drop_engine.spawner_ldg
    _entity_ldg_all = drop_engine.entity_ldg_all
    _ore_ldg = drop_engine.ore_ldg
    _spawn_rate_cache = drop_engine.spawn_rate_cache
    _spawn_rate_detail = drop_engine.spawn_rate_detail
    _spawn_rate_by_mode = drop_engine.spawn_rate_by_mode
    _entity_spawners = drop_engine.entity_spawners
    _log("[JSON] preloaded drop rate data via DropRateEngine")

    _item_max_score = build_and_save_lootdrop_details(
        loot_index,
        drop_engine,
        all_coords,
        resolver.resolve,
        _og_to_keywords,
        _coord_variant_count,
        entity_class,
        monsters,
        OUTPUT_DIR,
        _log,
    )
    _log("[JSON] lootdrops detail files DONE")

    # ── 更新物品实体 JSON，添加 group_drop_info ──
    _log("[JSON] updating item entities with group drop info...")
    _update_count = 0
    for _entry in loot_index:
        _iname = _entry["name"]
        _loot_path = OUTPUT_DIR / f"lootdrops/{_iname}.json"
        if not _loot_path.exists():
            continue
        with open(_loot_path) as _f:
            _loot_data = json.load(_f)
        _gdi = _loot_data.get("group_drop_info", {})
        if not _gdi:
            continue
        _entity_path = OUTPUT_DIR / f"items/{_iname}.json"
        if not _entity_path.exists():
            continue
        with open(_entity_path) as _f:
            _entity_data = json.load(_f)
        _entity_data["group_drop_info"] = _gdi
        with open(_entity_path, "w") as _f:
            json.dump(_entity_data, _f, ensure_ascii=False, indent=2)
        _update_count += 1
    _log(f"[JSON] updated {_update_count} item entities with group drop info")

    # ── 通过 spawner_entries 的 lootdrop_group_id 计算 group_drop_info（覆盖容器数据）──
    _log("[JSON] computing group_drop_info from ID_LootDropGroup...")
    _direct_count = 0
    for _item_file in (OUTPUT_DIR / "items").glob("*.json"):
        with open(_item_file) as _f:
            _entity_data = json.load(_f)
        _iname = _entity_data["name"]
        _ldg_id = _spawner_ldg.get(_iname, "")
        if not _ldg_id:
            continue
        _coords = _entity_data.get("coords", [])
        if not _coords:
            continue
        _seen_groups: set[str] = set()
        for _c in _coords:
            _g = _map_base_to_group.get(_c["map"], "")
            if _g:
                _seen_groups.add(_g)
        if not _seen_groups:
            continue
        _group_drop_info: dict[str, list[dict]] = {}
        for _g in _seen_groups:
            _suffixes = MODULE_GROUP_FLOOR_SUFFIXES.get(_g, [])
            if not _suffixes:
                continue
            _mode_rates: dict[str, float] = {}
            for _mode_id, _mode_name in DUNGEON_MODE_NAMES.items():
                if _mode_id == 4:
                    continue
                _best_rate = 0.0
                for _suffix in _suffixes:
                    _full_grade = _mode_id * 1000 + _suffix
                    _rate = drop_engine.compute_drop_rate(_ldg_id, _iname, _full_grade)
                    if _rate > _best_rate:
                        _best_rate = _rate
                _mode_rates[_mode_name] = _round_rate(_best_rate * 100)
            _group_drop_info[_g] = [
                {
                    "translation": _entity_data["translation"],
                    "spawn_rate": 100,
                    "drop_rates": _mode_rates,
                }
            ]
        if _group_drop_info:
            _entity_data["group_drop_info"] = _group_drop_info
            with open(_item_file, "w") as _f:
                json.dump(_entity_data, _f, ensure_ascii=False, indent=2)
            _direct_count += 1
    _log(f"[JSON] computed group_drop_info for {_direct_count} direct-spawn items")

    # ── 变体爆率聚合已禁用：variant_count 仅作为显示信息，不影响爆率计算 ──

    # ── 更新怪物实体 JSON，添加 group_drop_info ──
    _log("[JSON] updating monster entities with group drop info...")
    _mon_update = 0
    for _mfile in (OUTPUT_DIR / "monsters").glob("*.json"):
        with open(_mfile) as _f:
            _edata = json.load(_f)
        _mname = _edata["name"]
        # 查找 lootdrop_group_id（含后缀回退）
        _ldg_id = _spawner_ldg.get(_mname, "")
        if not _ldg_id:
            for _suffix in ("_Elite", "_Nightmare", "_Common"):
                _ldg_id = _spawner_ldg.get(_mname + _suffix, "")
                if _ldg_id:
                    break
        if not _ldg_id:
            _lower = _mname.lower()
            for _k, _v in _spawner_ldg.items():
                if _k.lower() == _lower:
                    _ldg_id = _v
                    break
        if not _ldg_id:
            continue
        _coords = _edata.get("coords", [])
        if not _coords:
            continue
        _seen_groups: set[str] = set()
        for _c in _coords:
            _g = _map_base_to_group.get(_c["map"], "")
            if _g:
                _seen_groups.add(_g)
        if not _seen_groups:
            continue
        _group_drop_info: dict[str, list[dict]] = {}
        _sr = _spawn_rate_cache.get(_mname, 0.0)
        for _g in _seen_groups:
            _dr = drop_engine.compute_group_drop_rates(_ldg_id, _g)
            if not _dr and not _sr:
                continue
            _group_drop_info[_g] = [
                {
                    "translation": _edata["translation"],
                    "spawn_rate": _sr,
                    "drop_rates": _dr,
                }
            ]
        if _group_drop_info:
            _edata["group_drop_info"] = _group_drop_info
            with open(_mfile, "w") as _f:
                json.dump(_edata, _f, ensure_ascii=False, indent=2)
            _mon_update += 1
    _log(f"[JSON] updated {_mon_update} monster entities with group drop info")

    # ── 更新实体（props）JSON，添加 group_drop_info ──
    _log("[JSON] updating props entities with group drop info...")
    _prop_update = 0
    for _pfile in (OUTPUT_DIR / "props").glob("*.json"):
        with open(_pfile) as _f:
            _edata = json.load(_f)
        _pname = _edata["name"]
        _ldg_id = _spawner_ldg.get(_pname, "")
        if not _ldg_id:
            _lower = _pname.lower()
            for _k, _v in _spawner_ldg.items():
                if _k.lower() == _lower:
                    _ldg_id = _v
                    break
        if not _ldg_id:
            _ldg_id = _ore_ldg.get(_pname, "")
        if not _ldg_id:
            continue
        _coords = _edata.get("coords", [])
        if not _coords:
            continue
        # Build per-keyword-type entries: {(is_undersea, type): {translation, spawn_rate}}
        _kw_entries: dict[tuple[bool, str], dict] = {}
        _locked_name = _pname + "_Locked"
        _undersea_name = _pname + "_UnderSea"
        _locked_undersea = _pname + "_Locked_UnderSea"
        _base_trans = _edata["translation"]
        for _sk in _entity_spawners.get(_pname, set()):
            _base = _spawn_rate_detail.get((_sk, _pname), 0)
            _lock = _spawn_rate_detail.get((_sk, _locked_name), 0) if _locked_name in _entity_spawners else 0
            _combined = _base + _lock
            if _combined > 0:
                _type = _classify_label(_sk, _pname)
                _suffix = _LABEL_TYPE_SUFFIX.get(_type, "")
                _label = _base_trans + _suffix + ("(可能上锁)" if _lock > 0 else "")
                _key = (False, _type)
                if _key not in _kw_entries or _combined > _kw_entries[_key]["spawn_rate"]:
                    _kw_entries[_key] = {"translation": _label, "spawn_rate": _combined}
        if _undersea_name in _entity_spawners:
            for _sk in _entity_spawners[_undersea_name]:
                _base = _spawn_rate_detail.get((_sk, _undersea_name), 0)
                _lock = (
                    _spawn_rate_detail.get((_sk, _locked_undersea), 0) if _locked_undersea in _entity_spawners else 0
                )
                _combined = _base + _lock
                if _combined > 0:
                    _type = _classify_label(_sk, _undersea_name)
                    _suffix = _LABEL_TYPE_SUFFIX.get(_type, "")
                    _label = "(海底)" + _base_trans + _suffix + ("(可能上锁)" if _lock > 0 else "")
                    _key = (True, _type)
                    if _key not in _kw_entries or _combined > _kw_entries[_key]["spawn_rate"]:
                        _kw_entries[_key] = {"translation": _label, "spawn_rate": _combined}
        if not _kw_entries:
            continue
        _seen_groups: set[str] = set()
        for _c in _coords:
            _g = _map_base_to_group.get(_c["map"], "")
            if _g:
                _seen_groups.add(_g)
        if not _seen_groups:
            continue
        _group_drop_info: dict[str, list[dict]] = {}
        for _g in _seen_groups:
            _dr = drop_engine.compute_container_drop_rates(_ldg_id, _g)
            if not _dr:
                continue
            _group_drop_info[_g] = [{**_entry, "drop_rates": _dr} for _entry in _kw_entries.values()]
        if _group_drop_info:
            _edata["group_drop_info"] = _group_drop_info
            with open(_pfile, "w") as _f:
                json.dump(_edata, _f, ensure_ascii=False, indent=2)
            _prop_update += 1
    _log(f"[JSON] updated {_prop_update} props entities with group drop info")

    # ── props 变体爆率聚合已禁用 ──

    # ── 清理：移除所有爆率为 0 的条目 ──
    _log("[JSON] cleaning up zero-rate entries...")
    _clean_count = 0
    for _subdir in ("items", "props", "monsters"):
        for _efile in (OUTPUT_DIR / _subdir).glob("*.json"):
            with open(_efile) as _f:
                _edata = json.load(_f)
            _gdi = _edata.get("group_drop_info")
            if not _gdi:
                continue
            _changed = False
            _new_gdi: dict[str, list[dict]] = {}
            for _g, _entries in _gdi.items():
                _filtered = [e for e in _entries if any(v > 0 for v in e.get("drop_rates", {}).values())]
                if _filtered:
                    _new_gdi[_g] = _filtered
                if len(_filtered) != len(_entries):
                    _changed = True
            if _changed:
                if _new_gdi:
                    _edata["group_drop_info"] = _new_gdi
                else:
                    del _edata["group_drop_info"]
                with open(_efile, "w") as _f:
                    json.dump(_edata, _f, ensure_ascii=False, indent=2)
                _clean_count += 1
    _log(f"[JSON] cleaned {_clean_count} files with zero-rate entries")

    # ── Quest data (from DB) ──
    timer.start_step("[JSON] quest data")
    _log("[JSON] quest data export START")
    print("\nExporting quest data from DB...")
    explore_count, quest_items_count, quest_npc_count, quest_npcs_data = save_quest_data(db, OUTPUT_DIR)
    print(f"  explore: {explore_count}, quest items: {quest_items_count}, quest NPCs: {quest_npc_count}")

    # ── Quest items groups (with coordinates) ──
    timer.start_step("[JSON] quest items groups")
    _log("[JSON] quest_items_groups START")
    generate_quest_items_groups(db, merged_loot, resolver.resolve, all_coords, modules, OUTPUT_DIR)
    _log("[JSON] quest_items_groups DONE")

    # ── index.json + search_index.json ──
    timer.start_step("[JSON] search index")
    _log("[JSON] search_index START")
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
    )
    _log("[JSON] search_index DONE")

    print(f"\n[DONE] Output written to {OUTPUT_DIR}")
    for entry in index_data:
        if "page" in entry:
            print(f"  {entry['page']}: {entry['count']}")

    _log("pipeline complete, closing DB")
    db.close()
    if _log_file:
        _log_file.close()
        _log_file = None
    return timer


def _save(filename: str, data: list | dict):
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
