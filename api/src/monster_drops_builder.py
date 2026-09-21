"""Build loot_pools for monster and props detail JSON."""

from __future__ import annotations

import json

from translator import ORE_QUALITY_RE, QUALITY_RE, VARIANT_RE

_LOOTDROP_PREFIXES = ("Id_Lootdrop_", "ID_Lootdrop_")
_LUCK_TO_SUFFIX = {n: f"{n}001" for n in range(1, 9)}
_CONSUMABLE_SUBTYPE = "Text_Code_DCDataBlueprintLibrary_Type_Item_Utility_Consumable"


def fold_item_page(item_name: str) -> tuple[str, str | None]:
    """Map a rate-table item name to the lootdrop JSON filename and suffix."""
    match = VARIANT_RE.match(item_name)
    if not match:
        return item_name, None
    suffix = match.group(0).rsplit("_", 1)[-1]
    if suffix == "8001":
        return item_name, suffix
    return match.group(1), suffix


def lootdrop_stem(lootdrop_id: str) -> str:
    lower = lootdrop_id.lower()
    for prefix in _LOOTDROP_PREFIXES:
        if lower.startswith(prefix.lower()):
            return lootdrop_id[len(prefix) :]
    return lootdrop_id


def is_quest_pool(lootdrop_id: str) -> bool:
    stem = lootdrop_stem(lootdrop_id)
    return stem.startswith("Quest_") or stem.startswith("QuestSpecial_")


def is_event_currency_pool(lootdrop_id: str) -> bool:
    stem = lootdrop_stem(lootdrop_id)
    return "EventCurrency" in stem


def canonical_monster_name(entity_name: str, monster_names: set[str]) -> str:
    stripped = QUALITY_RE.sub("", entity_name)
    if stripped in monster_names:
        return stripped
    if entity_name in monster_names:
        return entity_name
    lower_map = {name.lower(): name for name in monster_names}
    return lower_map.get(stripped.lower()) or lower_map.get(entity_name.lower()) or stripped


def canonical_entity_name(entity_name: str, entity_names: set[str], *, fold_quality: bool) -> str:
    if fold_quality:
        return canonical_monster_name(entity_name, entity_names)
    lower_map = {name.lower(): name for name in entity_names}
    candidates: list[str] = [entity_name]
    stripped = QUALITY_RE.sub("", entity_name)
    if stripped != entity_name:
        candidates.append(stripped)
    ore = ORE_QUALITY_RE.match(entity_name)
    if ore:
        base = ore.group(1)
        candidates.extend([base, f"Ore_{base}"])
    for cand in candidates:
        if cand in entity_names:
            return cand
        hit = lower_map.get(cand.lower())
        if hit:
            return hit
    return entity_name


def _item_sort_key(item: dict) -> tuple[int, str]:
    suffix = item.get("suffix")
    if suffix and suffix.isdigit():
        rank = int(suffix)
    else:
        luck = int(item.get("luck_grade") or 0)
        rank = int(_LUCK_TO_SUFFIX.get(luck, "0"))
    return (-rank, item.get("translation") or item.get("page") or "")


def _resolve_item_text(
    item_name: str, page: str, translations: dict[str, str], item_keys: dict[str, str]
) -> tuple[str, str]:
    direct_key = f"Text_DesignData_Item_Item_{item_name}"
    if direct_key in translations:
        return translations[direct_key], direct_key
    for lookup in (page, VARIANT_RE.sub(r"\1", page) if VARIANT_RE.match(page) else None):
        if not lookup:
            continue
        key = item_keys.get(lookup, "")
        if key:
            return translations.get(key, lookup), key
    return page, ""


def _dedupe_items(items: list[dict]) -> list[dict]:
    by_page: dict[str, dict] = {}
    for item in items:
        existing = by_page.get(item["page"])
        if existing is None or int(item.get("luck_grade") or 0) > int(existing.get("luck_grade") or 0):
            by_page[item["page"]] = item
    return sorted(by_page.values(), key=_item_sort_key)


def monster_map_groups(entity: dict, map_base_to_group: dict[str, str]) -> set[str]:
    groups: set[str] = set()
    for coord in entity.get("coords") or []:
        map_name = coord.get("map") or ""
        group = map_base_to_group.get(map_name, "")
        if group:
            groups.add(group)
    return groups


def item_is_consumable(item: dict, item_subtypes: dict[str, set[str]]) -> bool:
    for key in (item.get("name"), item.get("page")):
        if key and _CONSUMABLE_SUBTYPE in item_subtypes.get(key, set()):
            return True
    return False


def item_has_positive_rate(drop_engine, item_name: str, monster_name: str, group_keys: set[str]) -> bool:
    """True if any mode on any of the monster's map groups has drop rate > 0."""
    if not group_keys:
        return True
    for group_key in group_keys:
        rates = drop_engine.get_group_drop_rates(item_name, monster_name, group_key) or {}
        if any(value > 0 for value in rates.values()):
            return True
    return False


