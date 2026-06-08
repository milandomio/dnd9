import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from config import (
    DB_PATH,
    DUNGEON_MODULE_DIR,
    GAME_JSON,
    ITEM_DIR,
    LOOTDROP_DIR,
    LOOTDROP_GROUP_DIR,
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
            with open(fp, "r", encoding="utf-8") as f:
                result[fp.stem] = json.load(f)
        except Exception:
            pass
    return result


def _load_game_json() -> dict[str, str]:
    if not GAME_JSON.exists():
        return {}
    try:
        with open(GAME_JSON, "r", encoding="utf-8") as f:
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


def _strip_ids_prefix(name: str, prefix: str) -> str:
    return name.removeprefix(prefix).removeprefix("Id_Item_").removeprefix("Id_Monster_").removeprefix("Id_Props_").removeprefix("Id_DungeonModule_").removeprefix("ID_Lootdrop_").removeprefix("ID_LootDropGroup_").removeprefix("Id_Spawner_New_Monster_").removeprefix("Id_Spawner_New_Props_").removeprefix("Id_Spawner_New_LootDrop_")


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
    return name


def _extract_props_name(raw_name: str) -> str:
    return raw_name.removeprefix("Id_Props_")


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
                category TEXT NOT NULL DEFAULT ''
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
                sl_base_name TEXT NOT NULL DEFAULT ''
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
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL,
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
        """)
        self.conn.commit()

    def connect(self):
        return self.conn

    # ─── Import: Translations ───

    def import_translations(self):
        data = _load_game_json()
        if not data:
            return 0
        count = 0
        c = self.conn.cursor()
        c.execute("DELETE FROM translations")
        rows = [(k, v) for k, v in data.items() if k and v]
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
            rows.append((item_name, raw_name, name_key, ""))
        seen = set()
        deduped = []
        for r in rows:
            if r[0] not in seen:
                seen.add(r[0])
                deduped.append(r)
        c.executemany(
            "INSERT OR REPLACE INTO item_entities (item_name, raw_name, translation_key, category) VALUES (?, ?, ?, ?)",
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
            monster_name = _extract_monster_name(raw_name)
            rows.append((monster_name, raw_name, name_key))
        seen = set()
        deduped = []
        for r in rows:
            if r[0] not in seen:
                seen.add(r[0])
                deduped.append(r)
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

    # ─── Import: Dungeon Modules ───

    def import_dungeon_modules(self) -> int:
        files = _load_json_dir(DUNGEON_MODULE_DIR)
        c = self.conn.cursor()
        c.execute("DELETE FROM dungeon_modules")
        rows = []
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

            sl_base = ""
            for variant in ["SubLevelAssetD_HR", "SubLevelAssetD", "SubLevelAssetA"]:
                asset = (props.get(variant) or {}).get("AssetPathName", "")
                if asset:
                    base = _ue_asset_base_name(asset) or ""
                    sl_base = _sl_base_name(base)
                    break
            rows.append((module_name, name_key, module_type, size_x, size_y, sl_base))
        c.executemany(
            "INSERT OR REPLACE INTO dungeon_modules (module_name, translation_key, module_group, size_x, size_y, sl_base_name) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    # ─── Import: LootDrop ───

    def import_lootdrops(self) -> int:
        groups = _load_json_dir(LOOTDROP_GROUP_DIR)
        drops = _load_json_dir(LOOTDROP_DIR)

        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_items")

        ld_group = {}
        for raw_name, data_list in groups.items():
            if not data_list:
                continue
            entry = data_list[0]
            monster_name = raw_name.removeprefix("ID_LootDropGroup_")
            items = entry.get("Properties", {}).get("LootDropGroupItemArray", []) or []
            for item in items:
                asset = (item.get("LootDropId") or {}).get("AssetPathName", "")
                if not asset:
                    continue
                ld_name = _ue_asset_base_name(asset) or ""
                ld_name = ld_name.removeprefix("ID_Lootdrop_")
                if ld_name not in ld_group:
                    ld_group[ld_name] = []
                ld_group[ld_name].append(monster_name)

        rows = []
        for raw_name, data_list in drops.items():
            if not data_list:
                continue
            entry = data_list[0]
            ld_name = raw_name.removeprefix("ID_Lootdrop_")
            monsters = ld_group.get(ld_name, [])
            items_arr = entry.get("Properties", {}).get("LootDropItemArray", []) or []
            for drop_item in items_arr:
                item_asset = (drop_item.get("ItemId") or {}).get("AssetPathName", "")
                if not item_asset:
                    continue
                item_name = _ue_asset_base_name(item_asset) or ""
                item_name = item_name.removeprefix("Id_Item_")
                item_name = _VARIANT_RE.sub("", item_name)
                for mon in monsters:
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

    # ─── Import: Spawners & Matches ───

    def import_spawners_and_matches(self):
        from search_engine import build_all_matches
        matches, spawners = build_all_matches()
        c = self.conn.cursor()
        c.execute("DELETE FROM spawners")
        c.execute("DELETE FROM search_term_matches")
        for s in spawners:
            c.execute(
                "INSERT INTO spawners (keyword, original_keyword, spawner_type, x, y, z, json_filename, module_type, version, map_base) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (s["keyword"], s.get("original_keyword", ""), s["spawner_type"], s["x"], s["y"], s["z"], s["json_filename"], s.get("module_type", ""), s.get("version", ""), s.get("map_base", "")),
            )
        for term, spawner_ids in matches.items():
            rows = [(term, sid) for sid in spawner_ids]
            c.executemany(
                "INSERT OR IGNORE INTO search_term_matches (search_term, spawner_id) VALUES (?, ?)",
                rows,
            )
        self.conn.commit()
        return len(spawners), len(matches)

    # ─── FTS Rebuild ───

    def _rebuild_fts(self, fts_table: str, content_table: str):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
        self.conn.commit()

    # ─── Query Helpers ───

    def get_item_entities(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT item_name, translation_key, category FROM item_entities ORDER BY item_name")
        return [dict(r) for r in c.fetchall()]

    def get_monster_entities(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT monster_name, translation_key FROM monster_entities ORDER BY monster_name")
        return [dict(r) for r in c.fetchall()]

    def get_props_entities(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT asset_name, translation_key FROM props_entities ORDER BY asset_name")
        return [dict(r) for r in c.fetchall()]

    def get_dungeon_modules(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT module_name, translation_key, module_group, size_x, size_y, sl_base_name FROM dungeon_modules ORDER BY module_name")
        return [dict(r) for r in c.fetchall()]

    def get_lootdrop_relationships(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("SELECT item_name, monster_name FROM lootdrop_items ORDER BY item_name, monster_name")
        return [dict(r) for r in c.fetchall()]

    def get_spawner_matches(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("""
            SELECT sm.search_term, s.keyword, s.spawner_type, s.x, s.y, s.z,
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
        c.execute("""
            SELECT DISTINCT s.x, s.y, s.z, s.json_filename, s.version, s.map_base, s.module_type
            FROM search_term_matches sm
            JOIN spawners s ON s.id = sm.spawner_id
            WHERE sm.search_term = ?
            ORDER BY s.map_base, s.json_filename
        """, (item_name,))
        return [dict(r) for r in c.fetchall()]

    def get_items_with_matches(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute("""
            SELECT e.item_name, e.translation_key, e.category,
                   GROUP_CONCAT(DISTINCT l.monster_name) as monster_names
            FROM item_entities e
            LEFT JOIN lootdrop_items l ON l.item_name = e.item_name
            GROUP BY e.item_name
            ORDER BY e.item_name
        """)
        results = []
        for r in c.fetchall():
            d = dict(r)
            d["monster_names"] = d["monster_names"].split(",") if d["monster_names"] else []
            results.append(d)
        return results

    def close(self):
        self.conn.close()
