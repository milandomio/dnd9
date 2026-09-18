import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db._helpers import (  # noqa: E402
    monster_class_from_properties,
    monster_is_passive,
    monster_list_type,
    monster_race_from_properties,
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
            monster_class_from_properties({"ClassType": {"TagName": "Type.Monster.Class.Normal"}}),
            "Normal",
        )
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
        self.assertEqual(monster_list_type("Passive"), "misc")
        self.assertEqual(monster_list_type(""), "normal")

    def test_passive_from_abilities_and_npc(self):
        salmon = {
            "ClassType": {"TagName": "Type.Monster.Class.Normal"},
            "IdTag": {"TagName": "Id.Monster.Salmon"},
            "Abilities": [
                {"AssetPathName": "/Game/.../Id_MonsterAbility_Salmon_RunState.Id_MonsterAbility_Salmon_RunState"},
                {"AssetPathName": "/Game/.../Id_MonsterAbility_Salmon_Death.Id_MonsterAbility_Salmon_Death"},
            ],
        }
        archer = {
            "ClassType": {"TagName": "Type.Monster.Class.Normal"},
            "IdTag": {"TagName": "Id.Monster.SkeletonArcher"},
            "Abilities": [
                {
                    "AssetPathName": "/Game/.../Id_MonsterAbility_SkeletonArcherAttackState.Id_MonsterAbility_SkeletonArcherAttackState"
                },
                {
                    "AssetPathName": "/Game/.../Id_MonsterAbility_SkeletonArcherDeath.Id_MonsterAbility_SkeletonArcherDeath"
                },
            ],
        }
        goblin = {
            "ClassType": {"TagName": "Type.Monster.Class.Normal"},
            "IdTag": {"TagName": "Id.Monster.LootGoblin.Unique"},
            "Abilities": [
                {
                    "AssetPathName": "/Game/.../Id_MonsterAbility_LootGoblin_Surprised.Id_MonsterAbility_LootGoblin_Surprised"
                },
                {"AssetPathName": "/Game/.../Id_MonsterAbility_LootGoblin_Death.Id_MonsterAbility_LootGoblin_Death"},
            ],
        }
        urchin = {
            "ClassType": {"TagName": "Type.Monster.Class.Normal"},
            "IdTag": {"TagName": "Id.Monster.Seaurchin"},
            "Abilities": [
                {
                    "AssetPathName": "/Game/.../Id_MonsterAbility_Seaurchin_AddBleeding.Id_MonsterAbility_Seaurchin_AddBleeding"
                },
                {"AssetPathName": "/Game/.../Id_MonsterAbility_Seaurchin_Death.Id_MonsterAbility_Seaurchin_Death"},
            ],
        }
        expressman = {
            "ClassType": {"TagName": "Type.Monster.Class.Normal"},
            "IdTag": {"TagName": "Id.NPC.Expressman"},
            "Abilities": [
                {"AssetPathName": "/Game/.../Id_NPCAbility_Expressman_Gesture_1.Id_NPCAbility_Expressman_Gesture_1"},
            ],
        }
        self.assertTrue(monster_is_passive(salmon))
        self.assertEqual(monster_class_from_properties(salmon), "Passive")
        self.assertFalse(monster_is_passive(archer))
        self.assertEqual(monster_class_from_properties(archer), "Normal")
        self.assertFalse(monster_is_passive(goblin))
        self.assertEqual(monster_class_from_properties(goblin), "Normal")
        self.assertFalse(monster_is_passive(urchin))
        self.assertEqual(monster_class_from_properties(urchin), "Normal")
        self.assertTrue(monster_is_passive(expressman))
        self.assertEqual(monster_class_from_properties(expressman), "Passive")
        self.assertEqual(preferred_monster_class("Passive", "Normal"), "Normal")
        self.assertEqual(preferred_monster_class("Normal", "Passive"), "Normal")

    def test_race_from_properties(self):
        self.assertEqual(
            monster_race_from_properties(
                {
                    "CharacterTypes": [
                        {"TagName": "Type.Character.Undead.Ghost"},
                        {"TagName": "Type.Character.Undead"},
                    ]
                }
            ),
            "Ghost",
        )
        self.assertEqual(
            monster_race_from_properties({"CharacterTypes": [{"TagName": "Type.Character.Beast.Aquatic"}]}),
            "Aquatic",
        )
        self.assertEqual(
            monster_race_from_properties(
                {
                    "CharacterTypes": [
                        {"TagName": "Type.Character.Demon.Demon"},
                        {"TagName": "Type.Character.Aberration"},
                        {"TagName": "Type.Character.Demon"},
                    ]
                }
            ),
            "Demon",
        )
        self.assertEqual(monster_race_from_properties({}), "")


class ExportMonsterTypeTest(unittest.TestCase):
    def test_index_uses_highest_class(self):
        monsters = [
            {
                "monster_name": "Banshee",
                "translation_key": "Text_DesignData_Monster_Monster_Banshee",
                "class_type": "Boss",
                "race": "Ghost",
            },
            {
                "monster_name": "Banshee_Elite",
                "translation_key": "Text_DesignData_Monster_Monster_Banshee",
                "class_type": "Normal",
                "race": "Ghost",
            },
            {
                "monster_name": "SkeletonChampion",
                "translation_key": "Text_DesignData_Monster_Monster_SkeletonChampion",
                "class_type": "SubBoss",
                "race": "Skeleton",
            },
            {
                "monster_name": "SkeletonArcher",
                "translation_key": "Text_DesignData_Monster_Monster_SkeletonArcher",
                "class_type": "Normal",
                "race": "Skeleton",
            },
            {
                "monster_name": "Salmon",
                "translation_key": "Text_DesignData_Monster_Monster_Salmon",
                "class_type": "Passive",
                "race": "Aquatic",
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
        by_name = {row["name"]: row for row in index}
        self.assertEqual(by_name["Banshee"]["type"], "boss")
        self.assertEqual(by_name["Banshee"]["race"], "Ghost")
        self.assertEqual(by_name["SkeletonChampion"]["type"], "miniboss")
        self.assertEqual(by_name["SkeletonChampion"]["race"], "Skeleton")
        self.assertEqual(by_name["SkeletonArcher"]["type"], "normal")
        self.assertEqual(by_name["Salmon"]["type"], "misc")
        self.assertEqual(by_name["Salmon"]["race"], "Aquatic")


if __name__ == "__main__":
    unittest.main()
