import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import (  # noqa: E402
    EXPLICIT_TRANSLATION_KEY_OVERRIDES,
    HARDCODED_LOCALE_OVERRIDES,
    hardcoded_locale_entries,
)
from locale_builder import SUPPORTED_LANGUAGES  # noqa: E402
from translator import resolve_translation_key  # noqa: E402


class HardcodedI18nTest(unittest.TestCase):
    def test_user_facing_hardcoded_monsters_have_distinct_locale_values(self):
        keys = {
            resolve_translation_key(name)
            for name in (
                "ExpressmanOtto",
                "GoblinMelee",
                "GoblinRanged",
                "SkeletonMelee",
                "SkeletonRanged",
            )
        }
        values = {lang: hardcoded_locale_entries(lang, keys) for lang in SUPPORTED_LANGUAGES}

        for lang, entries in values.items():
            self.assertEqual(set(entries), keys, lang)
        self.assertNotEqual(
            values["ja"]["df5.hardcoded.GoblinMelee"],
            values["en"]["df5.hardcoded.GoblinMelee"],
        )

    def test_verified_aliases_keep_official_game_keys(self):
        self.assertEqual(
            resolve_translation_key("LittleToad_Poison"),
            "Text_DesignData_Monster_Monster_LittleToad",
        )
        self.assertEqual(
            resolve_translation_key("Ruins_Chapel"),
            "Text_DesignData_Dungeon_DungeonModule_Abandoned_Sanctuary",
        )

    def test_lootdrop_weapon_sources_have_explicit_locale_values(self):
        source_names = (
            "Weapon_DualBoss",
            "Weapon_MysticalTreasureRoom",
            "Weapon",
            "Weapon_GoldenRoom",
            "DwarfSecretWeapon",
            "Weapon_FrozenRoom",
            "Weapon_SkullRoom",
            "Weapon_Rare",
        )

        for name in source_names:
            self.assertEqual(set(HARDCODED_LOCALE_OVERRIDES[name]), set(SUPPORTED_LANGUAGES), name)

        keys = {resolve_translation_key(name) for name in source_names}
        values = {lang: hardcoded_locale_entries(lang, keys) for lang in SUPPORTED_LANGUAGES}
        self.assertEqual(values["ja"]["df5.hardcoded.Weapon_GoldenRoom"], "黄金部屋の武器")
        self.assertEqual(values["zh-Hant"]["df5.hardcoded.Weapon_GoldenRoom"], "黃金房-武器")
        self.assertEqual(values["ja"]["df5.hardcoded.Weapon_MysticalTreasureRoom"], "神秘の宝物庫の武器")

    def test_map_source_aliases_use_official_translation_keys(self):
        expected = {
            "Armor": "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Armor",
            "BlueMarlin": "Text_DesignData_Monster_Monster_Bluemarlin",
            "Coin": "Text_DesignData_Item_Item_GoldCoins",
            "DwarfHandCannoneer": "Text_DesignData_Monster_Monster_DwarfHandcannoneer",
            "Gems": "Text_Code_DCDataBlueprintLibrary_Type_Item_Misc_Gem",
            "PirateCrossbow": "Text_DesignData_Monster_Monster_PirateCrossbowman",
            "PirateSwiftBlade": "Text_DesignData_Monster_Monster_PirateSwiftblade",
            "StingrayEgg": "Text_DesignData_Item_Item_AncientStingrayEgg",
            "TideWalkerClubFighter": "Text_DesignData_Monster_Monster_TidewalkerClubfighter",
            "TideWalkerShaman": "Text_DesignData_Monster_Monster_TidewalkerShaman",
            "TideWalkerSpearer": "Text_DesignData_Monster_Monster_TidewalkerSpearer",
            "Trinkets": "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Accessory",
            "Weapon": "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Weapon",
        }

        for name, key in expected.items():
            self.assertEqual(EXPLICIT_TRANSLATION_KEY_OVERRIDES[name], key)
            self.assertEqual(resolve_translation_key(name), key)

    def test_map_sources_without_official_keys_have_full_locale_overrides(self):
        source_names = (
            "Accessory_OldRustRoom",
            "ChestLarge",
            "ChestLarge_UnderSea",
            "ChestMedium",
            "ChestMedium_UnderSea",
            "ChestSmall",
            "ChestSpecial",
            "Ground",
            "Potion",
            "SkeletonWoodenBarrel",
        )

        for name in source_names:
            self.assertEqual(set(HARDCODED_LOCALE_OVERRIDES[name]), set(SUPPORTED_LANGUAGES), name)

        keys = {resolve_translation_key(name) for name in source_names}
        values = {lang: hardcoded_locale_entries(lang, keys) for lang in SUPPORTED_LANGUAGES}
        self.assertEqual(values["ja"]["df5.hardcoded.Potion"], "ポーション")
        self.assertNotIn("技術オブジェクト", values["ja"]["df5.hardcoded.Potion"])
        self.assertEqual(values["en"]["df5.hardcoded.Ground"], "Ground")


if __name__ == "__main__":
    unittest.main()
