import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monster_drops_builder import (  # noqa: E402
    build_loot_pools,
    fold_item_page,
    is_quest_pool,
    item_has_positive_rate,
    lootdrop_stem,
    monster_map_groups,
)


class FoldItemPageTest(unittest.TestCase):
    def test_plain_name(self):
        self.assertEqual(fold_item_page("GoldCoinPouch"), ("GoldCoinPouch", None))

    def test_non_artifact_suffix(self):
        self.assertEqual(fold_item_page("CopperPowder_3001"), ("CopperPowder", "3001"))

    def test_artifact_kept(self):
        self.assertEqual(fold_item_page("CrystalBall_8001"), ("CrystalBall_8001", "8001"))


class QuestPoolTest(unittest.TestCase):
    def test_quest_and_special(self):
        self.assertTrue(is_quest_pool("ID_Lootdrop_Quest_Goblins"))
        self.assertTrue(is_quest_pool("ID_Lootdrop_QuestSpecial_Cockatrices"))
        self.assertFalse(is_quest_pool("Id_Lootdrop_LootGoblin_StolenGoods"))

    def test_stem(self):
        self.assertEqual(lootdrop_stem("Id_Lootdrop_LootGoblin_StolenGoods"), "LootGoblin_StolenGoods")
        self.assertEqual(lootdrop_stem("ID_Lootdrop_Drop_Coin"), "Drop_Coin")


def _row(entity, lootdrop_id, item, luck):
    return (entity, lootdrop_id, item, luck)


