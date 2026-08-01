import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db.importers.items import _item_type_metadata  # noqa: E402


class ItemTypeMetadataTest(unittest.TestCase):
    def test_armor_subtype(self):
        item_type, category_key, subtype_keys = _item_type_metadata(
            {
                "ItemType": "EItemType::Armor",
                "ArmorType": {"TagName": "Type.Item.Armor.Leather"},
            }
        )

        self.assertEqual(item_type, "Armor")
        self.assertEqual(
            category_key,
            "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Armor",
        )
        self.assertEqual(
            subtype_keys,
            ["Text_Code_DCDataBlueprintLibrary_Type_Item_Armor_Leather"],
        )

    def test_utility_and_misc_subtypes(self):
        for item_type, field, tag, subtype in (
            ("Utility", "UtilityType", "Consumable", "Consumable"),
            ("Misc", "MiscType", "Treasure", "Treasure"),
        ):
            with self.subTest(item_type=item_type):
                parsed_type, category_key, subtype_keys = _item_type_metadata(
                    {
                        "ItemType": f"EItemType::{item_type}",
                        field: {"TagName": f"Type.Item.{item_type}.{tag}"},
                    }
                )
                self.assertEqual(parsed_type, item_type)
                self.assertTrue(category_key.endswith(f"Category_{item_type}"))
                self.assertEqual(
                    subtype_keys,
                    [f"Text_Code_DCDataBlueprintLibrary_Type_Item_{item_type}_{subtype}"],
                )

    def test_accessory_and_multiple_weapon_types(self):
        item_type, category_key, subtype_keys = _item_type_metadata(
            {
                "ItemType": "EItemType::Weapon",
                "WeaponTypes": [
                    {"TagName": "Type.Item.Weapon.Sword"},
                    {"TagName": "Type.Item.Weapon.Melee"},
                    {"TagName": "Type.Item.Weapon.Sword"},
                ],
            }
        )

        self.assertEqual(item_type, "Weapon")
        self.assertTrue(category_key.endswith("Category_Weapon"))
        self.assertEqual(
            subtype_keys,
            [
                "Text_Code_DCDataBlueprintLibrary_Type_Item_Weapon_Sword",
                "Text_Code_DCDataBlueprintLibrary_Type_Item_Weapon_Melee",
            ],
        )

        accessory = _item_type_metadata(
            {
                "ItemType": "EItemType::Accessory",
                "AccessoryType": {"TagName": "Type.Item.Accessory.Ring"},
            }
        )
        self.assertEqual(accessory[2], ["Text_Code_DCDataBlueprintLibrary_Type_Item_Accessory_Ring"])

    def test_missing_subtype_is_a_valid_category(self):
        item_type, category_key, subtype_keys = _item_type_metadata({"ItemType": "EItemType::Utility"})

        self.assertEqual(item_type, "Utility")
        self.assertTrue(category_key.endswith("Category_Utility"))
        self.assertEqual(subtype_keys, [])


if __name__ == "__main__":
    unittest.main()
