import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from consumable_effects import (  # noqa: E402
    build_effect_index,
    load_ability_rolls,
    load_effect_values,
    resolve_item_effects,
)

# Real asset shapes from the game extract. They are inlined because CI runs the
# suite without the unpacked game directory, and these tests must still prove the
# parsing rules rather than silently pass on an empty source tree.
_STATUS_EFFECT: dict[str, int] = {
    "Luck02": 20,
    "Luck05": 50,
    "Luck08": 80,
    "Luck10": 100,
    "Luck15": 150,
    "Luck20": 200,
    "Luck25": 250,
    "Luck30": 300,
}
# GA_LuckPotion_{suffix}_Consume -> (status-effect suffix, weight) triples.
_BLUEPRINTS: dict[str, list[tuple[str, int]]] = {
    "GA_LuckPotion_3001_Consume": [("Luck02", 4500), ("Luck05", 3500), ("Luck08", 2000)],
    "GA_LuckPotion_4001_Consume": [("Luck05", 2500), ("Luck10", 5000), ("Luck15", 2500)],
    "GA_LuckPotion_5001_Consume": [("Luck10", 2000), ("Luck15", 4000), ("Luck20", 4000)],
    "GA_LuckPotion_6001_Consume": [("Luck20", 1000), ("Luck25", 1000), ("Luck30", 1000)],
}
# Id_ItemAbility_{item} -> ability class, i.e. the bridge to the blueprint.
_ITEM_ABILITIES: dict[str, str] = {
    "LuckPotion_3001": "GA_LuckPotion_3001_Consume",
    "LuckPotion_4001": "GA_LuckPotion_4001_Consume",
    "LuckPotion_5001": "GA_LuckPotion_5001_Consume",
    "LuckPotion_6001": "GA_LuckPotion_6001_Consume",
}


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_effect_dir(root: Path) -> Path:
    directory = root / "StatusEffect"
    directory.mkdir(parents=True, exist_ok=True)
    for suffix, value in _STATUS_EFFECT.items():
        _write_json(
            directory / f"Id_ActorStatusEffect_{suffix}.json",
            [
                {
                    "Type": "DCGameplayEffectDataAsset",
                    "Name": f"Id_ActorStatusEffect_{suffix}",
                    "Properties": {"Luck": value},
                }
            ],
        )
    return directory


def _make_ability_dir(root: Path) -> Path:
    directory = root / "GameplayAbility"
    directory.mkdir(parents=True, exist_ok=True)
    for ability, rolls in _BLUEPRINTS.items():
        _write_json(
            directory / f"{ability}.json",
            [
                {
                    "Type": "BlueprintGeneratedClass",
                    "Name": f"{ability}_C",
                    "Properties": {
                        "RandomEffectDataArray": [
                            {
                                "EffectDataAsset": {
                                    "ObjectName": f"DCGameplayEffectDataAsset'Id_ActorStatusEffect_{effect}'"
                                },
                                "RandomRate": rate,
                            }
                            for effect, rate in rolls
                        ]
                    },
                }
            ],
        )
    return directory


def _make_item_ability_dir(root: Path) -> Path:
    directory = root / "ItemAbility"
    directory.mkdir(parents=True, exist_ok=True)
    for item, ability in _ITEM_ABILITIES.items():
        _write_json(
            directory / f"Id_ItemAbility_{item}.json",
            [
                {
                    "Type": "DCGameplayAbilityDataAsset",
                    "Name": f"Id_ItemAbility_{item}",
                    "Properties": {"Class": {"ObjectName": f"BlueprintGeneratedClass'{ability}_C'"}},
                }
            ],
        )
    return directory


def _make_item_dir(root: Path) -> Path:
    """Item assets whose ``Abilities`` list points at the fixture abilities.

    CI has no game extract, so the resolver must read these rather than the
    configured ``ITEM_DIR``.
    """
    directory = root / "Item"
    directory.mkdir(parents=True, exist_ok=True)
    for item in _ITEM_ABILITIES:
        _write_json(
            directory / f"Id_Item_{item}.json",
            [
                {
                    "Type": "DCItemDataAsset",
                    "Name": f"Id_Item_{item}",
                    "Properties": {
                        "Abilities": [
                            {
                                "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/Item/ItemAbility/"
                                f"Id_ItemAbility_{item}.Id_ItemAbility_{item}",
                            }
                        ]
                    },
                }
            ],
        )
    return directory


