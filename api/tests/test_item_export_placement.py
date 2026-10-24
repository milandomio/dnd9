import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db.repositories.lootdrops import LootdropsRepository  # noqa: E402
from db.schema import SchemaManager  # noqa: E402
from entity_export import export_items  # noqa: E402


def _coord(keyword: str) -> dict:
    return {
        "keyword": keyword,
        "x": 1.0,
        "y": 2.0,
        "z": 3.0,
        "yaw": 0.0,
        "map_base": "TestMap",
        "json_filename": "TestMap_HR_D.json",
        "version": "",
        "spawner_type": "lootdrop",
        "original_keyword": keyword,
        "group_parent": "",
        "sub_group_parent": "",
    }


def _item(name: str, spawner_type: str = "lootdrop") -> dict:
    return {
        "item_name": name,
        "raw_name": f"Id_Item_{name}",
        "translation_key": f"Text_DesignData_Item_Item_{name}",
        "category": "",
        "variant_count": 1,
        "spawner_type": spawner_type,
    }


class SelfPlacedItemQueryTest(unittest.TestCase):
    """`get_self_placed_item_keywords` must find ground-placed lootdrops only."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "placed.db"
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        SchemaManager(conn).create_tables()
        conn.executemany(
            "INSERT INTO spawners (keyword, original_keyword, spawner_type, has_lootdrop, x, y, z, yaw,"
            " json_filename, version, map_base, group_parent, sub_group_parent, is_container)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("BronzeScale", "BronzeScale", "unknown", 1, 0, 0, 0, 0, "A_HR_D.json", "", "A", "", "", 0),
                ("BrokenGlasses", "BrokenGlasses", "unknown", 1, 0, 0, 0, 0, "B_HR_D.json", "", "B", "", "", 0),
                ("Lifeleaf", "Lifeleaf", "props", 0, 0, 0, 0, 0, "C_HR_D.json", "", "C", "", "", 0),
                ("SkeletonMage", "SkeletonMage", "monster", 1, 0, 0, 0, 0, "D_HR_D.json", "", "D", "", "", 0),
                ("FrostWyvernEgg", "FrostWyvernEgg", "lootdrop", 0, 0, 0, 0, 0, "E_HR_D.json", "", "E", "", "", 0),
            ],
        )
        conn.executemany(
            "INSERT INTO spawner_entries (spawner_keyword, entity_name, spawn_rate, dungeon_grades,"
            " lootdrop_group_id, session_spawn_limit) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("BronzeScale", "", 100.0, "[]", "ID_LootdropGroup_BronzeScale", 0),
                ("BrokenGlasses", "", 100.0, "[]", "ID_LootdropGroup_BrokenGlasses", 0),
                ("Lifeleaf", "", 100.0, "[]", "ID_LootdropGroup_Lifeleaf", 0),
                ("SkeletonMage", "SkeletonMage", 100.0, "[]", "ID_LootdropGroup_SkeletonMage", 0),
                # Prefixed keyword: the spawners row is named without the prefix.
                ("Spawn_FrostWyvernEgg", "", 100.0, "[]", "ID_LootdropGroup_FrostWyvernEgg", 0),
            ],
        )
        conn.commit()
        self.repo = LootdropsRepository(conn)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_ground_placed_lootdrops(self):
        keywords = self.repo.get_self_placed_item_keywords()

        self.assertIn("BronzeScale", keywords)
        self.assertIn("BrokenGlasses", keywords)

    def test_excludes_props_entities(self):
        # Lifeleaf has an empty entity_name too, but props own /props pages.
        self.assertNotIn("Lifeleaf", self.repo.get_self_placed_item_keywords())

    def test_excludes_monster_bound_spawners(self):
        self.assertNotIn("SkeletonMage", self.repo.get_self_placed_item_keywords())

    def test_strips_spawn_prefix(self):
        # `Spawn_FrostWyvernEgg` has no spawners row of its own; the placed
        # entity is `FrostWyvernEgg`.
        keywords = self.repo.get_self_placed_item_keywords()

        self.assertIn("FrostWyvernEgg", keywords)


class SelfPlacedItemExportTest(unittest.TestCase):
    """`export_items` keeps self-placed lootdrops that a monster also drops."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "json"
        self.items = [
            _item("BronzeScale"),
            _item("SkullKey"),
            _item("DemonSword"),
            _item("Lifeleaf", spawner_type="props"),
        ]
        self.merged_loot = {
            "BronzeScale": ["SkeletonMage"],
            "SkullKey": ["Cerberus"],
            "DemonSword": ["DemonImp"],
            "Lifeleaf": ["GiantWorm"],
        }
        self.all_coords = {name: [_coord(name)] for name in ("BronzeScale", "SkullKey", "DemonSword", "Lifeleaf")}

    def tearDown(self):
        self._tmp.cleanup()

    def _export(self, self_placed):
        return export_items(
            self.items,
            self.merged_loot,
            self.all_coords,
            lambda name, key, scope: name,
            set(),
            {},
            set(self.all_coords),
            self.out,
            self_placed_items=self_placed,
        )

    def test_keeps_self_placed_item_with_monster_sources(self):
        index = self._export({"BronzeScale", "SkullKey"})
        names = {entry["name"] for entry in index}

        self.assertIn("BronzeScale", names)
        self.assertIn("SkullKey", names)
        # Monster-only drop without its own spawner stays on /lootdrops.
        self.assertNotIn("DemonSword", names)

    def test_without_self_placed_set_keeps_old_behaviour(self):
        # Every fixture item is also in a monster loot group, so the legacy
        # rule drops all of them — this pins the pre-fix behaviour.
        index = self._export(set())

        self.assertEqual(index, [])

    def test_ground_items_always_kept(self):
        merged = dict(self.merged_loot, DemonSword=["Ground", "DemonImp"])

        index = export_items(
            self.items,
            merged,
            self.all_coords,
            lambda name, key, scope: name,
            set(),
            {},
            set(self.all_coords),
            self.out,
            self_placed_items=set(),
        )

        self.assertIn("DemonSword", {entry["name"] for entry in index})


if __name__ == "__main__":
    unittest.main()
