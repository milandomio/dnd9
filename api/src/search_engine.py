import json
import os
import re
from pathlib import Path

import ahocorasick

from config import MAPS_DIR, SPAWNER_ALIAS_MAP, SPAWNER_DIR

_VARIANT_RE = re.compile(r"_\d{4}$")

# Cache for spawner data asset info (keyword → has_lootdrop)
_spawner_data_cache: dict[str, bool] = {}


def _load_spawner_data_assets() -> dict[str, bool]:
    """Load all DCSpawnerDataAsset files and build mapping of keyword → has_lootdrop."""
    global _spawner_data_cache
    if _spawner_data_cache:
        return _spawner_data_cache

    if not SPAWNER_DIR.exists():
        return _spawner_data_cache

    for json_file in SPAWNER_DIR.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if not isinstance(data, list) or not data:
            continue

        entry = data[0]
        if entry.get("Type") != "DCSpawnerDataAsset":
            continue

        name = entry.get("Name", "")
        if not name:
            continue

        # Extract keyword from name (e.g., "Id_Spawner_Props_FiredeepTorch01On" → "FiredeepTorch01On")
        keyword = strip_id_prefix(name)
        if not keyword:
            continue

        # Check if LootDropGroupId is non-empty
        props = entry.get("Properties", {}) or {}
        items = props.get("SpawnerItemArray", []) or []
        has_lootdrop = False
        for item in items:
            ldg = item.get("LootDropGroupId", {}) or {}
            asset_path = ldg.get("AssetPathName", "")
            if asset_path:
                has_lootdrop = True
                break

        _spawner_data_cache[keyword] = has_lootdrop

    return _spawner_data_cache


def _ue_asset_base_name(asset_path: str) -> str:
    """Extract base name from UE asset path like '/Game/.../Id_Foo.Id_Foo' → 'Id_Foo'."""
    if not asset_path:
        return ""
    part = asset_path.rsplit("/", 1)[-1]
    if "." in part:
        part = part.split(".")[0]
    return part


