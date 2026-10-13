import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from monster_drops_builder import (  # noqa: E402
    attach_loot_pools,
    build_loot_pools,
    fold_item_page,
    is_event_currency_pool,
    is_quest_pool,
    item_has_positive_rate,
    load_drop_rows,
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
        self.assertFalse(is_quest_pool("ID_Lootdrop_Spawn_EventCurrency"))

    def test_event_currency(self):
        self.assertTrue(is_event_currency_pool("ID_Lootdrop_Spawn_EventCurrency"))
        self.assertTrue(is_event_currency_pool("ID_Lootdrop_Spawn_SpecialEventCurrency"))
        self.assertFalse(is_event_currency_pool("ID_Lootdrop_Drop_Coin"))

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
        self.assertFalse(any("EventCurrency" in (p.get("id") or "") for p in pools))
        self.assertFalse(any("EventCurrency" in (p.get("lootdrop_id") or "") for p in pools))

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

    def test_zero_rate_uses_raw_entity_name(self):
        translations = {"Text_DesignData_Item_Item_CopperOre": "铜矿"}
        item_keys = {"CopperOre": "Text_DesignData_Item_Item_CopperOre"}
        rows = [_row("Ore_CopperOre_Med", "ID_Lootdrop_Spawn_CopperOre", "CopperOres_3001", 3)]

        class FakeEngine:
            def get_group_drop_rates(self, item_name, monster_name, group_key, profile=None):
                if monster_name == "Ore_CopperOre_Med":
                    return {"PVE": 12.0}
                return {"PVE": 0}

        pools = build_loot_pools(
            monster_names={"CopperOre"},
            rows=rows,
            translations=translations,
            item_keys=item_keys,
            drop_engine=FakeEngine(),
            monster_groups={"CopperOre": {"GoblinCave"}},
            fold_quality=False,
        )
        self.assertIn("CopperOre", pools)
        self.assertEqual(pools["CopperOre"][0]["items"][0]["page"], "CopperOres")


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

    def test_item_has_positive_rate_uses_engine_shortcut(self):
        class FastEngine:
            def has_positive_group_drop_rate(self, item_name, monster_name, group_key):
                return group_key == "Crypt"

            def get_group_drop_rates(self, *args, **kwargs):
                raise AssertionError("the full rate calculation should be bypassed")

        self.assertTrue(item_has_positive_rate(FastEngine(), "CrystalBall_8001", "Banshee", {"Crypt"}))


class AttachLootPoolsTest(unittest.TestCase):
    def test_supplied_drop_rows_skip_duplicate_query(self):
        rows = [_row("Goblin", "DropGoblin", "Bone", 3)]
        entity_data = {"Goblin": {"coords": []}}
        with (
            patch("monster_drops_builder.load_drop_rows") as load_rows,
            patch("monster_drops_builder.load_item_keys", return_value={}),
            patch("monster_drops_builder.load_item_subtypes", return_value={}),
            patch("monster_drops_builder.build_loot_pools", return_value={}) as build_pools,
        ):
            self.assertEqual(
                attach_loot_pools(entity_data, object(), {}, rows=rows),
                0,
            )
        load_rows.assert_not_called()
        self.assertIs(build_pools.call_args.kwargs["rows"], rows)

    def test_drop_rows_use_engine_preload(self):
        rows = [_row("Goblin", "DropGoblin", "Bone", 3)]

        class FakeEngine:
            def get_entity_drop_rows(self):
                return rows

        self.assertIs(load_drop_rows(object(), FakeEngine()), rows)


class PropsLootPoolsTest(unittest.TestCase):
    def test_fold_quality_false_keeps_elite_page(self):
        translations = {
            "Text_DesignData_Item_Item_BrokenSkull": "破碎的头骨",
            "Text_DesignData_Item_Item_GoldCoins": "金币",
            "Text_DesignData_Item_Item_CopperOre": "铜矿",
        }
        item_keys = {
            "BrokenSkull": "Text_DesignData_Item_Item_BrokenSkull",
            "GoldCoins": "Text_DesignData_Item_Item_GoldCoins",
            "CopperOre": "Text_DesignData_Item_Item_CopperOre",
        }
        rows = [
            _row("LivingArmor", "ID_Lootdrop_Drop_LivingArmor", "BrokenSkull", 3),
            _row("LivingArmor_Elite", "ID_Lootdrop_Quest_LivingArmor", "BrokenSkull", 3),
            _row("LivingArmor_Elite", "ID_Lootdrop_Spawn_EventCurrency", "GoldCoins", 4),
            _row("Ore_CopperOre_Med", "ID_Lootdrop_Spawn_CopperOre", "CopperOre", 3),
            _row("WoodenBarrel", "ID_Lootdrop_Drop_Barrels", "GoldCoins", 2),
            _row("WoodenBarrel", "ID_Lootdrop_Spawn_EventCurrency", "GoldCoins", 4),
            _row("BossRewardDoor", "ID_Lootdrop_Spawn_EventCurrency", "GoldCoins", 4),
        ]
        names = {"LivingArmor", "WoodenBarrel", "CopperOre", "BossRewardDoor"}
        pools = build_loot_pools(
            monster_names=names,
            rows=rows,
            translations=translations,
            item_keys=item_keys,
            fold_quality=False,
        )
        self.assertIn("LivingArmor", pools)
        self.assertNotIn("LivingArmor_Elite", pools)
        living_ids = {p["id"] for p in pools["LivingArmor"]}
        self.assertIn("ID_Lootdrop_Drop_LivingArmor", living_ids)
        self.assertIn("quest", living_ids)
        self.assertFalse(any("EventCurrency" in (p.get("id") or "") for p in pools["LivingArmor"]))
        self.assertIn("CopperOre", pools)
        copper_ids = {p["id"] for p in pools["CopperOre"]}
        self.assertIn("ID_Lootdrop_Spawn_CopperOre", copper_ids)
        barrel_ids = {p["id"] for p in pools["WoodenBarrel"]}
        self.assertIn("ID_Lootdrop_Drop_Barrels", barrel_ids)
        self.assertFalse(any("EventCurrency" in (p.get("id") or "") for p in pools["WoodenBarrel"]))
        self.assertNotIn("BossRewardDoor", pools)

    def test_single_item_consumables_merge(self):
        translations = {
            "Text_DesignData_Item_Item_CaptainsCorrodedKey": "船长的锈钥匙",
            "Text_DesignData_Item_Item_EmberGem": "余烬宝石",
            "Text_DesignData_Item_Item_GoldCoins": "金币",
        }
        item_keys = {
            "CaptainsCorrodedKey": "Text_DesignData_Item_Item_CaptainsCorrodedKey",
            "EmberGem": "Text_DesignData_Item_Item_EmberGem",
            "GoldCoins": "Text_DesignData_Item_Item_GoldCoins",
        }
        subtypes = {
            "CaptainsCorrodedKey": {"Text_Code_DCDataBlueprintLibrary_Type_Item_Utility_Consumable"},
            "EmberGem": {"Text_Code_DCDataBlueprintLibrary_Type_Item_Utility_Consumable"},
        }
        rows = [
            _row("OrnateChestLarge", "ID_Lootdrop_Drop_CorrodedKey", "CaptainsCorrodedKey", 5),
            _row("OrnateChestLarge", "ID_Lootdrop_Drop_EmberGem", "EmberGem", 5),
            _row("OrnateChestLarge", "ID_Lootdrop_Drop_Gems", "GoldCoins", 4),
        ]
        pools = build_loot_pools(
            monster_names={"OrnateChestLarge"},
            rows=rows,
            translations=translations,
            item_keys=item_keys,
            fold_quality=False,
            item_subtypes=subtypes,
        )["OrnateChestLarge"]
        ids = {p["id"] for p in pools}
        self.assertIn("consumable", ids)
        self.assertNotIn("ID_Lootdrop_Drop_CorrodedKey", ids)
        self.assertNotIn("ID_Lootdrop_Drop_EmberGem", ids)
        self.assertIn("ID_Lootdrop_Drop_Gems", ids)
        pages = {i["page"] for i in next(p for p in pools if p["id"] == "consumable")["items"]}
        self.assertEqual(pages, {"CaptainsCorrodedKey", "EmberGem"})

    def test_fold_quality_true_still_merges_elite(self):
        translations = {"Text_DesignData_Item_Item_BrokenSkull": "破碎的头骨"}
        item_keys = {"BrokenSkull": "Text_DesignData_Item_Item_BrokenSkull"}
        rows = [
            _row("LivingArmor_Elite", "ID_Lootdrop_Drop_LivingArmor", "BrokenSkull", 3),
        ]
        pools = build_loot_pools(
            monster_names={"LivingArmor"},
            rows=rows,
            translations=translations,
            item_keys=item_keys,
        )
        self.assertIn("LivingArmor", pools)
        self.assertNotIn("LivingArmor_Elite", pools)


class PoolLabelTest(unittest.TestCase):
    """Lootdrop pool tabs must show a translated label, never a raw id."""

    TRANSLATIONS = {
        "Text_DesignData_Item_Item_Bloodbound_5001": "血缚",
        "Text_DesignData_Item_Item_CursedWater": "邪水",
        "Text_DesignData_Item_Item_SpectralFabric": "冥界织物",
        "Text_DesignData_Monster_Monster_CaveTroll": "洞穴巨魔",
        "Text_DesignData_Monster_Monster_Yeti": "冰雪巨猿",
        "Text_DesignData_Monster_Monster_TidewalkerShaman": "潮行者萨满",
        "Text_DesignData_Props_Props_WoodBarrel": "木桶",
        "Text_DesignData_Props_Props_Ore_IronOre": "铁矿",
        "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Armor": "护甲",
        "Text_DesignData_Item_Item_GoldCoins": "金币",
    }

    def _resolve(self, lootdrop_id):
        from monster_drops_builder import _build_entity_key_index, resolve_pool_text

        index = _build_entity_key_index(self.TRANSLATIONS)
        return resolve_pool_text(lootdrop_id, self.TRANSLATIONS, index)

    def test_item_named_pool_uses_official_key(self):
        text, key, sub = self._resolve("ID_Lootdrop_Drop_Bloodbound_5001")
        self.assertEqual(text, "血缚")
        self.assertEqual(key, "Text_DesignData_Item_Item_Bloodbound_5001")
        self.assertEqual(sub, "")

    def test_quest_item_pool_strips_quest_prefix(self):
        text, key, _ = self._resolve("ID_Lootdrop_QuestItem_SpectralFabric")
        self.assertEqual(text, "冥界织物")
        self.assertEqual(key, "Text_DesignData_Item_Item_SpectralFabric")

    def test_monster_named_pool_uses_official_key(self):
        text, key, sub = self._resolve("ID_Lootdrop_Drop_CaveTroll")
        self.assertEqual(text, "洞穴巨魔")
        self.assertEqual(key, "Text_DesignData_Monster_Monster_CaveTroll")
        self.assertEqual(sub, "")

    def test_spoils_pool_keeps_entity_name_and_marks_suffix(self):
        text, key, sub = self._resolve("ID_Lootdrop_Drop_CaveTroll_Spoils")
        self.assertEqual(text, "洞穴巨魔")
        self.assertEqual(key, "Text_DesignData_Monster_Monster_CaveTroll")
        self.assertEqual(sub, "df5.lootpool.Spoils")

    def test_case_variant_entity_name_resolves(self):
        text, key, _ = self._resolve("ID_Lootdrop_Drop_TideWalkerShaman")
        self.assertEqual(text, "潮行者萨满")
        self.assertEqual(key, "Text_DesignData_Monster_Monster_TidewalkerShaman")

    def test_misspelled_entity_name_uses_alias(self):
        text, _, _ = self._resolve("ID_Lootdrop_Drop_PirateSwiftBlade")
        self.assertNotEqual(text, "PirateSwiftBlade")

    def test_category_pool_uses_category_key(self):
        text, key, _ = self._resolve("ID_Lootdrop_Drop_ChestArmors")
        self.assertEqual(text, "护甲")
        self.assertEqual(key, "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Armor")

    def test_prop_pool_uses_prop_key(self):
        text, key, _ = self._resolve("ID_Lootdrop_Drop_Barrels")
        self.assertEqual(text, "木桶")
        self.assertEqual(key, "Text_DesignData_Props_Props_WoodBarrel")

    def test_ore_pool_uses_ore_key(self):
        text, key, _ = self._resolve("ID_Lootdrop_Spawn_IronOre")
        self.assertEqual(text, "铁矿")
        self.assertEqual(key, "Text_DesignData_Props_Props_Ore_IronOre")

    def test_label_only_pool_uses_synthetic_key(self):
        text, key, _ = self._resolve("ID_Lootdrop_Drop_Cloak_Physical")
        self.assertEqual(text, "物理披风")
        self.assertEqual(key, "df5.lootpool.Cloak_Physical")

    def test_hardcoded_name_pool(self):
        text, _, _ = self._resolve("ID_Lootdrop_Drop_Lumber")
        self.assertEqual(text, "木材")

    def test_unknown_pool_falls_back_to_readable_english(self):
        text, key, _ = self._resolve("ID_Lootdrop_Drop_Barrel_Junk")
        self.assertEqual(text, "Barrel Junk")
        self.assertEqual(key, "")

    def test_sub_pool_borrows_owner_name_and_marks_suffix(self):
        """Yeti_Gear resolves to Yeti but must stay distinct from Drop_Yeti."""
        text, key, sub = self._resolve("ID_Lootdrop_Drop_Yeti_Gear")
        self.assertEqual(text, "冰雪巨猿")
        self.assertEqual(sub, "df5.lootpool.Gear")
        own_text, _, own_sub = self._resolve("ID_Lootdrop_Drop_Yeti")
        self.assertEqual(own_text, text)
        self.assertEqual(own_sub, "")

    def test_monster_prefixed_pool_strips_prefix(self):
        text, key, _ = self._resolve("Id_Lootdrop_Monster_CaveTroll_Misc")
        self.assertEqual(text, "洞穴巨魔")
        self.assertEqual(key, "Text_DesignData_Monster_Monster_CaveTroll")


if __name__ == "__main__":
    unittest.main()
