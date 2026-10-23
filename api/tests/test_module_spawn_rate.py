import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from module_spawn_rate import (  # noqa: E402
    compute_spawn_rates,
    layout_stats,
    rare_groups,
    rare_pool_sizes,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_module_entries import _write_dungeon  # noqa: E402


def _write_module(root: Path, name: str, *, group: str, rare: bool, size=(1, 1)) -> None:
    import json

    payload = [
        {
            "Type": "DCDungeonModuleDataAsset",
            "Name": f"Id_DungeonModule_{name}",
            "Properties": {
                "ModuleType": f"EDCDungeonModuleType::{group}",
                "Size": {"X": size[0], "Y": size[1]},
                "bIsRare": rare,
            },
        }
    ]
    (root / f"Id_DungeonModule_{name}.json").write_text(json.dumps(payload), encoding="utf-8")


class RareGroupsTest(unittest.TestCase):
    def test_only_groups_with_num_max_rares(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_dungeon(
                root,
                "Id_Dungeon_RandomCrypt_N_Solo",
                module_type="Crypt",
                level_asset="Crypt_5x5_HR_R_P.Crypt_5x5_HR_R_P",
                extra={"NumMaxRares": 1},
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


class RarePoolTest(unittest.TestCase):
    def test_counts_only_rare_modules_per_group(self):
        modules = [
            {"module_name": "Crypt_A", "module_group": "Crypt", "is_rare": True},
            {"module_name": "Crypt_B", "module_group": "Crypt", "is_rare": True},
            {"module_name": "Crypt_C", "module_group": "Crypt", "is_rare": False},
            {"module_name": "Ruins_A", "module_group": "Ruins", "is_rare": True},
        ]
        self.assertEqual(rare_pool_sizes(modules), {"Crypt": 2, "Ruins": 1})


class ComputeSpawnRatesTest(unittest.TestCase):
    def _stats(self, group="Crypt", layouts=40, rare_layouts=2, grid=5, fixed=(4,)):
        return {
            group: {
                "source": "assets",
                "layouts": layouts,
                "rare_layouts": rare_layouts,
                "grid": grid,
                "fixed_cells": list(fixed),
            }
        }

    def test_matches_documented_crypt_value(self):
        modules = [
            {
                "module_name": f"Crypt_Rare_{i}",
                "module_group": "Crypt",
                "is_rare": True,
            }
            for i in range(5)
        ]
        rates = compute_spawn_rates(modules, self._stats())
        for name in rates:
            self.assertEqual(rates[name], 0.84)

    def test_groups_without_rare_slots_get_no_rate(self):
        modules = [
            {"module_name": "Ruins_Outer_01", "module_group": "Ruins", "is_rare": True},
        ]
        self.assertEqual(compute_spawn_rates(modules, self._stats()), {})

    def test_rare_pool_size_shrinks_rate(self):
        modules = [
            {"module_name": "Crypt_A", "module_group": "Crypt", "is_rare": True},
            {"module_name": "Crypt_B", "module_group": "Crypt", "is_rare": True},
        ]
        rates = compute_spawn_rates(modules, self._stats())
        self.assertEqual(rates["Crypt_A"], 2.1)

    def test_missing_layouts_yield_no_rates(self):
        modules = [
            {"module_name": "Crypt_A", "module_group": "Crypt", "is_rare": True},
        ]
        stats = self._stats(layouts=0, rare_layouts=0, fixed=())
        self.assertEqual(compute_spawn_rates(modules, stats), {})


class SpawnRateCachingTest(unittest.TestCase):
    """概率要写进 DB，否则没有游戏导出的 CI 会把它算成 0。"""

    def test_importer_persists_spawn_rate(self):
        import sqlite3

        from db.importers.modules import ModulesImporter
        from db.schema import SchemaManager

        # 显式注入统计，测试不依赖游戏导出目录（CI 里没有）
        stats = {
            "Crypt": {
                "source": "assets",
                "layouts": 40,
                "rare_layouts": 2,
                "grid": 5,
                "fixed_cells": [4],
            }
        }
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
            ModulesImporter(conn)._store_spawn_rates(stats=stats)
            rows = cur.execute("SELECT spawn_rate FROM dungeon_modules WHERE module_group = 'Crypt'").fetchall()
            self.assertEqual({row[0] for row in rows}, {0.84})

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
                " VALUES ('Crypt_A', 'Crypt', 1, 0.84)"
            )
            conn.commit()
            # 空 stats 表示资产缺失，必须保留旧值而不是清零
            ModulesImporter(conn)._store_spawn_rates(stats={})
            value = cur.execute("SELECT spawn_rate FROM dungeon_modules WHERE module_name = 'Crypt_A'").fetchone()[0]
            self.assertEqual(value, 0.84)


class LayoutStatsFallbackTest(unittest.TestCase):
    def test_uses_baseline_when_layout_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            module_dir = Path(tmp) / "DungeonModule"
            module_dir.mkdir()
            _write_module(module_dir, "CenterTower", group="Crypt", rare=False, size=(2, 2))
            dungeon_dir = Path(tmp) / "Dungeon"
            dungeon_dir.mkdir()
            _write_dungeon(
                dungeon_dir,
                "Id_Dungeon_RandomCrypt_N_Solo",
                module_type="Crypt",
                level_asset="Crypt_5x5_HR_R_P.Crypt_5x5_HR_R_P",
                extra={"NumMaxRares": 1},
            )
            stats = layout_stats(module_dir, Path(tmp) / "NoLayouts")
            self.assertEqual(stats["Crypt"]["source"], "baseline")
            self.assertEqual(stats["Crypt"]["layouts"], 40)
            self.assertEqual(stats["Crypt"]["rare_layouts"], 2)
            # CenterTower 2x2 覆盖 4 格
            self.assertEqual(stats["Crypt"]["fixed_cells"], [4])


if __name__ == "__main__":
    unittest.main()
