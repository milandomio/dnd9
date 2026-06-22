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
    TRANSLATION_ALIAS_MAP,
)
from db_manager import DatabaseManager
from drop_rate import DropRateEngine, _round_rate
from entity_export import export_items, export_monsters, export_props
from index_export import build_and_save_indexes, generate_quest_items_groups, save_quest_data
from layout_utils import load_all_layout_rotations
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
    HARD_SUFFIX_RE,
    QUALITY_RE,
    UNIQUE_SUFFIX_RE,
    VARIANT_RE,
    NameResolver,
    base_monster_name,
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
    loot_raw = db.get_lootdrop_relationships()
    loot_map: dict[str, set[str]] = {}
    for r in loot_raw:
        loot_map.setdefault(r["item_name"], set()).add(r["monster_name"])

    # detect variant families (_\d{4} suffix, ≥2 members)
    families: dict[str, list[str]] = {}
    for item_name in loot_map:
        m = VARIANT_RE.match(item_name)
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
        m = VARIANT_RE.match(item_name)
        base = m.group(1) if m else item_name
        merged_loot.setdefault(base, set()).update(monster_set)
    merged_loot = {k: sorted(v) for k, v in merged_loot.items()}
    print(f"  variant families merged: {len(families)} ({len(skip_variants)} variants skipped)")
    print(f"  unique items after merge: {len(merged_loot)}")

    # split _8001 variants: keep as own entry (monsters are shared with base)
    _variant_override: dict[str, int] = {}
    for base, variants in list(families.items()):
        _8001 = [v for v in variants if v.endswith("_8001")]
        if not _8001:
            continue
        v8001 = _8001[0]
        skip_variants.discard(v8001)
        merged_loot[v8001] = sorted(loot_map.get(v8001, []))
        _variant_override[base] = len(variants) - 1
    if _variant_override:
        print(f"  _8001 variants split: {len(_variant_override)} bases affected")

    # -- Inject SuperHoard spawners as separate monster entries --
    _superhoard_map: dict[str, list[str]] = {}
    for _row in (
        db.connect()
        .execute(
            "SELECT DISTINCT spawner_keyword, entity_name FROM spawner_entries WHERE entity_name IN ('Hoard01_9', 'HoardChest01') AND spawner_keyword != entity_name"
        )
        .fetchall()
    ):
        _sk, _en = _row
        _superhoard_map.setdefault(_en, []).append(_sk)
    for _mons in merged_loot.values():
        for _en, _sks in _superhoard_map.items():
            if _en in _mons:
                for _sk in _sks:
                    if _sk not in _mons:
                        _mons.append(_sk)
    merged_loot = {k: sorted(v) for k, v in merged_loot.items()}

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
    items_lookup = {r["item_name"]: r for r in items}
    monsters_lookup = {r["monster_name"]: r for r in monsters}
    loot_index = []
    for item_name, monster_names in merged_loot.items():
        item_row = items_lookup.get(item_name)
        translation = (
            resolver.resolve(item_name, item_row["translation_key"] if item_row else None, "item")
            if item_row
            else (resolver.resolve(item_name, None, "item") or item_name)
        )
        mon_translations = []
        for m in sorted(monster_names):
            cls = entity_class.get(m)
            if cls and "item" in cls["types"]:
                item_row = items_lookup.get(m)
                if item_row:
                    mon_translations.append(resolver.resolve(m, item_row["translation_key"], "item"))
                    continue
                tk = cls.get("translation_key", "")
                if tk:
                    mon_translations.append(resolver.resolve(m, tk, "item"))
                    continue
            elif cls and "props" in cls["types"]:
                mon_translations.append(resolver.resolve(m, cls.get("translation_key", ""), "props"))
                continue
            # Try direct monster lookup
            mon_row = monsters_lookup.get(m)
            if mon_row:
                mon_translations.append(resolver.resolve(m, mon_row["translation_key"], "monster"))
                continue
            # Try stripping _Hard/_VeryHard suffix → base monster lookup
            base = HARD_SUFFIX_RE.sub("", m) if HARD_SUFFIX_RE.search(m) else m
            if base != m:
                mon_row = monsters_lookup.get(base)
                if mon_row:
                    mon_translations.append(resolver.resolve(base, mon_row["translation_key"], "monster"))
                    continue
            # Try stripping trailing Unique → base monster lookup (e.g. FrostImpUnique → FrostImp)
            base2 = UNIQUE_SUFFIX_RE.sub("", base) if UNIQUE_SUFFIX_RE.search(base) else base
            if base2 != base:
                mon_row = monsters_lookup.get(base2)
                if mon_row:
                    mon_translations.append(resolver.resolve(base2, mon_row["translation_key"], "monster"))
                    continue
            # Try entity_class translation key as fallback
            if cls and cls.get("translation_key"):
                mon_translations.append(resolver.resolve(m, cls["translation_key"], cls["types"][0]))
                continue
            # Generic fallback
            mon_translations.append(resolver.resolve(m, None, "monster") or m)
        variant_count = _variant_override.get(item_name, item_row.get("variant_count", 1) if item_row else 1)
        # Merge _Hard/_VeryHard/Unique variants in loot_index too
        merged_names: list[str] = []
        merged_translations: list[str] = []
        seen_bases: set[str] = set()
        for mn, mt in zip(monster_names, mon_translations, strict=False):
            # Skip self-referencing
            if mn == item_name:
                continue
            base = HARD_SUFFIX_RE.sub("", mn)
            base = QUALITY_RE.sub("", base)
            base = UNIQUE_SUFFIX_RE.sub("", base)
            if base not in seen_bases:
                seen_bases.add(base)
                merged_names.append(mn)
                merged_translations.append(mt)
        loot_index.append(
            {
                "name": item_name,
                "translation": translation,
                "variant_count": variant_count,
                "monsters": sorted(merged_names),
                "monster_translations": merged_translations,
            }
        )
    loot_index.sort(key=lambda x: x["translation"] or x["name"])
    _save("lootdrops.json", loot_index)
    _log(f"[JSON] lootdrops index DONE -> {len(loot_index)} items")

    # ── lootdrops detail files ──
    _log("[JSON] lootdrops detail files START")
    _MONSTER_COLORS = [  # noqa: N806
        "#E74C3C",
        "#3498DB",
        "#2ECC71",
        "#F39C12",
        "#9B59B6",
        "#1ABC9C",
        "#E67E22",
        "#2980B9",
        "#27AE60",
        "#D35400",
        "#8E44AD",
        "#16A085",
        "#C0392B",
        "#2C3E50",
        "#7F8C8D",
        "#FF6B35",
        "#00BFFF",
        "#FFD700",
        "#FF69B4",
        "#32CD32",
        "#FF4500",
        "#9370DB",
        "#00FA9A",
        "#DC143C",
        "#00CED1",
    ]

    # ── 预加载爆率数据 ──
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

    # 翻译 variant_names（_coord_variant_count 已在管道开头计算，此处补充翻译）
    for _key, (_cnt, _raw_names) in list(_coord_variant_count.items()):
        if _raw_names:
            _translated: list[str] = []
            for _kw in _raw_names:
                _cls = entity_class.get(_kw, {})
                _mon_row = monsters_lookup.get(_kw)
                if _mon_row:
                    _translated.append(resolver.resolve(_kw, _mon_row["translation_key"], "monster"))
                elif _cls and "props" in _cls.get("types", []):
                    _translated.append(resolver.resolve(_kw, _cls.get("translation_key", ""), "props"))
                else:
                    _translated.append(_kw)
            _coord_variant_count[_key] = (_cnt, _translated)

    _loot_detail_count = 0
    _loot_detail_total = len(loot_index)
    _item_max_score: dict[str, float] = {}
    _log(f"[JSON] lootdrop detail loop starting: {_loot_detail_total} items")

    def _classify_label(label: str, entity_name: str) -> str:
        if not label:
            return "direct"
        # Strip quality suffix for matching (e.g. SkeletonFootmanFromFakeDeath_Unique → SkeletonFootmanFromFakeDeath)
        en_base = QUALITY_RE.sub("", entity_name)
        if label == en_base or label.startswith(en_base + "_"):
            return "direct"
        if "Random" in label:
            return "random"
        if "Special" in label or "ChestLarge" in label:
            return "special"
        return "other"

    _label_type_suffix = {
        "direct": "",
        "special": "(特殊)",
        "random": "(随机)",
        "other": "",
    }

    for entry in loot_index:
        item_name = entry["name"]
        merged: dict[str, dict] = {}
        for _i, m_name in enumerate(entry["monsters"]):
            if m_name == item_name:
                continue
            coords = all_coords.get(m_name, [])
            if not coords:
                # Try stripping quality suffix for coord lookup
                _m_base = QUALITY_RE.sub("", m_name)
                if _m_base != m_name:
                    coords = all_coords.get(_m_base, [])
            if not coords:
                alias = TRANSLATION_ALIAS_MAP.get(m_name)
                if alias:
                    coords = all_coords.get(alias, [])
            if not coords:
                alt_keywords = _og_to_keywords.get(m_name, set())
                for _ak in sorted(alt_keywords):
                    _c = all_coords.get(_ak, [])
                    if _c:
                        coords = _c
                        break
            # 按 _entity_spawners 过滤：只保留当前实体确实关联的生成器坐标
            _valid_sk = _entity_spawners.get(m_name, set())
            if _valid_sk:
                coords = [
                    c for c in coords if c.get("keyword", "") in _valid_sk or c.get("original_keyword", "") in _valid_sk
                ]
            if not coords:
                continue
            m_trans = entry["monster_translations"][_i]
            base = base_monster_name(m_name)
            locked_base = m_name.replace("_Locked", "")
            is_locked = locked_base != m_name
            if is_locked:
                base = base_monster_name(locked_base)
            # Group coords by spawner-keyword label type
            coords_by_type: dict[str, list[dict]] = {}
            for _c in coords:
                _t = _classify_label(_c.get("original_keyword", ""), m_name)
                coords_by_type.setdefault(_t, []).append(_c)
            for _type, _typed_coords in coords_by_type.items():
                _suffix = _label_type_suffix.get(_type, "")
                _type_trans = m_trans + _suffix if _suffix else m_trans
                _use_suffix = _suffix != ""
                _unique_name = base if not _use_suffix else f"{base}_{_type}"
                _merge_key = f"{m_trans}|{_type}"
                _existing = merged.get(_merge_key)
                if _existing is not None:
                    _existing["_bases"].add(base)
                    if is_locked:
                        _existing["_has_locked"] = True
                else:
                    merged[_merge_key] = {
                        "name": m_name,
                        "entity_name": m_name,
                        "translation": _type_trans,
                        "color": _MONSTER_COLORS[len(merged) % len(_MONSTER_COLORS)],
                        "coords": [],
                        "_has_locked": False,
                        "_bases": {base, m_name},
                    }
                if is_locked:
                    merged[_merge_key]["_has_locked"] = True
                for _c in _typed_coords:
                    _raw_label = _c.get("original_keyword") or _c.get("keyword", "")
                    coord_out = {
                        "x": _c["x"],
                        "y": _c["y"],
                        "z": _c["z"],
                        "yaw": _c.get("yaw", 0),
                        "map": _c["map_base"],
                        "file": _c["json_filename"],
                        "version": _c["version"],
                        "label": _raw_label,
                    }
                    _vc_info = _coord_variant_count.get(
                        (_c["map_base"], _c["json_filename"], _c.get("group_parent", ""))
                    )
                    if _vc_info and _vc_info[0] > 1:
                        coord_out["variant_count"] = _vc_info[0]
                        coord_out["variant_names"] = _vc_info[1]
                    if _c.get("keyword") != _c.get("original_keyword", ""):
                        _pair = (_c["keyword"], m_name)
                        _sr = _spawn_rate_detail.get(_pair, 100) if _pair else _spawn_rate_cache.get(m_name, 100)
                    else:
                        _sr = _spawn_rate_cache.get(m_name, 100)
                    coord_out["spawn_rate"] = _sr
                    merged[_merge_key]["coords"].append(coord_out)
        # 计算 per-group 爆率（在 dedup 之前，保留 _has_locked 标记）
        _group_drop_info: dict[str, list[dict]] = {}
        for _base, _m_data in merged.items():
            _has_locked = _m_data.get("_has_locked", False)
            _seen_groups: set[str] = set()
            for _c in _m_data["coords"]:
                _g = _map_base_to_group.get(_c["map"], "")
                if _g:
                    _seen_groups.add(_g)
            for _g in _seen_groups:
                _dr = drop_engine.get_group_drop_rates(item_name, _m_data.get("entity_name", _m_data["name"]), _g)
                if not _dr:
                    # 即使爆率为0，只要有该怪物在此分组有坐标就保留
                    _dr = {"PVE": 0, "普通": 0, "豪客赛": 0}
                _en = _m_data.get("entity_name", _m_data["name"])
                # For locked-merged entries: 取共同生成器中上锁+未上锁 spawn_rate 之和
                if _has_locked:
                    _locked_name = (
                        _en.replace("_UnderSea", "_Locked_UnderSea") if "_UnderSea" in _en else _en + "_Locked"
                    )
                    _common_sks = _entity_spawners.get(_en, set()) & _entity_spawners.get(_locked_name, set())
                    _best_rate = 0
                    for _sk in _common_sks:
                        _ul_sr = _spawn_rate_detail.get((_sk, _en), 0)
                        _l_sr = _spawn_rate_detail.get((_sk, _locked_name), 0)
                        _rate = _ul_sr + _l_sr
                        if _rate > _best_rate:
                            _best_rate = _rate
                    _sr = (
                        _best_rate
                        if _best_rate > 0
                        else max(_spawn_rate_cache.get(_bn, 100) for _bn in (_m_data.get("_bases") or {_en}))
                    )
                else:
                    _sr = max(_spawn_rate_cache.get(_bn, 100) for _bn in (_m_data.get("_bases") or {_en}))
                _en_mode_rates = _spawn_rate_by_mode.get(("", _en), {})
                _sr_by_mode: dict[str, float] = {}
                if _en_mode_rates:
                    for _mn in ("PVE", "普通", "豪客赛"):
                        if _mn in _en_mode_rates:
                            # Map group may restrict which grades are relevant
                            _sr_by_mode[_mn] = _en_mode_rates[_mn]
                _has_varied_spawn = len(set(_sr_by_mode.values())) > 1
                _group_drop_info.setdefault(_g, []).append(
                    {
                        "translation": _m_data["translation"],
                        "spawn_rate": _sr,
                        "drop_rates": _dr,
                        "_variant": _m_data.get("entity_name", _m_data["name"]),
                    }
                )
                if _has_varied_spawn:
                    _group_drop_info[_g][-1]["spawn_rates"] = _sr_by_mode
        # Deduplicate coords and update translation for locked-merged entries
        for _base_data in merged.values():
            if _base_data.pop("_has_locked", False):
                _old = _base_data["translation"]
                _base_data["translation"] += "(可能上锁)"
                for _g_list in _group_drop_info.values():
                    for _entry in _g_list:
                        if _entry["translation"] == _old:
                            _entry["translation"] = _base_data["translation"]
                _bn = _base_data.get("entity_name", _base_data["name"])
                _ln = _bn.replace("_UnderSea", "_Locked_UnderSea") if "_UnderSea" in _bn else _bn + "_Locked"
                _common = _entity_spawners.get(_bn, set()) & _entity_spawners.get(_ln, set())
                _combined_rate = 0
                for _sk in _common:
                    _ul = _spawn_rate_detail.get((_sk, _bn), 0)
                    _ll = _spawn_rate_detail.get((_sk, _ln), 0)
                    _r = _ul + _ll
                    if _r > _combined_rate:
                        _combined_rate = _r
                seen: set[tuple] = set()
                deduped = []
                for _c in _base_data["coords"]:
                    _k = (_c["x"], _c["y"], _c["z"], _c["file"])
                    if _k not in seen:
                        seen.add(_k)
                        deduped.append(_c)
                _base_data["coords"] = deduped
        # 质量变体去重：同一翻译只保留最高优先级变体（Elite > Nightmare > Common）
        for _g_list in _group_drop_info.values():
            _best: dict[str, dict] = {}
            for _entry in _g_list:
                _trans = _entry["translation"]
                _m = QUALITY_RE.search(_entry.get("_variant", ""))
                _prio = {"Elite": 3, "Nightmare": 2, "Common": 1}.get(_m.group(1) if _m else "", -1)
                if _trans not in _best or _prio > _best[_trans].get("_q_prio", -1):
                    _best[_trans] = _entry
                    _best[_trans]["_q_prio"] = _prio
            _g_list[:] = list(_best.values())
            for _entry in _g_list:
                _entry.pop("_variant", None)
                _entry.pop("_q_prio", None)
        # 按生成概率×豪客赛爆率降序排列（乘积越大越优先显示）
        for _g_list in _group_drop_info.values():
            _g_list.sort(key=lambda x: x["spawn_rate"] * x["drop_rates"].get("豪客赛", 0), reverse=True)

        # 计算每个坐标的 score（spawn_rate × 豪客赛爆率 / 100）
        _hk_lookup: dict[str, dict[str, float]] = {}
        for _g, _entries in _group_drop_info.items():
            for _entry in _entries:
                _hkl = _hk_lookup.setdefault(_entry["translation"], {})
                _hkl[_g] = _entry["drop_rates"].get("豪客赛", 0)
        for _base_data in merged.values():
            _trans = _base_data["translation"]
            _hk_map = _hk_lookup.get(_trans, {})
            for _c in _base_data["coords"]:
                _g = _map_base_to_group.get(_c["map"], "")
                _hk = _hk_map.get(_g, 0)
                _score = (_c.get("spawn_rate", 0) or 0) * _hk / 100
                _c["score"] = round(_score, 4)
            _base_data["coords"] = [c for c in _base_data["coords"] if c["score"] > 0]
        merged = {k: v for k, v in merged.items() if v["coords"]}
        for _v in merged.values():
            _v.pop("_bases", None)
        monsters_out = list(merged.values())
        # 预计算每个怪物的最大参考爆率（跨所有分组取 spawn_rate × 豪客赛 / 100 最大值）
        _max_scores: dict[str, float] = {}
        for _g_list in _group_drop_info.values():
            for _entry in _g_list:
                _trans = _entry["translation"]
                _score = round(_entry["spawn_rate"] * _entry["drop_rates"].get("豪客赛", 0) / 100, 4)
                if _trans not in _max_scores or _score > _max_scores[_trans]:
                    _max_scores[_trans] = _score
        for _m in monsters_out:
            _m["max_score"] = _max_scores.get(_m["translation"], -1)
        if monsters_out:
            _save(
                f"lootdrops/{item_name}.json",
                {
                    "name": item_name,
                    "translation": entry["translation"],
                    "monsters": monsters_out,
                    "group_drop_info": _group_drop_info,
                },
            )
            _item_max_score[item_name] = max(_max_scores.values(), default=0.0)
        elif item_name == "BloodsapBlade":
            _log(
                f"[DEBUG] BloodsapBlade: merged={ {k: v.get('translation','?') for k, v in merged.items()} }, group_drop_info={ {g: len(v) for g,v in _group_drop_info.items()} }"
            )
            for _i, m_name in enumerate(entry["monsters"]):
                _log(f"[DEBUG]   monster: {m_name}, trans={entry['monster_translations'][_i]}")
                coords = all_coords.get(m_name, [])
                _log(f"[DEBUG]     all_coords direct: {len(coords)}")
                _m_base = QUALITY_RE.sub("", m_name)
                if _m_base != m_name:
                    coords2 = all_coords.get(_m_base, [])
                    _log(f"[DEBUG]     all_coords base '{_m_base}': {len(coords2)}")
                _valid_sk = _entity_spawners.get(m_name, set())
                _log(f"[DEBUG]     _valid_sk: {_valid_sk}")
        _loot_detail_count += 1
        if _loot_detail_count % 100 == 0:
            _log(f"[JSON] lootdrops detail: {_loot_detail_count}/{_loot_detail_total}")
    _log(f"[JSON] lootdrops detail files DONE -> {_loot_detail_count} items")

    # ── 回写 lootdrops.json index，添加 max_score 和分类信息 ──
    _log("[JSON] updating lootdrops index with max_score...")
    for _entry in loot_index:
        _iname = _entry["name"]
        _entry["max_score"] = _item_max_score.get(_iname, 0.0)
    _save("lootdrops.json", loot_index)
    _log(f"[JSON] lootdrops index update DONE -> {len(loot_index)} items")

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
                _suffix = _label_type_suffix.get(_type, "")
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
                    _suffix = _label_type_suffix.get(_type, "")
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
