import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import hardcoded_locale_entries  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
