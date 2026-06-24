import re
import sqlite3
from pathlib import Path

from config import DB_PATH

from ._helpers import load_game_json
from .importers import ImporterRegistry
from .repositories import RepositoryRegistry
from .schema import SchemaManager


class DatabaseManager:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.schema = SchemaManager(self.conn)
        self.schema.create_tables()
        self.importers = ImporterRegistry(self.conn)
        self.repos = RepositoryRegistry(self.conn)

    _CRACKED_RE = re.compile(r"（裂开）")

    def connect(self):
        return self.conn

    def close(self):
        self.conn.close()

    def _rebuild_fts(self, fts_table: str, content_table: str):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
        self.conn.commit()

    # ─── Translation ───

    def import_translations(self):
        data = load_game_json()
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

    def get_translations_map(self) -> dict[str, str]:
        c = self.conn.cursor()
        c.execute("SELECT key, value FROM translations")
        return {r["key"]: r["value"] for r in c.fetchall()}

    # ─── Entity Classification (composite) ───

    def get_entity_classification(self) -> dict[str, dict]:
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

    # ─── Import Delegation ───

    def import_items(self) -> int:
        return self.importers.items.import_all()

    def import_monsters(self) -> int:
        return self.importers.monsters.import_all()

    def import_props(self) -> int:
        return self.importers.props.import_all()

    def import_dungeon_modules(self) -> int:
        return self.importers.modules.import_all()

    def import_lootdrops(self, spawner_monster_map: dict[str, list[str]] | None = None) -> int:
        return self.importers.lootdrops.import_all(spawner_monster_map)

    def import_spawner_fallback_entities(self) -> dict[str, int]:
        return self.importers.spawners.import_spawner_fallback_entities()

    def import_spawner_entries(self) -> int:
        return self.importers.spawners.import_spawner_entries()

    def import_lootdrop_groups(self) -> int:
        return self.importers.spawners.import_lootdrop_groups()

    def import_lootdrop_rate_items(self) -> int:
        return self.importers.spawners.import_lootdrop_rate_items()

    def import_lootdrop_rate_weights(self) -> int:
        return self.importers.spawners.import_lootdrop_rate_weights()

    def import_quest_items(self, items: list[dict]) -> int:
        return self.importers.quests.import_items(items)

    def import_quest_npcs(self, npcs: list[dict]) -> int:
        return self.importers.quests.import_npcs(npcs)

    def import_explore_targets(self, targets: list[dict]) -> int:
        return self.importers.quests.import_explore_targets(targets)

    # ─── Repository Delegation ───

    def get_item_entities(self) -> list[dict]:
        return self.repos.items.get_all()

    def get_monster_entities(self) -> list[dict]:
        return self.repos.monsters.get_all()

    def get_monster_name_map(self) -> dict[str, str]:
        return self.repos.monsters.get_name_map()

    def get_props_entities(self) -> list[dict]:
        return self.repos.props.get_all()

    def get_dungeon_modules(self) -> list[dict]:
        return self.repos.modules.get_all()

    def get_lootdrop_relationships(self) -> list[dict]:
        return self.repos.lootdrops.get_relationships()

    def get_spawner_entries_for_keyword(self, keyword: str) -> list[dict]:
        return self.repos.lootdrops.get_spawner_entries_for_keyword(keyword)

    def get_all_spawner_entries(self) -> list[dict]:
        return self.repos.lootdrops.get_all_spawner_entries()

    def get_item_drop_rate(self, lootdrop_group_id: str, item_name: str, full_grade: int) -> float:
        return self.repos.lootdrops.get_item_drop_rate(lootdrop_group_id, item_name, full_grade)

    def get_items_with_matches(self) -> list[dict]:
        return self.repos.items.get_with_matches()

    def get_quest_items(self) -> list[dict]:
        return self.repos.quests.get_items()

    def get_quest_npcs(self) -> list[dict]:
        return self.repos.quests.get_npcs()

    def get_explore_targets(self) -> list[dict]:
        return self.repos.quests.get_explore_targets()

    def get_all_coordinates(self) -> dict[str, list[dict]]:
        return self.repos.coordinates.get_all()

    def get_coord_variant_counts(self) -> dict[tuple[str, str, str], tuple[int, list[str]]]:
        return self.repos.coordinates.get_variant_counts()
