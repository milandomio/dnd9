import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db._helpers import module_placement_flags  # noqa: E402
from db.importers.modules import (  # noqa: E402
    ENTRY_LAYOUT_SIZE,
    _layout_size,
    load_entry_groups,
)


def _write_dungeon(root: Path, name: str, *, module_type: str, level_asset: str) -> None:
    payload = [
        {
            "Type": "DCDungeonDataAsset",
            "Name": name,
            "Properties": {
                "ModuleType": f"EDCDungeonModuleType::{module_type}",
                "LevelAsset": {"AssetPathName": level_asset, "SubPathString": ""},
                "LayoutSize": _layout_size(level_asset),
            },
        }
    ]
    (root / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")


class LayoutSizeTest(unittest.TestCase):
    def test_extracts_grid_size(self):
        self.assertEqual(_layout_size("/Game/.../Crypt_5x5_HR_R_P.Crypt_5x5_HR_R_P"), 5)
        self.assertEqual(_layout_size("ShipGraveyard_7x7_01_HR_P.ShipGraveyard_7x7_01_HR_P"), 7)
        self.assertEqual(_layout_size("Firedeep_3x3_01_N_P.Firedeep_3x3_01_N_P"), 3)

    def test_returns_none_without_size(self):
        self.assertIsNone(_layout_size(""))
        self.assertIsNone(_layout_size("Arena_Crypt_Vault_P"))


class LoadEntryGroupsTest(unittest.TestCase):
    def test_only_five_by_five_groups_are_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_dungeon(
                root,
                "Id_Dungeon_RandomCrypt_N_Solo",
                module_type="Crypt",
                level_asset="Crypt_5x5_HR_R_P.Crypt_5x5_HR_R_P",
            )
            _write_dungeon(
                root,
                "Id_Dungeon_RandomShipGraveyard_N_Solo",
                module_type="ShipGraveyard",
                level_asset="ShipGraveyard_7x7_01_HR_P.ShipGraveyard_7x7_01_HR_P",
            )
            groups = load_entry_groups(root)
            self.assertEqual(groups, {"Crypt": ENTRY_LAYOUT_SIZE})

    def test_s2r_dungeons_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_dungeon(
                root,
                "Id_Dungeon_RandomRuins_S2R",
                module_type="Ruins",
                level_asset="Ruins_5x5_HR_R_P.Ruins_5x5_HR_R_P",
            )
            self.assertEqual(load_entry_groups(root), {})

    def test_missing_directory_returns_empty(self):
        self.assertEqual(load_entry_groups(Path("/nonexistent-dungeon-dir")), {})


class ModulePlacementFlagsTest(unittest.TestCase):
    def test_edge_only(self):
        self.assertEqual(module_placement_flags({"bEdgeOnly": True}), (True, False))

    def test_corner_only(self):
        self.assertEqual(module_placement_flags({"bCornerOnly": True}), (False, True))

    def test_plain_module(self):
        self.assertEqual(module_placement_flags({"bIsRare": True}), (False, False))

    def test_none_properties(self):
        self.assertEqual(module_placement_flags(None), (False, False))


if __name__ == "__main__":
    unittest.main()
