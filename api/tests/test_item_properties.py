import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from item_properties import (  # noqa: E402
    _asset_stem,
    _tag_translation_key,
    build_property_type_index,
    resolve_item_properties,
)

# Real asset shapes from the game extract. They are inlined because CI runs the
# suite without the unpacked game directory, and these tests must still prove the
# parsing rules rather than silently pass on an empty source tree.
_PRIMARY_AKETON = {
    "Type": "DCItemPropertyDataAsset",
    "Name": "Id_ItemProperty_Primary_FrostlightAketon_5001",
    "Properties": {
        "ItemPropertyItemArray": [
            {
                "PropertyTypeId": {
                    "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/ItemProperty/ItemPropertyType/Id_ItemPropertyType_Effect_ArmorRating.Id_ItemPropertyType_Effect_ArmorRating",
                    "SubPathString": "",
                },
                "MinValue": 19,
                "MaxValue": 20,
                "EnchantMinValue": 0,
                "EnchantMaxValue": 0,
                "PropertyRate": 0,
            },
            {
                "PropertyTypeId": {
                    "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/ItemProperty/ItemPropertyType/Id_ItemPropertyType_Effect_ActionSpeed.Id_ItemPropertyType_Effect_ActionSpeed",
                    "SubPathString": "",
                },
                "MinValue": 10,
                "MaxValue": 10,
                "EnchantMinValue": 0,
                "EnchantMaxValue": 0,
                "PropertyRate": 0,
            },
        ]
    },
}
_SECONDARY_CHEST = {
    "Type": "DCItemPropertyDataAsset",
    "Name": "Id_ItemProperty_Secondary_Chest",
    "Properties": {
        "ItemPropertyItemArray": [
            {
                "PropertyTypeId": {
                    "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/ItemProperty/ItemPropertyType/Id_ItemPropertyType_Effect_Strength.Id_ItemPropertyType_Effect_Strength",
                    "SubPathString": "",
                },
                "MinValue": 2,
                "MaxValue": 3,
                "PropertyRate": 2000,
            },
            {
                "PropertyTypeId": {
                    "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/ItemProperty/ItemPropertyType/Id_ItemPropertyType_Effect_MoveSpeedBonus.Id_ItemPropertyType_Effect_MoveSpeedBonus",
                    "SubPathString": "",
                },
                "MinValue": 10,
                "MaxValue": 15,
                "PropertyRate": 1000,
            },
        ]
    },
}
_TYPE_ASSETS = {
    # ArmorRating / Strength are flat; ActionSpeed and MoveSpeedBonus are the
    # 0.001-ratio percentage stats (raw 10 -> 1%).
    "Id_ItemPropertyType_Effect_ArmorRating": ("Type.Item.Property.Effect.ArmorRating", None),
    "Id_ItemPropertyType_Effect_ActionSpeed": ("Type.Item.Property.Effect.ActionSpeed", 0.001),
    "Id_ItemPropertyType_Effect_Strength": ("Type.Item.Property.Effect.Strength", None),
    "Id_ItemPropertyType_Effect_MoveSpeedBonus": ("Type.Item.Property.Effect.MoveSpeedBonus", 0.001),
}
_ITEM_AKETON = {
    "Type": "DCItemDataAsset",
    "Name": "Id_Item_FrostlightAketon_5001",
    "Properties": {
        "PrimaryProperty": {
            "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/ItemProperty/ItemProperty/Id_ItemProperty_Primary_FrostlightAketon_5001.Id_ItemProperty_Primary_FrostlightAketon_5001",
            "SubPathString": "",
        },
        "SecondaryProperties": [
            {
                "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/ItemProperty/ItemProperty/Id_ItemProperty_Secondary_Chest.Id_ItemProperty_Secondary_Chest",
                "SubPathString": "",
            }
        ]
        * 3,
    },
}
_ITEM_POWDER = {
    "Type": "DCItemDataAsset",
    "Name": "Id_Item_FrostStonePowder_5001",
    "Properties": {"Name": {"Key": "Text_DesignData_Item_Item_FrostStonePowder_5001"}},
}


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class ItemPropertiesTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.item_dir = root / "Item"
        self.property_dir = root / "ItemProperty"
        self.type_dir = root / "ItemPropertyType"
        for directory in (self.item_dir, self.property_dir, self.type_dir):
            directory.mkdir(parents=True)

        _write_json(self.item_dir / "Id_Item_FrostlightAketon_5001.json", [_ITEM_AKETON])
        _write_json(self.item_dir / "Id_Item_FrostStonePowder_5001.json", [_ITEM_POWDER])
        _write_json(
            self.property_dir / "Id_ItemProperty_Primary_FrostlightAketon_5001.json",
            [_PRIMARY_AKETON],
        )
        _write_json(self.property_dir / "Id_ItemProperty_Secondary_Chest.json", [_SECONDARY_CHEST])
        for stem, (tag, ratio) in _TYPE_ASSETS.items():
            properties = {"PropertyType": {"TagName": tag}}
            if ratio is not None:
                properties["ValueRatio"] = ratio
            _write_json(self.type_dir / f"{stem}.json", [{"Name": stem, "Properties": properties}])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_asset_stem_and_translation_key(self):
        self.assertEqual(
            _asset_stem("/Game/X/Y/Id_ItemProperty_Secondary_Chest.Id_ItemProperty_Secondary_Chest"),
            "Id_ItemProperty_Secondary_Chest",
        )
        self.assertEqual(
            _tag_translation_key("Type.Item.Property.Effect.ArmorRating"),
            "Text_Code_DCDataBlueprintLibrary_Type_Item_Property_Effect_ArmorRating",
        )

    def test_type_index_carries_key_and_ratio(self):
        index = build_property_type_index(self.type_dir)
        self.assertEqual(
            index["Id_ItemPropertyType_Effect_ActionSpeed"],
            {
                "key": "Text_Code_DCDataBlueprintLibrary_Type_Item_Property_Effect_ActionSpeed",
                "ratio": 0.001,
            },
        )
        self.assertEqual(
            index["Id_ItemPropertyType_Effect_ArmorRating"]["ratio"],
            0.0,
        )

    def test_resolve_primary_and_shared_pool(self):
        items, pools = resolve_item_properties(self.item_dir, self.property_dir, self.type_dir)

        # Materials carry no property asset and must not create a row.
        self.assertEqual(sorted(items), ["FrostlightAketon_5001"])
        aketon = items["FrostlightAketon_5001"]
        self.assertEqual(aketon["secondary_pool"], "Id_ItemProperty_Secondary_Chest")
        self.assertEqual(aketon["secondary_rolls"], 3)
        self.assertEqual(
            aketon["primary"],
            [
                {
                    "type": "Effect_ArmorRating",
                    "key": "Text_Code_DCDataBlueprintLibrary_Type_Item_Property_Effect_ArmorRating",
                    "ratio": 0.0,
                    "min": 19,
                    "max": 20,
                },
                {
                    "type": "Effect_ActionSpeed",
                    "key": "Text_Code_DCDataBlueprintLibrary_Type_Item_Property_Effect_ActionSpeed",
                    "ratio": 0.001,
                    "min": 10,
                    "max": 10,
                },
            ],
        )
        # Primary rows carry no draw rate; pool rows do.
        self.assertNotIn("rate", aketon["primary"][0])
        self.assertEqual(
            [row["rate"] for row in pools["Id_ItemProperty_Secondary_Chest"]],
            [2000, 1000],
        )
        self.assertEqual(
            pools["Id_ItemProperty_Secondary_Chest"][1]["ratio"],
            0.001,
        )

    def test_unknown_property_type_keeps_the_row(self):
        """A type asset missing from the extract still shows its raw range."""
        _write_json(
            self.property_dir / "Id_ItemProperty_Primary_FrostlightAketon_5001.json",
            [
                {
                    "Properties": {
                        "ItemPropertyItemArray": [
                            {
                                "PropertyTypeId": {
                                    "AssetPathName": "/Game/X/Id_ItemPropertyType_Effect_WeightLimitAdd.Id_ItemPropertyType_Effect_WeightLimitAdd"
                                },
                                "MinValue": 5,
                                "MaxValue": 7,
                            }
                        ]
                    }
                }
            ],
        )
        items, _ = resolve_item_properties(self.item_dir, self.property_dir, self.type_dir)
        row = items["FrostlightAketon_5001"]["primary"][0]
        self.assertEqual(
            (row["type"], row["key"], row["ratio"], row["min"], row["max"]), ("Effect_WeightLimitAdd", "", 0.0, 5, 7)
        )

    def test_missing_source_dirs_resolve_to_nothing(self):
        items, pools = resolve_item_properties(
            Path(self.temp_dir.name) / "nope",
            self.property_dir,
            self.type_dir,
        )
        self.assertEqual((items, pools), ({}, {}))


if __name__ == "__main__":
    unittest.main()
