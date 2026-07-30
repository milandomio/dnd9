import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drop_rate import DropRateEngine  # noqa: E402
from lootdrop_builder import (  # noqa: E402
    _artifact_translation_key,
    _detail_variant_suffixes,
    _get_variant_rarity,
    _resolve_legend_ref,
)


class DropRateVariantTest(unittest.TestCase):
    def setUp(self):
        self.engine = DropRateEngine()
        self.engine._ld_groups = {"group": {1001: [("drop", "rate", 1)]}}
        self.engine._ld_rate_items = {"drop": {"Bandage_4001": (4, 1)}}
        self.engine._ld_luck_grade_count = {("drop", 4): 1}
        self.engine._ld_rate_weights = {"rate": {4: 4000, 5: 2000}}
        self.engine._ld_rate_totals = {"rate": 10000}

    def test_missing_variant_never_borrows_another_quality_weight(self):
        self.assertEqual(self.engine.compute_drop_rate("group", "Bandage_5001", 1001), 0)
        self.assertEqual(
            self.engine.compute_variant_rate("group", 5, 1001, item_name="Bandage_5001"),
            0,
        )

    def test_base_family_uses_highest_real_variant_when_epic_is_absent(self):
        self.assertEqual(self.engine.compute_drop_rate("group", "Bandage", 1001), 0.4)
        self.assertEqual(
            self.engine.compute_variant_rate("group", 4, 1001, item_name="Bandage_4001"),
            0.4,
        )

    def test_detail_suffixes_come_from_real_drop_entries(self):
        self.engine._existing_variant_suffixes = {"Bandage": {"1001", "2001", "3001", "4001"}}
        entry = {"name": "Bandage", "variant_count": 7}
        self.assertEqual(
            _detail_variant_suffixes(entry, self.engine),
            ["1001", "2001", "3001", "4001"],
        )

    def test_artifact_translation_key_does_not_require_game_json(self):
        key = "Text_DesignData_Item_Item_HeaterShield_8001"
        self.assertEqual(
            _artifact_translation_key("HeaterShield_8001", {key: "不朽神盾"}),
            key,
        )

    def test_variant_rarity_uses_suffix_and_db_translations(self):
        key = "Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_Artifact"
        self.assertEqual(
            _get_variant_rarity("HeaterShield", ["8001"], {key: "神器"}),
            {"8001": {"name": "神器", "translation_key": key}},
        )

    def test_gdi_legend_ref_uses_exported_base_entity_coords(self):
        self.assertEqual(
            _resolve_legend_ref(
                "战争遗骨组",
                "SkeletonFootmanFromFakeDeath_Unique",
                [],
                {"SkeletonFootmanFromFakeDeath": "coords/SkeletonFootmanFromFakeDeath"},
            ),
            "coords/SkeletonFootmanFromFakeDeath",
        )


if __name__ == "__main__":
    unittest.main()
