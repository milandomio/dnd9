import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db.importers.effects import ItemEffectsImporter  # noqa: E402
from db.importers.merchants import parse_asset_name, parse_merchant_name  # noqa: E402
from db.repositories.merchants import InGameMerchantRepository  # noqa: E402
from db.schema import SchemaManager  # noqa: E402
from merchant_builder import (  # noqa: E402
    REGION_LABEL_KEY,
    build_shop_data,
    save_shop_data,
)


class ParseAssetNameTest(unittest.TestCase):
    def test_merchant_asset(self):
        self.assertEqual(
            parse_asset_name("Id_InGameMerchant_GoblinSmuggler_Crypts_N"),
            ("GoblinSmuggler_Crypts_N", "Crypts", "N", None),
        )

    def test_schedule_asset_shares_variant_id(self):
        self.assertEqual(
            parse_asset_name("Id_InGameMerchantSchedule_GoblinSmuggler_IceCavern_HR"),
            ("GoblinSmuggler_IceCavern_HR", "IceCavern", "HR", None),
        )

    def test_stock_buy_asset_carries_slot(self):
        self.assertEqual(
            parse_asset_name("Id_InGameMerchantStockBuy_GoblinSmuggler_Goblin_N_01"),
            ("GoblinSmuggler_Goblin_N", "Goblin", "N", 1),
        )
        self.assertEqual(
            parse_asset_name("Id_InGameMerchantStockBuy_GoblinSmuggler_IceCavern_HR_12"),
            ("GoblinSmuggler_IceCavern_HR", "IceCavern", "HR", 12),
        )

    def test_unknown_asset_returns_empty(self):
        self.assertEqual(parse_asset_name("SomethingElse"), ("", "", "", None))

    def test_merchant_name_is_shared_across_regions(self):
        self.assertEqual(parse_merchant_name("Id_InGameMerchant_GoblinSmuggler_Crypts_N"), "GoblinSmuggler")
        self.assertEqual(parse_merchant_name("Id_InGameMerchantStockBuy_GoblinSmuggler_Goblin_HR_03"), "GoblinSmuggler")


def _merchant_data():
    variants = []
    stock = []
    for region in ("Crypts", "Goblin", "IceCavern"):
        for difficulty in ("N", "HR"):
            vid = f"GoblinSmuggler_{region}_{difficulty}"
            variants.append(
                {
                    "variant_id": vid,
                    "merchant_name": "GoblinSmuggler",
                    "region": region,
                    "difficulty": difficulty,
                }
            )
            # Slot 1 is shared by every region; slots 8/9 are identical pools
            # rolled twice, mirroring the real assets; Crypts additionally sells
            # a region-exclusive material.
            # Slot 1 holds two quality tiers so chances split 80/20.
            stock.append(_row(vid, 1, "HealingPotion_4001", 100, 3, 800))
            stock.append(_row(vid, 1, "HealingPotion_5001", 250, 3, 200))
            for slot in (8, 9):
                stock.append(_row(vid, slot, "Bone", 30, 1, 1000))
                stock.append(_row(vid, slot, "WolfPelt", 40, 1, 1000))
                if region == "Crypts":
                    stock.append(_row(vid, slot, "BatClaw", 10, 1, 1000))
    return {
        "merchants": [
            {
                "merchant_name": "GoblinSmuggler",
                "translation_key": "Text_DesignData_InGameMerchant_InGameMerchant_GoblinSmuggler",
                "greeting_key": "Text_DesignData_InGameMerchant_InGameMerchant_GoblinSmugglerGreetings",
                "npc_id": "Id_NPC_GoblinSmuggler_Crypts_N",
            }
        ],
        "variants": variants,
        "stock": stock,
    }


def _row(variant_id, slot, item, price, count, rate):
    return {
        "variant_id": variant_id,
        "slot_index": slot,
        "item_name": item,
        "item_count": count,
        "item_rate": rate,
        "stock": 1,
        "price": price,
        "currency": "GoldCoins",
    }