def build_loot_pools(
    *,
    monster_names: set[str],
    rows: list[tuple[str, str, str, int]],
    translations: dict[str, str],
    item_keys: dict[str, str],
    drop_engine=None,
    monster_groups: dict[str, set[str]] | None = None,
    fold_quality: bool = True,
    item_subtypes: dict[str, set[str]] | None = None,
) -> dict[str, list[dict]]:
    """rows: (entity_name, lootdrop_id, item_name, luck_grade)."""
    subtypes = item_subtypes or {}
    grouped: dict[str, dict[str, list[dict]]] = {}
    rate_ok: dict[tuple[str, str], bool] = {}
    for entity_name, lootdrop_id, item_name, luck_grade in rows:
        if not entity_name or not lootdrop_id or not item_name:
            continue
        canonical = canonical_entity_name(entity_name, monster_names, fold_quality=fold_quality)
        if canonical not in monster_names:
            continue
        if drop_engine is not None:
            cache_key = (item_name, entity_name)
            ok = rate_ok.get(cache_key)
            if ok is None:
                groups = (monster_groups or {}).get(canonical, set())
                ok = item_has_positive_rate(drop_engine, item_name, entity_name, groups)
                rate_ok[cache_key] = ok
            if not ok:
                continue
        page, suffix = fold_item_page(item_name)
        translation, translation_key = _resolve_item_text(item_name, page, translations, item_keys)
        grouped.setdefault(canonical, {}).setdefault(lootdrop_id, []).append(
            {
                "name": item_name,
                "page": page,
                "translation": translation,
                "translation_key": translation_key,
                "suffix": suffix,
                "luck_grade": int(luck_grade or 0),
            }
        )

    result: dict[str, list[dict]] = {}
    for monster, pools in grouped.items():
        quest_items: list[dict] = []
        artifact_items: list[dict] = []
        consumable_items: list[dict] = []
        other: list[tuple[str, list[dict]]] = []
        for lootdrop_id, items in pools.items():
            if is_event_currency_pool(lootdrop_id):
                continue
            if is_quest_pool(lootdrop_id):
                quest_items.extend(items)
                continue
            remaining = []
            for item in items:
                if item.get("suffix") == "8001" or (item.get("page") or "").endswith("_8001"):
                    artifact_items.append(item)
                else:
                    remaining.append(item)
            if not remaining:
                continue
            remaining_deduped = _dedupe_items(remaining)
            if len(remaining_deduped) == 1 and item_is_consumable(remaining_deduped[0], subtypes):
                consumable_items.extend(remaining)
                continue
            other.append((lootdrop_id, remaining))

        loot_pools: list[dict] = []
        quest_deduped = _dedupe_items(quest_items)
        if quest_deduped:
            loot_pools.append({"id": "quest", "kind": "quest", "lootdrop_id": None, "items": quest_deduped})
        artifact_deduped = _dedupe_items(artifact_items)
        if artifact_deduped:
            loot_pools.append({"id": "artifact", "kind": "artifact", "lootdrop_id": None, "items": artifact_deduped})
        consumable_deduped = _dedupe_items(consumable_items)
        if consumable_deduped:
            loot_pools.append(
                {"id": "consumable", "kind": "consumable", "lootdrop_id": None, "items": consumable_deduped}
            )
        other.sort(key=lambda pair: lootdrop_stem(pair[0]).lower())
        for lootdrop_id, items in other:
            loot_pools.append(
                {
                    "id": lootdrop_id,
                    "kind": "pool",
                    "lootdrop_id": lootdrop_id,
                    "items": _dedupe_items(items),
                }
            )
        if loot_pools:
            result[monster] = loot_pools
    return result


def load_drop_rows(db) -> list[tuple[str, str, str, int]]:
    cursor = db.connect().execute("""
        SELECT se.entity_name, lg.lootdrop_id, r.item_name, MAX(r.luck_grade) AS luck_grade
        FROM spawner_entries se
        JOIN lootdrop_groups lg ON lg.group_id = se.lootdrop_group_id
        JOIN lootdrop_rate_items r ON r.lootdrop_id = lg.lootdrop_id
        WHERE se.entity_name != '' AND se.lootdrop_group_id != ''
        GROUP BY se.entity_name, lg.lootdrop_id, r.item_name
        """)
    return [(row["entity_name"], row["lootdrop_id"], row["item_name"], int(row["luck_grade"] or 0)) for row in cursor]


def load_item_keys(db) -> dict[str, str]:
    return {
        row["item_name"]: row["translation_key"]
        for row in db.connect().execute("SELECT item_name, translation_key FROM item_entities")
    }


def load_item_subtypes(db) -> dict[str, set[str]]:
    subtypes: dict[str, set[str]] = {}
    for row in db.connect().execute("SELECT item_name, item_subtype_keys FROM item_entities"):
        raw = row["item_subtype_keys"] or "[]"
        try:
            keys = json.loads(raw)
        except json.JSONDecodeError:
            keys = []
        subtypes[row["item_name"]] = {str(key) for key in keys if key}
    return subtypes


def attach_loot_pools(
    monster_data: dict[str, dict],
    db,
    translations: dict[str, str],
    drop_engine=None,
    *,
    fold_quality: bool = True,
) -> int:
    """Inject loot_pools onto in-memory detail dicts. Returns entity count updated."""
    if not monster_data:
        return 0
    map_base_to_group = drop_engine.map_base_to_group if drop_engine is not None else {}
    monster_groups = {name: monster_map_groups(entity, map_base_to_group) for name, entity in monster_data.items()}
    pools = build_loot_pools(
        monster_names=set(monster_data),
        rows=load_drop_rows(db),
        translations=translations,
        item_keys=load_item_keys(db),
        item_subtypes=load_item_subtypes(db),
        drop_engine=drop_engine,
        monster_groups=monster_groups,
        fold_quality=fold_quality,
    )
    updated = 0
    for name, entity in monster_data.items():
        loot_pools = pools.get(name)
        if loot_pools:
            entity["loot_pools"] = loot_pools
            updated += 1
        else:
            entity.pop("loot_pools", None)
    return updated
