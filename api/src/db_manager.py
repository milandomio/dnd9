import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from config import (
    DB_PATH,
    DUNGEON_MODULE_DIR,
    GAME_JSON,
    GAME_ROOT,
    GROUP_TO_ART_DIR,
    ITEM_DIR,
    LOOTDROP_DIR,
    LOOTDROP_GROUP_DIR,
    LOOTDROP_RATE_DIR,
    MAPS_DIR,
    MONSTER_DIR,
    PROPS_DIR,
    SPAWNER_DIR,
)


def _load_json_dir(directory: Path) -> dict[str, Any]:
    result = {}
    if not directory.exists():
        return result
    for fp in sorted(directory.glob("*.json")):
        try:
            with open(fp, encoding="utf-8") as f:
                result[fp.stem] = json.load(f)
        except Exception:
            pass
    return result


def _load_game_json() -> dict[str, str]:
    if not GAME_JSON.exists():
        return {}
    try:
        with open(GAME_JSON, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, dict):
                    return v
        return {}
    except Exception:
        return {}


_VARIANT_RE = re.compile(r"_\d{4}$")
_QUALITY_RE = re.compile(r"_(Common|Elite|Nightmare|Unique)$")
_MONSTER_SUBTYPE_RE = re.compile(r"_(BoneWall|BonePrison)$", re.IGNORECASE)


def _strip_ids_prefix(name: str, prefix: str) -> str:
    return (
        name.removeprefix(prefix)
        .removeprefix("Id_Item_")
        .removeprefix("Id_Monster_")
        .removeprefix("Id_Props_")
        .removeprefix("Id_DungeonModule_")
        .removeprefix("ID_Lootdrop_")
        .removeprefix("ID_LootDropGroup_")
        .removeprefix("Id_Spawner_New_Monster_")
        .removeprefix("Id_Spawner_New_Props_")
        .removeprefix("Id_Spawner_New_LootDrop_")
    )


def _extract_translation_key(name: str, prefix: str) -> str:
    key = name.removeprefix(prefix)
    key = _QUALITY_RE.sub("", key)
    key = _VARIANT_RE.sub("", key)
    return key


def _extract_item_name(raw_name: str) -> str:
    name = raw_name.removeprefix("Id_Item_")
    name = _VARIANT_RE.sub("", name)
    return name


def _extract_monster_name(raw_name: str) -> str:
    name = raw_name.removeprefix("Id_Monster_")
    name = _QUALITY_RE.sub("", name)
    name = _MONSTER_SUBTYPE_RE.sub("", name)
    return name


def _extract_props_name(raw_name: str) -> str:
    name = raw_name.removeprefix("Id_Props_")
    name = re.sub(r"_Dummy$", "", name)
    return name


def _extract_dungeon_module_name(raw_name: str) -> str:
    return raw_name.removeprefix("Id_DungeonModule_")


_UE_PATH_RE = re.compile(r"/Game/DungeonCrawler/(.*)\.\w+$")


def _ue_to_fs_path(ue_path: str) -> str | None:
    m = _UE_PATH_RE.search(ue_path)
    if not m:
        return None
    return m.group(1).replace("/", "/")


def _ue_asset_base_name(ue_path: str) -> str | None:
    stem = ue_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return stem


_SL_SUFFIX_RE = re.compile(r"_(HR_D|D|A)$")


def _sl_base_name(asset_name: str) -> str:
    return _SL_SUFFIX_RE.sub("", asset_name)


def _has_map_file(ue_path: str) -> bool:
    """Check if a SubLevelAssetD/HR UE path corresponds to an actual map file on disk.

    Extracts the directory path from the UE asset path and checks if it exists
    under GAME_ROOT. Returns False if the directory doesn't exist (stale reference).
    """
    fs = _ue_to_fs_path(ue_path)
    if not fs:
        return False
    # fs example: Maps/Dungeon/Modules/ShipGraveyard/ShipGraveyard_FloatingIsland_01/ShipGraveyard_FloatingIsland_01_D
    # Extract directory part (everything except the final filename)
    parts = fs.rsplit("/", 1)
    if len(parts) < 2:
        return False
    dir_rel = parts[0]  # e.g. Maps/Dungeon/Modules/ShipGraveyard/ShipGraveyard_FloatingIsland_01
    return (GAME_ROOT / dir_rel).is_dir()


