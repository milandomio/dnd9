import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from craft_builder import build_and_save_crafts  # noqa: E402

_ARMOR_KEY = "Text_Code_DCDataBlueprintLibrary_Type_Item_Property_Effect_ArmorRating"
_STRENGTH_KEY = "Text_Code_DCDataBlueprintLibrary_Type_Item_Property_Effect_Strength"
_MOVE_BONUS_KEY = "Text_Code_DCDataBlueprintLibrary_Type_Item_Property_Effect_MoveSpeedBonus"
_LABELS = {_ARMOR_KEY: "护甲值", _STRENGTH_KEY: "力量", _MOVE_BONUS_KEY: "移动速度加成"}

# Shape written by db/importers/item_properties.py (see test_item_properties.py
# for the asset parsing that produces it).
_ITEM_PROPERTIES = {
    "FrostlightAketon_5001": {
        "primary": [{"type": "Effect_ArmorRating", "key": _ARMOR_KEY, "ratio": 0.0, "min": 19, "max": 20}],
        "secondary_pool": "Id_ItemProperty_Secondary_Chest",
        "secondary_rolls": 3,
    }
}
_POOLS = {
    "Id_ItemProperty_Secondary_Chest": [
        {"type": "Effect_Strength", "key": _STRENGTH_KEY, "ratio": 0.0, "min": 2, "max": 3, "rate": 2000},
        {"type": "Effect_MoveSpeedBonus", "key": _MOVE_BONUS_KEY, "ratio": 0.001, "min": 10, "max": 15, "rate": 1000},
    ]
}


def _resolve(_name, key, _domain):
    return _LABELS.get(key, "")


def _merchant():
    return [
        {
            "merchant_name": "Tailor",
            "kind": "npc",
            "translation_key": "Text_DesignData_Merchant_Merchant_Tailor",
            "sort_order": 4,
        }
    ]


def _recipe(output_raw_name="FrostlightAketon_5001", output_item_name="FrostlightAketon", recipe_id="R1"):
    return [
        {
            "merchant_name": "Tailor",
            "recipe_id": recipe_id,
            "unique_id": 160,
            "output_raw_name": output_raw_name,
            "output_item_name": output_item_name,
            "output_rarity": "Epic",
            "requirements_json": json.dumps(
                [{"name": "LightAketon", "raw_name": "LightAketon_4001", "rarity": "Rare", "amount": 1}]
            ),
        }
    ]


def _items():
    return [
        {
            "item_name": "FrostlightAketon",
            "translation_key": "Text_DesignData_Item_Item_FrostlightAketon_5001",
            "item_category_key": "",
            "item_subtype_keys": "[]",
            "item_type": "Armor",
            "item_slot_key": "",
        }
    ]


class CraftBuilderPropertiesTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _build(self, item_properties=None, property_pools=None):
        return build_and_save_crafts(
            _merchant(),
            _recipe(),
            _items(),
            _resolve,
            self.output_dir,
            item_properties=item_properties,
            property_pools=property_pools,
        )

    def test_primary_stats_carry_label_and_range(self):
        payload = self._build(_ITEM_PROPERTIES, _POOLS)
        properties = payload["recipes"][0]["properties"]
        self.assertEqual(
            properties["primary"],
            [
                {
                    "type": "Effect_ArmorRating",
                    "translation": "护甲值",
                    "translation_key": _ARMOR_KEY,
                    "min": 19,
                    "max": 20,
                }
            ],
        )

    def test_random_slots_reference_the_shared_pool(self):
        payload = self._build(_ITEM_PROPERTIES, _POOLS)
        recipe = payload["recipes"][0]
        self.assertEqual(recipe["properties"]["random"], {"rolls": 3, "pool": "Id_ItemProperty_Secondary_Chest"})

        # The pool ships once per payload, with the draw chance resolved.
        pool = payload["property_pools"]["Id_ItemProperty_Secondary_Chest"]
        self.assertEqual([entry["type"] for entry in pool], ["Effect_Strength", "Effect_MoveSpeedBonus"])
        self.assertEqual(pool[0]["chance"], 0.6667)
        self.assertEqual(pool[1]["chance"], 0.3333)
        # 0.001 marks the percentage stats; the client renders 10 -> 1%.
        self.assertEqual(pool[1]["ratio"], 0.001)
        self.assertNotIn("ratio", pool[0])

    def test_pool_entries_are_not_repeated_per_recipe(self):
        payload = self._build(_ITEM_PROPERTIES, _POOLS)
        self.assertEqual(len(payload["recipes"]), 1)
        self.assertNotIn("entries", payload["recipes"][0]["properties"].get("random", {}))
        self.assertEqual(len(payload["property_pools"]), 1)

    def test_missing_pool_keeps_the_primary_stats(self):
        payload = self._build({"FrostlightAketon_5001": dict(_ITEM_PROPERTIES["FrostlightAketon_5001"])}, {})
        properties = payload["recipes"][0]["properties"]
        self.assertEqual(len(properties["primary"]), 1)
        self.assertNotIn("random", properties)
        self.assertEqual(payload["property_pools"], {})

    def test_unknown_item_gets_no_properties_key(self):
        payload = self._build({}, {})
        self.assertNotIn("properties", payload["recipes"][0])
        self.assertEqual(payload["property_pools"], {})

    def test_payload_is_written_to_disk(self):
        self._build(_ITEM_PROPERTIES, _POOLS)
        saved = json.loads((self.output_dir / "crafts.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["recipes"][0]["properties"]["primary"][0]["translation"], "护甲值")
        self.assertIn("Id_ItemProperty_Secondary_Chest", saved["property_pools"])


if __name__ == "__main__":
    unittest.main()
