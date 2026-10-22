import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from craft_builder import build_and_save_crafts  # noqa: E402

_SHIELD_KEY = "Text_Code_DCDataBlueprintLibrary_Data_SetByCaller_MaxPhysicalShield"
_DURATION_KEY = "Text_Code_DCDataBlueprintLibrary_Data_SetByCaller_Duration"
_LUCK_KEY = "Text_Code_DCDataBlueprintLibrary_Data_SetByCaller_Luck"
_LABELS = {_SHIELD_KEY: "最大物理护盾", _DURATION_KEY: "持续时间", _LUCK_KEY: "幸运值"}

# Shape written by db/importers/effects.py for a Protection potion: a fixed
# shield plus the buff duration, both resolved from the gameplay assets.
_PROTECTION_EFFECT = {
    "values": {"MaxPhysicalShield": [30, 30], "Duration": [24, 24]},
    "rolls": [],
}

# A Luck potion rolls one of several tiers instead of granting a fixed value.
_LUCK_EFFECT = {
    "values": {"Luck": [100, 200]},
    "rolls": [{"effect": "Luck10", "rate": 2000, "chance": 0.2, "Luck": 100}],
}


def _resolve(_name, key, _domain):
    return _LABELS.get(key, "")


def _merchant():
    return [
        {
            "merchant_name": "Alchemist",
            "kind": "npc",
            "translation_key": "Text_DesignData_Merchant_Merchant_Alchemist",
            "sort_order": 1,
        }
    ]


def _recipe(output_raw_name="ProtectionPotion_5001", output_item_name="ProtectionPotion"):
    return [
        {
            "merchant_name": "Alchemist",
            "recipe_id": "Id_StockCraft_Alchemist_17#0",
            "unique_id": 28,
            "output_raw_name": output_raw_name,
            "output_item_name": output_item_name,
            "output_rarity": "Epic",
            "requirements_json": json.dumps(
                [{"name": "Wardweed", "raw_name": "Wardweed_2001", "rarity": "Common", "amount": 1}]
            ),
        }
    ]


def _items():
    return [
        {
            "item_name": "ProtectionPotion",
            "translation_key": "Text_DesignData_Item_Item_ProtectionPotion_5001",
            "item_category_key": "",
            "item_subtype_keys": "[]",
            "item_type": "",
            "item_slot_key": "",
        }
    ]


class CraftEffectTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _build(self, item_effects=None):
        return build_and_save_crafts(
            _merchant(),
            _recipe(),
            _items(),
            _resolve,
            self.output_dir,
            item_effects=item_effects,
        )

    def test_protection_potion_carries_shield_and_duration(self):
        payload = self._build({"ProtectionPotion_5001": _PROTECTION_EFFECT})
        effect = payload["recipes"][0]["effect"]
        self.assertEqual(
            [(entry["type"], entry["min"], entry["max"]) for entry in effect["values"]],
            [("MaxPhysicalShield", 30, 30), ("Duration", 24, 24)],
        )
        self.assertEqual(effect["values"][0]["translation"], "最大物理护盾")
        self.assertEqual(effect["values"][0]["translation_key"], _SHIELD_KEY)
        # Only the duration renders with a 秒 suffix.
        self.assertEqual(
            [bool(entry.get("seconds")) for entry in effect["values"]],
            [False, True],
        )
        # A fixed shield is never rolled, so no random hint is attached.
        self.assertFalse(effect["random"])

    def test_random_effect_is_flagged(self):
        payload = self._build({"LuckPotion_5001": _LUCK_EFFECT})
        # The recipe names ProtectionPotion, so a Luck summary is not merged in.
        self.assertNotIn("effect", payload["recipes"][0])

    def test_items_without_an_effect_are_untouched(self):
        payload = self._build()
        self.assertNotIn("effect", payload["recipes"][0])


if __name__ == "__main__":
    unittest.main()
