"""Entity enrichment: inject group_drop_info into items/monsters/props JSON files."""

import json
from pathlib import Path

from config import DUNGEON_MODE_NAMES, MODULE_GROUP_FLOOR_SUFFIXES
from drop_rate import _round_rate
from label_type import GOLDCHEST_SPECIAL, LABEL_TYPE_SUFFIX, classify_label

_LABEL_TYPE_SUFFIX = LABEL_TYPE_SUFFIX
_classify_label = classify_label


def _save_entity_files(output_dir: Path, entity_data_by_type: dict[str, dict[str, dict]]) -> None:
    for entity_type, entities in entity_data_by_type.items():
        for name, entity_data in entities.items():
            path = output_dir / entity_type / f"{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entity_data, f, ensure_ascii=False, indent=2)


def enrich_all_entities(
    drop_engine,
    loot_index: list[dict],
    entity_data_by_type: dict[str, dict[str, dict]],
    lootdrop_group_info_by_item: dict[str, dict[str, list[dict]]],
    output_dir: Path,
    log_fn=None,
) -> None:
    """Enrich in-memory entity data, then write each detail file once."""
    spawner_ldg = drop_engine.spawner_ldg
    ore_ldg = drop_engine.ore_ldg
    map_base_to_group = drop_engine.map_base_to_group
    spawn_rate_cache = drop_engine.spawn_rate_cache
    spawn_rate_detail = drop_engine.spawn_rate_detail
    entity_spawners = drop_engine.entity_spawners

    _spawner_ldg_lower: dict[str, str] = {k.lower(): v for k, v in spawner_ldg.items()}

    # ── Update item entities with group_drop_info from the in-memory lootdrop result ──
    if log_fn:
        log_fn("[JSON] updating item entities with group drop info...")
    update_count = 0
    for entry in loot_index:
        iname = entry["name"]
        entity_data = entity_data_by_type["items"].get(iname)
        gdi = lootdrop_group_info_by_item.get(iname)
        if entity_data is None or not gdi:
            continue
        entity_data["group_drop_info"] = gdi
        update_count += 1
    if log_fn:
        log_fn(f"[JSON] updated {update_count} item entities with group drop info")

    # ── Compute group_drop_info for direct-spawn items ──
    if log_fn:
        log_fn("[JSON] computing group_drop_info from ID_LootDropGroup...")
    direct_count = 0
    for iname, entity_data in entity_data_by_type["items"].items():
        ldg_id = spawner_ldg.get(iname, "")
        if not ldg_id:
            continue
        coords = entity_data.get("coords", [])
        if not coords:
            continue
        seen_groups: set[str] = set()
        for c in coords:
            g = map_base_to_group.get(c["map"], "")
            if g:
                seen_groups.add(g)
        if not seen_groups:
            continue
        group_drop_info: dict[str, list[dict]] = {}
        for g in seen_groups:
            suffixes = MODULE_GROUP_FLOOR_SUFFIXES.get(g, [])
            if not suffixes:
                continue
            mode_rates: dict[str, float] = {}
            for mode_id, mode_name in DUNGEON_MODE_NAMES.items():
                best_rate = 0.0
                for suffix in suffixes:
                    full_grade = mode_id * 1000 + suffix
                    rate = drop_engine.compute_drop_rate(ldg_id, iname, full_grade)
                    if rate > best_rate:
                        best_rate = rate
                rate_pct = _round_rate(best_rate * 100)
                if rate_pct > 0:
                    mode_rates[mode_name] = rate_pct
            group_drop_info[g] = [
                {
                    "translation": entity_data["translation"],
                    "translation_key": entity_data.get("translation_key", ""),
                    "spawn_rate": 100,
                    "drop_rates": mode_rates,
                }
            ]
        if group_drop_info:
            entity_data["group_drop_info"] = group_drop_info
            direct_count += 1
    if log_fn:
        log_fn(f"[JSON] computed group_drop_info for {direct_count} direct-spawn items")

    # ── Update monster entities with group_drop_info ──
    if log_fn:
        log_fn("[JSON] updating monster entities with group drop info...")
    mon_update = 0
    for mname, edata in entity_data_by_type["monsters"].items():
        # Find lootdrop_group_id (with suffix fallback)
        ldg_id = spawner_ldg.get(mname, "")
        if not ldg_id:
            for suffix in ("_Elite", "_Nightmare", "_Common"):
                ldg_id = spawner_ldg.get(mname + suffix, "")
                if ldg_id:
                    break
        if not ldg_id:
            ldg_id = _spawner_ldg_lower.get(mname.lower(), "")
        if not ldg_id:
            continue
        coords = edata.get("coords", [])
        if not coords:
            continue
        seen_groups: set[str] = set()
        for c in coords:
            g = map_base_to_group.get(c["map"], "")
            if g:
                seen_groups.add(g)
        if not seen_groups:
            continue
        group_drop_info: dict[str, list[dict]] = {}
        sr = drop_engine.get_combined_spawn_rate(mname)
        if not sr:
            sr = spawn_rate_cache.get(mname, 0.0)
        for g in seen_groups:
            dr = drop_engine.compute_group_drop_rates(ldg_id, g)
            if not dr and not sr:
                continue
            group_drop_info[g] = [
                {
                    "translation": edata["translation"],
                    "translation_key": edata.get("translation_key", ""),
                    "spawn_rate": sr,
                    "drop_rates": dr,
                }
            ]
        if group_drop_info:
            edata["group_drop_info"] = group_drop_info
            mon_update += 1
    if log_fn:
        log_fn(f"[JSON] updated {mon_update} monster entities with group drop info")

    # ── Update props entities with group_drop_info ──
    if log_fn:
        log_fn("[JSON] updating props entities with group drop info...")
    prop_update = 0
    for pname, edata in entity_data_by_type["props"].items():
        # GoldChest_special: synthetic page — rates from GoldChest_UnderSea + ChestSpecial*
        if pname == GOLDCHEST_SPECIAL:
            ldg_id = (
                spawner_ldg.get("GoldChest_UnderSea")
                or spawner_ldg.get("GoldChest")
                or _spawner_ldg_lower.get("goldchest_undersea", "")
                or _spawner_ldg_lower.get("goldchest", "")
            )
            if not ldg_id:
                continue
            coords = edata.get("coords", [])
            if not coords:
                continue
            base_trans = edata["translation"]
            # strip existing (特殊) if present for clean single entry
            if base_trans.endswith("(特殊)"):
                base_trans = base_trans[: -len("(特殊)")]
            special_label = base_trans + _LABEL_TYPE_SUFFIX["special"]
            best_sr = 0.0
            for sk in entity_spawners.get("GoldChest_UnderSea", set()):
                if _classify_label(sk, "GoldChest_UnderSea") != "special":
                    continue
                sr = spawn_rate_detail.get((sk, "GoldChest_UnderSea"), 0)
                if sr > best_sr:
                    best_sr = sr
            if best_sr <= 0:
                best_sr = 17.5
            kw_entries = {
                (True, "special"): {
                    "translation": special_label,
                    "translation_key": edata.get("translation_key", ""),
                    "label_type": "special",
                    "spawn_rate": _round_rate(best_sr),
                }
            }
            seen_groups: set[str] = set()
            for c in coords:
                g = map_base_to_group.get(c["map"], "")
                if g:
                    seen_groups.add(g)
            if not seen_groups:
                continue
            group_drop_info: dict[str, list[dict]] = {}
            for g in seen_groups:
                dr = drop_engine.compute_container_drop_rates(ldg_id, g)
                if not dr:
                    continue
                group_drop_info[g] = [{**entry, "drop_rates": dr} for entry in kw_entries.values()]
            if group_drop_info:
                edata["group_drop_info"] = group_drop_info
                prop_update += 1
            continue

        ldg_id = spawner_ldg.get(pname, "")
        if not ldg_id:
            ldg_id = _spawner_ldg_lower.get(pname.lower(), "")
        if not ldg_id:
            ldg_id = ore_ldg.get(pname, "")
        if not ldg_id:
            continue
        coords = edata.get("coords", [])
        if not coords:
            continue
        # Build per-keyword-type entries: {(is_undersea, type): {translation, spawn_rate}}
        kw_entries: dict[tuple[bool, str], dict] = {}
        locked_name = pname + "_Locked"
        undersea_name = pname + "_UnderSea"
        locked_undersea = pname + "_Locked_UnderSea"
        base_trans = edata["translation"]
        for sk in entity_spawners.get(pname, set()):
            base = spawn_rate_detail.get((sk, pname), 0)
            lock = spawn_rate_detail.get((sk, locked_name), 0) if locked_name in entity_spawners else 0
            combined = _round_rate(base + lock)
            if combined > 0:
                typ = _classify_label(sk, pname)
                # special coords moved to GoldChest_special — skip on base GoldChest page
                if pname == "GoldChest" and typ == "special":
                    continue
                suffix = _LABEL_TYPE_SUFFIX.get(typ, "")
                label = base_trans + suffix + ("(可能上锁)" if lock > 0 else "")
                key = (False, typ)
                if key not in kw_entries or combined > kw_entries[key]["spawn_rate"]:
                    entry = {
                        "translation": label,
                        "translation_key": edata.get("translation_key", ""),
                        "label_type": typ,
                        "may_be_locked": lock > 0,
                        "spawn_rate": combined,
                    }
                    kw_entries[key] = entry
        if undersea_name in entity_spawners:
            for sk in entity_spawners[undersea_name]:
                base = spawn_rate_detail.get((sk, undersea_name), 0)
                lock = spawn_rate_detail.get((sk, locked_undersea), 0) if locked_undersea in entity_spawners else 0
                combined = _round_rate(base + lock)
                if combined > 0:
                    typ = _classify_label(sk, undersea_name)
                    # special → GoldChest_special page only
                    if pname == "GoldChest" and typ == "special":
                        continue
                    suffix = _LABEL_TYPE_SUFFIX.get(typ, "")
                    label = "(海底)" + base_trans + suffix + ("(可能上锁)" if lock > 0 else "")
                    key = (True, typ)
                    if key not in kw_entries or combined > kw_entries[key]["spawn_rate"]:
                        kw_entries[key] = {
                            "translation": label,
                            "translation_key": edata.get("translation_key", ""),
                            "label_prefix": "undersea",
                            "label_type": typ,
                            "may_be_locked": lock > 0,
                            "spawn_rate": combined,
                        }
        if not kw_entries:
            continue
        seen_groups = set()
        for c in coords:
            g = map_base_to_group.get(c["map"], "")
            if g:
                seen_groups.add(g)
        if not seen_groups:
            continue
        group_drop_info = {}
        for g in seen_groups:
            dr = drop_engine.compute_container_drop_rates(ldg_id, g)
            if not dr:
                continue
            group_drop_info[g] = [
                {**entry, "drop_rates": dr}
                for entry in sorted(kw_entries.values(), key=lambda e: e["spawn_rate"], reverse=True)
            ]
        if group_drop_info:
            edata["group_drop_info"] = group_drop_info
            prop_update += 1
    if log_fn:
        log_fn(f"[JSON] updated {prop_update} props entities with group drop info")

    # ── Cleanup: remove all zero-rate entries ──
    if log_fn:
        log_fn("[JSON] cleaning up zero-rate entries...")
    clean_count = 0
    for entities in entity_data_by_type.values():
        for edata in entities.values():
            gdi = edata.get("group_drop_info")
            if not gdi:
                continue
            changed = False
            new_gdi: dict[str, list[dict]] = {}
            for g, entries in gdi.items():
                filtered = [
                    e
                    for e in entries
                    if e.get("spawn_rate", 0) > 0 or any(v > 0 for v in e.get("drop_rates", {}).values())
                ]
                if filtered:
                    new_gdi[g] = filtered
                if len(filtered) != len(entries):
                    changed = True
            if changed:
                if new_gdi:
                    edata["group_drop_info"] = new_gdi
                else:
                    del edata["group_drop_info"]
                clean_count += 1
    _save_entity_files(output_dir, entity_data_by_type)
    if log_fn:
        log_fn(f"[JSON] cleaned {clean_count} files with zero-rate entries")
