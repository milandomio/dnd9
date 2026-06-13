import json
import os
import re
from pathlib import Path

from config import (
    DB_PATH,
    DUNGEON_MODULE_DIR,
    GAME_JSON,
    GAME_ROOT,
    GROUP_TO_ART_DIR,
    HARDCODED_TRANSLATIONS,
    IMG_SRC,
    ITEM_DIR,
    LAYOUT_DIR,
    LOOTDROP_DIR,
    LOOTDROP_GROUP_DIR,
    MAPS_DIR,
    MODULE_DISPLAY_OVERRIDE,
    MODULE_NAME_OVERRIDE,
    MODULE_OFFSET_MAP,
    MONSTER_DIR,
    OUTPUT_DIR,
    PROPS_DIR,
    SPAWNER_DIR,
    TRANSLATION_ALIAS_MAP,
)
from db_manager import DatabaseManager
from layout_utils import load_all_layout_rotations
from quest_collector import run_quest_extraction
from search_engine import _load_spawner_data_assets, build_all_matches

_VARIANT_RE = re.compile(r"^(.+)_\d{4}$")
_HARD_SUFFIX_RE = re.compile(r"_(Hard|VeryHard)$")
_UNIQUE_SUFFIX_RE = re.compile(r"Unique$")
_QUALITY_RE = re.compile(r"_(Common|Elite|Nightmare|Unique)$")
_ORE_QUALITY_RE = re.compile(r"^(?:Ore_)?(.+?)(?:_)?(?:High|Med|Low|VeryLow|Random)$")
_ORE_ITEM_STRIP_RE = re.compile(r"^(Cobalt|Copper|FrostStone|Gold|Iron|Obsidian|Rubysilver|Tidestone)Ores$")
_ORE_ITEM_COORD_RE = re.compile(r"^(Cobalt|Copper|FrostStone|Gold|Iron|Obsidian|Rubysilver|Tidestone)Ores$")
_RESOLVE_STRIP_RE = re.compile(r"_(?:\d+|Common|Elite|Nightmare|Hard|VeryHard|Unique|VeryLow|Low|Med|High|Random)$")
# 模糊后缀：先于 HARDCODED 兜底，用这些后缀剥离后重试 Game.json 前缀匹配
_RESOLVE_FUZZY_RE = re.compile(
    r"(?:"
    r"_[Rr]"  # _R（棺材变体）
    r"|_On$|_Off$"  # 开关状态
    r"|_Lit$|_Unlit$"  # 灯光状态
    r"|__UnderSea$"  # 海底变体（双下划线）
    r"|_UnderSea$"  # 海底变体
    r"|Random$"  # 随机变体（含 BlackRoseRandom 无下划线前缀）
    r"|_(?:Elite|Nightmare)$"  # 难度变体
    r"|(?:_0[1-9])$"  # 编号后缀 _01~_09
    r")"
)
# 第二轮模糊：On/Off + 中间段 + 尾部数字组合剥离（迭代应用）
_RESOLVE_FUZZY_PASS2_RE = re.compile(
    r"(?:"
    r"_On$|_Off$"  # 尾部 On/Off
    r"|_Lit$|_Unlit$"  # 尾部灯光
    r"|_[A-Z](?!\w)$"  # 单字母后缀 _A _B
    r"|_\w+_(?:On|Off|Lit|Unlit)$"  # 中间段+状态 Torch02_Purple_On
    r"|_\d+(?:_(?:On|Off|Lit|Unlit))?$"  # 尾部数字+可选状态 _03_On
    r"|_\d+(?:On|Off|ON|OFF)$"  # 尾部数字+状态（无间隔）_01ON
    r"|(?:\d+(?:On|Off|ON|OFF))$"  # 无下划线数字+状态 Roaster07On
    r"|(?:\d+)$"  # 尾部纯数字（剥离 On 后残留）Torch03
    r"|_Ruins$|_Cave$|_Crypt$"  # 地图变体后缀
    r")"
)
_DEBUG_VARIANT_RE = re.compile(r"_(?:Resize|Test|BossTest|DistantView)$")

# Props 目录中的 _Dummy 实体同时也是怪物
_DUMMY_AS_MONSTER = {
    "LivingArmor",
    "LivingStatue",
    "LivingArmor_Elite",
    "LivingArmor_Nightmare",
    "LivingStatue_Elite",
    "LivingStatue_Nightmare",
}


