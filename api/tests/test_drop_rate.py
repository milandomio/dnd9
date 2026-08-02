import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from drop_rate import DropRateEngine, _find_rate_item  # noqa: E402
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
        self.engine._ld_rate_items = {"drop": {"Bandage_4001": [(4, 1)]}}
        self.engine._ld_luck_grade_count = {("drop", 4): 1}
        self.engine._ld_rate_weights = {"rate": {4: 4000, 5: 2000}}
        self.engine._ld_rate_totals = {"rate": 10000}

    def test_missing_variant_never_borrows_another_quality_weight(self):
        self.engine._ld_preferred_base_items = {"drop": {"Bandage": [(4, 1)]}}
        self.assertEqual(self.engine.compute_drop_rate("group", "Bandage_5001", 1001), 0)
        self.assertEqual(
            self.engine.compute_variant_rate("group", 5, 1001, item_name="Bandage_5001"),
            0,
        )

    def test_preloaded_cache_prefers_epic_variant_for_base_item(self):
        self.engine._ld_rate_items = {
            "drop": {
                "Bandage_4001": [(4, 1)],
                "Bandage_5001": [(5, 1)],
                "Bandage_7001": [(7, 1)],
            }
        }
        self.engine._ld_preferred_base_items = {"drop": {"Bandage": [(5, 1)]}}
        self.engine._ld_luck_grade_count = {("drop", 4): 1, ("drop", 5): 1, ("drop", 7): 1}
        self.engine._ld_rate_weights = {"rate": {4: 4000, 5: 5000, 7: 7000}}

        self.assertEqual(self.engine.compute_drop_rate("group", "Bandage", 1001), 0.5)

    def test_preloaded_cache_uses_highest_variant_without_epic(self):
        self.engine._ld_rate_items = {"drop": {"Bandage_4001": [(4, 1)], "Bandage_7001": [(7, 1)]}}
        self.engine._ld_preferred_base_items = {"drop": {"Bandage": [(7, 1)]}}
        self.engine._ld_luck_grade_count = {("drop", 4): 1, ("drop", 7): 1}
        self.engine._ld_rate_weights = {"rate": {4: 4000, 7: 7000}}

        self.assertEqual(self.engine.compute_drop_rate("group", "Bandage", 1001), 0.7)

    def test_exact_base_item_beats_preloaded_variant(self):
        self.engine._ld_rate_items = {"drop": {"Bandage": [(2, 1)], "Bandage_5001": [(5, 1)]}}
        self.engine._ld_preferred_base_items = {"drop": {"Bandage": [(5, 1)]}}
        self.engine._ld_luck_grade_count = {("drop", 2): 1, ("drop", 5): 1}
        self.engine._ld_rate_weights = {"rate": {2: 2000, 5: 5000}}

        self.assertEqual(self.engine.compute_drop_rate("group", "Bandage", 1001), 0.2)

    def test_preloaded_cache_excludes_artifact_variant(self):
        self.engine._ld_rate_items = {"drop": {"Bandage_8001": [(8, 1)]}}
        self.engine._ld_preferred_base_items = {"drop": {}}
        self.engine._ld_luck_grade_count = {("drop", 8): 1}
        self.engine._ld_rate_weights = {"rate": {8: 8000}}

        self.assertEqual(self.engine.compute_drop_rate("group", "Bandage", 1001), 0)

    def test_preloaded_cache_matches_legacy_base_resolution(self):
        rate_items = {
            "Bandage_4001": [(4, 1)],
            "Bandage_5001": [(5, 1)],
            "Bandage_7001": [(7, 1)],
            "Sword_4001": [(4, 1)],
            "Sword_7001": [(7, 1)],
            "Artifact_8001": [(8, 1)],
            "ExactItem": [(2, 1)],
        }
        self.engine._ld_preferred_base_items = self.engine._build_preferred_base_items({"drop": rate_items})

        for item_name in ("Bandage", "Sword", "Artifact", "ExactItem", "Bandage_3001"):
            self.assertEqual(
                self.engine._resolve_rate_item("drop", rate_items, item_name),
                _find_rate_item(rate_items, item_name),
            )

    def test_base_family_uses_highest_real_variant_when_epic_is_absent(self):
        self.assertEqual(self.engine.compute_drop_rate("group", "Bandage", 1001), 0.4)
        self.assertEqual(
            self.engine.compute_variant_rate("group", 4, 1001, item_name="Bandage_4001"),
            0.4,
        )

    def test_item_with_multiple_luck_grades_sums_each_pool_weight(self):
        self.engine._ld_rate_items = {"drop": {"ShiningPearl": [(6, 1), (7, 1)]}}
        self.engine._ld_luck_grade_count = {("drop", 6): 1, ("drop", 7): 1}
        self.engine._ld_rate_weights = {"rate": {6: 1250, 7: 50}}

        self.assertEqual(self.engine.compute_drop_rate("group", "ShiningPearl", 1001), 0.13)
        self.assertEqual(
            self.engine.compute_variant_rate("group", 6, 1001, item_name="ShiningPearl"),
            0.13,
        )

    def test_bellows_sums_all_three_registered_luck_grades(self):
        self.engine._ld_rate_items = {"drop": {"Bellows": [(2, 1), (3, 1), (4, 1)]}}
        self.engine._ld_luck_grade_count = {("drop", 2): 1, ("drop", 3): 1, ("drop", 4): 1}
        self.engine._ld_rate_weights = {"rate": {2: 500, 3: 1000, 4: 2000}}

        self.assertAlmostEqual(self.engine.compute_drop_rate("group", "Bellows", 1001), 0.35)

    def test_detail_suffixes_come_from_real_drop_entries(self):
        self.engine._existing_variant_suffixes = {"Bandage": {"1001", "2001", "3001", "4001", "8001"}}
        entry = {"name": "Bandage", "variant_count": 7}
        self.assertEqual(
            _detail_variant_suffixes(entry, self.engine),
            ["1001", "2001", "3001", "4001", "8001"],
        )

    def test_artifact_and_ordinary_pages_share_rarity_suffixes(self):
        self.engine._existing_variant_suffixes = {
            "Spellbook": {
                "1001",
                "2001",
                "3001",
                "4001",
                "5001",
                "6001",
                "7001",
                "8001",
            }
        }
        self.assertEqual(
            _detail_variant_suffixes({"name": "Spellbook"}, self.engine)[-1],
            "8001",
        )
        self.assertEqual(
            _detail_variant_suffixes({"name": "Spellbook_8001"}, self.engine),
            ["1001", "2001", "3001", "4001", "5001", "6001", "7001", "8001"],
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


class DropRatePreloadIndexTest(unittest.TestCase):
    def test_base_item_spawner_index_matches_rate_item_join(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript("""
            CREATE TABLE spawner_entries (spawner_keyword TEXT, entity_name TEXT, lootdrop_group_id TEXT);
            CREATE TABLE lootdrop_groups (group_id TEXT, dungeon_grade INTEGER, lootdrop_id TEXT, lootdrop_rate_id TEXT, drop_count INTEGER);
            CREATE TABLE lootdrop_rate_items (lootdrop_id TEXT, item_name TEXT, luck_grade INTEGER, drop_count INTEGER);
            CREATE TABLE lootdrop_rate_weights (rate_id TEXT, luck_grade INTEGER, weight INTEGER);
            CREATE TABLE spawners (keyword TEXT, map_base TEXT);
            INSERT INTO spawner_entries VALUES ('TearofHrithurs', '', 'group-a');
            INSERT INTO spawner_entries VALUES ('TearofHrimthurs', '', 'group-a');
            INSERT INTO lootdrop_groups VALUES ('group-a', 1001, 'drop-a', 'rate-a', 1);
            INSERT INTO lootdrop_rate_items VALUES ('drop-a', 'TearofHrimthurs_5001', 5, 1);
            INSERT INTO lootdrop_rate_items VALUES ('orphan-drop', 'OrphanItem_5001', 5, 1);
        """)

        class _Db:
            def connect(self):
                return conn

            def get_all_spawner_entries(self):
                return []

        engine = DropRateEngine()
        engine.preload(_Db(), [])
        old_sql_map = {}
        for row in conn.execute(
            "SELECT DISTINCT lri.item_name, se.spawner_keyword "
            "FROM lootdrop_rate_items lri "
            "JOIN lootdrop_groups lg ON lri.lootdrop_id = lg.lootdrop_id "
            "JOIN spawner_entries se ON lg.group_id = se.lootdrop_group_id"
        ):
            old_sql_map.setdefault(row["item_name"].removesuffix("_5001"), set()).add(row["spawner_keyword"])

        self.assertEqual(engine.base_item_spawners, old_sql_map)
        self.assertEqual(
            list(engine.base_item_spawners["TearofHrimthurs"]),
            list(old_sql_map["TearofHrimthurs"]),
        )


if __name__ == "__main__":
    unittest.main()
