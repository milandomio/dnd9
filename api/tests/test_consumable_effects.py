import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import ACTOR_STATUS_EFFECT_DIR, ITEM_ABILITY_DIR, POTION_ABILITY_DIR  # noqa: E402
from consumable_effects import (  # noqa: E402
    build_effect_index,
    load_ability_rolls,
    load_effect_values,
    resolve_item_effects,
)


class EffectValueTest(unittest.TestCase):
    def test_reads_luck_from_status_effect_asset(self):
        """The asset suffix is a shorthand: Luck10 holds 100, not 10."""
        values = load_effect_values()
        self.assertEqual(values["Luck10"]["Luck"], 100)

    def test_all_luck_tiers_are_ten_times_the_suffix(self):
        values = load_effect_values()
        for suffix, expected in (
            ("02", 20),
            ("05", 50),
            ("08", 80),
            ("15", 150),
            ("20", 200),
            ("25", 250),
            ("30", 300),
        ):
            self.assertEqual(values[f"Luck{suffix}"]["Luck"], expected)

    def test_returns_empty_for_missing_directory(self):
        self.assertEqual(load_effect_values(Path("/nonexistent")), {})


class AbilityRollTest(unittest.TestCase):
    def test_luck_potion_rolls_carry_weights(self):
        rolls = load_ability_rolls()
        self.assertIn("GA_LuckPotion_5001_Consume", rolls)
        effects = {r["effect"]: r["rate"] for r in rolls["GA_LuckPotion_5001_Consume"]}
        self.assertEqual(effects, {"Luck10": 2000, "Luck15": 4000, "Luck20": 4000})

    def test_returns_empty_for_missing_directory(self):
        self.assertEqual(load_ability_rolls(Path("/nonexistent")), {})


class BuildEffectIndexTest(unittest.TestCase):
    def test_four_luck_potions_are_resolved(self):
        index = build_effect_index()
        self.assertEqual(
            sorted(index),
            [
                "GA_LuckPotion_3001_Consume",
                "GA_LuckPotion_4001_Consume",
                "GA_LuckPotion_5001_Consume",
                "GA_LuckPotion_6001_Consume",
            ],
        )

    def test_ranges_match_the_shipped_tiers(self):
        index = build_effect_index()
        expected = {
            "GA_LuckPotion_3001_Consume": [20, 80],
            "GA_LuckPotion_4001_Consume": [50, 150],
            "GA_LuckPotion_5001_Consume": [100, 200],
            "GA_LuckPotion_6001_Consume": [200, 300],
        }
        for ability, want in expected.items():
            self.assertEqual(index[ability]["values"]["Luck"], want)

    def test_chances_sum_to_one(self):
        for summary in build_effect_index().values():
            self.assertAlmostEqual(sum(r["chance"] for r in summary["rolls"]), 1.0, places=6)

    def test_6001_is_uniform_across_three_tiers(self):
        summary = build_effect_index()["GA_LuckPotion_6001_Consume"]
        self.assertEqual(len(summary["rolls"]), 3)
        for roll in summary["rolls"]:
            self.assertAlmostEqual(roll["chance"], 1 / 3, places=6)


class ResolveItemEffectsTest(unittest.TestCase):
    def test_item_name_maps_through_its_ability_asset(self):
        effects = resolve_item_effects({"LuckPotion_5001", "LuckPotion_6001"}, build_effect_index(), ITEM_ABILITY_DIR)
        self.assertEqual(effects["LuckPotion_5001"]["values"]["Luck"], [100, 200])
        self.assertEqual(effects["LuckPotion_6001"]["values"]["Luck"], [200, 300])

    def test_items_without_a_rollable_effect_are_skipped(self):
        effects = resolve_item_effects({"HealingPotion_5001", "Bandage_4001"}, build_effect_index(), ITEM_ABILITY_DIR)
        self.assertEqual(effects, {})

    def test_unknown_item_is_skipped(self):
        effects = resolve_item_effects({"NotARealItem"}, build_effect_index(), ITEM_ABILITY_DIR)
        self.assertEqual(effects, {})


class ConfigPathTest(unittest.TestCase):
    def test_source_directories_exist(self):
        """Guard against the game extract being re-exported elsewhere."""
        self.assertTrue(ACTOR_STATUS_EFFECT_DIR.exists(), ACTOR_STATUS_EFFECT_DIR)
        self.assertTrue(POTION_ABILITY_DIR.exists(), POTION_ABILITY_DIR)


if __name__ == "__main__":
    unittest.main()
