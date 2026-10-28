import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from module_spawn_rate import (  # noqa: E402
    compute_spawn_rates,
    rare_chances,
    rare_groups,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_module_entries import _write_dungeon  # noqa: E402


class RareGroupsTest(unittest.TestCase):
    def test_only_groups_with_num_max_rares(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_dungeon(
                root,
                "Id_Dungeon_RandomCrypt_N_Solo",
                module_type="Crypt",
                level_asset="Crypt_5x5_HR_R_P.Crypt_5x5_HR_R_P",
                extra={"NumMaxRares": 1, "RareChance": 15},
            )
            _write_dungeon(
                root,
                "Id_Dungeon_RandomRuins_N_Solo",
                module_type="Ruins",
                level_asset="Ruins_5x5_HR_R_P.Ruins_5x5_HR_R_P",
            )
            self.assertEqual(rare_groups(root), {"Crypt"})

    def test_missing_dir_returns_empty(self):
        self.assertEqual(rare_groups(Path("/nonexistent-dungeon")), set())


class RareChancesTest(unittest.TestCase):
    def test_reads_rare_chance_only_for_rare_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_dungeon(
                root,
                "Id_Dungeon_RandomCrypt_N_Solo",
                module_type="Crypt",
                level_asset="Crypt_5x5_HR_R_P.Crypt_5x5_HR_R_P",
                extra={"NumMaxRares": 1, "RareChance": 15},
            )
            _write_dungeon(
                root,
                "Id_Dungeon_RandomCrypt_HR_Trio",
                module_type="Crypt",
                level_asset="Crypt_5x5_HR_R_P.Crypt_5x5_HR_R_P",
                extra={"NumMaxRares": 1, "RareChance": 15},
            )
            _write_dungeon(
                root,
                "Id_Dungeon_RandomRuins_N_Solo",
                module_type="Ruins",
                level_asset="Ruins_5x5_HR_R_P.Ruins_5x5_HR_R_P",
                extra={"RareChance": 99},
            )
            self.assertEqual(rare_chances(root), {"Crypt": 15.0})

    def test_group_without_rare_chance_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_dungeon(
                root,
                "Id_Dungeon_RandomCrypt_N_Solo",
                module_type="Crypt",
                level_asset="Crypt_5x5_HR_R_P.Crypt_5x5_HR_R_P",
                extra={"NumMaxRares": 1},
            )
            self.assertEqual(rare_chances(root), {})


class ComputeSpawnRatesTest(unittest.TestCase):
    def test_uses_rare_chance_directly(self):
        modules = [{"module_name": f"Crypt_Rare_{i}", "module_group": "Crypt", "is_rare": True} for i in range(5)]
        rates = compute_spawn_rates(modules, {"Crypt": 15.0})
        self.assertEqual(set(rates.values()), {15.0})

    def test_groups_without_rare_slots_get_no_rate(self):
        modules = [
            {"module_name": "Ruins_Outer_01", "module_group": "Ruins", "is_rare": True},
        ]
        self.assertEqual(compute_spawn_rates(modules, {"Crypt": 15.0}), {})

    def test_non_rare_modules_are_skipped(self):
        modules = [
            {"module_name": "Crypt_Plain", "module_group": "Crypt", "is_rare": False},
        ]
        self.assertEqual(compute_spawn_rates(modules, {"Crypt": 15.0}), {})

    def test_zero_or_missing_chance_yields_no_rate(self):
        modules = [
            {"module_name": "Crypt_A", "module_group": "Crypt", "is_rare": True},
        ]
        self.assertEqual(compute_spawn_rates(modules, {"Crypt": 0}), {})


class SpawnRateCachingTest(unittest.TestCase):
    """概率要写进 DB，否则没有游戏导出的 CI 会把它算成 0。"""

    def test_importer_persists_spawn_rate(self):
        import sqlite3

        from db.importers.modules import ModulesImporter
        from db.schema import SchemaManager

        with tempfile.TemporaryDirectory() as tmp:
            conn = sqlite3.connect(Path(tmp) / "test.db")
            conn.row_factory = sqlite3.Row
            SchemaManager(conn).create_tables()
            cur = conn.cursor()
            cur.executemany(
                "INSERT INTO dungeon_modules (module_name, module_group, is_rare) VALUES (?, ?, ?)",
                [(f"Crypt_Rare_{i}", "Crypt", 1) for i in range(5)],
            )
            conn.commit()
            ModulesImporter(conn)._store_spawn_rates(chances={"Crypt": 15.0})
            rows = cur.execute("SELECT spawn_rate FROM dungeon_modules WHERE module_group = 'Crypt'").fetchall()
            self.assertEqual({row[0] for row in rows}, {15.0})

    def test_missing_assets_keep_stored_values(self):
        import sqlite3

        from db.importers.modules import ModulesImporter
        from db.schema import SchemaManager

        with tempfile.TemporaryDirectory() as tmp:
            conn = sqlite3.connect(Path(tmp) / "test.db")
            conn.row_factory = sqlite3.Row
            SchemaManager(conn).create_tables()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dungeon_modules (module_name, module_group, is_rare, spawn_rate)"
                " VALUES ('Crypt_A', 'Crypt', 1, 15)"
            )
            conn.commit()
            # 空 chances 表示资产缺失，必须保留旧值而不是清零
            ModulesImporter(conn)._store_spawn_rates(chances={})
            value = cur.execute("SELECT spawn_rate FROM dungeon_modules WHERE module_name = 'Crypt_A'").fetchone()[0]
            self.assertEqual(value, 15)


if __name__ == "__main__":
    unittest.main()
