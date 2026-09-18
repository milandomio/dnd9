import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db._helpers import (  # noqa: E402
    monster_class_from_properties,
    monster_list_type,
    preferred_monster_class,
)
from entity_export import export_monsters  # noqa: E402


def _coord(name: str, x: float, map_base: str, filename: str) -> dict:
    return {
        "x": x,
        "y": 0,
        "z": 0,
        "yaw": 0,
        "map_base": map_base,
        "json_filename": filename,
        "version": "",
        "keyword": name,
        "original_keyword": name,
        "search_term": name,
    }


class MonsterClassHelpersTest(unittest.TestCase):
    def test_class_from_properties(self):
        self.assertEqual(
            monster_class_from_properties({"ClassType": {"TagName": "Type.Monster.Class.Boss"}}),
            "Boss",
        )
        self.assertEqual(
            monster_class_from_properties({"ClassType": {"TagName": "Type.Monster.Class.SubBoss"}}),
            "SubBoss",
        )
        self.assertEqual(
            monster_class_from_properties({"ClassType": {"TagName": "Type.Monster.Class.Normal"}}),
            "Normal",
        )
        self.assertEqual(monster_class_from_properties({}), "")
        self.assertEqual(
            monster_class_from_properties({"ClassType": {"TagName": "Type.Monster.Class.Unknown"}}),
            "",
        )

    def test_preferred_and_list_type(self):
        self.assertEqual(preferred_monster_class("Normal", "Boss"), "Boss")
        self.assertEqual(preferred_monster_class("Boss", "SubBoss"), "Boss")
        self.assertEqual(preferred_monster_class("", "SubBoss"), "SubBoss")
        self.assertEqual(monster_list_type("Boss"), "boss")
        self.assertEqual(monster_list_type("SubBoss"), "miniboss")
        self.assertEqual(monster_list_type("Normal"), "normal")
        self.assertEqual(monster_list_type(""), "normal")


class ExportMonsterTypeTest(unittest.TestCase):
    def test_index_uses_highest_class(self):
        monsters = [
            {
                "monster_name": "Banshee",
                "translation_key": "Text_DesignData_Monster_Monster_Banshee",
                "class_type": "Boss",
            },
            {
                "monster_name": "Banshee_Elite",
                "translation_key": "Text_DesignData_Monster_Monster_Banshee",
                "class_type": "Normal",
            },
            {
                "monster_name": "SkeletonChampion",
                "translation_key": "Text_DesignData_Monster_Monster_SkeletonChampion",
                "class_type": "SubBoss",
            },
            {
                "monster_name": "SkeletonArcher",
                "translation_key": "Text_DesignData_Monster_Monster_SkeletonArcher",
                "class_type": "Normal",
            },
        ]
        names = {m["monster_name"] for m in monsters}
        coords = {name: [_coord(name, i, "Ruins", f"{name}.json")] for i, name in enumerate(names)}
        with tempfile.TemporaryDirectory() as tmp:
            index = export_monsters(
                monsters,
                coords,
                resolve_name=lambda name, key, kind: ("Banshee" if name.startswith("Banshee") else name),
                coord_variant_count={},
                monster_names=names,
                output_dir=Path(tmp),
                entity_data_out={},
            )
        by_name = {row["name"]: row["type"] for row in index}
        self.assertEqual(by_name["Banshee"], "boss")
        self.assertEqual(by_name["SkeletonChampion"], "miniboss")
        self.assertEqual(by_name["SkeletonArcher"], "normal")


if __name__ == "__main__":
    unittest.main()
