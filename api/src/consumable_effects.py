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

A second shape exists for the Protection potions, which apply one fixed shield
through the consume ability's `Effects` list instead of rolling one of several:

    Id_Item_ProtectionPotion_5001
      -> ItemAbility/Id_ItemAbility_ProtectionPotionConsume_5001
           Effects: [Id_ItemEffect_ProtectionPotionConsume,
                     Id_ActorStatusEffect_ProtectionPotionConsumeShield_5001]
                        MaxPhysicalShield 30, duration 24000

Every buff also carries a `duration`, so it is tracked like a stat: the game
stores milliseconds while the UI shows seconds.

Only the values needed by the shop pages are extracted, keyed by the item name
the shop references (`LuckPotion_5001`).
"""

import json
from pathlib import Path

from config import ACTOR_STATUS_EFFECT_DIR, ITEM_DIR, POTION_ABILITY_DIR

# Status-effect fields worth surfacing on a shop card. The name is the key in
# the ActorStatusEffect JSON, not a display label.
_TRACKED_FIELDS = ("Luck", "MaxPhysicalShield", "MaxMagicalShield")

# ``duration`` lives on every buff as milliseconds. It is surfaced as the
# ``Duration`` stat in seconds, matching the game tooltip and the wiki.
_DURATION_FIELD = "Duration"
_DURATION_KEY = "Text_Code_DCDataBlueprintLibrary_Data_SetByCaller_Duration"
_DURATION_DIVISOR = 1000


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


def _asset_stem(asset_path_name: str) -> str:
    """``/Game/.../Id_ActorStatusEffect_Luck10.Id_ActorStatusEffect_Luck10`` -> stem."""
    return asset_path_name.rsplit("/", 1)[-1].split(".", 1)[0]


def load_fixed_effects(effect_dir: Path = ACTOR_STATUS_EFFECT_DIR) -> dict[str, dict[str, int]]:
    """Map a status-effect asset name to its fixed numbers plus its duration.

    Unlike :func:`load_effect_values` this keeps *every* status effect that
    carries a tracked stat or a duration, because the Protection potions reach
    their shield through the ability's ``Effects`` list rather than through a
    weighted roll. ``Duration`` is the game's millisecond value divided down to
    the seconds the tooltip shows.
    """
    fixed: dict[str, dict[str, int]] = {}
    if not effect_dir.exists():
        return fixed
    for fp in effect_dir.glob("*.json"):
        data = _load(fp)
        if not data:
            continue
        for block in data:
            props = block.get("Properties") or {}
            tracked = {k: props[k] for k in _TRACKED_FIELDS if isinstance(props.get(k), int)}
            duration = props.get("duration")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration > 0:
                tracked[_DURATION_FIELD] = int(round(duration / _DURATION_DIVISOR))
            if tracked:
                # Id_ActorStatusEffect_ProtectionPotionConsumeShield_5001 -> ...
                fixed[fp.stem.removeprefix("Id_ActorStatusEffect_")] = tracked
    return fixed


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


def _ability_effects(
    data: list,
    fixed_index: dict[str, dict[str, int]],
) -> list[dict[str, int]]:
    """Fixed status effects an ability's ``Effects`` list points at.

    The list mixes the effect that tags the consume action with the one that
    actually changes the player, so only entries resolving to a status effect
    with tracked numbers are returned.
    """
    found: list[dict[str, int]] = []
    for block in data:
        props = block.get("Properties") or {}
        for entry in props.get("Effects") or []:
            if not isinstance(entry, dict):
                continue
            stem = _asset_stem(entry.get("AssetPathName", "")).removeprefix("Id_ActorStatusEffect_")
            tracked = fixed_index.get(stem)
            if tracked:
                found.append(tracked)
    # ``Id_ItemEffect_*`` entries only tag the consume action, so they resolve to
    # nothing and drop out here.
    return found


def _item_ability_names(data: list) -> list[str]:
    """Ability asset names an item asset lists under ``Abilities``.

    The asset name is not derived from the item name: a Protection potion is
    ``Id_Item_ProtectionPotion_5001`` but its consume ability is
    ``Id_ItemAbility_ProtectionPotionConsume_5001``, so only the item asset
    itself knows the bridge.
    """
    names: list[str] = []
    for block in data:
        props = block.get("Properties") or {}
        for ref in props.get("Abilities") or []:
            if not isinstance(ref, dict):
                continue
            stem = _asset_stem(ref.get("AssetPathName", "")).removeprefix("Id_ItemAbility_")
            if stem:
                names.append(stem)
    return names


def resolve_item_effects(
    item_names: set[str],
    ability_index: dict[str, dict],
    item_ability_dir: Path,
    fixed_index: dict[str, dict[str, int]] | None = None,
    item_dir: Path | None = None,
) -> dict[str, dict]:
    """Map shop item names to their effect summary via the item's ability asset.

    ``Id_ItemAbility_LuckPotion_5001`` names the ability class
    ``GA_LuckPotion_5001_Consume_C``, which is the bridge to the blueprint.

    Items whose ability carries no weighted roll fall back to the fixed effects
    of its ``Effects`` list — that is how the Protection potions publish their
    shield amount and duration.
    """
    fixed_index = fixed_index if fixed_index is not None else {}
    item_dir = item_dir or ITEM_DIR
    effects: dict[str, dict] = {}
    for name in item_names:
        item_data = _load(item_dir / f"Id_Item_{name}.json")
        if not item_data:
            continue
        ability_names = _item_ability_names(item_data)
        if not ability_names:
            continue
        summary: dict | None = None
        for ability_name in ability_names:
            ability_data = _load(item_ability_dir / f"Id_ItemAbility_{ability_name}.json")
            if not ability_data:
                continue
            # The weighted roll is the primary path (Luck potions); the fixed
            # ``Effects`` list is the fallback (Protection potions).
            class_name = ""
            for block in ability_data:
                props = block.get("Properties") or {}
                class_name = (props.get("Class") or {}).get("ObjectName", "")
                if class_name:
                    break
            if "'" in class_name:
                summary = ability_index.get(class_name.split("'")[1].removesuffix("_C"))
            if summary is None:
                fixed = _ability_effects(ability_data, fixed_index)
                if fixed:
                    merged: dict[str, list[int]] = {}
                    for entry in fixed:
                        for field, value in entry.items():
                            bounds = merged.setdefault(field, [value, value])
                            bounds[0] = min(bounds[0], value)
                            bounds[1] = max(bounds[1], value)
                    summary = {"values": merged, "rolls": []}
            if summary is not None:
                break
        if summary:
            effects[name] = summary
    return effects
