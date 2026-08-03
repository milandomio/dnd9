import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quest_collector import _extract_npc_list  # noqa: E402
from quest_extractor.quest_extractor import QuestExtractor  # noqa: E402


class _Translator:
    values = {
        "Text_DesignData_Merchant_Merchant_TavernMaster": "酒馆老板",
        "Text_DesignData_Dungeon_DungeonModule_Center_Altar": "中心祭坛",
        "Text_DesignData_Dungeon_DungeonModule_ShipGraveyard_HangingShip": "吊船",
    }

    def translate(self, key):
        return self.values.get(key)

    def translate_npc(self, name):
        return self.values.get(f"Text_DesignData_Merchant_Merchant_{name}", name)


class _Extractor:
    module_asset_path = (
        "/Game/DungeonCrawler/Data/Generated/V2/Dungeon/DungeonModule/"
        "Id_DungeonModule_ShipGraveyard_HangingShip.Id_DungeonModule_ShipGraveyard_HangingShip"
    )

    def __init__(self):
        self.match_calls = []

    def group_quests_by_npc(self, use_translated_names):
        del use_translated_names
        return {
            "TavernMaster": [
                {
                    "id": "Id_Quest_TavernMaster_55",
                    "title_display": "海寇的藏身处",
                    "title_key": "Text_DesignData_Quest_TavernMaster_Title_55_EAS_09",
                    "quest_number": 58,
                    "contents": [
                        {
                            "content_type": "Explore",
                            "asset_path": "/Game/Quest/Id_QuestContent_Explore_HangingShip_01",
                            "content_data": {"ModuleId": {"AssetPathName": self.module_asset_path}},
                        }
                    ],
                    "rewards": [],
                }
            ]
        }

    def get_reward_item_info(self, reward):
        del reward
        return "", "item", ""

    def get_dungeon_type_translation(self, content_data):
        del content_data
        return None

    def match_asset_path_to_module(self, asset_path, content_data):
        self.match_calls.append((asset_path, content_data))
        return content_data["ModuleId"]["AssetPathName"]

    def get_explore_target_translation(self, asset_path):
        self.assert_module_path(asset_path)
        return "吊船"

    def assert_module_path(self, asset_path):
        assert asset_path == self.module_asset_path

    def get_source_string_from_asset_path(self, asset_path):
        self.assert_module_path(asset_path)
        return "Text_DesignData_Dungeon_DungeonModule_ShipGraveyard_HangingShip"


class _ModuleDb:
    def get_dungeon_modules(self):
        return [
            {
                "module_name": "IceCave_Hut_03",
                "translation_key": "Text_DesignData_Dungeon_DungeonModule_IceCave_Hut_C",
                "module_group": "IceCavern",
                "sl_base_name": "IceCave_Hut_03",
                "aliases": [],
            },
            {
                "module_name": "Ruins_Chapel",
                "translation_key": "",
                "module_group": "Ruins",
                "sl_base_name": "",
                "aliases": [],
            },
        ]


class QuestI18nTest(unittest.TestCase):
    def test_explore_targets_use_module_id_translation_key(self):
        extractor = _Extractor()

        result = _extract_npc_list(_Translator(), extractor, [])

        content = result[0]["quests"][0]["contents"][0]
        self.assertEqual(content["target"], "吊船")
        self.assertEqual(
            content["translation_key"],
            "Text_DesignData_Dungeon_DungeonModule_ShipGraveyard_HangingShip",
        )
        self.assertEqual(len(extractor.match_calls), 1)
        self.assertEqual(extractor.match_calls[0][1]["ModuleId"]["AssetPathName"], extractor.module_asset_path)

    def test_module_lookup_keeps_numbered_name_and_official_override(self):
        extractor = QuestExtractor(translator=_Translator(), db=_ModuleDb())
        numbered_path = "/Game/Data/Id_DungeonModule_IceCave_Hut_03.Id_DungeonModule_IceCave_Hut_03"
        chapel_path = "/Game/Data/Id_DungeonModule_Ruins_Chapel.Id_DungeonModule_Ruins_Chapel"

        self.assertEqual(extractor._get_module_record(numbered_path)["module_name"], "IceCave_Hut_03")
        self.assertEqual(
            extractor.get_source_string_from_asset_path(chapel_path),
            "Text_DesignData_Dungeon_DungeonModule_Abandoned_Sanctuary",
        )


if __name__ == "__main__":
    unittest.main()