def _load_multi_entity_spawners() -> dict[str, list[dict]]:
    """Build mapping of spawner keywords → entity details for expansion/redirect.

    Returns: {keyword: [{"entity_name": str, "spawn_rate": int, "spawner_type": str,
                         "lootdrop_group_id": str}, ...]}
    - Multi-entity spawners (≥2 entities with LootDropGroupId) → expand to each entity
    - Single-entity spawners where keyword ≠ entity_name → redirect keyword to entity_name
    """
    result: dict[str, list[dict]] = {}
    if not SPAWNER_DIR.exists():
        return result

    for json_file in SPAWNER_DIR.glob("*.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, list) or not data:
            continue
        entry = data[0]
        if entry.get("Type") != "DCSpawnerDataAsset":
            continue
        name = entry.get("Name", "")
        if not name:
            continue
        keyword = strip_id_prefix(name)
        if not keyword:
            continue

        props = entry.get("Properties", {}) or {}
        items = props.get("SpawnerItemArray", []) or []

        # Only count items with LootDropGroupId (meaningful spawn entries)
        active_items = [item for item in items if (item.get("LootDropGroupId", {}) or {}).get("AssetPathName", "")]
        if not active_items:
            continue

        entities: set[str] = set()
        for item in active_items:
            entity_name = ""
            for id_key in ("MonsterId", "PropsId"):
                id_path = (item.get(id_key, {}) or {}).get("AssetPathName", "")
                if id_path:
                    raw = _ue_asset_base_name(id_path) or ""
                    entity_name = raw.removeprefix("Id_Monster_").removeprefix("Id_Props_")
                    break
            if entity_name:
                entities.add(entity_name)

        if not entities:
            continue

        need_expand = len(entities) >= 2
        need_redirect = len(entities) == 1 and keyword != next(iter(entities))

        if not need_expand and not need_redirect:
            continue

        # Build entry list
        entries: list[dict] = []
        total_rate = sum(it.get("SpawnRate", 10000) for it in active_items)
        if total_rate <= 0:
            total_rate = 1

        for item in active_items:
            entity_name = ""
            spawner_type = ""
            for id_key in ("MonsterId", "PropsId"):
                id_path = (item.get(id_key, {}) or {}).get("AssetPathName", "")
                if id_path:
                    raw = _ue_asset_base_name(id_path) or ""
                    entity_name = raw.removeprefix("Id_Monster_").removeprefix("Id_Props_")
                    if "/V2/Monster/" in id_path:
                        spawner_type = "monster"
                    elif "/V2/Props/" in id_path:
                        spawner_type = "props"
                    break
            if not entity_name:
                continue
            raw_rate = item.get("SpawnRate", 10000)
            spawn_rate = round(raw_rate / total_rate * 100)
            ldg = item.get("LootDropGroupId", {}) or {}
            ldg_path = ldg.get("AssetPathName", "")
            ldg_id = _ue_asset_base_name(ldg_path) if ldg_path else ""
            entries.append(
                {
                    "entity_name": entity_name,
                    "spawn_rate": spawn_rate,
                    "spawner_type": spawner_type,
                    "lootdrop_group_id": ldg_id,
                }
            )
        if entries:
            result[keyword] = entries

    return result


_PREFIXES = [
    "DCSpawnerDataAsset'Id_Spawner_New_Monster_",
    "DCSpawnerDataAsset'Id_Spawner_New_Props_",
    "DCSpawnerDataAsset'Id_Spawner_New_LootDrop_",
    "DCSpawnerDataAsset'Id_Spawner_Monster_",
    "DCSpawnerDataAsset'Id_Spawner_Props_",
    "DCSpawnerDataAsset'Id_Spawner_LootDrop_",
    "DCSpawnerDataAsset'Id_Spawner_New_Lootdrop_",
    "DCSpawnerDataAsset'Id_Spawner_Lootdrop_",
    "DCSpawnerDataAsset'Id_Spawner_New_NPC_",
    "DCSpawnerDataAsset'Id_Spawner_NPC_",
    "DCSpawnerDataAsset'",
    "Id_Spawner_New_Monster_",
    "Id_Spawner_New_Props_",
    "Id_Spawner_New_LootDrop_",
    "Id_Spawner_New_NPC_",
    "Id_Spawner_Monster_",
    "Id_Spawner_Props_",
    "Id_Spawner_LootDrop_",
    "Id_Spawner_Lootdrop_",
    "Spawn_",
    "Spawner_New_",
]

_SUFFIXES = [
    "_Elite",
    "_Random",
    "_2type",
    "_3type",
    "_4type",
    "_5type",
]


def strip_id_prefix(name: str) -> str:
    result = name
    changed = True
    while changed:
        changed = False
        for prefix in _PREFIXES:
            if result.startswith(prefix):
                result = result[len(prefix) :].rstrip("'\"")
                changed = True
                break
        if not changed and result.startswith("Id_"):
            result = result[3:]
            changed = True
    for suffix in _SUFFIXES:
        if result.endswith(suffix):
            result = result[: -len(suffix)]
    return result


def _preview_type(asset_path: str) -> str:
    if "/V2/Monster/" in asset_path:
        return "monster"
    if "/V2/Props/" in asset_path:
        return "props"
    if "/V2/LootDrop/" in asset_path:
        return "lootdrop"
    return "unknown"


def _preview_entity_name(asset_path: str) -> str:
    """Extract entity name from PreviewData.AssetPathName.
    e.g., /Game/.../Id_Props_StatueDwarven.Id_Props_StatueDwarven -> StatueDwarven
    """
    if not asset_path:
        return ""
    # Extract filename from path
    parts = asset_path.rstrip("/").split("/")
    if not parts:
        return ""
    filename = parts[-1]
    # Remove duplicate suffix (e.g., Id_Props_StatueDwarven.Id_Props_StatueDwarven -> Id_Props_StatueDwarven)
    if "." in filename:
        filename = filename.split(".")[0]
    # Strip Id_Props_, Id_Monster_, Id_LootDrop_ prefixes
    for prefix in ["Id_Props_", "Id_Monster_", "Id_LootDrop_", "Id_Spawner_New_", "Id_Spawner_"]:
        if filename.startswith(prefix):
            filename = filename[len(prefix) :]
            break
    return filename


def _sl_base_name(name: str) -> str:
    for suffix in ["_HR_D", "_D", "_A"]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _extract_actor_name(outer_str: str) -> str:
    if "'" in outer_str:
        parts = outer_str.split("'")
        last_part = parts[-2] if len(parts) > 2 and parts[-1] == "" else parts[-1]
        if "." in last_part:
            return last_part.split(".")[-1]
        return last_part
    return outer_str


def _strip_bp_prefix(bp_type: str) -> str:
    """Strip BP_ prefix and _C suffix from entity type name."""
    name = bp_type
    if name.startswith("BP_"):
        name = name[3:]
    if name.endswith("_C"):
        name = name[:-2]
    # Strip trailing _ice, _01, _02 etc. numeric suffix for matching
    # But keep meaningful suffixes like _Crypt, _Soulflame
    return name


def _list_map_jsons(root: str | Path) -> list[Path]:
    root = Path(root)
    if not root.exists():
        return []
    files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(("_HR_D.json", "_D.json", "_A.json")):
                continue
            if "_SR" in fn or "_BossTest" in fn or "_Resize" in fn or "_Test" in fn:
                continue
            if "Arena" in fn or "ArenaStart" in dirpath:
                continue
            if fn in ("Ruins_Passage_Outer_11_D.json",):
                continue
                continue
            files.append(Path(dirpath) / fn)
    return sorted(files)


def extract_spawners(
    map_json_path: Path,
    multi_entity_spawners: dict[str, list[dict]] | None = None,
) -> list[dict]:
    try:
        with open(map_json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    spawners: dict[str, dict] = {}
    scene: dict[str, dict] = {}

    if multi_entity_spawners is None:
        multi_entity_spawners = {}

    # Load spawner data assets for lootdrop info
    spawner_data_map = _load_spawner_data_assets()

    # Collect all scene-component-like entries for parent-chain resolution
    _sc_entries: list[tuple[int, dict]] = []  # (array_index, entry)
    _scene_comp_types = {"SphereComponent", "SceneComponent"}
    _ap_suffix_re = re.compile(r"\.(\d+)'?$")

    # Build map from DefaultSceneRoot entry index → BP_GameSpawnerGroup_C name
    group_root_to_name: dict[int, str] = {}
    for _idx, entry in enumerate(data):
        if entry.get("Type") == "BP_GameSpawnerGroup_C":
            props = entry.get("Properties", {}) or {}
            root = props.get("RootComponent", {}) or {}
            op = root.get("ObjectPath", "")
            m = _ap_suffix_re.search(op) if op else None
            if m:
                group_root_to_name[int(m.group(1))] = entry.get("Name", "")

    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue
        t = entry.get("Type", "")

        if t == "BP_GameSpawner_C":
            props = entry.get("Properties", {}) or {}
            sd = props.get("SpawnerDataAsset", {}) or {}
            raw_obj = sd.get("ObjectName", "")
            keyword = strip_id_prefix(raw_obj)
            if not keyword:
                continue
            pd = props.get("PreviewData", {}) or {}
            asset_path = pd.get("AssetPathName", "")
            spawner_type = _preview_type(asset_path)
            preview_name = _preview_entity_name(asset_path)
            spawner_name = entry.get("Name", "")
            # Check if this spawner has lootdrop from spawner data asset
            has_lootdrop = spawner_data_map.get(keyword, False)
            if spawner_name:
                spawners[spawner_name] = {
                    "keyword": keyword,
                    "spawner_type": spawner_type,
                    "preview_name": preview_name,
                    "has_lootdrop": has_lootdrop,
                }

        elif t.startswith("BP_") and t.endswith("_C") and t not in ("BP_GameSpawner_C",):
            entry_name = entry.get("Name", "")
            if entry_name:
                spawners[entry_name] = {
                    "keyword": _strip_bp_prefix(t),
                    "spawner_type": "props",
                    "has_lootdrop": False,
                }

        if t in _scene_comp_types and entry.get("Name") in (
            "SceneComponent",
            "RootScene",
            "DefaultSceneRoot",
        ):
            _sc_entries.append((idx, entry))

    # Build scene coords with AttachParent chain resolution
    _ap_suffix_re = re.compile(r"\.(\d+)'?$")

    def _resolve_world_loc(start_idx: int) -> tuple[float, float, float, float, str]:
        """Walk up AttachParent chain to compute world-space x, y, z, yaw and group name."""
        x = y = z = 0.0
        yaw_total = 0.0
        group_name = ""
        visited: set[int] = set()
        cur = start_idx
        while cur >= 0 and cur not in visited:
            visited.add(cur)
            if cur >= len(data):
                break
            if cur in group_root_to_name:
                group_name = group_root_to_name[cur]
            entry = data[cur]
            props = entry.get("Properties", {}) or {}
            loc = props.get("RelativeLocation", {}) or {}
            rot = props.get("RelativeRotation", {}) or {}
            x += loc.get("X", 0)
            y += loc.get("Y", 0)
            z += loc.get("Z", 0)
            yaw_total += rot.get("Yaw", 0)
            ap = props.get("AttachParent", {}) or {}
            ap_path = ap.get("ObjectPath", "")
            m = _ap_suffix_re.search(ap_path)
            cur = int(m.group(1)) if m else -1
        return x, y, z, yaw_total, group_name

    for idx, entry in _sc_entries:
        outer_raw = entry.get("Outer", "")
        if isinstance(outer_raw, dict):
            outer_raw = (outer_raw or {}).get("ObjectName", "")
        if not outer_raw or not isinstance(outer_raw, str):
            continue
        actor_name = _extract_actor_name(outer_raw)
        if not actor_name:
            continue
        props = entry.get("Properties", {}) or {}
        ap = props.get("AttachParent", {}) or {}
        if ap and ap.get("ObjectPath"):
            # Has parent: resolve world coords by walking up the chain
            wx, wy, wz, wyaw, group_name = _resolve_world_loc(idx)
            scene[actor_name] = {
                "x": wx,
                "y": wy,
                "z": wz,
                "yaw": round(wyaw % 360, 1),
                "group_parent": group_name,
            }
        else:
            # No parent: use RelativeLocation directly
            loc = props.get("RelativeLocation", {}) or {}
            rot = props.get("RelativeRotation", {}) or {}
            yaw_deg = rot.get("Yaw", 0)
            yaw = round(yaw_deg % 360, 1)
            scene[actor_name] = {
                "x": loc.get("X", 0),
                "y": loc.get("Y", 0),
                "z": loc.get("Z", 0),
                "yaw": yaw,
                "group_parent": "",
            }

    results = []
    for name, info in spawners.items():
        coord = scene.get(name, {"x": 0, "y": 0, "z": 0, "group_parent": ""})
        stem = map_json_path.stem
        version = ""
        if stem.endswith("_HR_D"):
            version = ""
        elif stem.endswith("_D"):
            version = "(D)"
        elif stem.endswith("_A"):
            version = "(A)"
        map_base = _sl_base_name(stem)
        keyword = info["keyword"]
        # Check if this spawner keyword is a multi-entity random generator
        if multi_entity_spawners and keyword in multi_entity_spawners:
            # Expand: one spawner entry per possible entity type
            for entity_info in multi_entity_spawners[keyword]:
                results.append(
                    {
                        "keyword": entity_info["entity_name"],
                        "original_keyword": keyword,
                        "spawner_type": entity_info["spawner_type"],
                        "preview_name": entity_info["entity_name"],
                        "has_lootdrop": True,
                        "x": coord["x"],
                        "y": coord["y"],
                        "z": coord["z"],
                        "yaw": coord.get("yaw", 0),
                        "json_filename": map_json_path.name,
                        "map_base": map_base,
                        "version": version,
                        "group_parent": coord.get("group_parent", ""),
                    }
                )
        else:
            results.append(
                {
                    "keyword": info["keyword"],
                    "original_keyword": info["keyword"],
                    "spawner_type": info["spawner_type"],
                    "preview_name": info.get("preview_name", ""),
                    "has_lootdrop": info.get("has_lootdrop", False),
                    "x": coord["x"],
                    "y": coord["y"],
                    "z": coord["z"],
                    "yaw": coord.get("yaw", 0),
                    "json_filename": map_json_path.name,
                    "map_base": map_base,
                    "version": version,
                    "group_parent": coord.get("group_parent", ""),
                }
            )
    return results


def build_automaton(terms: list[str]) -> ahocorasick.Automaton:
    auto = ahocorasick.Automaton()
    for t in terms:
        t_lower = t.lower()
        if len(t_lower) >= 5:
            auto.add_word(t_lower, t)
    auto.make_automaton()
    return auto


def match_keyword(keyword: str, terms: set[str], auto: ahocorasick.Automaton) -> list[str]:
    kw_lower = keyword.lower()
    matched = set()
    for _end_index, original_term in auto.iter(kw_lower):
        matched.add(original_term)
    for t in terms:
        t_lower = t.lower()
        if len(t_lower) >= 5:
            continue
        if t_lower == kw_lower or f"_{t_lower}" in kw_lower:
            matched.add(t)
        elif kw_lower.startswith(t_lower) and len(kw_lower) > len(t_lower):
            next_char = kw_lower[len(t_lower)]
            if next_char.isdigit() or next_char == "_":
                matched.add(t)
    return sorted(matched, key=len, reverse=True)


def coord_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def build_all_matches(search_terms: list[str]) -> tuple[dict[str, list[int]], list[dict]]:
    map_files = _list_map_jsons(MAPS_DIR)
    # Sort so HR_D comes first, then D, then A — single pass dedup ordering
    map_files.sort(key=lambda fp: (0 if fp.stem.endswith("_HR_D") else 1 if fp.stem.endswith("_D") else 2))

    terms_set = set(t for t in search_terms if t)
    auto = build_automaton(list(terms_set))

    hr_coords: dict[str, list[tuple[float, float, float]]] = {}
    d_coords: dict[str, list[tuple[float, float, float]]] = {}
    all_spawners: list[dict] = []

    multi_entity_spawners = _load_multi_entity_spawners()

    for fp in map_files:
        spawners = extract_spawners(fp, multi_entity_spawners=multi_entity_spawners)
        stem = fp.stem
        is_hr = stem.endswith("_HR_D")
        is_d = stem.endswith("_D") and not is_hr

        for s in spawners:
            base = s["map_base"]
            coord = (s["x"], s["y"], s["z"])
            if is_hr:
                hr_coords.setdefault(base, []).append(coord)
            elif is_d:
                if any(coord_distance(coord[:2], c[:2]) < 120 for c in hr_coords.get(base, [])):
                    continue
                d_coords.setdefault(base, []).append(coord)
            all_spawners.append(s)

    matches: dict[str, list[int]] = {}
    for idx, s in enumerate(all_spawners):
        # Always match against the spawner keyword itself
        kw = SPAWNER_ALIAS_MAP.get(s["keyword"], s["keyword"])
        matched = set(match_keyword(kw, terms_set, auto))
        # Also match against preview_name if present
        preview_name = s.get("preview_name", "")
        if preview_name:
            matched.update(match_keyword(preview_name, terms_set, auto))
        # Remove shorter prefix matches when a longer exact match exists.
        # e.g. "Banshee_Soulflame" should not also match "Banshee"; keep "Banshee_Soulflame".
        if len(matched) > 1:
            sorted_m = sorted(matched, key=len)
            to_remove: set[str] = set()
            for i, short_term in enumerate(sorted_m):
                short_lower = short_term.lower()
                for long_term in sorted_m[i + 1 :]:
                    if long_term.lower().startswith(short_lower):
                        to_remove.add(short_term)
                        break
            matched -= to_remove
        for m in matched:
            if m not in matches:
                matches[m] = []
            matches[m].append(idx)

    return matches, all_spawners