class BuildLootPoolsTest(unittest.TestCase):
    def test_lootgoblin_pools(self):
        translations = {
            "Text_DesignData_Item_Item_GoblinEars": "哥布林耳朵",
            "Text_DesignData_Item_Item_GoldCoinPouch": "小型金币袋",
            "Text_DesignData_Item_Item_GoldCoinBag": "金币袋",
            "Text_DesignData_Item_Item_GoldCoinChest": "金币箱",
            "Text_DesignData_Item_Item_CopperPowder_3001": "铜粉",
            "Text_DesignData_Item_Item_WolfPelt": "狼皮",
        }
        item_keys = {
            "GoblinEars": "Text_DesignData_Item_Item_GoblinEars",
            "GoldCoinPouch": "Text_DesignData_Item_Item_GoldCoinPouch",
            "GoldCoinBag": "Text_DesignData_Item_Item_GoldCoinBag",
            "GoldCoinChest": "Text_DesignData_Item_Item_GoldCoinChest",
            "CopperPowder": "Text_DesignData_Item_Item_CopperPowder_3001",
            "WolfPelt": "Text_DesignData_Item_Item_WolfPelt",
        }
        stolen = [
            "GoldenTeeth",
            "WolfPelt",
            "CopperPowder_3001",
            "MermaidsTear",
            "MermaidScale",
            "PocketWatch",
            "ExtraThickPelts",
            "CobaltPowder_4001",
            "SpiderSilk",
            "BonePowder",
            "GoldPowder_5001",
            "ShiningPearl",
            "CockatricesLuckyFeather",
            "SpectralFabric",
        ]
        rows = [
            _row("LootGoblin_Unique", "ID_Lootdrop_Quest_Goblins", "GoblinEars", 3),
            _row("LootGoblin_Unique", "Id_Lootdrop_LootGoblin_GoldContainer", "GoldCoinPouch", 4),
            _row("LootGoblin_Unique", "Id_Lootdrop_LootGoblin_GoldContainer", "GoldCoinBag", 5),
            _row("LootGoblin_Unique", "Id_Lootdrop_LootGoblin_GoldContainer", "GoldCoinChest", 6),
            _row("LootGoblin_Unique", "ID_Lootdrop_Drop_Coin", "GoldCoins", 4),
            _row("LootGoblin_Unique", "ID_Lootdrop_Drop_Gems", "Ruby_5001", 5),
            _row("LootGoblin_Unique", "ID_Lootdrop_Drop_HoardTreasure", "HuntingTrap", 4),
        ]
        for i, name in enumerate(stolen):
            rows.append(_row("LootGoblin_Unique", "Id_Lootdrop_LootGoblin_StolenGoods", name, 3 + (i % 4)))

        pools = build_loot_pools(
            monster_names={"LootGoblin"},
            rows=rows,
            translations=translations,
            item_keys=item_keys,
        )["LootGoblin"]
        kinds = [p["kind"] for p in pools]
        self.assertEqual(kinds[0], "quest")
        self.assertNotIn("artifact", kinds)
        quest_pages = [i["page"] for i in pools[0]["items"]]
        self.assertEqual(quest_pages, ["GoblinEars"])
        by_id = {p["id"]: p for p in pools}
        self.assertIn("Id_Lootdrop_LootGoblin_StolenGoods", by_id)
        self.assertEqual(len(by_id["Id_Lootdrop_LootGoblin_StolenGoods"]["items"]), 14)
        gold_pages = {i["page"] for i in by_id["Id_Lootdrop_LootGoblin_GoldContainer"]["items"]}
        self.assertEqual(gold_pages, {"GoldCoinPouch", "GoldCoinBag", "GoldCoinChest"})
        stolen_pages = {i["page"] for i in by_id["Id_Lootdrop_LootGoblin_StolenGoods"]["items"]}
        self.assertIn("CopperPowder", stolen_pages)
        self.assertNotIn("CopperPowder_3001", stolen_pages)

    def test_skeleton_mage_artifact_split(self):
        translations = {
            "Text_DesignData_Item_Item_Bone": "骨头",
            "Text_DesignData_Item_Item_CrystalBall_8001": "茨戈奇之眼",
            "Text_DesignData_Item_Item_CrystalSword_8001": "水晶剑",
            "Text_DesignData_Item_Item_Quarterstaff_8001": "短杖",
            "Text_DesignData_Item_Item_Spellbook_8001": "法术书",
            "Text_DesignData_Item_Item_WizardStaff_8001": "巫师法杖",
            "Text_DesignData_Item_Item_ArmingSword_1001": "武装剑",
        }
        item_keys = {
            "Bone": "Text_DesignData_Item_Item_Bone",
            "ArmingSword": "Text_DesignData_Item_Item_ArmingSword_1001",
        }
        artifacts = [
            "CrystalBall_8001",
            "CrystalSword_8001",
            "Quarterstaff_8001",
            "Spellbook_8001",
            "WizardStaff_8001",
        ]
        rows = [
            _row("SkeletonMage_Common", "ID_Lootdrop_Quest_SkeletonMage", "Bone", 3),
            _row("SkeletonMage_Elite", "ID_Lootdrop_Quest_Skeletons", "BrokenSkull", 3),
            _row("SkeletonMage_Nightmare", "ID_Lootdrop_Drop_SkeletonMage", "ArmingSword_1001", 1),
            _row("SkeletonMage_Common", "ID_Lootdrop_Spawn_EventCurrency", "GoldCoins", 4),
        ]
        for name in artifacts:
            rows.append(_row("SkeletonMage_Common", "ID_Lootdrop_Drop_SkeletonMage", name, 8))

        pools = build_loot_pools(
            monster_names={"SkeletonMage"},
            rows=rows,
            translations=translations,
            item_keys=item_keys,
        )["SkeletonMage"]
        by_kind = {p["kind"]: p for p in pools}
        self.assertEqual(pools[0]["kind"], "quest")
        quest_pages = {i["page"] for i in by_kind["quest"]["items"]}
        self.assertTrue({"Bone", "BrokenSkull"} <= quest_pages)
        artifact_pages = [i["page"] for i in by_kind["artifact"]["items"]]
        self.assertEqual(set(artifact_pages), set(artifacts))
        self.assertEqual(artifact_pages[0].endswith("_8001"), True)
        drop_pool = next(p for p in pools if p["id"] == "ID_Lootdrop_Drop_SkeletonMage")
        drop_pages = {i["page"] for i in drop_pool["items"]}
        self.assertIn("ArmingSword", drop_pages)
        for name in artifacts:
            self.assertNotIn(name, drop_pages)

    def test_zero_rate_artifacts_filtered_before_fold(self):
        translations = {
            "Text_DesignData_Item_Item_CrystalBall_8001": "茨戈奇之眼",
            "Text_DesignData_Item_Item_CrystalBall_5001": "水晶球",
            "Text_DesignData_Item_Item_BansheeSonnet": "狺女的十四行诗",
        }
        item_keys = {
            "CrystalBall": "Text_DesignData_Item_Item_CrystalBall_5001",
            "BansheeSonnet": "Text_DesignData_Item_Item_BansheeSonnet",
        }
        rows = [
            _row("Banshee_Common", "ID_Lootdrop_Quest_Banshee", "BansheeSonnet", 5),
            _row("Banshee_Elite", "ID_Lootdrop_Drop_Banshee", "CrystalBall_5001", 5),
            _row("Banshee_Elite", "ID_Lootdrop_Drop_Banshee", "CrystalBall_8001", 8),
        ]

        class FakeEngine:
            def get_group_drop_rates(self, item_name, monster_name, group_key, profile=None):
                if item_name.endswith("_8001"):
                    return {"PVE": 0, "普通": 0, "豪客赛": 0, "逆袭赛": 0}
                return {"PVE": 1.0, "普通": 2.0, "豪客赛": 3.0, "逆袭赛": 0}

        pools = build_loot_pools(
            monster_names={"Banshee"},
            rows=rows,
            translations=translations,
            item_keys=item_keys,
            drop_engine=FakeEngine(),
            monster_groups={"Banshee": {"Ruins"}},
        )["Banshee"]
        kinds = [p["kind"] for p in pools]
        self.assertNotIn("artifact", kinds)
        by_kind = {p["kind"]: p for p in pools}
        self.assertEqual([i["page"] for i in by_kind["quest"]["items"]], ["BansheeSonnet"])
        drop_pool = next(p for p in pools if p["id"] == "ID_Lootdrop_Drop_Banshee")
        self.assertEqual({i["page"] for i in drop_pool["items"]}, {"CrystalBall"})


class RateFilterHelpersTest(unittest.TestCase):
    def test_monster_map_groups(self):
        entity = {"coords": [{"map": "Ruins_GreatHall_01_Destroyed"}, {"map": "Crypt_Chapel"}]}
        groups = monster_map_groups(
            entity,
            {"Ruins_GreatHall_01_Destroyed": "Ruins", "Crypt_Chapel": "Crypt"},
        )
        self.assertEqual(groups, {"Ruins", "Crypt"})

    def test_item_has_positive_rate(self):
        class FakeEngine:
            def get_group_drop_rates(self, item_name, monster_name, group_key, profile=None):
                if group_key == "Ruins":
                    return {"豪客赛": 0, "PVE": 0}
                return {"豪客赛": 0.12}

        self.assertFalse(item_has_positive_rate(FakeEngine(), "CrystalBall_8001", "Banshee", {"Ruins"}))
        self.assertTrue(item_has_positive_rate(FakeEngine(), "CrystalBall_8001", "Banshee", {"Ruins", "Crypt"}))
        self.assertTrue(item_has_positive_rate(FakeEngine(), "CrystalBall_8001", "Banshee", set()))


if __name__ == "__main__":
    unittest.main()
