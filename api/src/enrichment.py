"""Entity enrichment: inject group_drop_info into items/monsters/props JSON files."""

import json
from pathlib import Path

from config import DUNGEON_MODE_NAMES, MODULE_GROUP_FLOOR_SUFFIXES
from drop_rate import _round_rate
from lootdrop_builder import _LABEL_TYPE_SUFFIX, _classify_label


def enrich_all_entities(
    drop_engine,
    loot_index: list[dict],
    output_dir: Path,
    log_fn=None,
) -> None:
    """Inject group_drop_info into all entity JSON files and clean zero-rate entries."""
    spawner_ldg = drop_engine.spawner_ldg
    ore_ldg = drop_engine.ore_ldg
    map_base_to_group = drop_engine.map_base_to_group
    spawn_rate_cache = drop_engine.spawn_rate_cache
    spawn_rate_detail = drop_engine.spawn_rate_detail
    entity_spawners = drop_engine.entity_spawners

    # ── Update item entities with group_drop_info from lootdrop files ──
    if log_fn:
        log_fn("[JSON] updating item entities with group drop info...")
    update_count = 0
    for entry in loot_index:
        iname = entry["name"]
        loot_path = output_dir / f"lootdrops/{iname}.json"
        if not loot_path.exists():
            continue
        with open(loot_path) as f:
            loot_data = json.load(f)
        gdi = loot_data.get("group_drop_info", {})
        if not gdi:
            continue
        entity_path = output_dir / f"items/{iname}.json"
        if not entity_path.exists():
            continue
        with open(entity_path) as f:
            entity_data = json.load(f)
        entity_data["group_drop_info"] = gdi
        with open(entity_path, "w") as f:
            json.dump(entity_data, f, ensure_ascii=False, indent=2)
        update_count += 1
    if log_fn:
        log_fn(f"[JSON] updated {update_count} item entities with group drop info")

    # ── Compute group_drop_info for direct-spawn items ──
    if log_fn:
        log_fn("[JSON] computing group_drop_info from ID_LootDropGroup...")
    direct_count = 0
    for item_file in (output_dir / "items").glob("*.json"):
        with open(item_file) as f:
            entity_data = json.load(f)
        iname = entity_data["name"]
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
                if mode_id == 4:
                    continue
                best_rate = 0.0
                for suffix in suffixes:
                    full_grade = mode_id * 1000 + suffix
                    rate = drop_engine.compute_drop_rate(ldg_id, iname, full_grade)
                    if rate > best_rate:
                        best_rate = rate
                mode_rates[mode_name] = _round_rate(best_rate * 100)
            group_drop_info[g] = [
                {
                    "translation": entity_data["translation"],
                    "spawn_rate": 100,
                    "drop_rates": mode_rates,
                }
            ]
        if group_drop_info:
            entity_data["group_drop_info"] = group_drop_info
            with open(item_file, "w") as f:
                json.dump(entity_data, f, ensure_ascii=False, indent=2)
            direct_count += 1
    if log_fn:
        log_fn(f"[JSON] computed group_drop_info for {direct_count} direct-spawn items")

    # ── Update monster entities with group_drop_info ──
    if log_fn:
        log_fn("[JSON] updating monster entities with group drop info...")
    mon_update = 0
    for mfile in (output_dir / "monsters").glob("*.json"):
        with open(mfile) as f:
            edata = json.load(f)
        mname = edata["name"]
        # Find lootdrop_group_id (with suffix fallback)
        ldg_id = spawner_ldg.get(mname, "")
        if not ldg_id:
            for suffix in ("_Elite", "_Nightmare", "_Common"):
                ldg_id = spawner_ldg.get(mname + suffix, "")
                if ldg_id:
                    break
        if not ldg_id:
            lower = mname.lower()
            for k, v in spawner_ldg.items():
                if k.lower() == lower:
                    ldg_id = v
                    break
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
        sr = spawn_rate_cache.get(mname, 0.0)
        for g in seen_groups:
            dr = drop_engine.compute_group_drop_rates(ldg_id, g)
            if not dr and not sr:
                continue
            group_drop_info[g] = [
                {
                    "translation": edata["translation"],
                    "spawn_rate": sr,
                    "drop_rates": dr,
                }
            ]
        if group_drop_info:
            edata["group_drop_info"] = group_drop_info
            with open(mfile, "w") as f:
                json.dump(edata, f, ensure_ascii=False, indent=2)
            mon_update += 1
    if log_fn:
        log_fn(f"[JSON] updated {mon_update} monster entities with group drop info")

    # ── Update props entities with group_drop_info ──
    if log_fn:
        log_fn("[JSON] updating props entities with group drop info...")
    prop_update = 0
    for pfile in (output_dir / "props").glob("*.json"):
        with open(pfile) as f:
            edata = json.load(f)
        pname = edata["name"]
        ldg_id = spawner_ldg.get(pname, "")
        if not ldg_id:
            lower = pname.lower()
            for k, v in spawner_ldg.items():
                if k.lower() == lower:
                    ldg_id = v
                    break
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
            combined = base + lock
            if combined > 0:
                typ = _classify_label(sk, pname)
                suffix = _LABEL_TYPE_SUFFIX.get(typ, "")
                label = base_trans + suffix + ("(可能上锁)" if lock > 0 else "")
                key = (False, typ)
                if key not in kw_entries or combined > kw_entries[key]["spawn_rate"]:
                    kw_entries[key] = {"translation": label, "spawn_rate": combined}
        if undersea_name in entity_spawners:
            for sk in entity_spawners[undersea_name]:
                base = spawn_rate_detail.get((sk, undersea_name), 0)
                lock = spawn_rate_detail.get((sk, locked_undersea), 0) if locked_undersea in entity_spawners else 0
                combined = base + lock
                if combined > 0:
                    typ = _classify_label(sk, undersea_name)
                    suffix = _LABEL_TYPE_SUFFIX.get(typ, "")
                    label = "(海底)" + base_trans + suffix + ("(可能上锁)" if lock > 0 else "")
                    key = (True, typ)
                    if key not in kw_entries or combined > kw_entries[key]["spawn_rate"]:
                        kw_entries[key] = {"translation": label, "spawn_rate": combined}
        if not kw_entries:
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
            dr = drop_engine.compute_container_drop_rates(ldg_id, g)
            if not dr:
                continue
            group_drop_info[g] = [
                {**entry, "drop_rates": dr}
                for entry in sorted(kw_entries.values(), key=lambda e: e["spawn_rate"], reverse=True)
            ]
        if group_drop_info:
            edata["group_drop_info"] = group_drop_info
            with open(pfile, "w") as f:
                json.dump(edata, f, ensure_ascii=False, indent=2)
            prop_update += 1
    if log_fn:
        log_fn(f"[JSON] updated {prop_update} props entities with group drop info")

    # ── Cleanup: remove all zero-rate entries ──
    if log_fn:
        log_fn("[JSON] cleaning up zero-rate entries...")
    clean_count = 0
    for subdir in ("items", "props", "monsters"):
        for efile in (output_dir / subdir).glob("*.json"):
            with open(efile) as f:
                edata = json.load(f)
            gdi = edata.get("group_drop_info")
            if not gdi:
                continue
            changed = False
            new_gdi: dict[str, list[dict]] = {}
            for g, entries in gdi.items():
                filtered = [e for e in entries if any(v > 0 for v in e.get("drop_rates", {}).values())]
                if filtered:
                    new_gdi[g] = filtered
                if len(filtered) != len(entries):
                    changed = True
            if changed:
                if new_gdi:
                    edata["group_drop_info"] = new_gdi
                else:
                    del edata["group_drop_info"]
                with open(efile, "w") as f:
                    json.dump(edata, f, ensure_ascii=False, indent=2)
                clean_count += 1
    if log_fn:
        log_fn(f"[JSON] cleaned {clean_count} files with zero-rate entries")