ITEM_INDEX = {
    "HealingPotion": {
        "page": "HealingPotion",
        "translation": "治疗药水",
        "translation_key": "Text_DesignData_Item_Item_HealingPotion_4001",
    },
    "Bone": {"page": "Bone", "translation": "骨头棒", "translation_key": "Text_DesignData_Item_Item_Bone"},
    "WolfPelt": {"page": "WolfPelt", "translation": "狼皮", "translation_key": ""},
    "BatClaw": {"page": "BatClaw", "translation": "蝙蝠爪子", "translation_key": ""},
    "CrystalBall_8001": {
        "page": "CrystalBall_8001",
        "translation": "茨戈奇之眼",
        "translation_key": "Text_DesignData_Item_Item_CrystalBall_8001",
    },
}


class BuildShopDataTest(unittest.TestCase):
    def _build(self):
        return build_shop_data(
            _merchant_data(),
            {},
            ITEM_INDEX,
            {r: r for r in REGION_LABEL_KEY},
        )

    def test_regions_are_ordered_crypts_goblin_icecavern(self):
        data = self._build()
        self.assertEqual([r["region"] for r in data["index"]["regions"]], ["Crypts", "Goblin", "IceCavern"])

    def test_each_region_has_both_difficulties(self):
        data = self._build()
        for detail in data["details"].values():
            self.assertEqual([d["difficulty"] for d in detail["difficulties"]], ["N", "HR"])

    def test_duplicate_material_slots_merge_into_one(self):
        """Slots 8 and 9 are byte-identical pools; they must render once."""
        data = self._build()
        detail = data["details"]["Goblin"]
        slots = detail["difficulties"][0]["slots"]
        self.assertEqual([s["slot"] for s in slots], [1, 8])
        material = slots[1]
        self.assertEqual({i["name"] for i in material["items"]}, {"Bone", "WolfPelt"})

    def test_items_sorted_by_descending_price(self):
        data = self._build()
        detail = data["details"]["Goblin"]
        material = detail["difficulties"][0]["slots"][1]
        prices = [i["price"] for i in material["items"]]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_region_exclusive_item_flagged(self):
        data = self._build()
        crypts_material = data["details"]["Crypts"]["difficulties"][0]["slots"][1]
        flags = {i["name"]: i["map_exclusive"] for i in crypts_material["items"]}
        self.assertTrue(flags["BatClaw"])
        self.assertFalse(flags["Bone"])
        self.assertFalse(flags["WolfPelt"])

    def test_exclusive_count_matches_region(self):
        data = self._build()
        by_region = {r["region"]: r["exclusive_count"] for r in data["index"]["regions"]}
        self.assertEqual(by_region, {"Crypts": 1, "Goblin": 0, "IceCavern": 0})

    def test_region_counts_match_the_rendered_detail_cards(self):
        """The list page and detail header must never disagree."""
        data = self._build()
        for summary in data["index"]["regions"]:
            detail = data["details"][summary["region"]]
            widest = max(sum(len(slot["items"]) for slot in diff["slots"]) for diff in detail["difficulties"])
            self.assertEqual(summary["item_count"], widest)
            self.assertEqual(detail["total_items"], widest)

    def test_region_count_uses_max_across_difficulties(self):
        """HR carries extra tiers, so the region count must follow the wider one."""
        merchant = _merchant_data()
        # Give Crypts-HR two extra items the other variants lack.
        for item in ("Ruby_6001", "Diamond_6001"):
            merchant["stock"].append(_row("GoblinSmuggler_Crypts_HR", 1, item, 200, 1, 100))
        item_index = dict(ITEM_INDEX)
        item_index["Ruby_6001"] = {"page": "Ruby", "translation": "红宝石", "translation_key": ""}
        item_index["Diamond_6001"] = {"page": "Diamond", "translation": "钻石", "translation_key": ""}
        data = build_shop_data(merchant, {}, item_index, {r: r for r in REGION_LABEL_KEY})
        by_region = {r["region"]: r for r in data["index"]["regions"]}
        crypts = data["details"]["Crypts"]
        hr = next(d for d in crypts["difficulties"] if d["difficulty"] == "HR")
        n_diff = next(d for d in crypts["difficulties"] if d["difficulty"] == "N")
        hr_cards = sum(len(s["items"]) for s in hr["slots"])
        n_cards = sum(len(s["items"]) for s in n_diff["slots"])
        self.assertGreater(hr_cards, n_cards)
        self.assertEqual(by_region["Crypts"]["item_count"], hr_cards)
        self.assertEqual(crypts["total_items"], hr_cards)

    def test_items_carry_link_and_price_metadata(self):
        data = self._build()
        slot = data["details"]["Crypts"]["difficulties"][0]["slots"][0]
        item = next(i for i in slot["items"] if i["name"] == "HealingPotion_4001")
        self.assertEqual(item["page"], "HealingPotion")
        self.assertEqual(item["translation"], "治疗药水")
        self.assertEqual(item["price"], 100)
        self.assertEqual(item["currency"], "GoldCoins")
        self.assertEqual(item["count"], 3)

    def test_quality_suffix_folds_to_base_detail_page(self):
        """HealingPotion_4001 links to the HealingPotion detail page."""
        data = self._build()
        item = data["details"]["Crypts"]["difficulties"][0]["slots"][0]["items"][0]
        self.assertEqual(item["page"], "HealingPotion")
        self.assertNotIn("_4001", item["page"])

    def test_artifact_suffix_is_not_folded(self):
        """Artifacts (_8001) keep their suffix as the detail page."""
        merchant = _merchant_data()
        for row in merchant["stock"]:
            if row["slot_index"] == 1:
                row["item_name"] = "CrystalBall_8001"
        payload = build_shop_data(merchant, {}, ITEM_INDEX, {r: r for r in REGION_LABEL_KEY})
        item = payload["details"]["Crypts"]["difficulties"][0]["slots"][0]["items"][0]
        self.assertEqual(item["name"], "CrystalBall_8001")
        self.assertEqual(item["page"], "CrystalBall_8001")
        self.assertEqual(item["translation"], "茨戈奇之眼")

    def test_quality_tier_difference_is_not_a_region_exclusive(self):
        """Ruby_4001 in one region and Ruby_7001 in another is the same item."""
        merchant = _merchant_data()
        for row in merchant["stock"]:
            if row["slot_index"] == 8 and row["item_name"] == "WolfPelt":
                row["item_name"] = (
                    "WolfPelt_4001" if row["variant_id"].startswith("GoblinSmuggler_Crypts") else "WolfPelt_7001"
                )
        payload = build_shop_data(merchant, {}, ITEM_INDEX, {r: r for r in REGION_LABEL_KEY})
        # WolfPelt appears in every region, so it must not be flagged exclusive
        # even though the quality tier differs.
        seen = False
        for region in ("Crypts", "Goblin"):
            for slot in payload["details"][region]["difficulties"][0]["slots"]:
                for item in slot["items"]:
                    if item["name"].startswith("WolfPelt"):
                        seen = True
                        self.assertFalse(item["map_exclusive"])
        self.assertTrue(seen)

    def test_merchant_greeting_is_exported(self):
        data = self._build()
        merchant = data["details"]["Crypts"]["merchant"]
        self.assertEqual(merchant["translation_key"], "Text_DesignData_InGameMerchant_InGameMerchant_GoblinSmuggler")
        self.assertTrue(merchant["greeting_key"])

    def test_merchant_carries_resolved_display_and_greeting(self):
        """zh-Hans does not load the locale dict, so the JSON must embed them."""
        translations = {
            "Text_DesignData_InGameMerchant_InGameMerchant_GoblinSmuggler": "哥布林走私者",
            "Text_DesignData_InGameMerchant_InGameMerchant_GoblinSmugglerGreetings": "嘘！小声点儿！",
        }
        data = build_shop_data(_merchant_data(), translations, ITEM_INDEX, {r: r for r in REGION_LABEL_KEY})
        merchant = data["details"]["Goblin"]["merchant"]
        self.assertEqual(merchant["display"], "哥布林走私者")
        self.assertEqual(merchant["greeting"], "嘘！小声点儿！")
        # The index payload carries the same resolved merchant entry.
        self.assertEqual(data["index"]["merchants"][0]["display"], "哥布林走私者")

    def test_merchant_display_falls_back_to_asset_name(self):
        data = self._build()
        merchant = data["details"]["Crypts"]["merchant"]
        self.assertEqual(merchant["display"], "GoblinSmuggler")
        self.assertEqual(merchant["greeting"], "")

    def test_shop_only_item_falls_back_to_game_json_key(self):
        """LuckPotion is sold but never drops, so it is absent from the loot index."""
        merchant = _merchant_data()
        for row in merchant["stock"]:
            if row["slot_index"] == 1:
                row["item_name"] = "LuckPotion_5001"
        translations = {"Text_DesignData_Item_Item_LuckPotion": "幸运药水"}
        payload = build_shop_data(merchant, translations, ITEM_INDEX, {r: r for r in REGION_LABEL_KEY})
        item = payload["details"]["Crypts"]["difficulties"][0]["slots"][0]["items"][0]
        self.assertEqual(item["name"], "LuckPotion_5001")
        self.assertEqual(item["page"], "LuckPotion")
        self.assertEqual(item["translation"], "幸运药水")
        self.assertEqual(item["translation_key"], "Text_DesignData_Item_Item_LuckPotion")

    def test_save_writes_index_and_per_region_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            save_shop_data(self._build(), out)
            index = json.loads((out / "dungeon_shops.json").read_text(encoding="utf-8"))
            self.assertEqual(len(index["regions"]), 3)
            for region in ("Crypts", "Goblin", "IceCavern"):
                detail = json.loads((out / "dungeon_shops" / f"{region}.json").read_text(encoding="utf-8"))
                self.assertEqual(detail["region"], region)
                self.assertEqual(len(detail["difficulties"]), 2)


