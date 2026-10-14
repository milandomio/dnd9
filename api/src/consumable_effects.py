"""Resolve the numeric effect of consumable items from Unreal data assets.

Consumables carry no numbers in their item JSON: the item points at a
GameplayAbility blueprint, which rolls one of several status effects by weight,
and each status effect holds the real value.

    Id_Item_LuckPotion_5001
      -> ItemAbility/Id_ItemAbility_LuckPotion_5001
        -> GameplayAbility/GA_LuckPotion_5001_Consume
             RandomEffectDataArray: Luck10 (w=2000), Luck15 (w=4000), Luck20 (w=4000)
               -> Data/Generated/V2/ActorStatus/StatusEffect/Id_ActorStatusEffect_Luck10
                    "Luck": 100

Note the asset suffix is a shorthand: `Luck10` is 100, not 10.

Only the values needed by the shop pages are extracted, keyed by the item name
the shop references (`LuckPotion_5001`).
"""

import json
from pathlib import Path

from config import ACTOR_STATUS_EFFECT_DIR, POTION_ABILITY_DIR

# Status-effect fields worth surfacing on a shop card. The name is the key in
# the ActorStatusEffect JSON, not a display label.
_TRACKED_FIELDS = ("Luck",)


def _load(path: Path) -> list | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_effect_values(effect_dir: Path = ACTOR_STATUS_EFFECT_DIR) -> dict[str, dict[str, int]]:
    """Map a status-effect asset name to its tracked numeric fields."""
    values: dict[str, dict[str, int]] = {}
    if not effect_dir.exists():
        return values
    for fp in effect_dir.glob("*.json"):
        data = _load(fp)
        if not data:
            continue
        for block in data:
            props = block.get("Properties") or {}
            tracked = {k: props[k] for k in _TRACKED_FIELDS if isinstance(props.get(k), int)}
            if tracked:
                # Id_ActorStatusEffect_Luck10 -> Luck10
                values[fp.stem.removeprefix("Id_ActorStatusEffect_")] = tracked
    return values


def load_ability_rolls(ability_dir: Path = POTION_ABILITY_DIR) -> dict[str, list[dict]]:
    """Map a GameplayAbility asset name to its weighted random effect list."""
    rolls: dict[str, list[dict]] = {}
    if not ability_dir.exists():
        return rolls
    for fp in ability_dir.glob("*.json"):
        data = _load(fp)
        if not data:
            continue
        for block in data:
            props = block.get("Properties") or {}
            entries = props.get("RandomEffectDataArray")
            if not entries:
                continue
            parsed = []
            for entry in entries:
                asset = (entry.get("EffectDataAsset") or {}).get("ObjectName", "")
                # DCGameplayEffectDataAsset'Id_ActorStatusEffect_Luck10'
                if "'" not in asset:
                    continue
                effect = asset.split("'")[1].removeprefix("Id_ActorStatusEffect_")
                parsed.append({"effect": effect, "rate": int(entry.get("RandomRate") or 0)})
            if parsed:
                rolls[fp.stem] = parsed
    return rolls


def build_effect_index(
    effect_dir: Path = ACTOR_STATUS_EFFECT_DIR,
    ability_dir: Path = POTION_ABILITY_DIR,
) -> dict[str, dict]:
    """Resolve every consumable ability into an effect summary.

    Returns ``{ability_name: {"values": {field: [min, max]}, "rolls": [...]}}``
    where each roll carries its weight-derived chance.
    """
    values = load_effect_values(effect_dir)
    rolls = load_ability_rolls(ability_dir)
    index: dict[str, dict] = {}
    for ability, entries in rolls.items():
        total = sum(e["rate"] for e in entries) or 1
        resolved = []
        for entry in entries:
            tracked = values.get(entry["effect"])
            if not tracked:
                continue
            resolved.append(
                {
                    "effect": entry["effect"],
                    "rate": entry["rate"],
                    "chance": entry["rate"] / total,
                    **tracked,
                }
            )
        if not resolved:
            continue
        summary: dict[str, dict[str, list[int]]] = {}
        for field in _TRACKED_FIELDS:
            seen = [r[field] for r in resolved if field in r]
            if seen:
                summary[field] = [min(seen), max(seen)]
        index[ability] = {"values": summary, "rolls": resolved}
    return index


def resolve_item_effects(
    item_names: set[str],
    ability_index: dict[str, dict],
    item_ability_dir: Path,
) -> dict[str, dict]:
    """Map shop item names to their effect summary via the item's ability asset.

    ``Id_ItemAbility_LuckPotion_5001`` names the ability class
    ``GA_LuckPotion_5001_Consume_C``, which is the bridge to the blueprint.
    """
    effects: dict[str, dict] = {}
    for name in item_names:
        data = _load(item_ability_dir / f"Id_ItemAbility_{name}.json")
        if not data:
            continue
        for block in data:
            props = block.get("Properties") or {}
            class_name = (props.get("Class") or {}).get("ObjectName", "")
            if "'" not in class_name:
                continue
            ability = class_name.split("'")[1].removesuffix("_C")
            summary = ability_index.get(ability)
            if summary:
                effects[name] = summary
            break
    return effects