class DatabaseManager:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS item_entities (
                item_name TEXT PRIMARY KEY,
                raw_name TEXT NOT NULL,
                translation_key TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                variant_count INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS monster_entities (
                monster_name TEXT PRIMARY KEY,
                raw_name TEXT NOT NULL,
                translation_key TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS props_entities (
                asset_name TEXT PRIMARY KEY,
                raw_name TEXT NOT NULL,
                translation_key TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS dungeon_modules (
                module_name TEXT PRIMARY KEY,
                translation_key TEXT NOT NULL DEFAULT '',
                module_group TEXT NOT NULL DEFAULT '',
                size_x INTEGER DEFAULT 1,
                size_y INTEGER DEFAULT 1,
                sl_base_name TEXT NOT NULL DEFAULT '',
                map_image_name TEXT NOT NULL DEFAULT '',
                aliases TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS lootdrop_items (
                item_name TEXT NOT NULL,
                monster_name TEXT NOT NULL,
                lootdrop_name TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (item_name, monster_name)
            );

            CREATE TABLE IF NOT EXISTS spawners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                original_keyword TEXT NOT NULL DEFAULT '',
                spawner_type TEXT NOT NULL DEFAULT 'unknown',
                has_lootdrop INTEGER NOT NULL DEFAULT 0,
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL,
                yaw REAL NOT NULL DEFAULT 0.0,
                json_filename TEXT NOT NULL,
                module_type TEXT DEFAULT '',
                version TEXT NOT NULL DEFAULT '',
                map_base TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS search_term_matches (
                search_term TEXT NOT NULL,
                spawner_id INTEGER NOT NULL,
                PRIMARY KEY (search_term, spawner_id),
                FOREIGN KEY (spawner_id) REFERENCES spawners(id)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                item_name, translation_key, category,
                content='item_entities',
                content_rowid='rowid',
                tokenize='unicode61'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS monsters_fts USING fts5(
                monster_name, translation_key,
                content='monster_entities',
                content_rowid='rowid',
                tokenize='unicode61'
            );

            CREATE TABLE IF NOT EXISTS translations (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS quest_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                item_translation TEXT NOT NULL DEFAULT '',
                npc_name TEXT NOT NULL,
                npc_name_cn TEXT NOT NULL DEFAULT '',
                quest_number INTEGER NOT NULL DEFAULT 0,
                count INTEGER NOT NULL DEFAULT 1,
                rarity TEXT NOT NULL DEFAULT '',
                is_loot TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS quest_npcs (
                npc_name TEXT PRIMARY KEY,
                npc_name_display TEXT NOT NULL DEFAULT '',
                quest_count INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL DEFAULT '',
                quests_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS explore_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                module_name TEXT NOT NULL DEFAULT '',
                quest_id TEXT NOT NULL DEFAULT '',
                quest_title TEXT NOT NULL DEFAULT '',
                quest_number INTEGER NOT NULL DEFAULT 0,
                npc_name TEXT NOT NULL DEFAULT '',
                npc_name_display TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS spawner_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spawner_keyword TEXT NOT NULL,
                entity_name TEXT NOT NULL DEFAULT '',
                spawn_rate REAL NOT NULL DEFAULT 100.0,
                dungeon_grades TEXT NOT NULL DEFAULT '[]',
                lootdrop_group_id TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS lootdrop_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                dungeon_grade INTEGER NOT NULL DEFAULT 0,
                lootdrop_id TEXT NOT NULL DEFAULT '',
                lootdrop_rate_id TEXT NOT NULL DEFAULT '',
                drop_count INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS lootdrop_rate_items (
                lootdrop_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                luck_grade INTEGER NOT NULL DEFAULT 0,
                drop_count INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS lootdrop_rate_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_id TEXT NOT NULL,
                luck_grade INTEGER NOT NULL DEFAULT 0,
                weight INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_lrw_rate_grade ON lootdrop_rate_weights (rate_id, luck_grade);

            CREATE TABLE IF NOT EXISTS mutually_exclusive_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                map_base TEXT NOT NULL,
                json_filename TEXT NOT NULL,
                group_name TEXT NOT NULL,
                search_term TEXT NOT NULL DEFAULT '',
                spawner_count INTEGER NOT NULL DEFAULT 0
            );
        """)
        self._migrate_spawners_table()
        self.conn.commit()

    def _migrate_spawners_table(self):
        """Add missing columns to spawners table."""
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(spawners)")
        columns = [row[1] for row in c.fetchall()]
        if "has_lootdrop" not in columns:
            c.execute("ALTER TABLE spawners ADD COLUMN has_lootdrop INTEGER NOT NULL DEFAULT 0")
        if "group_parent" not in columns:
            c.execute("ALTER TABLE spawners ADD COLUMN group_parent TEXT NOT NULL DEFAULT ''")

    def connect(self):
        return self.conn

    # ─── Import: Translations ───

    _CRACKED_RE = re.compile(r"（裂开）")

    def import_translations(self):
        data = _load_game_json()
        if not data:
            return 0
        c = self.conn.cursor()
        c.execute("DELETE FROM translations")
        rows = [(k, self._CRACKED_RE.sub("", v)) for k, v in data.items() if k and v]
        c.executemany("INSERT OR REPLACE INTO translations (key, value) VALUES (?, ?)", rows)
        self.conn.commit()
        return len(rows)

    def get_translation(self, key: str) -> str:
        c = self.conn.cursor()
        c.execute("SELECT value FROM translations WHERE key = ?", (key,))
        row = c.fetchone()
        return row["value"] if row else ""

    # ─── Import: Items ───

    def import_items(self) -> int:
        files = _load_json_dir(ITEM_DIR)
        c = self.conn.cursor()
        c.execute("DELETE FROM item_entities")
        # Count variants per item_name from raw filenames
        from collections import Counter

        variant_counts: Counter = Counter()
        rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            name_key = ""
            props = entry.get("Properties", {}) or {}
            if "Name" in props:
                name_key = (props["Name"] or {}).get("Key", "")
            item_name = _extract_item_name(raw_name)
            variant_counts[item_name] += 1
            rows.append((item_name, raw_name, name_key, ""))
        seen = set()
        deduped = []
        for r in rows:
            if r[0] not in seen:
                seen.add(r[0])
                row = r + (variant_counts.get(r[0], 1),)
                deduped.append(row)
        c.executemany(
            "INSERT OR REPLACE INTO item_entities (item_name, raw_name, translation_key, category, variant_count) VALUES (?, ?, ?, ?, ?)",
            deduped,
        )
        self._rebuild_fts("items_fts", "item_entities")
        self.conn.commit()
        return len(deduped)

    # ─── Import: Monsters ───

    def import_monsters(self) -> int:
        files = _load_json_dir(MONSTER_DIR)
        c = self.conn.cursor()
        c.execute("DELETE FROM monster_entities")
        rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = (props.get("Name") or {}).get("Key", "")
            name_key = _MONSTER_SUBTYPE_RE.sub("", name_key)
            monster_name = _extract_monster_name(raw_name)
            rows.append((monster_name, raw_name, name_key))
        seen_lower: dict[str, int] = {}
        deduped = []
        for r in rows:
            key = r[0].lower()
            if key not in seen_lower:
                seen_lower[key] = len(deduped)
                deduped.append(r)
            else:
                idx = seen_lower[key]
                existing = deduped[idx]
                if r[2] and (
                    not existing[2]
                    or (r[2].startswith("Text_DesignData_") and not existing[2].startswith("Text_DesignData_"))
                ):
                    # 保留首遇的名称大小写，只替换翻译键
                    deduped[idx] = (existing[0], existing[1], r[2])

        # Fallback: also import monsters from spawner files
        spawner_files = _load_json_dir(SPAWNER_DIR)
        for raw_name, data_list in spawner_files.items():
            if not data_list:
                continue
            raw = raw_name.removeprefix("Id_Spawner_Monster_")
            if raw.lower() not in seen_lower:
                seen_lower[raw.lower()] = len(deduped)
                entry = data_list[0]
                props = entry.get("Properties", {}) or {}
                name_key = (props.get("Name") or {}).get("Key", "")
                name_key = _MONSTER_SUBTYPE_RE.sub("", name_key)
                deduped.append((raw, raw_name, name_key))

        c.executemany(
            "INSERT OR REPLACE INTO monster_entities (monster_name, raw_name, translation_key) VALUES (?, ?, ?)",
            deduped,
        )
        self._rebuild_fts("monsters_fts", "monster_entities")
        self.conn.commit()
        return len(deduped)

    # ─── Import: Props ───

    def import_props(self) -> int:
        files = _load_json_dir(PROPS_DIR)
        c = self.conn.cursor()
        c.execute("DELETE FROM props_entities")
        rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = (props.get("Name") or {}).get("Key", "")
            asset_name = _extract_props_name(raw_name)
            rows.append((asset_name, raw_name, name_key))
        c.executemany(
            "INSERT OR REPLACE INTO props_entities (asset_name, raw_name, translation_key) VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def import_spawner_fallback_entities(self) -> dict[str, int]:
        """Add spawner keywords not yet in items/props/monsters tables as fallback entries."""
        c = self.conn.cursor()

        # Get existing entity names
        c.execute("SELECT item_name FROM item_entities")
        existing_items = {r["item_name"] for r in c.fetchall()}

        c.execute("SELECT monster_name FROM monster_entities")
        existing_monsters = {r["monster_name"] for r in c.fetchall()}

        c.execute("SELECT asset_name FROM props_entities")
        existing_props = {r["asset_name"] for r in c.fetchall()}

        # Get distinct spawner keywords by type
        c.execute(
            "SELECT DISTINCT keyword, spawner_type FROM spawners WHERE spawner_type IN ('item', 'monster', 'props')"
        )
        spawner_keywords = c.fetchall()

        added = {"item": 0, "monster": 0, "props": 0}
        item_rows = []
        monster_rows = []
        props_rows = []

        for row in spawner_keywords:
            keyword = row["keyword"]
            stype = row["spawner_type"]

            if stype == "item" and keyword not in existing_items:
                item_rows.append((keyword, keyword, ""))
                existing_items.add(keyword)
            elif stype == "monster" and keyword not in existing_monsters:
                monster_rows.append((keyword, keyword, ""))
                existing_monsters.add(keyword)
            elif stype == "props" and keyword not in existing_props:
                props_rows.append((keyword, keyword, ""))
                existing_props.add(keyword)

        if item_rows:
            c.executemany(
                "INSERT OR IGNORE INTO item_entities (item_name, raw_name, translation_key) VALUES (?, ?, ?)",
                item_rows,
            )
            added["item"] = len(item_rows)

        if monster_rows:
            c.executemany(
                "INSERT OR IGNORE INTO monster_entities (monster_name, raw_name, translation_key) VALUES (?, ?, ?)",
                monster_rows,
            )
            added["monster"] = len(monster_rows)

        if props_rows:
            c.executemany(
                "INSERT OR IGNORE INTO props_entities (asset_name, raw_name, translation_key) VALUES (?, ?, ?)",
                props_rows,
            )
            added["props"] = len(props_rows)

        self.conn.commit()

        # Rebuild FTS tables if entities were added
        if added["item"] > 0:
            self._rebuild_fts("items_fts", "item_entities")
        if added["monster"] > 0:
            self._rebuild_fts("monsters_fts", "monster_entities")

        return added

    # ─── Import: Dungeon Modules ───

    def _build_path_group_map(self) -> dict[str, str]:
        """Scan MAPS_DIR to infer module group from file path directory structure.
        Returns map_base → group mapping."""
        import os

        path_group: dict[str, str] = {}
        if not MAPS_DIR.exists():
            return path_group
        # Map directory names under MAPS_DIR to module group names
        dir_to_group: dict[str, str] = {}
        for group, art_dir in GROUP_TO_ART_DIR.items():
            dir_to_group[art_dir] = group
        for dirpath, _, filenames in os.walk(MAPS_DIR):
            rel = Path(dirpath).relative_to(MAPS_DIR)
            group = dir_to_group.get(rel.parts[0], "") if rel.parts else ""
            if not group:
                continue
            for fn in filenames:
                if not fn.endswith(("_HR_D.json", "_D.json", "_A.json")):
                    continue
                stem = fn.rsplit(".", 1)[0]
                if "_SR" in stem or "_Arena" in stem or "_BossTest" in stem or "_Resize" in stem or "_Test" in stem:
                    continue
                base = _sl_base_name(stem)
                if base not in path_group:
                    path_group[base] = group
        return path_group

    def import_dungeon_modules(self) -> int:
        files = _load_json_dir(DUNGEON_MODULE_DIR)
        c = self.conn.cursor()
        c.execute("DELETE FROM dungeon_modules")
        # Build path-based group map as fallback
        path_group_map = self._build_path_group_map()
        # First pass: build module_name → (ModuleType, entry data) map
        type_map: dict[str, str] = {}
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            module_name = _extract_dungeon_module_name(raw_name)
            module_type = (props.get("ModuleType") or "").removeprefix("EDCDungeonModuleType::")
            if module_type:
                type_map[module_name] = module_type
        # Second pass: build rows with ModuleType fallback via sl_base lookup
        rows = []
        inserted_names: set[str] = set()
        skipped_names: list[str] = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = (props.get("Name") or {}).get("Key", "")
            module_type = (props.get("ModuleType") or "").removeprefix("EDCDungeonModuleType::")
            size_x = (props.get("Size") or {}).get("X", 1) or 1
            size_y = (props.get("Size") or {}).get("Y", 1) or 1
            module_name = _extract_dungeon_module_name(raw_name)
            if "_SR" in module_name or "_BossTest" in module_name or "_Resize" in module_name or "_Test" in module_name:
                continue

            sl_base = ""
            found_valid = False
            for variant in ["SubLevelAssetD_HR", "SubLevelAssetD", "SubLevelAssetA"]:
                asset = (props.get(variant) or {}).get("AssetPathName", "")
                if not asset:
                    continue
                # D variants (HR/D) must map to an existing map directory on disk
                if variant in ("SubLevelAssetD_HR", "SubLevelAssetD") and not _has_map_file(asset):
                    break  # stale reference → skip module
                base = _ue_asset_base_name(asset) or ""
                sl_base = _sl_base_name(base)
                # SubLevelAssetD_HR/D 指向其他模块的地图目录 → 无效数据，跳过
                # 判断依据：从 UE 路径提取目录名，若与 sl_base 互不包含则判定为借用
                if variant in ("SubLevelAssetD_HR", "SubLevelAssetD") and sl_base:
                    fs_path = _ue_to_fs_path(asset)
                    if fs_path:
                        dir_name = fs_path.rsplit("/", 1)[0].rsplit("/", 1)[-1] if "/" in fs_path else ""
                        if (
                            dir_name
                            and sl_base.lower() not in dir_name.lower()
                            and dir_name.lower() not in sl_base.lower()
                        ):
                            skipped_names.append(module_name)
                            sl_base = ""
                            break
                found_valid = True
                break
            # Use sl_base as module name if it differs (sl_base matches actual map directory)
            # Store original module_name as alias
            aliases = []
            if sl_base and sl_base != module_name:
                aliases.append(module_name)
                module_name = sl_base
            if not found_valid:
                skipped_names.append(module_name)
                continue
            # Priority 1: infer group from map file path directory structure
            path_group = path_group_map.get(module_name, "")
            if path_group:
                module_type = path_group
            # Priority 2: ModuleType from JSON / sl_base type_map lookup
            if not module_type and sl_base:
                module_type = type_map.get(sl_base, "")
            # Priority 3: infer from module name prefix
            if not module_type:
                for prefix, group in [
                    ("ShipGraveyard", "ShipGraveyard"),
                    ("Shipgraveyard", "ShipGraveyard"),
                    ("GoblinCave", "GoblinCave"),
                    ("GoblinJail", "GoblinCave"),
                    ("GoblinMine", "GoblinCave"),
                    ("Goblin", "GoblinCave"),
                    ("Firedeep", "FireDeep"),
                    ("FireDeep", "FireDeep"),
                    ("IceCavern", "IceCavern"),
                    ("IceAbyss", "IceAbyss"),
                    ("IceCave", "IceCavern"),
                    ("Crypt", "Crypt"),
                    ("Inferno", "Inferno"),
                    ("Ruins", "Ruins"),
                    ("Swamp", "Crypt"),
                    ("Cave_", "GoblinCave"),
                    ("CorridorCrypt", "Crypt"),
                    ("Cemetery", "Crypt"),
                    ("SpiderCave", "GoblinCave"),
                    ("Prison", "Ruins"),
                ]:
                    if module_name.lower().startswith(prefix.lower()):
                        module_type = group
                        break
            # Extract MapImage (direct Art file reference, e.g. CaveMaze_02)
            mi_asset = (props.get("MapImage") or {}).get("AssetPathName", "")
            map_image = _ue_asset_base_name(mi_asset) or ""
            import json as _json

            aliases_json = _json.dumps(aliases) if aliases else "[]"
            rows.append((module_name, name_key, module_type, size_x, size_y, sl_base, map_image, aliases_json))
            inserted_names.add(module_name)
        c.executemany(
            "INSERT OR REPLACE INTO dungeon_modules (module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        if skipped_names:
            print(f"  skipped {len(skipped_names)} modules with stale SubLevelAsset: {skipped_names}")
        # Third pass: insert modules that exist as map files but have no DungeonModule JSON
        sl_base_to_key = {r[5]: r[1] for r in rows if r[5]}
        module_name_to_key = {r[0]: r[1] for r in rows if r[1]}
        _VARIANT_SUFFIX_RE = re.compile(r"_(Resize|Test|BossTest|DistantView)$")  # noqa: N806
        extra_rows = []
        for base_name, group in path_group_map.items():
            if base_name not in inserted_names:
                tk = sl_base_to_key.get(base_name, "") or module_name_to_key.get(base_name, "")
                if not tk:
                    stripped = _VARIANT_SUFFIX_RE.sub("", base_name)
                    if stripped != base_name:
                        tk = sl_base_to_key.get(stripped, "") or module_name_to_key.get(stripped, "")
                extra_rows.append((base_name, tk, group, 1, 1, "", "", "[]"))
                inserted_names.add(base_name)
        if extra_rows:
            c.executemany(
                "INSERT OR REPLACE INTO dungeon_modules (module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                extra_rows,
            )
        # Remove modules with no group (no corresponding map file found)
        c.execute("DELETE FROM dungeon_modules WHERE module_group = '' OR module_group IS NULL")
        self.conn.commit()
        # Return final count
        c.execute("SELECT COUNT(*) FROM dungeon_modules")
        total = c.fetchone()[0]
        return total

    # ─── Import: LootDrop ───

    def import_lootdrops(self, spawner_monster_map: dict[str, list[str]] | None = None) -> int:
        groups = _load_json_dir(LOOTDROP_GROUP_DIR)
        drops = _load_json_dir(LOOTDROP_DIR)

        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_items")

        def _strip_prefix(name: str, *prefixes: str) -> str:
            for p in sorted(prefixes, key=len, reverse=True):
                if name.lower().startswith(p.lower()):
                    return name[len(p) :]
            return name

        ld_group = {}
        for raw_name, data_list in groups.items():
            if not data_list:
                continue
            entry = data_list[0]
            ldg_name = _strip_prefix(raw_name, "Id_LootDropGroup_", "ID_LootDropGroup_")
            items = entry.get("Properties", {}).get("LootDropGroupItemArray", []) or []
            for item in items:
                asset = (item.get("LootDropId") or {}).get("AssetPathName", "")
                if not asset:
                    continue
                ld_name = _ue_asset_base_name(asset) or ""
                ld_name = _strip_prefix(ld_name, "Id_Lootdrop_", "ID_Lootdrop_")
                if ld_name not in ld_group:
                    ld_group[ld_name] = []
                ld_group[ld_name].append(ldg_name)

        # Override with spawner-derived canonical monster names when available
        if spawner_monster_map:
            for ld_name, ldg_names in ld_group.items():
                canonical = set()
                for ldg in ldg_names:
                    mapped = spawner_monster_map.get(ldg)
                    if mapped:
                        canonical.update(mapped)
                if canonical:
                    ld_group[ld_name] = sorted(canonical)

        rows = []
        for raw_name, data_list in drops.items():
            if not data_list:
                continue
            entry = data_list[0]
            ld_name = _strip_prefix(raw_name, "Id_Lootdrop_", "ID_Lootdrop_")
            monsters = ld_group.get(ld_name, [])

            items_arr = entry.get("Properties", {}).get("LootDropItemArray", []) or []
            for drop_item in items_arr:
                item_asset = (drop_item.get("ItemId") or {}).get("AssetPathName", "")
                if not item_asset:
                    continue
                item_name = _ue_asset_base_name(item_asset) or ""
                item_name = _strip_prefix(item_name, "Id_Item_", "Id_Props_")
                for mon in monsters:
                    if item_name == mon:
                        continue
                    rows.append((item_name, mon, ld_name))
        seen = set()
        deduped = []
        for r in rows:
            key = (r[0], r[1])
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        c.executemany(
            "INSERT OR REPLACE INTO lootdrop_items (item_name, monster_name, lootdrop_name) VALUES (?, ?, ?)",
            deduped,
        )
        self.conn.commit()
        return len(deduped)

    # ─── FTS Rebuild ───

    def _rebuild_fts(self, fts_table: str, content_table: str):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
        self.conn.commit()

    # ─── Query Helpers ───

    def get_item_entities(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT item_name, translation_key, category, variant_count FROM item_entities ORDER BY item_name")
        return [dict(r) for r in c.fetchall()]

    def get_monster_entities(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT monster_name, translation_key FROM monster_entities ORDER BY monster_name")
        return [dict(r) for r in c.fetchall()]

    def get_monster_name_map(self) -> dict[str, str]:
        """Return mapping of lowercase monster_name → canonical monster_name."""
        c = self.conn.cursor()
        c.execute("SELECT monster_name FROM monster_entities")
        result = {}
        for row in c.fetchall():
            name = row["monster_name"]
            result[name.lower()] = name
        return result

    def get_props_entities(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT asset_name, translation_key FROM props_entities ORDER BY asset_name")
        return [dict(r) for r in c.fetchall()]

    def get_dungeon_modules(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            "SELECT module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases FROM dungeon_modules ORDER BY module_name"
        )
        results = []
        for r in c.fetchall():
            d = dict(r)
            import json as _json

            d["aliases"] = _json.loads(d.get("aliases", "[]") or "[]")
            results.append(d)
        return results

    def get_lootdrop_relationships(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT item_name, monster_name FROM lootdrop_items ORDER BY item_name, monster_name")
        return [dict(r) for r in c.fetchall()]

    def get_entity_classification(self) -> dict[str, dict]:
        """Build entity classification from DB data (avoids re-scanning JSON files)."""
        classification: dict[str, dict] = {}
        seen_lower: dict[str, str] = {}

        def _add(name: str, type_label: str, tk: str):
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
                if (not existing_tk or not existing_tk.startswith("Text_DesignData_")) and tk.startswith(
                    "Text_DesignData_"
                ):
                    existing["translation_key"] = tk

        for r in self.get_item_entities():
            _add(r["item_name"], "item", r["translation_key"])
        for r in self.get_monster_entities():
            _add(r["monster_name"], "monster", r["translation_key"])
        for r in self.get_props_entities():
            _add(r["asset_name"], "props", r["translation_key"])

        return classification

    def get_spawner_matches(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("""
            SELECT sm.search_term, s.keyword, s.spawner_type, s.x, s.y, s.z, s.yaw,
                   s.json_filename, s.module_type, s.version, s.map_base
            FROM search_term_matches sm
            JOIN spawners s ON s.id = sm.spawner_id
            ORDER BY sm.search_term
        """)
        return [dict(r) for r in c.fetchall()]

    def get_translations_map(self) -> dict[str, str]:
        c = self.conn.cursor()
        c.execute("SELECT key, value FROM translations")
        return {r["key"]: r["value"] for r in c.fetchall()}

    def get_item_coordinates(self, item_name: str) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            """
            SELECT DISTINCT s.x, s.y, s.z, s.yaw, s.json_filename, s.version, s.map_base, s.module_type, s.original_keyword
            FROM search_term_matches sm
            JOIN spawners s ON s.id = sm.spawner_id
            WHERE sm.search_term = ?
            ORDER BY s.map_base, s.json_filename
        """,
            (item_name,),
        )
        return [dict(r) for r in c.fetchall()]

    def get_all_coordinates(self) -> dict[str, list[dict]]:
        """Bulk-fetch all search_term → coordinates mapping in a single query."""
        c = self.conn.cursor()
        c.execute("""
            SELECT sm.search_term, s.x, s.y, s.z, s.yaw, s.json_filename,
                   s.version, s.map_base, s.module_type, s.keyword, s.original_keyword, s.spawner_type,
                   s.group_parent
            FROM search_term_matches sm
            JOIN spawners s ON s.id = sm.spawner_id
            ORDER BY sm.search_term, s.map_base, s.json_filename
        """)
        result: dict[str, list[dict]] = {}
        for row in c.fetchall():
            term = row["search_term"]
            if term not in result:
                result[term] = []
            coord = dict(row)
            # Deduplicate: same (x, y, z, json_filename) can appear when a
            # spawner keyword is a prefix of another and both expand from the
            # same multi-entity spawner (e.g. OrnateChestLarge_Locked also
            # matches "OrnateChestLarge" via prefix, adding the same position twice).
            dup_key = (coord["x"], coord["y"], coord["z"], coord["json_filename"])
            coord["_dup_key"] = dup_key
            existing_keys = {c["_dup_key"] for c in result[term]}
            if dup_key not in existing_keys:
                result[term].append(coord)
        # Strip internal dedup key before returning
        for term in result:
            for c in result[term]:
                c.pop("_dup_key", None)
        return result

    def get_items_with_matches(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("""
            SELECT e.item_name, e.translation_key, e.category,
                   GROUP_CONCAT(DISTINCT l.monster_name) as monster_names
            FROM item_entities e
            LEFT JOIN lootdrop_items l ON e.item_name = SUBSTR(l.item_name, 1, INSTR(l.item_name||'_', '_') - 1)
            GROUP BY e.item_name
            ORDER BY e.item_name
        """)
        results = []
        for r in c.fetchall():
            d = dict(r)
            d["monster_names"] = d["monster_names"].split(",") if d["monster_names"] else []
            results.append(d)
        return results

    # ─── Import: Quest Data ───

    def import_quest_items(self, items: list[dict]) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM quest_items")
        rows = [
            (
                qi.get("item_name", ""),
                qi.get("item_translation", ""),
                qi.get("npc_name", ""),
                qi.get("npc_name_cn", ""),
                qi.get("quest_number", 0),
                qi.get("count", 1),
                qi.get("rarity", ""),
                qi.get("is_loot", ""),
            )
            for qi in items
        ]
        c.executemany(
            "INSERT INTO quest_items (item_name, item_translation, npc_name, npc_name_cn, quest_number, count, rarity, is_loot) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def get_quest_items(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            "SELECT item_name, item_translation, npc_name, npc_name_cn, quest_number, count, rarity, is_loot FROM quest_items ORDER BY npc_name, quest_number"
        )
        return [dict(r) for r in c.fetchall()]

    def import_quest_npcs(self, npcs: list[dict]) -> int:
        import json as _json

        c = self.conn.cursor()
        c.execute("DELETE FROM quest_npcs")
        rows = [
            (
                npc.get("npc_name", ""),
                npc.get("npc_name_display", ""),
                npc.get("quest_count", 0),
                npc.get("category", ""),
                _json.dumps(npc.get("quests", []), ensure_ascii=False),
            )
            for npc in npcs
        ]
        c.executemany(
            "INSERT OR REPLACE INTO quest_npcs (npc_name, npc_name_display, quest_count, category, quests_json) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def get_quest_npcs(self) -> list[dict]:
        import json as _json

        c = self.conn.cursor()
        c.execute(
            "SELECT npc_name, npc_name_display, quest_count, category, quests_json FROM quest_npcs ORDER BY npc_name"
        )
        results = []
        for r in c.fetchall():
            d = dict(r)
            d["quests"] = _json.loads(d.pop("quests_json", "[]") or "[]")
            results.append(d)
        return results

    def import_explore_targets(self, targets: list[dict]) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM explore_targets")
        rows = [
            (
                t.get("name", ""),
                t.get("module_name", ""),
                t.get("quest_id", ""),
                t.get("quest_title", ""),
                t.get("quest_number", 0),
                t.get("npc_name", ""),
                t.get("npc_name_display", ""),
            )
            for t in targets
        ]
        c.executemany(
            "INSERT INTO explore_targets (name, module_name, quest_id, quest_title, quest_number, npc_name, npc_name_display) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def get_explore_targets(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            "SELECT name, module_name, quest_id, quest_title, quest_number, npc_name, npc_name_display FROM explore_targets ORDER BY quest_number, npc_name"
        )
        return [dict(r) for r in c.fetchall()]

    # ─── Import: Spawner Entries (爆率) ───

    _SPAWNER_PREFIXES = [
        "Id_Spawner_New_Monster_",
        "Id_Spawner_New_Props_",
        "Id_Spawner_New_LootDrop_",
        "Id_Spawner_New_Lootdrop_",
        "Id_Spawner_Monster_",
        "Id_Spawner_Props_",
        "Id_Spawner_LootDrop_",
        "Id_Spawner_Lootdrop_",
        "Id_Spawner_New_NPC_",
        "Id_Spawner_NPC_",
        "Id_Spawner_New_",
        "Id_Spawner_",
    ]

    def import_spawner_entries(self) -> int:
        """从 SpawnerDataAsset JSON 导入 spawner_entries 表。

        SpawnRate 存储为百分比（0~100），按同 SpawnerItemArray 内的比例计算。
        """
        c = self.conn.cursor()
        c.execute("DELETE FROM spawner_entries")
        rows = []
        if not SPAWNER_DIR.exists():
            return 0
        for fp in sorted(SPAWNER_DIR.glob("*.json")):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if not isinstance(data, list) or not data:
                continue
            entry = data[0]
            if entry.get("Type") != "DCSpawnerDataAsset":
                continue
            name = entry.get("Name", "")
            if not name:
                continue
            keyword = name
            for prefix in self._SPAWNER_PREFIXES:
                if keyword.startswith(prefix):
                    keyword = keyword[len(prefix) :]
                    break
            props = entry.get("Properties", {}) or {}
            items = props.get("SpawnerItemArray", []) or []
            # 按 DungeonGrades 分组计算 spawn_rate
            # 先将全量条目按 grade set 分组，再将含有该组 grade 的空条目（无 entity）纳入同一池
            _grade_groups: dict[str, list[dict]] = {}
            for item in items:
                _dg = json.dumps(sorted(item.get("DungeonGrades", []) or []), sort_keys=True)
                _grade_groups.setdefault(_dg, []).append(item)
            # 对每个非空组，检查是否有空条目的 grade set 是其超集
            _empty_items = [it for it in items if not ((it.get("LootDropGroupId", {}) or {}).get("AssetPathName", ""))]
            _dg_sets = {k: set(json.loads(k)) for k in _grade_groups}
            for _dg_key, _dg_items in list(_grade_groups.items()):
                _has_entity = any(
                    (it.get("MonsterId", {}) or {}).get("AssetPathName", "")
                    or (it.get("PropsId", {}) or {}).get("AssetPathName", "")
                    for it in _dg_items
                )
                if not _has_entity:
                    continue
                _dgs = _dg_sets[_dg_key]
                for _ei in _empty_items:
                    _e_grades = set(_ei.get("DungeonGrades", []) or [])
                    if _dgs.issubset(_e_grades):
                        _dg_items.append(_ei)
            for _dg_items in _grade_groups.values():
                _total = sum(it.get("SpawnRate", 10000) for it in _dg_items)
                if _total <= 0:
                    _total = 1
                for item in _dg_items:
                    ldg = item.get("LootDropGroupId", {}) or {}
                    ldg_path = ldg.get("AssetPathName", "")
                    if not ldg_path:
                        continue
                    raw_rate = item.get("SpawnRate", 10000)
                    spawn_rate = round(raw_rate / _total * 100, 2)
                    dungeon_grades = item.get("DungeonGrades", []) or []
                    ldg_id = _ue_asset_base_name(ldg_path) or ""
                    entity_name = ""
                    for id_key in ("MonsterId", "PropsId"):
                        id_path = (item.get(id_key, {}) or {}).get("AssetPathName", "")
                        if id_path:
                            raw = _ue_asset_base_name(id_path) or ""
                            entity_name = raw.removeprefix("Id_Monster_").removeprefix("Id_Props_")
                            break
                    rows.append((keyword, entity_name, spawn_rate, json.dumps(dungeon_grades), ldg_id))
        c.executemany(
            "INSERT INTO spawner_entries (spawner_keyword, entity_name, spawn_rate, dungeon_grades, lootdrop_group_id) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    # ─── Import: LootDrop Groups ───

    def import_lootdrop_groups(self) -> int:
        """从 LootDropGroup JSON 导入 lootdrop_groups 表。"""
        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_groups")
        rows = []
        files = _load_json_dir(LOOTDROP_GROUP_DIR)
        for stem, data_list in files.items():
            if not data_list:
                continue
            props = data_list[0].get("Properties", {}) or {}
            group_items = props.get("LootDropGroupItemArray", []) or []
            for gi in group_items:
                ld_path = (gi.get("LootDropId", {}) or {}).get("AssetPathName", "")
                lr_path = (gi.get("LootDropRateId", {}) or {}).get("AssetPathName", "")
                if not ld_path:
                    continue
                ld_id = _ue_asset_base_name(ld_path) or ""
                lr_id = _ue_asset_base_name(lr_path) if lr_path else ""
                grade = gi.get("DungeonGrade", 0)
                count = gi.get("LootDropCount", 1)
                rows.append((stem, grade, ld_id, lr_id, count))
        c.executemany(
            "INSERT INTO lootdrop_groups (group_id, dungeon_grade, lootdrop_id, lootdrop_rate_id, drop_count) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    # ─── Import: LootDrop Rate Items ───

    def import_lootdrop_rate_items(self) -> int:
        r"""从 LootDrop JSON 导入 lootdrop_rate_items 表（物品→LuckGrade 映射）。

        有以 _\d{4} 为后缀的变体的物品（如 Mitre_5001）：
          保留变体后缀，按 (lootdrop_id, base_name) 去重，优先级 _5001 > _4001 > _3001 > 其他。
          详见 docs/REFERENCE.md 中的变体锁定说明。
        """
        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_rate_items")
        rows = []
        files = _load_json_dir(LOOTDROP_DIR)
        _variant_re = re.compile(r"_\d{4}$")
        _variant_priority = {"_5001": 0, "_4001": 1, "_3001": 2}

        def _variant_rank(name: str) -> int:
            m = _variant_re.search(name)
            if m:
                return _variant_priority.get(m.group(0), 99)
            return 100  # 无变体后缀（基础名）— 最低优先级

        for stem, data_list in files.items():
            if not data_list:
                continue
            props = data_list[0].get("Properties", {}) or {}
            ld_items = props.get("LootDropItemArray", []) or []
            for li in ld_items:
                item_path = (li.get("ItemId", {}) or {}).get("AssetPathName", "")
                if not item_path:
                    continue
                raw_name = _ue_asset_base_name(item_path) or ""
                item_name = raw_name.removeprefix("Id_Item_")
                luck_grade = li.get("LuckGrade", 0)
                count = li.get("ItemCount", 1)
                rows.append((stem, item_name, luck_grade, count))
        # 去重：有变体后缀时每 (lootdrop_id, base_name) 按优先级保留；无后缀时保留末条（兼容多 LuckGrade 物品）
        seen: dict[tuple[str, str], int] = {}
        filtered = []
        for _i, (stem, item_name, luck_grade, count) in enumerate(rows):
            base = _variant_re.sub("", item_name)
            key = (stem, base)
            if base == item_name:
                # 无变体后缀：保留最后一条
                seen[key] = len(filtered)
                filtered.append((stem, item_name, luck_grade, count))
            elif key in seen:
                existing_idx = seen[key]
                existing_name = filtered[existing_idx][1]
                if _variant_rank(item_name) < _variant_rank(existing_name):
                    filtered[existing_idx] = (stem, item_name, luck_grade, count)
            else:
                seen[key] = len(filtered)
                filtered.append((stem, item_name, luck_grade, count))
        c.executemany(
            "INSERT INTO lootdrop_rate_items (lootdrop_id, item_name, luck_grade, drop_count) VALUES (?, ?, ?, ?)",
            filtered,
        )
        self.conn.commit()
        return len(filtered)

    # ─── Import: LootDrop Rate Weights ───

    def import_lootdrop_rate_weights(self) -> int:
        """从 LootDropRate JSON 导入 lootdrop_rate_weights 表。"""
        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_rate_weights")
        rows = []
        files = _load_json_dir(LOOTDROP_RATE_DIR)
        for stem, data_list in files.items():
            if not data_list:
                continue
            props = data_list[0].get("Properties", {}) or {}
            rate_items = props.get("LootDropRateItemArray", []) or []
            for ri in rate_items:
                grade = ri.get("LuckGrade", 0)
                weight = ri.get("DropRate", 0)
                rows.append((stem, grade, weight))
        c.executemany(
            "INSERT INTO lootdrop_rate_weights (rate_id, luck_grade, weight) VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    # ─── Query: 爆率相关 ───

    def get_spawner_entries_for_keyword(self, keyword: str) -> list[dict]:
        """获取某 keyword 的全部 spawner 条目（按 spawner_keyword 或 entity_name 匹配）。"""
        c = self.conn.cursor()
        c.execute(
            "SELECT spawner_keyword, entity_name, spawn_rate, dungeon_grades, lootdrop_group_id "
            "FROM spawner_entries WHERE spawner_keyword = ? OR entity_name = ?",
            (keyword, keyword),
        )
        results = []
        for r in c.fetchall():
            results.append(
                {
                    "spawner_keyword": r["spawner_keyword"],
                    "entity_name": r["entity_name"],
                    "spawn_rate": r["spawn_rate"],
                    "dungeon_grades": json.loads(r["dungeon_grades"]),
                    "lootdrop_group_id": r["lootdrop_group_id"],
                }
            )
        return results

    def get_all_spawner_entries(self) -> list[dict]:
        """获取所有 spawner_entries（批量预加载用）。"""
        c = self.conn.cursor()
        c.execute("SELECT spawner_keyword, entity_name, spawn_rate FROM spawner_entries")
        return [dict(r) for r in c.fetchall()]

    def get_item_drop_rate(self, lootdrop_group_id: str, item_name: str, full_grade: int) -> float:
        """查询某物品在指定 LootDropGroup + DungeonGrade 下的爆率（0~1）。"""
        c = self.conn.cursor()
        # 先查 grade-specific，再查 fallback(grade=0)
        for grade in (full_grade, 0):
            c.execute(
                "SELECT lg.lootdrop_id, lg.lootdrop_rate_id, lg.drop_count "
                "FROM lootdrop_groups lg "
                "WHERE lg.group_id = ? AND lg.dungeon_grade = ?",
                (lootdrop_group_id, grade),
            )
            rows = c.fetchall()
            if not rows:
                continue
            total_weight = 0.0
            found_any = False
            for r in rows:
                ld_id = r["lootdrop_id"]
                lr_id = r["lootdrop_rate_id"]
                group_count = r["drop_count"]
                # 查该 lootdrop 中目标物品的 luck_grade 和 drop_count
                c.execute(
                    "SELECT luck_grade, drop_count FROM lootdrop_rate_items WHERE lootdrop_id = ? AND item_name = ?",
                    (ld_id, item_name),
                )
                items = c.fetchall()
                if not items:
                    continue
                found_any = True
                for item_row in items:
                    lg = item_row["luck_grade"]
                    item_count = item_row["drop_count"]
                    # 查该 luck_grade 的权重
                    c.execute(
                        "SELECT COALESCE(SUM(weight), 0) as total FROM lootdrop_rate_weights WHERE rate_id = ? AND luck_grade = ?",
                        (lr_id, lg),
                    )
                    w_row = c.fetchone()
                    if w_row:
                        total_weight += w_row["total"] * group_count * item_count
            if found_any:
                return total_weight / 10000
        return 0.0

    def close(self):
        self.conn.close()