class ShopItemEffectTest(unittest.TestCase):
    """Consumable effects travel to the JSON through the DB, never the assets."""

    def _plain(self):
        return build_shop_data(
            _merchant_data(),
            {},
            ITEM_INDEX,
            {r: r for r in REGION_LABEL_KEY},
        )

    def _build_with_effects(self):
        merchant = _merchant_data()
        for row in merchant["stock"]:
            if row["slot_index"] == 1:
                row["item_name"] = "LuckPotion_5001"
        merchant["effects"] = {
            "LuckPotion_5001": {
                "values": {"Luck": [100, 200]},
                "rolls": [
                    {"effect": "Luck10", "rate": 2000, "chance": 0.2, "Luck": 100},
                    {"effect": "Luck15", "rate": 4000, "chance": 0.4, "Luck": 150},
                    {"effect": "Luck20", "rate": 4000, "chance": 0.4, "Luck": 200},
                ],
            }
        }
        item_index = dict(ITEM_INDEX)
        item_index["LuckPotion"] = {
            "page": "LuckPotion",
            "translation": "幸运药水",
            "translation_key": "Text_DesignData_Item_Item_GreatLuckPotion",
        }
        return build_shop_data(
            merchant,
            {"Text_DesignData_Item_Item_GreatLuckPotion": "大型幸运药水"},
            item_index,
            {r: r for r in REGION_LABEL_KEY},
        )

    def test_effect_range_is_attached(self):
        payload = self._build_with_effects()
        item = payload["details"]["Crypts"]["difficulties"][0]["slots"][0]["items"][0]
        self.assertEqual(item["name"], "LuckPotion_5001")
        self.assertEqual(item["effect"]["values"]["Luck"], [100, 200])

    def test_rolls_carry_value_and_chance(self):
        payload = self._build_with_effects()
        item = payload["details"]["Crypts"]["difficulties"][0]["slots"][0]["items"][0]
        rolls = {r["effect"]: (r["Luck"], r["chance"]) for r in item["effect"]["rolls"]}
        self.assertEqual(rolls["Luck10"], (100, 0.2))
        self.assertEqual(rolls["Luck15"], (150, 0.4))
        self.assertEqual(rolls["Luck20"], (200, 0.4))

    def test_items_without_effects_carry_none(self):
        data = self._plain()
        detail = data["details"]["Crypts"]["difficulties"][0]
        for slot in detail["slots"]:
            for item in slot["items"]:
                self.assertIsNone(item["effect"])

    def test_effects_are_absent_when_not_requested(self):
        """A merchant payload without an effects map keeps the field empty."""
        data = self._plain()
        item = data["details"]["Crypts"]["difficulties"][0]["slots"][0]["items"][0]
        self.assertIsNone(item["effect"])


