import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from consumable_effects import (  # noqa: E402
    _asset_stem,
    _item_ability_names,
    load_effect_values,
    load_fixed_effects,
    resolve_item_effects,
)

# Id_ItemAbility_ProtectionPotionConsume_5001 points at a fixed status effect
# through its Effects list, exactly like the real asset does.
_SHIELD_EFFECT = {
    "Type": "DCGameplayEffectDataAsset",
    "Name": "Id_ActorStatusEffect_ProtectionPotionConsumeShield_5001",
    "Properties": {
        "EffectClass": {"ObjectName": "BlueprintGeneratedClass'GE_ProtectionPotion_C'"},
        "EventTag": {"TagName": "Ability.Player.Act.Item.Consume"},
        "duration": 24000,
        "MaxPhysicalShield": 30,
        "GrantedTags": [{"TagName": "State.ActorStatus.Buff.PhysicalShield"}],
    },
}

# A Luck effect: same shape, but the value lives behind a weighted roll.
_LUCK_EFFECT = {
    "Type": "DCGameplayEffectDataAsset",
    "Name": "Id_ActorStatusEffect_Luck10",
    "Properties": {
        "EffectClass": {"ObjectName": "BlueprintGeneratedClass'GE_Luck_C'"},
        "EventTag": {"TagName": "Ability.Player.Act.Item.Consume"},
        "duration": 600000,
        "Luck": 100,
    },
}

_SHIELD_ABILITY_NAME = "ProtectionPotionConsume_5001"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_effect_dir(directory: Path) -> None:
    _write_json(directory / "Id_ActorStatusEffect_ProtectionPotionConsumeShield_5001.json", [_SHIELD_EFFECT])
    _write_json(directory / "Id_ActorStatusEffect_Luck10.json", [_LUCK_EFFECT])


def _make_item_dir(directory: Path, name: str, ability_name: str) -> None:
    """An item asset whose ``Abilities`` list names the consume ability."""
    _write_json(
        directory / f"Id_Item_{name}.json",
        [
            {
                "Type": "DCItemDataAsset",
                "Name": f"Id_Item_{name}",
                "Properties": {
                    "Abilities": [
                        {
                            "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/Item/ItemAbility/"
                            f"Id_ItemAbility_{ability_name}.Id_ItemAbility_{ability_name}",
                        }
                    ],
                },
            }
        ],
    )


def _make_ability_dir(directory: Path, ability_name: str) -> None:
    _write_json(
        directory / f"Id_ItemAbility_{ability_name}.json",
        [
            {
                "Type": "DCGameplayAbilityDataAsset",
                "Name": f"Id_ItemAbility_{ability_name}",
                "Properties": {
                    "Class": {"ObjectName": "BlueprintGeneratedClass'GA_PotionConsumeBase_C'"},
                    "Effects": [
                        {
                            "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/Item/ItemEffect/"
                            "Id_ItemEffect_ProtectionPotionConsume.Id_ItemEffect_ProtectionPotionConsume",
                        },
                        {
                            "AssetPathName": "/Game/DungeonCrawler/Data/Generated/V2/ActorStatus/StatusEffect/"
                            "Id_ActorStatusEffect_ProtectionPotionConsumeShield_5001."
                            "Id_ActorStatusEffect_ProtectionPotionConsumeShield_5001",
                        },
                    ],
                },
            }
        ],
    )


class AssetStemTest(unittest.TestCase):
    def test_strips_package_and_object_suffix(self):
        self.assertEqual(
            _asset_stem(
                "/Game/DungeonCrawler/Data/Generated/V2/ActorStatus/StatusEffect/"
                "Id_ActorStatusEffect_Luck10.Id_ActorStatusEffect_Luck10"
            ),
            "Id_ActorStatusEffect_Luck10",
        )


class ItemAbilityNamesTest(unittest.TestCase):
    def test_reads_the_ability_asset_from_the_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_item_dir(Path(tmp), "ProtectionPotion_5001", _SHIELD_ABILITY_NAME)
            data = json.loads((Path(tmp) / "Id_Item_ProtectionPotion_5001.json").read_text(encoding="utf-8"))
        # The ability name is not the item name: it carries the Consume step.
        self.assertEqual(_item_ability_names(data), [_SHIELD_ABILITY_NAME])


class LoadFixedEffectsTest(unittest.TestCase):
    def test_shield_amount_and_duration_in_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_effect_dir(Path(tmp))
            fixed = load_fixed_effects(Path(tmp))
        shield = fixed["ProtectionPotionConsumeShield_5001"]
        self.assertEqual(shield["MaxPhysicalShield"], 30)
        # 24000 ms is the 24 seconds the in-game tooltip shows.
        self.assertEqual(shield["Duration"], 24)

    def test_duration_is_not_a_stat_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_effect_dir(Path(tmp))
            values = load_effect_values(Path(tmp))
        self.assertNotIn("Duration", values["ProtectionPotionConsumeShield_5001"])

    def test_missing_directory_yields_an_empty_index(self):
        self.assertEqual(load_fixed_effects(Path("/nonexistent")), {})


class ResolveFixedEffectsTest(unittest.TestCase):
    def _resolve(self, tmp: str, items: set[str]) -> dict:
        root = Path(tmp)
        effect_dir = root / "StatusEffect"
        _make_effect_dir(effect_dir)
        item_dir = root / "Item"
        ability_dir = root / "ItemAbility"
        for name in items:
            _make_item_dir(item_dir, name, _SHIELD_ABILITY_NAME)
            _make_ability_dir(ability_dir, _SHIELD_ABILITY_NAME)
        return resolve_item_effects(
            items,
            {},
            ability_dir,
            fixed_index=load_fixed_effects(effect_dir),
            item_dir=item_dir,
        )

    def test_protection_potion_publishes_shield_and_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            effects = self._resolve(tmp, {"ProtectionPotion_5001"})
        self.assertEqual(effects["ProtectionPotion_5001"]["values"]["MaxPhysicalShield"], [30, 30])
        self.assertEqual(effects["ProtectionPotion_5001"]["values"]["Duration"], [24, 24])
        # A fixed shield never rolls, so there is no breakdown to show.
        self.assertEqual(effects["ProtectionPotion_5001"]["rolls"], [])

    def test_item_without_an_ability_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            effect_dir = root / "StatusEffect"
            _make_effect_dir(effect_dir)
            item_dir = root / "Item"
            item_dir.mkdir(parents=True, exist_ok=True)
            ability_dir = root / "ItemAbility"
            ability_dir.mkdir(parents=True, exist_ok=True)
            effects = resolve_item_effects(
                {"Bandage_4001"},
                {},
                ability_dir,
                fixed_index=load_fixed_effects(effect_dir),
                item_dir=item_dir,
            )
        self.assertEqual(effects, {})


if __name__ == "__main__":
    unittest.main()