class EffectValueTest(unittest.TestCase):
    def test_reads_luck_from_status_effect_asset(self):
        """The asset suffix is a shorthand: Luck10 holds 100, not 10."""
        with tempfile.TemporaryDirectory() as tmp:
            values = load_effect_values(_make_effect_dir(Path(tmp)))
        self.assertEqual(values["Luck10"]["Luck"], 100)

    def test_all_luck_tiers_are_ten_times_the_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            values = load_effect_values(_make_effect_dir(Path(tmp)))
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
        with tempfile.TemporaryDirectory() as tmp:
            rolls = load_ability_rolls(_make_ability_dir(Path(tmp)))
        self.assertIn("GA_LuckPotion_5001_Consume", rolls)
        effects = {r["effect"]: r["rate"] for r in rolls["GA_LuckPotion_5001_Consume"]}
        self.assertEqual(effects, {"Luck10": 2000, "Luck15": 4000, "Luck20": 4000})

    def test_returns_empty_for_missing_directory(self):
        self.assertEqual(load_ability_rolls(Path("/nonexistent")), {})


class BuildEffectIndexTest(unittest.TestCase):
    def _index(self, tmp: str) -> dict[str, dict]:
        root = Path(tmp)
        return build_effect_index(_make_effect_dir(root), _make_ability_dir(root))

    def test_four_luck_potions_are_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = self._index(tmp)
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
        with tempfile.TemporaryDirectory() as tmp:
            index = self._index(tmp)
        expected = {
            "GA_LuckPotion_3001_Consume": [20, 80],
            "GA_LuckPotion_4001_Consume": [50, 150],
            "GA_LuckPotion_5001_Consume": [100, 200],
            "GA_LuckPotion_6001_Consume": [200, 300],
        }
        for ability, want in expected.items():
            self.assertEqual(index[ability]["values"]["Luck"], want)

    def test_chances_sum_to_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = self._index(tmp)
        for summary in index.values():
            self.assertAlmostEqual(sum(r["chance"] for r in summary["rolls"]), 1.0, places=6)

    def test_6001_is_uniform_across_three_tiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self._index(tmp)["GA_LuckPotion_6001_Consume"]
        self.assertEqual(len(summary["rolls"]), 3)
        for roll in summary["rolls"]:
            self.assertAlmostEqual(roll["chance"], 1 / 3, places=6)


class ResolveItemEffectsTest(unittest.TestCase):
    def _resolve(self, tmp: str, items: set[str]) -> dict[str, dict]:
        root = Path(tmp)
        return resolve_item_effects(
            items,
            build_effect_index(_make_effect_dir(root), _make_ability_dir(root)),
            _make_item_ability_dir(root),
            item_dir=_make_item_dir(root),
        )

    def test_item_name_maps_through_its_ability_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            effects = self._resolve(tmp, {"LuckPotion_5001", "LuckPotion_6001"})
        self.assertEqual(effects["LuckPotion_5001"]["values"]["Luck"], [100, 200])
        self.assertEqual(effects["LuckPotion_6001"]["values"]["Luck"], [200, 300])

    def test_items_without_a_rollable_effect_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            effects = self._resolve(tmp, {"HealingPotion_5001", "Bandage_4001"})
        self.assertEqual(effects, {})

    def test_unknown_item_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            effects = self._resolve(tmp, {"NotARealItem"})
        self.assertEqual(effects, {})


class MissingSourceTest(unittest.TestCase):
    """Exports run without the game extract (CI has none) and must not fail."""

    def test_missing_directories_yield_an_empty_index(self):
        self.assertEqual(
            build_effect_index(Path("/nonexistent"), Path("/nonexistent")),
            {},
        )
        self.assertEqual(
            resolve_item_effects(
                {"LuckPotion_5001"},
                {},
                Path("/nonexistent"),
                item_dir=Path("/nonexistent"),
            ),
            {},
        )


if __name__ == "__main__":
    unittest.main()
