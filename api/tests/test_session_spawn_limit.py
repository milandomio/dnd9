import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db.importers.spawners import SpawnersImporter  # noqa: E402
from db.repositories.lootdrops import LootdropsRepository  # noqa: E402


def _spawner_entry(name: str, items: list[dict]) -> list[dict]:
    return [{"Type": "DCSpawnerDataAsset", "Name": name, "Properties": {"SpawnerItemArray": items}}]


def _item(monster_path: str, ldg_path: str, rate: int = 10000, limit: int | None = None) -> dict:
    item = {
        "LookupId": {"AssetPathName": "", "SubPathString": ""},
        "DungeonGrades": [2001, 2002],
        "LootDropGroupId": {"AssetPathName": ldg_path},
        "MonsterId": {"AssetPathName": monster_path},
        "PropsId": {"AssetPathName": ""},
        "SpawnRate": rate,
        "ItemHolderActorClassOverride": None,
        "ExcludedPlayModeTags": [],
    }
    if limit is not None:
        item["SessionSpawnLimit"] = limit
    return item


class SessionSpawnLimitTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.conn = sqlite3.connect(self.root / "test.db")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE spawner_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spawner_keyword TEXT NOT NULL,
                entity_name TEXT NOT NULL DEFAULT '',
                spawn_rate REAL NOT NULL DEFAULT 100.0,
                dungeon_grades TEXT NOT NULL DEFAULT '[]',
                lootdrop_group_id TEXT NOT NULL DEFAULT '',
                session_spawn_limit INTEGER NOT NULL DEFAULT 0
            )
        """)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def _import(self, entries: list[list[dict]]):
        from config import SPAWNER_DIR

        for name, payload in entries:
            (self.root / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
        importer = SpawnersImporter(self.conn)
        original = SPAWNER_DIR
        try:
            import db.importers.spawners as mod

            mod.SPAWNER_DIR = self.root
            return importer.import_spawner_entries()
        finally:
            mod.SPAWNER_DIR = original

    def test_npc_spawner_without_lootdrop_keeps_limit(self):
        """NPC spawners have no LootDropGroupId; the session limit must survive."""
        rows = self._import(
            [
                (
                    "Id_Spawner_New_NPC_GoblinSmuggler",
                    _spawner_entry(
                        "Id_Spawner_New_NPC_GoblinSmuggler",
                        [
                            _item(
                                "/Game/DungeonCrawler/Data/Generated/V2/Monster/Monster/"
                                "Id_NPC_GoblinSmuggler_Goblin_N.Id_NPC_GoblinSmuggler_Goblin_N",
                                "",
                                limit=1,
                            )
                        ],
                    ),
                )
            ]
        )
        self.assertEqual(rows, 1)
        row = self.conn.execute("SELECT * FROM spawner_entries").fetchone()
        self.assertEqual(row["spawner_keyword"], "GoblinSmuggler")
        self.assertEqual(row["entity_name"], "Id_NPC_GoblinSmuggler_Goblin_N")
        self.assertEqual(row["lootdrop_group_id"], "")
        self.assertEqual(row["session_spawn_limit"], 1)

    def test_lootdrop_spawner_records_limit(self):
        rows = self._import(
            [
                (
                    "Id_Spawner_Monster_X",
                    _spawner_entry(
                        "Id_Spawner_Monster_X",
                        [
                            _item(
                                "/Game/DungeonCrawler/Data/Generated/V2/Monster/Monster/"
                                "Id_Monster_CaveTroll_Common.Id_Monster_CaveTroll_Common",
                                "/Game/DungeonCrawler/Data/Generated/V2/LootDrop/LootdropGroup/"
                                "LootdropGroup_CaveTroll.LootdropGroup_CaveTroll",
                                limit=0,
                            )
                        ],
                    ),
                )
            ]
        )
        self.assertEqual(rows, 1)
        row = self.conn.execute("SELECT * FROM spawner_entries").fetchone()
        self.assertEqual(row["session_spawn_limit"], 0)
        self.assertEqual(row["lootdrop_group_id"], "LootdropGroup_CaveTroll")

    def test_missing_session_spawn_limit_defaults_to_zero(self):
        self._import(
            [
                (
                    "Id_Spawner_Monster_Y",
                    _spawner_entry(
                        "Id_Spawner_Monster_Y",
                        [
                            _item(
                                "/Game/DungeonCrawler/Data/Generated/V2/Monster/Monster/"
                                "Id_Monster_Slime_Common.Id_Monster_Slime_Common",
                                "/Game/DungeonCrawler/Data/Generated/V2/LootDrop/LootdropGroup/"
                                "LootdropGroup_Slime.LootdropGroup_Slime",
                            )
                        ],
                    ),
                )
            ]
        )
        row = self.conn.execute("SELECT session_spawn_limit FROM spawner_entries").fetchone()
        self.assertEqual(row["session_spawn_limit"], 0)

    def test_get_session_spawn_limits_aggregates_per_entity(self):
        self._import(
            [
                (
                    "Id_Spawner_New_NPC_GoblinSmuggler",
                    _spawner_entry(
                        "Id_Spawner_New_NPC_GoblinSmuggler",
                        [
                            _item(
                                "/Game/.../Id_NPC_GoblinSmuggler_Goblin_N.Id_NPC_GoblinSmuggler_Goblin_N",
                                "",
                                limit=1,
                            ),
                            _item(
                                "/Game/.../Id_NPC_GoblinSmuggler_Goblin_HR.Id_NPC_GoblinSmuggler_Goblin_HR",
                                "",
                                limit=1,
                            ),
                        ],
                    ),
                )
            ]
        )
        limits = LootdropsRepository(self.conn).get_session_spawn_limits()
        self.assertEqual(
            limits,
            {
                "Id_NPC_GoblinSmuggler_Goblin_N": 1,
                "Id_NPC_GoblinSmuggler_Goblin_HR": 1,
            },
        )

    def test_zero_limits_are_excluded_from_query(self):
        self._import(
            [
                (
                    "Id_Spawner_Monster_Z",
                    _spawner_entry(
                        "Id_Spawner_Monster_Z",
                        [
                            _item(
                                "/Game/.../Id_Monster_Slime_Common.Id_Monster_Slime_Common",
                                "/Game/.../LootdropGroup_Slime.LootdropGroup_Slime",
                                limit=0,
                            )
                        ],
                    ),
                )
            ]
        )
        self.assertEqual(LootdropsRepository(self.conn).get_session_spawn_limits(), {})


if __name__ == "__main__":
    unittest.main()