_SOURCE_PATHS = [
    GAME_JSON,
    ITEM_DIR,
    MONSTER_DIR,
    PROPS_DIR,
    DUNGEON_MODULE_DIR,
    LOOTDROP_DIR,
    LOOTDROP_GROUP_DIR,
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


def _load_spawner_lootdrop_monster_map(
    monster_name_map: dict[str, str],
) -> dict[str, list[str]]:
    """Build mapping: lootdrop_group_name → [canonical monster_names].

    Reads DCSpawnerDataAsset files, extracts MonsterId→LootDropGroupId links
    from SpawnerItemArray, then resolves each MonsterId to the canonical
    monster_name via monster_name_map.
    """
    if not SPAWNER_DIR.exists():
        return {}

    ldg_to_monsters: dict[str, set[str]] = {}
    for json_file in SPAWNER_DIR.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, list) or not data:
            continue
        entry = data[0]
        if entry.get("Type") != "DCSpawnerDataAsset":
            continue
        props = entry.get("Properties", {}) or {}
        items = props.get("SpawnerItemArray", []) or []
        for item in items:
            ldg = item.get("LootDropGroupId") or {}
            ldg_asset = ldg.get("AssetPathName", "")
            if not ldg_asset:
                continue
            ldg_name = _ue_asset_base_name(ldg_asset)
            if not ldg_name:
                continue
            # Strip lootdrop group prefix
            for pfx in ("ID_LootDropGroup_", "Id_LootDropGroup_"):
                if ldg_name.startswith(pfx):
                    ldg_name = ldg_name[len(pfx) :]
                    break
            mid = item.get("MonsterId") or {}
            mid_asset = mid.get("AssetPathName", "")
            if not mid_asset:
                # Fall back to PropsId for container spawners
                pid = item.get("PropsId") or {}
                mid_asset = pid.get("AssetPathName", "")
                if not mid_asset:
                    continue
            mid_name = _ue_asset_base_name(mid_asset)
            if not mid_name:
                continue
            # Strip monster/props prefix, then strip quality suffix to get base name
            for pfx in ("Id_Monster_", "Id_Props_"):
                if mid_name.startswith(pfx):
                    mid_name = mid_name[len(pfx) :]
                    break
            mid_name = _QUALITY_RE.sub("", mid_name)
            # Resolve to canonical monster_name via entity map
            canonical = monster_name_map.get(mid_name.lower(), mid_name)
            ldg_to_monsters.setdefault(ldg_name, set()).add(canonical)

    return {k: sorted(v) for k, v in ldg_to_monsters.items()}


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
        monster_name_map = db.get_monster_name_map()
        spawner_monster_map = _load_spawner_lootdrop_monster_map(monster_name_map)
        count = db.import_lootdrops(spawner_monster_map)
        print(f"  -> {count} lootdrop relationships")

        # 7. Build spawner matches via search engine
        print("[7/7] Building spawner matches...")
        _search_term_set: set[str] = set()
        for r in db.get_item_entities():
            _search_term_set.add(r["item_name"])
        for r in db.get_monster_entities():
            _search_term_set.add(r["monster_name"])
        for r in db.get_props_entities():
            name = r["asset_name"]
            m = _ORE_QUALITY_RE.match(name)
            if m:
                _search_term_set.add(m.group(1))
            _search_term_set.add(name)
        search_terms = sorted(_search_term_set)
        # Clean ore item names: GoldOres → GoldOre (add stripped form for spawner matching)
        for t in list(search_terms):
            m = _ORE_ITEM_STRIP_RE.match(t)
            if m:
                _search_term_set.add(m.group(1) + "Ore")
        search_terms = sorted(_search_term_set)
        matches, spawners = build_all_matches(search_terms)
        print(f"  -> {len(spawners)} spawners, {len(matches)} matched terms")

        # Store spawners in DB
        c = db.connect()
        c.execute("DELETE FROM spawners")
        c.execute("DELETE FROM search_term_matches")
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
            )
            for idx, s in enumerate(spawners)
        ]
        c.executemany(
            "INSERT INTO spawners (id, keyword, original_keyword, spawner_type, has_lootdrop, x, y, z, yaw, json_filename, version, map_base) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            spawner_rows,
        )
        db.connect().commit()

        # 7.5. Add spawner fallback entities and rebuild matches
        print("[7.5/8] Adding spawner fallback entities...")
        added = db.import_spawner_fallback_entities()
        print(f"  -> added: {added['item']} items, {added['monster']} monsters, {added['props']} props")

        # Rebuild search terms including fallback entities
        _search_term_set = set()
        for r in db.get_item_entities():
            _search_term_set.add(r["item_name"])
        for r in db.get_monster_entities():
            _search_term_set.add(r["monster_name"])
        for r in db.get_props_entities():
            name = r["asset_name"]
            m = _ORE_QUALITY_RE.match(name)
            if m:
                _search_term_set.add(m.group(1))
            _search_term_set.add(name)
        # Add all spawner keywords as search terms
        cur = db.connect().cursor()
        cur.execute("SELECT DISTINCT keyword FROM spawners")
        for row in cur.fetchall():
            _search_term_set.add(row["keyword"])
        search_terms = sorted(_search_term_set)
        for t in list(search_terms):
            m = _ORE_ITEM_STRIP_RE.match(t)
            if m:
                _search_term_set.add(m.group(1) + "Ore")
        search_terms = sorted(_search_term_set)

        # Re-match search terms to spawners
        from config import SPAWNER_ALIAS_MAP
        from search_engine import build_automaton, match_keyword

        auto = build_automaton(search_terms)
        cur.execute("SELECT id, keyword FROM spawners")
        all_spawners_db = cur.fetchall()
        match_rows = []
        for row in all_spawners_db:
            sid = row["id"]
            kw = SPAWNER_ALIAS_MAP.get(row["keyword"], row["keyword"])
            matched_terms = match_keyword(kw, set(search_terms), auto)
            for term in matched_terms:
                match_rows.append((term, sid))
        cur.executemany(
            "INSERT OR IGNORE INTO search_term_matches (search_term, spawner_id) VALUES (?, ?)",
            match_rows,
        )
        db.connect().commit()
        print(f"  -> {len(match_rows)} search term matches")

        # 8. Quest extraction
        print("[8/8] Extracting quest data...")
        entity_class = db.get_entity_classification()
        explore_data, quest_items_data, quest_npcs_data = run_quest_extraction(entity_classification=entity_class)
        db.import_explore_targets(explore_data)
        db.import_quest_items(quest_items_data)
        db.import_quest_npcs(quest_npcs_data)
        print(f"  -> {len(explore_data)} explore, {len(quest_items_data)} quest items, {len(quest_npcs_data)} NPCs")
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

    # Entity name sets for coord type filtering (prevents cross-type contamination)
    _item_names = {r["item_name"] for r in items}
    _monster_names = {r["monster_name"] for r in monsters}
    _prop_names = {r["asset_name"] for r in props}

    def _filter_coords(coords: list[dict], entity_names: set[str], is_prop: bool = False) -> list[dict]:
        """Keep only coords whose original_keyword belongs to the target entity type."""

        def _match(c):
            kw = c["original_keyword"]
            st = c.get("spawner_type", "")
            return bool(kw in entity_names or (is_prop and kw.startswith("Ore_")) or (is_prop and st == "props"))

        return [c for c in coords if _match(c)]

    # ─── Export JSON ───
    print("\nExporting JSON files...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    translations = db.get_translations_map()

    cracked_re = re.compile(r"（裂开）")

    def resolve_name(name: str, translation_key: str, scope: str = "item") -> str:
        result = _resolve_name_inner(name, translation_key, scope)
        return cracked_re.sub("", result)

    def _resolve_name_inner(name: str, translation_key: str, scope: str) -> str:
        if translation_key and translation_key in translations:
            return translations[translation_key]
        alias_name = TRANSLATION_ALIAS_MAP.get(name, name)
        for prefix in [
            "Text_DesignData_Item_Item_",
            "Text_DesignData_Monster_Monster_",
            "Text_DesignData_Props_Props_",
            "Text_DesignData_Dungeon_DungeonModule_",
            "Text_DesignData_Emote_Emote_",
            "Text_DesignData_ActionSkin_",
        ]:
            alias_key = prefix + alias_name
            if alias_key in translations:
                return translations[alias_key]
        if name in HARDCODED_TRANSLATIONS:
            return HARDCODED_TRANSLATIONS[name]
        # 模糊后缀剥离后重试 Game.json 前缀匹配
        fuzzy = _RESOLVE_FUZZY_RE.sub("", name)
        if fuzzy != name:
            fuzzy_alias = TRANSLATION_ALIAS_MAP.get(fuzzy, fuzzy)
            for prefix in [
                "Text_DesignData_Item_Item_",
                "Text_DesignData_Monster_Monster_",
                "Text_DesignData_Props_Props_",
                "Text_DesignData_Dungeon_DungeonModule_",
                "Text_DesignData_Emote_Emote_",
                "Text_DesignData_ActionSkin_",
            ]:
                fuzzy_key = prefix + fuzzy_alias
                if fuzzy_key in translations:
                    return translations[fuzzy_key]
        # 第二轮模糊：On/Off+数字/中间段 组合剥离（迭代最多3次）
        prev = name
        fuzzy2 = name
        for _ in range(3):
            fuzzy2 = _RESOLVE_FUZZY_PASS2_RE.sub("", fuzzy2)
            if fuzzy2 == prev:
                break
            prev = fuzzy2
        if fuzzy2 != name and fuzzy2 != fuzzy:
            fuzzy2_alias = TRANSLATION_ALIAS_MAP.get(fuzzy2, fuzzy2)
            for prefix in [
                "Text_DesignData_Item_Item_",
                "Text_DesignData_Monster_Monster_",
                "Text_DesignData_Props_Props_",
                "Text_DesignData_Dungeon_DungeonModule_",
                "Text_DesignData_Emote_Emote_",
                "Text_DesignData_ActionSkin_",
            ]:
                fuzzy2_key = prefix + fuzzy2_alias
                if fuzzy2_key in translations:
                    return translations[fuzzy2_key]
        # 剥离末尾数字/难度/矿石品质后缀后重试翻译
        stripped = _RESOLVE_STRIP_RE.sub("", name)
        if stripped != name:
            if stripped in HARDCODED_TRANSLATIONS:
                return HARDCODED_TRANSLATIONS[stripped]
            stripped_alias = TRANSLATION_ALIAS_MAP.get(stripped, stripped)
            for prefix in [
                "Text_DesignData_Item_Item_",
                "Text_DesignData_Monster_Monster_",
                "Text_DesignData_Props_Props_",
                "Text_DesignData_Dungeon_DungeonModule_",
                "Text_DesignData_Emote_Emote_",
                "Text_DesignData_ActionSkin_",
            ]:
                stripped_key = prefix + stripped_alias
                if stripped_key in translations:
                    return translations[stripped_key]
        if scope == "module":
            if name in MODULE_NAME_OVERRIDE:
                return MODULE_NAME_OVERRIDE[name]
            for group_prefix in [
                "Firedeep_",
                "Inferno_",
                "Crypt_",
                "Ruins_",
                "GoblinCave_",
                "Goblin_",
                "IceCavern_",
                "IceCave_",
                "IceAbyss_",
                "ShipGraveyard_",
                "Shipgraveyard_",
                "Swamp_",
                "Cave_",
            ]:
                if name.startswith(group_prefix):
                    stripped = name[len(group_prefix) :]
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
    items_index = []
    for r in items:
        name = r["item_name"]
        if name in skip_variants:
            continue
        coords = _filter_coords(all_coords.get(name, []), _item_names)
        # Try ore name cleaning: GoldOres → GoldOre
        if not coords:
            m = _ORE_ITEM_COORD_RE.match(name)
            if m:
                coords = _filter_coords(all_coords.get(m.group(1) + "Ore", []), _item_names)
        if not coords:
            continue
        translation = resolve_name(name, r["translation_key"], "item")
        variant_count = r.get("variant_count", 1)
        items_index.append(
            {
                "name": name,
                "translation": translation,
                "category": r["category"],
                "variant_count": variant_count,
                "monsters": merged_loot.get(name, []),
                "coordCount": len(coords),
            }
        )
        _save(
            f"items/{name}.json",
            {
                "name": name,
                "translation": translation,
                "category": r["category"],
                "variant_count": variant_count,
                "monsters": merged_loot.get(name, []),
                "coords": [
                    {
                        "x": c["x"],
                        "y": c["y"],
                        "z": c["z"],
                        "yaw": c.get("yaw", 0),
                        "map": c["map_base"],
                        "file": c["json_filename"],
                        "version": c["version"],
                        "label": c["original_keyword"],
                    }
                    for c in coords
                ],
            },
        )
    _save("items.json", items_index)

    # ── monsters: index + individual files ──
    monsters_index = []
    for r in monsters:
        coords = _filter_coords(all_coords.get(r["monster_name"], []), _monster_names)
        if not coords:
            continue
        translation = resolve_name(r["monster_name"], r["translation_key"], "monster")
        monsters_index.append(
            {
                "name": r["monster_name"],
                "translation": translation,
                "coordCount": len(coords),
            }
        )
        _save(
            f"monsters/{r['monster_name']}.json",
            {
                "name": r["monster_name"],
                "translation": translation,
                "coords": [
                    {
                        "x": c["x"],
                        "y": c["y"],
                        "z": c["z"],
                        "yaw": c.get("yaw", 0),
                        "map": c["map_base"],
                        "file": c["json_filename"],
                        "version": c["version"],
                        "label": c["original_keyword"],
                    }
                    for c in coords
                ],
            },
        )
    _save("monsters.json", monsters_index)

    # ── props: index + individual files (merged by translation) ──
    _ORE_QUALITY_ORDER = {"VeryLow": 0, "Low": 1, "Med": 2, "High": 3}  # noqa: N806

    def _ore_quality_key(r):
        m = re.search(r"_(High|Med|Low|VeryLow)$", r["asset_name"])
        return _ORE_QUALITY_ORDER.get(m.group(1), 99) if m else 99

    props_index = []
    props_by_translation: dict[str, list[dict]] = {}
    for r in sorted(props, key=_ore_quality_key):
        translation = resolve_name(r["asset_name"], r["translation_key"], "props")
        # Ore quality variants without translation: normalize to base ore name
        if translation == r["asset_name"]:
            m = _ORE_QUALITY_RE.match(r["asset_name"])
            if m:
                translation = m.group(1) if m.group(1).startswith("Ore_") else "Ore_" + m.group(1)
        props_by_translation.setdefault(translation, []).append(r)
    for translation, group in props_by_translation.items():
        merged_coords = []
        seen_coords: set[tuple] = set()
        for r in group:
            coords = _filter_coords(all_coords.get(r["asset_name"], []), _prop_names, is_prop=True)
            for c in coords:
                key = (c["x"], c["y"], c["z"], c["map_base"], c["json_filename"])
                if key not in seen_coords:
                    seen_coords.add(key)
                    merged_coords.append(c)
        # Also try matching via cleaned ore name
        if not merged_coords:
            for r in group:
                m = _ORE_QUALITY_RE.match(r["asset_name"])
                if m:
                    coords = _filter_coords(all_coords.get(m.group(1), []), _prop_names, is_prop=True)
                    for c in coords:
                        key = (c["x"], c["y"], c["z"], c["map_base"], c["json_filename"])
                        if key not in seen_coords:
                            seen_coords.add(key)
                            merged_coords.append(c)
                    if merged_coords:
                        break
        if not merged_coords:
            continue
        # For merged ore quality variants, use English base ore name as key
        name_key = group[0]["asset_name"]
        if len(group) > 1:
            m = _ORE_QUALITY_RE.match(name_key)
            if m:
                name_key = m.group(1)
        props_index.append(
            {
                "name": name_key,
                "translation": translation,
                "coordCount": len(merged_coords),
            }
        )
        _save(
            f"props/{name_key}.json",
            {
                "name": name_key,
                "translation": translation,
                "coords": [
                    {
                        "x": c["x"],
                        "y": c["y"],
                        "z": c["z"],
                        "yaw": c.get("yaw", 0),
                        "map": c["map_base"],
                        "file": c["json_filename"],
                        "version": c["version"],
                        "label": c["original_keyword"],
                    }
                    for c in merged_coords
                ],
            },
        )
    _save("props.json", props_index)

    # ── dungeon_modules.json ──
    module_rotations = load_all_layout_rotations()
    modules = db.get_dungeon_modules()
    art_root = (
        Path(__file__).parent.parent.parent.parent
        / "Output"
        / "Exports"
        / "DungeonCrawler"
        / "Content"
        / "DungeonCrawler"
        / "Data"
        / "Art"
        / "DungeonModuleMapImage"
    )
    modules_map: dict[str, dict] = {}
    for r in modules:
        override = MODULE_DISPLAY_OVERRIDE.get(r["module_name"], {})
        sx = override.get("size_x", r["size_x"])
        sy = override.get("size_y", r["size_y"])
        custom_range = override.get("range", 0)
        offset_x, offset_y = MODULE_OFFSET_MAP.get(r["module_name"], (0, 0))
        rot1 = module_rotations.get(r["module_name"])
        rotate = rot1 if rot1 is not None else module_rotations.get(r["sl_base_name"], 270)
        sl = r["sl_base_name"]
        map_image = r.get("map_image_name", "")
        module_name = r["module_name"]
        PLACEHOLDERS = ("RareModule_1x1", "UnderConstruction_1x1")  # noqa: N806

        def _try_resolve(name: str):
            """Return (resolved_name, status). status: 'found'|'not_found'|'no_art'."""
            resolved, status = _resolve_img(art_root, r["module_group"], name, IMG_SRC)  # noqa: B023
            if resolved in PLACEHOLDERS:  # noqa: B023
                return resolved, status  # placeholder — don't accept
            return resolved, status

        img_name, art_status = _try_resolve(sl)

        # Priority logic:
        # 1. sl_base_name (SubLevelAsset) — always primary
        # 2. module_name — only when Art dir exists AND sl was not found
        # 3. MapImage — last resort
        if art_status == "no_art":
            # No Art dir → sl is the best guess (matches webp in img/ dir)
            # BUT if MapImage is a placeholder, the module's own image might differ from sl
            if map_image in PLACEHOLDERS and module_name != sl:
                candidate, c_status = _try_resolve(module_name)
                if c_status in ("no_art", "found"):
                    img_name = candidate
        elif art_status == "not_found":
            # Art dir exists but no match for sl → try module_name (may differ)
            if module_name != sl:
                candidate, c_status = _try_resolve(module_name)
                if c_status == "found":
                    img_name = candidate
                elif c_status == "not_found":
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
        if art_status in ("not_found", "no_art") and img_name not in PLACEHOLDERS:  # noqa: SIM102
            if not (IMG_SRC / f"{img_name}.webp").exists() and module_name:
                stripped = re.sub(r"_[A-Z]$", "", module_name)
                if stripped != module_name and (IMG_SRC / f"{stripped}.webp").exists():
                    img_name = stripped

        # Final fallback: if nothing matched and the only candidate was a placeholder,
        # keep the placeholder so the frontend shows RareModule_1x1.webp.
        # Only when Art was searched (not_found) AND sl == module_name (single source) AND MapImage was a placeholder.
        if not img_name or img_name in PLACEHOLDERS:
            img_name = module_name or ""
        elif art_status == "not_found" and img_name == module_name == sl and map_image in PLACEHOLDERS:
            img_name = map_image
        has_img = (IMG_SRC / f"{img_name}.webp").exists()
        # Final fallback: no image found → use placeholder so frontend shows a fallback
        if not has_img:
            img_name = "RareModule_1x1"
            has_img = True
        aliases = r.get("aliases", []) or []
        modules_map[r["module_name"]] = {
            "name": r["module_name"],
            "translation_key": r["translation_key"],
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
            "aliases": aliases,
        }
    for override_name, override_translation in MODULE_NAME_OVERRIDE.items():
        if override_name not in modules_map:
            resolved_name, _ = _resolve_img(art_root, "", override_name, IMG_SRC)
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
                "rotate": 270,
                "range": 0,
            }
    # ── 模块名 ↔ 地图名 双向映射 ──
    # map_base → module_name（正向：地图名查模块名）
    map_to_module: dict[str, str] = {}
    # module_name → {关联的所有 map_base}（反向：模块名查地图名）
    module_to_maps: dict[str, set[str]] = {}
    # 第一遍：建立直接映射 (module_name → module_name)
    for mn in modules_map:
        map_to_module[mn] = mn
        module_to_maps.setdefault(mn, set()).add(mn)
    # 第二遍：建立 sl_base 映射 (sl_base → module_name)
    # DungeonModule JSON 定义的模块名优先于地图文件名，允许覆盖直接映射
    # 但如果 sl 已经自映射（自身就是该 sublevel 的主模块），则保留自映射不被覆盖
    for mn, mod in modules_map.items():
        sl = mod["sl_base_name"]
        if sl and sl != mn:
            if map_to_module.get(sl) != sl:
                map_to_module[sl] = mn
            module_to_maps.setdefault(mn, set()).add(sl)

    # ── dungeon_module_coords: per-module entity coordinates ──
    # Build entity classification index from DB (ground truth type)
    entity_class = db.get_entity_classification()
    # _Dummy 实体同时也是怪物，补全 monster 翻译键
    for name in _DUMMY_AS_MONSTER:
        if name in entity_class:
            if "monster" not in entity_class[name]["types"]:
                entity_class[name]["types"].append("monster")
            if not entity_class[name]["translation_key"]:
                base = _QUALITY_RE.sub("", name)
                if base != name:
                    entity_class[name]["translation_key"] = "Text_DesignData_Monster_Monster_" + base
        else:
            base = _QUALITY_RE.sub("", name)
            entity_class[name] = {
                "types": ["props", "monster"],
                "translation_key": "Text_DesignData_Monster_Monster_" + base,
            }
    _save(
        "entity_index.json",
        [
            {"name": n, "types": v["types"], "translation_key": v["translation_key"]}
            for n, v in sorted(entity_class.items())
        ],
    )

    # Build translation lookup from DB entity tables (covers all names including props variants)
    trans_lookup = {}
    for r in items:
        trans_lookup[r["item_name"]] = resolve_name(r["item_name"], r["translation_key"], "item")
    for r in monsters:
        trans_lookup[r["monster_name"]] = resolve_name(r["monster_name"], r["translation_key"], "monster")
    for r in props:
        trans_lookup[r["asset_name"]] = resolve_name(r["asset_name"], r["translation_key"], "props")

    _MODULE_COLORS = [  # noqa: N806
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
    rows = (
        db.connect()
        .execute(
            "SELECT keyword, original_keyword, spawner_type, has_lootdrop, x, y, z, yaw, version, map_base FROM spawners ORDER BY map_base, keyword"
        )
        .fetchall()
    )
    # Load spawner data asset info for decoration classification
    spawner_data_map = _load_spawner_data_assets()
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
            has_ld = row["has_lootdrop"]
            # Determine entity type: decoration (no lootdrop), item (lootdrop type), or props/monster
            if st == "lootdrop":
                mapped_st = "item"
            elif st == "props" and has_ld == 0 and ek in spawner_data_map and not spawner_data_map[ek]:
                # Only mark as decoration if we found the spawner data and it has no lootdrop
                mapped_st = "decoration"
            else:
                mapped_st = st
            if cls:
                types = cls.get("types", [])
                # If mapped_st is decoration, always use it (overrides props classification)
                if mapped_st == "decoration":
                    entity_type = "decoration"
                else:
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
        module_coords[mb]["entities"][ek]["coords"].append(
            {
                "x": row["x"],
                "y": row["y"],
                "z": row["z"],
                "yaw": row["yaw"],
                "version": row["version"] or "",
                "label": row["original_keyword"],
            }
        )
    # 按模块名合并坐标并保存（处理多个 map_base 映射到同一模块的情况）
    merged_coords: dict[str, dict] = {}
    for mb, data in module_coords.items():
        target = map_to_module.get(mb, mb)
        if target not in merged_coords:
            merged_coords[target] = {"map_base": target, "entities": {}}
        for ek, entity in data["entities"].items():
            if ek not in merged_coords[target]["entities"]:
                merged_coords[target]["entities"][ek] = entity
            else:
                merged_coords[target]["entities"][ek]["coords"].extend(entity["coords"])
    # 按 (translation, type) 合并同翻译实体（如 GlowingCoralRoaster01_On/02/03 → 灯架子）
    for target_name, data in merged_coords.items():
        merge_groups: dict[tuple, list[dict]] = {}
        for entity in data["entities"].values():
            key = (entity["translation"], entity["type"])
            merge_groups.setdefault(key, []).append(entity)
        merged_entities = []
        for (_trans, _type), group in merge_groups.items():
            if len(group) == 1:
                merged_entities.append(group[0])
                continue
            canonical = min(group, key=lambda e: len(e["name"]))
            seen: set[tuple] = set()
            deduped = []
            for e in group:
                for c in e["coords"]:
                    ck = (c["x"], c["y"], c["z"], c.get("label", ""))
                    if ck not in seen:
                        seen.add(ck)
                        deduped.append(c)
            merged_entities.append(
                {
                    "name": canonical["name"],
                    "translation": _trans,
                    "type": _type,
                    "color": canonical["color"],
                    "coords": deduped,
                }
            )
        _save(
            f"dungeon_modules_coords/{target_name}.json",
            {
                "map_base": target_name,
                "entities": merged_entities,
            },
        )
    # 清理孤立坐标文件（旧 map_base 命名残留）
    coord_dir = OUTPUT_DIR / "dungeon_modules_coords"
    if coord_dir.exists():
        expected = set(merged_coords.keys())
        for p in coord_dir.iterdir():
            if p.suffix == ".json" and p.stem not in expected:
                p.unlink()
    print(f"  module coords: {len(merged_coords)} modules with coordinates")

    # ── dungeon_modules.json（在坐标构建之后保存，过滤无坐标模块）──
    # 合并使用相同翻译键（相同地图）的模块
    from collections import defaultdict

    translation_groups: dict[str, list[dict]] = defaultdict(list)
    for mod in modules_map.values():
        tk = mod.get("translation_key", "")
        if tk:
            translation_groups[tk].append(mod)
        else:
            # 无翻译键的模块单独处理
            translation_groups[mod["name"]].append(mod)

    merged_modules: list[dict] = []
    for _tk, group in translation_groups.items():
        if len(group) == 1:
            # 单个模块，直接使用
            mod = group[0].copy()
            # 收集所有名称：主名称 + 别名
            all_names = [mod["name"]] + mod.get("aliases", [])
            mod["names"] = list(dict.fromkeys(all_names))  # 去重保序
            merged_modules.append(mod)
        else:
            # 多个模块共享同一翻译，合并
            primary = group[0].copy()
            # 收集所有名称：所有模块主名称 + 所有别名
            all_names = []
            for m in group:
                all_names.append(m["name"])
                all_names.extend(m.get("aliases", []))
            primary["names"] = list(dict.fromkeys(all_names))  # 去重保序
            # 合并 sl_base_name 列表
            all_sl_bases = list(dict.fromkeys(m["sl_base_name"] for m in group if m["sl_base_name"]))
            primary["all_sl_base_names"] = all_sl_bases
            merged_modules.append(primary)

    modules_data = sorted(merged_modules, key=lambda x: x["name"])
    modules_data = [m for m in modules_data if not _DEBUG_VARIANT_RE.search(m["name"])]
    # 过滤无坐标模块（详情页无数据的模块从列表中剔除）
    # 仅当模块自身名字在 merged_coords 中才算有坐标（排除 sl_base 指向其他模块的别名）
    modules_with_coords = {mn for mn in modules_map if mn in merged_coords}
    exempt = set(MODULE_NAME_OVERRIDE.keys())
    before_count = len(modules_data)
    modules_data = [m for m in modules_data if m["name"] in modules_with_coords or m["name"] in exempt]
    # 标记是否含有物品/怪物坐标（仅 props 的模块在列表页默认隐藏）
    for m in modules_data:
        # 合并后的模块检查所有相关地图
        maps = set()
        for name in m.get("names", [m["name"]]):
            maps.update(module_to_maps.get(name, {name}))
        has_useful = False
        for mk in maps:
            if mk in merged_coords:
                for e in merged_coords[mk]["entities"].values():
                    if e["type"] in ("item", "monster"):
                        has_useful = True
                        break
            if has_useful:
                break
        m["has_useful_entities"] = has_useful
    filtered_count = before_count - len(modules_data)
    if filtered_count:
        print(f"  filtered {filtered_count} modules without coordinates")
    _save("dungeon_modules.json", modules_data)

    # ── lootdrops.json (grouped by item for list page) ──
    items_lookup = {r["item_name"]: r for r in items}
    monsters_lookup = {r["monster_name"]: r for r in monsters}
    loot_index = []
    for item_name, monster_names in merged_loot.items():
        item_row = items_lookup.get(item_name)
        translation = (
            resolve_name(item_name, item_row["translation_key"] if item_row else None, "item")
            if item_row
            else (resolve_name(item_name, None, "item") or item_name)
        )
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
        for mn, mt in zip(monster_names, mon_translations, strict=False):
            # Skip self-referencing
            if mn == item_name:
                continue
            base = _HARD_SUFFIX_RE.sub("", mn)
            base = _UNIQUE_SUFFIX_RE.sub("", base)
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

    # ── lootdrops detail files ──
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

    def _base_monster_name(name: str) -> str:
        """Strip _Hard/_VeryHard/Unique suffix to get base name."""
        base = _HARD_SUFFIX_RE.sub("", name)
        base = _UNIQUE_SUFFIX_RE.sub("", base)
        return base

    for entry in loot_index:
        item_name = entry["name"]
        # Build merged monsters: base_name → {name, translation, coords}
        merged: dict[str, dict] = {}
        for _i, m_name in enumerate(entry["monsters"]):
            # Skip self-referencing: item dropping itself (e.g. GoldOres → GoldOres)
            if m_name == item_name:
                continue
            coords = all_coords.get(m_name, [])
            if not coords:
                alias = TRANSLATION_ALIAS_MAP.get(m_name)
                if alias:
                    coords = all_coords.get(alias, [])
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
                merged[base]["coords"].append(
                    {
                        "x": c["x"],
                        "y": c["y"],
                        "z": c["z"],
                        "yaw": c.get("yaw", 0),
                        "map": c["map_base"],
                        "file": c["json_filename"],
                        "version": c["version"],
                        "label": c.get("original_keyword", ""),
                    }
                )
        monsters_out = list(merged.values())
        if monsters_out:
            _save(
                f"lootdrops/{item_name}.json",
                {
                    "name": item_name,
                    "translation": entry["translation"],
                    "monsters": monsters_out,
                },
            )

    # ── Quest data (from DB) ──
    print("\nExporting quest data from DB...")
    explore_data = db.get_explore_targets()
    quest_items_data = db.get_quest_items()
    quest_npcs_data = db.get_quest_npcs()
    explore_count = len(explore_data)
    quest_items_count = len(quest_items_data)
    quest_npc_count = sum(n.get("quest_count", 0) for n in quest_npcs_data)
    _save("explore.json", explore_data)
    _save("quest_items.json", quest_items_data)
    _save("quest_npc.json", quest_npcs_data)
    print(f"  explore: {explore_count}, quest items: {quest_items_count}, quest NPCs: {quest_npc_count}")

    # ── Quest items groups (with coordinates) ──
    _generate_quest_items_groups(db, merged_loot, resolve_name, all_coords, modules)

    # ── index.json: page index ──
    index_data = [
        {
            "_comment": "该文件由 api/src/collector.py 自动生成，请勿手动编辑。如需修改，请编辑 collector.py 中的 index_data 列表。"
        },
        {"page": "items", "label": "物品表", "count": len(items_index)},
        {"page": "props", "label": "实体表", "count": len(props_index)},
        {"page": "monsters", "label": "怪物表", "count": len(monsters_index)},
        {"page": "lootdrops", "label": "掉落表", "count": len(loot_index)},
        {"page": "explore", "label": "探索地点表", "count": explore_count},
        {"page": "quest_items", "label": "任务物品表", "count": quest_items_count},
        {"page": "quest_npc", "label": "任务NPC表", "count": quest_npc_count},
        {"page": "dungeon_modules", "label": "地图模块表", "count": len(modules_data)},
    ]
    _save("index.json", index_data)

    print(f"\n[DONE] Output written to {OUTPUT_DIR}")
    for entry in index_data:
        if "page" in entry:
            print(f"  {entry['page']}: {entry['count']}")

    db.close()


def _generate_quest_items_groups(db, merged_loot, resolve_name, all_coords, modules):
    quest_items_path = OUTPUT_DIR / "quest_items.json"
    if not quest_items_path.exists():
        return
    with open(quest_items_path) as f:
        quest_items = json.load(f)

    # Build map_base -> module_group lookup
    map_to_group = {}
    for m in modules:
        g = m.get("module_group", "") or ""
        if g:
            map_to_group[m["module_name"]] = g
            if m.get("sl_base_name"):
                map_to_group[m["sl_base_name"]] = g

    item_names = sorted(set(qi["item_name"] for qi in quest_items))
    quest_map = {}
    for qi in quest_items:
        quest_map.setdefault(qi["item_name"], []).append(qi)

    _COLORS = [  # noqa: N806
        "#E74C3C",
        "#3498DB",
        "#2ECC71",
        "#E67E22",
        "#9B59B6",
        "#1ABC9C",
        "#F39C12",
        "#2980B9",
        "#D35400",
        "#C0392B",
        "#7F8C8D",
        "#27AE60",
        "#16A085",
        "#8E44AD",
        "#2C3E50",
        "#F1C40F",
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
            groups.setdefault(mt, {"group": mt, "entities": {}})
            ek = f"item::{item_name}"
            if ek not in groups[mt]["entities"]:
                groups[mt]["entities"][ek] = {
                    "name": item_name,
                    "translation": trans,
                    "type": "item",
                    "color": _COLORS[ci % len(_COLORS)],
                    "coords": [],
                    "quest_npcs": [
                        {
                            "npc_name": qi["npc_name"],
                            "npc_name_cn": qi["npc_name_cn"],
                            "quest_number": qi["quest_number"],
                            "count": qi["count"],
                        }
                        for qi in info_list
                    ],
                }
                ci += 1
            groups[mt]["entities"][ek]["coords"].append(
                {
                    "x": c["x"],
                    "y": c["y"],
                    "z": c["z"],
                    "yaw": c.get("yaw", 0),
                    "map": mb,
                    "file": c["json_filename"],
                    "version": c["version"],
                    "label": c["original_keyword"],
                }
            )
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
                groups.setdefault(mt, {"group": mt, "entities": {}})
                ek = f"monster::{mn}"
                if ek not in groups[mt]["entities"]:
                    groups[mt]["entities"][ek] = {
                        "name": mn,
                        "translation": mtrans,
                        "type": "monster",
                        "color": _COLORS[ci % len(_COLORS)],
                        "coords": [],
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
                    groups[mt]["entities"][ek]["coords"].append(
                        {
                            "x": c["x"],
                            "y": c["y"],
                            "z": c["z"],
                            "yaw": c.get("yaw", 0),
                            "map": mb,
                            "file": c["json_filename"],
                            "version": c["version"],
                            "label": c["original_keyword"],
                        }
                    )

    GROUP_LABELS = {  # noqa: N806
        "Crypt": "废墟2层地牢",
        "FireDeep": "哥布林洞穴2层",
        "GoblinCave": "哥布林洞穴1层",
        "IceAbyss": "冰图2层",
        "IceCavern": "冰图1层",
        "Inferno": "废墟3层炼狱",
        "Ruins": "废墟1层",
        "ShipGraveyard": "水图",
    }
    groups_index = []
    for gname in sorted(groups):
        g = groups[gname]
        g["group_display"] = GROUP_LABELS.get(gname, gname)
        entities = list(g["entities"].values())
        for e in entities:
            e.pop("_seen_coords", None)
        pos_count = sum(len(e["coords"]) for e in entities)
        groups_index.append(
            {
                "group": gname,
                "group_display": g["group_display"],
                "entity_count": len(entities),
                "position_count": pos_count,
            }
        )
        _save(
            f"quest_items_groups/{gname}.json",
            {
                "group": gname,
                "group_display": g["group_display"],
                "entities": entities,
            },
        )
    _save("quest_items_groups.json", groups_index)
    print(f"  quest items groups: {len(groups_index)}")


def _match_in_dir(directory: Path, sl: str):
    """Match sl against webp/png files in a flat directory using the same logic as _resolve_img."""
    import re

    files = [p for p in directory.iterdir() if p.suffix.lower() in (".png", ".webp")]
    stems_lower = {p.stem.lower(): p.stem for p in files}
    sl_lower = sl.lower()
    # exact
    if sl_lower in stems_lower:
        return stems_lower[sl_lower], "found"
    # tail
    tail = sl.split("_", 1)[-1] if "_" in sl else sl
    if tail.lower() in stems_lower:
        return stems_lower[tail.lower()], "found"
    # strip numeric suffix
    sl_stripped = re.sub(r"_\d{2,4}$", "", sl)
    if sl_stripped != sl and sl_stripped.lower() in stems_lower:
        return stems_lower[sl_stripped.lower()], "found"
    tail_stripped = re.sub(r"_\d{2,4}$", "", tail)
    if tail_stripped != tail and tail_stripped.lower() in stems_lower:
        return stems_lower[tail_stripped.lower()], "found"
    # strip _Center/_Corner/_Passage
    sl_center = re.sub(r"_(?:Center|Corner|Passage)(?=_\d|$)", "", sl)
    if sl_center != sl and sl_center.lower() in stems_lower:
        return stems_lower[sl_center.lower()], "found"
    # strip debug suffixes
    sl_debug = re.sub(r"_(?:Resize|Test|BossTest|DistantView)$", "", sl)
    if sl_debug != sl and sl_debug.lower() in stems_lower:
        return stems_lower[sl_debug.lower()], "found"
    # numeric prefix
    if sl_stripped != sl:
        prefix = sl_stripped.lower()
        for s, orig in stems_lower.items():
            if s.startswith(prefix):
                return orig, "found"
    return sl, "not_found"


def _resolve_img(art_root: Path, group: str, sl: str, webp_cache: Path | None = None):
    """Return (resolved_name, status).
    Priority: webp cache first (already processed), then Art directory (raw PNG).
    status: 'found', 'not_found' (searched, no match), 'no_art' (no source available).
    """
    import re

    # 1. Always check webp cache first — if a cached webp exists, use it directly
    if webp_cache and webp_cache.exists():
        cached, cache_status = _match_in_dir(webp_cache, sl)
        if cache_status == "found":
            return cached, "found"

    # 2. Fall back to Art directory (raw PNG files)
    if not art_root.exists() or not group:
        return sl, "no_art"
    art_dir_name = GROUP_TO_ART_DIR.get(group, group)
    group_dir = art_root / art_dir_name
    if not group_dir.exists():
        return sl, "no_art"
    # Try exact match (case-insensitive)
    png = group_dir / f"{sl}.png"
    if png.exists():
        return sl, "found"
    for p in group_dir.iterdir():
        if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl.lower():
            return p.stem, "found"
    # Try tail match (part after first underscore)
    tail = sl.split("_", 1)[-1] if "_" in sl else sl
    png = group_dir / f"{tail}.png"
    if png.exists():
        return tail, "found"
    for p in group_dir.iterdir():
        if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == tail.lower():
            return p.stem, "found"
    # Try stripping numeric suffix (_01, _02 etc.)
    sl_stripped = re.sub(r"_\d{2,4}$", "", sl)
    if sl_stripped != sl:
        for p in group_dir.iterdir():
            if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl_stripped.lower():
                return p.stem, "found"
        tail_stripped = re.sub(r"_\d{2,4}$", "", tail)
        if tail_stripped != tail:
            for p in group_dir.iterdir():
                if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == tail_stripped.lower():
                    return p.stem, "found"
    # Try stripping _Center / _Corner / _Passage suffix (keep trailing _NN)
    sl_center_stripped = re.sub(r"_(?:Center|Corner|Passage)(?=_\d|$)", "", sl)
    if sl_center_stripped != sl:
        for p in group_dir.iterdir():
            if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl_center_stripped.lower():
                return p.stem, "found"
    # Try stripping _Resize / _Test / _BossTest / _DistantView debug suffixes
    sl_debug_stripped = re.sub(r"_(?:Resize|Test|BossTest|DistantView)$", "", sl)
    if sl_debug_stripped != sl:
        for p in group_dir.iterdir():
            if p.suffix.lower() in (".png", ".webp") and p.stem.lower() == sl_debug_stripped.lower():
                return p.stem, "found"
    # Try numeric prefix match: after stripping _\d{2,4}$, find any file starting with the stripped prefix
    if sl_stripped != sl:
        prefix = sl_stripped.lower()
        for p in group_dir.iterdir():
            if p.suffix.lower() in (".png", ".webp") and p.stem.lower().startswith(prefix):
                return p.stem, "found"
    return sl, "not_found"


def _save(filename: str, data: list | dict):
    path = OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