class ItemEffectsImporterTest(unittest.TestCase):
    """The import phase persists effects so a DB-only export can still show them."""

    def _temp_db(self):
        tmp = tempfile.TemporaryDirectory()
        conn = sqlite3.connect(str(Path(tmp.name) / "effects.db"))
        conn.row_factory = sqlite3.Row
        SchemaManager(conn).create_tables()
        conn.executemany(
            "INSERT INTO ingame_merchant_stock (variant_id, slot_index, item_name) VALUES (?, ?, ?)",
            [("v", 1, "LuckPotion_5001"), ("v", 2, "HealingPotion_5001")],
        )
        conn.commit()
        return tmp, conn

    def test_import_then_repository_round_trip(self):
        import db.importers.effects as effects_module

        tmp, conn = self._temp_db()
        original_index = effects_module.build_effect_index
        original_dir = effects_module.ITEM_ABILITY_DIR
        effects_module.build_effect_index = lambda: {"GA_LuckPotion_5001_Consume": {"values": {"Luck": [100, 200]}}}
        effects_module.ITEM_ABILITY_DIR = Path("/nonexistent")
        try:
            # resolve_item_effects needs a real ability asset; patch it too so the
            # test target stays the DB round trip rather than asset parsing.
            original_resolve = effects_module.resolve_item_effects
            effects_module.resolve_item_effects = lambda items, index, directory: {
                "LuckPotion_5001": {"values": {"Luck": [100, 200]}}
            }
            try:
                stored = ItemEffectsImporter(conn).import_all()
            finally:
                effects_module.resolve_item_effects = original_resolve
        finally:
            effects_module.build_effect_index = original_index
            effects_module.ITEM_ABILITY_DIR = original_dir

        self.assertEqual(stored, 1)
        effects = InGameMerchantRepository(conn).get_item_effects()
        self.assertEqual(effects["LuckPotion_5001"]["values"]["Luck"], [100, 200])
        conn.close()
        tmp.cleanup()

    def test_repository_returns_empty_without_the_table(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        self.assertEqual(InGameMerchantRepository(conn).get_item_effects(), {})
        conn.close()


class ShopChanceTest(unittest.TestCase):
    """Per-slot drop chance and item rarity."""

    def _slot(self, region, slot_index, difficulty=0):
        data = build_shop_data(
            _merchant_data(),
            {},
            ITEM_INDEX,
            {r: r for r in REGION_LABEL_KEY},
        )
        detail = data["details"][region]["difficulties"][difficulty]
        return next(s for s in detail["slots"] if s["slot"] == slot_index)

    def test_chance_splits_by_weight_within_a_slot(self):
        slot = self._slot("Crypts", 1)
        chances = {i["name"]: i["chance"] for i in slot["items"]}
        self.assertAlmostEqual(chances["HealingPotion_4001"], 0.8, places=6)
        self.assertAlmostEqual(chances["HealingPotion_5001"], 0.2, places=6)

    def test_single_roll_slot_chances_sum_to_one(self):
        slot = self._slot("Crypts", 1)
        self.assertAlmostEqual(slot["chance_total"], 1.0, places=6)

    def test_duplicated_pool_folds_two_rolls(self):
        """Slots 8 and 9 each roll once, so odds combine as 1-(1-p)^2."""
        slot = self._slot("Crypts", 8)
        # Cranium pool: three items at 1000 out of 3000 per roll.
        bone = next(i for i in slot["items"] if i["name"] == "Bone")
        self.assertAlmostEqual(bone["chance"], 1 - (1 - 1000 / 3000) ** 2, places=6)
        # Two rolls mean the per-slot total is ~2, not 1.
        self.assertGreater(slot["chance_total"], 1.5)

    def test_slot_total_is_exported(self):
        slot = self._slot("Crypts", 1)
        item = next(i for i in slot["items"] if i["name"] == "HealingPotion_4001")
        self.assertEqual(item["slot_total"], 1000)
        self.assertEqual(item["rate"], 800)

    def test_rarity_comes_from_quality_suffix(self):
        slot = self._slot("Crypts", 1)
        by_name = {i["name"]: i["rarity"] for i in slot["items"]}
        self.assertEqual(by_name["HealingPotion_4001"], "Rare")
        self.assertEqual(by_name["HealingPotion_5001"], "Epic")

    def test_suffixless_item_has_no_rarity(self):
        slot = self._slot("Crypts", 8)
        bone = next(i for i in slot["items"] if i["name"] == "Bone")
        self.assertEqual(bone["rarity"], "")


if __name__ == "__main__":
    unittest.main()
