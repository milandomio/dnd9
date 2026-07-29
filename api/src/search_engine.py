import re

_VARIANT_RE = re.compile(r"_\d{4}$")
_QUALITY_RE = re.compile(r"_(Common|Elite|Nightmare|Unique)$")
_HARD_SUFFIX_RE = re.compile(r"_(Hard|VeryHard)$")
_LOOTDROP_GROUP_PREFIXES = ("ID_LootDropGroup_", "Id_LootDropGroup_")


def strip_variant_suffixes(name: str) -> str:
    result = _QUALITY_RE.sub("", name)
    result = _HARD_SUFFIX_RE.sub("", result)
    return _VARIANT_RE.sub("", result)


def load_all_spawner_data(
    db,
    monster_name_map: dict[str, str] | None = None,
) -> tuple[dict[str, bool], dict[str, list[dict]], dict[str, list[str]]]:
    """Build spawner lookup maps from the preloaded DB tables."""
    keyword_has_lootdrop: dict[str, bool] = {}
    multi_entity: dict[str, list[dict]] = {}
    ldg_to_monsters: dict[str, set[str]] = {}

    entries = db.get_all_spawner_entries()
    monster_names = {row["monster_name"] for row in db.get_monster_entities()}
    props_names = {row["asset_name"] for row in db.get_props_entities()}
    grouped: dict[str, list[dict]] = {}
    for row in entries:
        keyword = row["spawner_keyword"]
        if not keyword:
            continue
        keyword_base = strip_variant_suffixes(keyword)
        has_lootdrop = bool(row["lootdrop_group_id"])
        keyword_has_lootdrop[keyword_base] = keyword_has_lootdrop.get(keyword_base, False) or has_lootdrop
        if not has_lootdrop:
            continue
        grouped.setdefault(keyword, []).append(row)
        entity_name = row["entity_name"]
        if entity_name:
            canonical = (monster_name_map or {}).get(entity_name.lower())
            if not canonical:
                stripped = strip_variant_suffixes(entity_name)
                canonical = (monster_name_map or {}).get(stripped.lower(), entity_name)
            ldg_name = row["lootdrop_group_id"]
            for prefix in _LOOTDROP_GROUP_PREFIXES:
                if ldg_name.startswith(prefix):
                    ldg_name = ldg_name[len(prefix) :]
                    break
            ldg_to_monsters.setdefault(ldg_name, set()).add(canonical)

    for keyword, keyword_entries in grouped.items():
        entity_names = {strip_variant_suffixes(row["entity_name"]) for row in keyword_entries if row["entity_name"]}
        need_expand = len(entity_names) >= 2
        need_redirect = len(entity_names) == 1 and keyword != next(iter(entity_names))
        if need_redirect and keyword.startswith("SuperHoard"):
            need_redirect = False
        if not (need_expand or need_redirect):
            continue

        expanded = []
        for row in keyword_entries:
            entity_name = strip_variant_suffixes(row["entity_name"])
            if not entity_name:
                continue
            spawner_type = (
                "monster" if entity_name in monster_names else "props" if entity_name in props_names else "unknown"
            )
            expanded.append(
                {
                    "entity_name": entity_name,
                    "spawn_rate": min(row["spawn_rate"], 100.0),
                    "spawner_type": spawner_type,
                    "lootdrop_group_id": row["lootdrop_group_id"],
                }
            )
        if expanded:
            multi_entity[keyword] = expanded

    return keyword_has_lootdrop, multi_entity, {key: sorted(value) for key, value in ldg_to_monsters.items()}
