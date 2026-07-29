import json
import math
import os
import re
from pathlib import Path

from config import SPAWNER_ALIAS_MAP

_VARIANT_RE = re.compile(r"_\d{4}$")
_QUALITY_RE = re.compile(r"_(Common|Elite|Nightmare|Unique)$")
_HARD_SUFFIX_RE = re.compile(r"_(Hard|VeryHard)$")
_AP_SUFFIX_RE = re.compile(r"\.(\d+)'?$")


def strip_variant_suffixes(name: str) -> str:
    result = name
    result = _QUALITY_RE.sub("", result)
    result = _HARD_SUFFIX_RE.sub("", result)
    result = _VARIANT_RE.sub("", result)
    return result


def _ue_asset_base_name(asset_path: str) -> str:
    """Extract base name from UE asset path like '/Game/.../Id_Foo.Id_Foo' → 'Id_Foo'."""
    if not asset_path:
        return ""
    part = asset_path.rsplit("/", 1)[-1]
    if "." in part:
        part = part.split(".")[0]
    return part


def load_all_spawner_data(
    db,
    monster_name_map: dict[str, str] | None = None,
) -> tuple[dict[str, bool], dict[str, list[dict]], dict[str, list[str]]]:
    """Build spawner lookup maps from the preloaded DB tables."""
    keyword_has_lootdrop: dict[str, bool] = {}
    multi_entity: dict[str, list[dict]] = {}
    _ldg_to_monsters: dict[str, set[str]] = {}

    entries = db.get_all_spawner_entries()
    monster_names = {row["monster_name"] for row in db.get_monster_entities()}
    props_names = {row["asset_name"] for row in db.get_props_entities()}
    grouped: dict[str, list[dict]] = {}
    for row in entries:
        keyword = row["spawner_keyword"]
        if not keyword:
            continue
        kw_base = strip_variant_suffixes(keyword)
        has_ld = bool(row["lootdrop_group_id"])
        keyword_has_lootdrop[kw_base] = keyword_has_lootdrop.get(kw_base, False) or has_ld
        if not has_ld:
            continue
        grouped.setdefault(keyword, []).append(row)
        entity_name = row["entity_name"]
        if entity_name and row["lootdrop_group_id"]:
            canonical = (monster_name_map or {}).get(entity_name.lower())
            if not canonical:
                stripped = strip_variant_suffixes(entity_name)
                canonical = (monster_name_map or {}).get(stripped.lower(), entity_name)
            _ldg_to_monsters.setdefault(row["lootdrop_group_id"], set()).add(canonical)

    for keyword, keyword_entries in grouped.items():
        entity_names = {row["entity_name"] for row in keyword_entries if row["entity_name"]}
        need_expand = len(entity_names) >= 2
        need_redirect = len(entity_names) == 1 and keyword != next(iter(entity_names))
        if need_redirect and keyword.startswith("SuperHoard"):
            need_redirect = False
        if not (need_expand or need_redirect):
            continue
        expanded = []
        for row in keyword_entries:
            entity_name = row["entity_name"]
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

    lootdrop_monster = {k: sorted(v) for k, v in _ldg_to_monsters.items()}
    return keyword_has_lootdrop, multi_entity, lootdrop_monster


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
            files.append(Path(dirpath) / fn)
    return sorted(files)


def extract_spawners(
    map_json_path: Path,
    multi_entity_spawners: dict[str, list[dict]] | None = None,
    spawner_data_map: dict[str, bool] | None = None,
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
    if spawner_data_map is None:
        spawner_data_map = {}

    # Collect all scene-component-like entries for parent-chain resolution
    _sc_entries: list[tuple[int, dict]] = []  # (array_index, entry)
    _scene_comp_types = {"SphereComponent", "SceneComponent"}

    # Build map from DefaultSceneRoot entry index → BP_GameSpawnerGroup_C name
    group_root_to_name: dict[int, str] = {}
    # Build map for sub-group containers (ObjectLinker, TriggerBox) → name
    sub_group_root_to_name: dict[int, str] = {}
    _sub_group_types = {"BP_GameObjectLinker_C", "BP_ObjectLinkWithTriggerBox_C"}
    for _idx, entry in enumerate(data):
        t = entry.get("Type", "")
        props = entry.get("Properties", {}) or {}
        root = props.get("RootComponent", {}) or {}
        op = root.get("ObjectPath", "")
        m = _AP_SUFFIX_RE.search(op) if op else None
        if not m:
            continue
        idx = int(m.group(1))
        if t == "BP_GameSpawnerGroup_C":
            group_root_to_name[idx] = entry.get("Name", "")
        elif t in _sub_group_types:
            sub_group_root_to_name[idx] = entry.get("Name", "")

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
            # Apply alias map (before variant stripping)
            keyword_alias = SPAWNER_ALIAS_MAP.get(keyword, keyword)
            # Stripped keyword for direct entity matching
            keyword_stripped = strip_variant_suffixes(keyword_alias)
            pd = props.get("PreviewData", {}) or {}
            asset_path = pd.get("AssetPathName", "")
            spawner_type = _preview_type(asset_path)
            preview_name = strip_variant_suffixes(_preview_entity_name(asset_path))
            spawner_name = entry.get("Name", "")
            # Check if this spawner has lootdrop from spawner data asset
            has_lootdrop = spawner_data_map.get(keyword_stripped, False) or spawner_data_map.get(keyword_alias, False)
            if spawner_name:
                spawners[spawner_name] = {
                    "keyword": keyword_stripped,
                    "keyword_original": keyword,
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

    def _resolve_world_loc(start_idx: int) -> tuple[float, float, float, float, str, str]:
        """Walk up AttachParent chain to compute world-space x, y, z, yaw,
        group name and sub-group name (closest container in chain)."""
        chain: list[tuple[float, float, float, float]] = []
        group_name = ""
        sub_group_name = ""
        visited: set[int] = set()
        cur = start_idx
        while cur >= 0 and cur not in visited:
            visited.add(cur)
            if cur >= len(data):
                break
            if cur in group_root_to_name:
                group_name = group_root_to_name[cur]
            if cur in sub_group_root_to_name and not sub_group_name:
                sub_group_name = sub_group_root_to_name[cur]
            entry = data[cur]
            props = entry.get("Properties", {}) or {}
            loc = props.get("RelativeLocation", {}) or {}
            rot = props.get("RelativeRotation", {}) or {}
            chain.append(
                (
                    loc.get("X", 0),
                    loc.get("Y", 0),
                    loc.get("Z", 0),
                    rot.get("Yaw", 0),
                )
            )
            ap = props.get("AttachParent", {}) or {}
            ap_path = ap.get("ObjectPath", "")
            m = _AP_SUFFIX_RE.search(ap_path)
            cur = int(m.group(1)) if m else -1
        # Accumulate from root to leaf, rotating child offsets by parent rotation
        x = y = z = 0.0
        yaw_total = 0.0
        for lx, ly, lz, lyaw in reversed(chain):
            if yaw_total != 0:
                r = math.radians(yaw_total)
                cos_r, sin_r = math.cos(r), math.sin(r)
                rx = lx * cos_r - ly * sin_r
                ry = lx * sin_r + ly * cos_r
            else:
                rx, ry = lx, ly
            x += rx
            y += ry
            z += lz
            yaw_total += lyaw
        return x, y, z, yaw_total, group_name, sub_group_name

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
            wx, wy, wz, wyaw, group_name, sub_group_name = _resolve_world_loc(idx)
            scene[actor_name] = {
                "x": wx,
                "y": wy,
                "z": wz,
                "yaw": round(wyaw % 360, 1),
                "group_parent": group_name,
                "sub_group_parent": sub_group_name,
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
                "sub_group_parent": "",
            }

    results = []
    for name, info in spawners.items():
        coord = scene.get(name, {"x": 0, "y": 0, "z": 0, "group_parent": "", "sub_group_parent": ""})
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
        kw_original = info.get("keyword_original", keyword)
        # Check if this spawner keyword is a multi-entity random generator
        # Use the original (non-stripped) keyword for multi_entity lookup
        if multi_entity_spawners and kw_original in multi_entity_spawners:
            # Expand: one spawner entry per possible entity type
            # Filter: if the spawner keyword base matches any entity's base,
            # only include entities of the same base (avoids GoblinWarrior → LavaGolem bleed)
            entities = multi_entity_spawners[kw_original]
            kw_base = keyword
            entity_bases = {e["entity_name"] for e in entities}
            has_match = any(kw_base == eb or kw_base in eb or eb in kw_base for eb in entity_bases)
            for entity_info in entities:
                if has_match:
                    en = entity_info["entity_name"]
                    if en != kw_base and kw_base not in en and en not in kw_base:
                        continue
                results.append(
                    {
                        "keyword": entity_info["entity_name"],
                        "original_keyword": kw_original,
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
                        "sub_group_parent": coord.get("sub_group_parent", ""),
                    }
                )
        else:
            results.append(
                {
                    "keyword": info["keyword"],
                    "original_keyword": info.get("keyword_original", info["keyword"]),
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
                    "sub_group_parent": coord.get("sub_group_parent", ""),
                }
            )
    return results


def coord_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def extract_all_spawners(
    map_root: str | Path,
    has_lootdrop_map: dict[str, bool] | None = None,
    multi_entity_spawners: dict[str, list[dict]] | None = None,
) -> list[dict]:
    """Iterate all map files, extract spawners, deduplicate across HR_D/D variants.
    Returns a flat list of spawner dicts with variant-stripped keywords."""
    map_files = _list_map_jsons(map_root)
    # Sort so HR_D comes first, then D, then A — single pass dedup ordering
    map_files.sort(key=lambda fp: (0 if fp.stem.endswith("_HR_D") else 1 if fp.stem.endswith("_D") else 2))

    hr_coords: dict[str, list[tuple[float, float, float]]] = {}
    all_spawners: list[dict] = []

    if multi_entity_spawners is None:
        multi_entity_spawners = {}
    if has_lootdrop_map is None:
        has_lootdrop_map = {}

    for fp in map_files:
        spawners = extract_spawners(fp, multi_entity_spawners=multi_entity_spawners, spawner_data_map=has_lootdrop_map)
        stem = fp.stem
        is_hr = stem.endswith("_HR_D")
        is_d = stem.endswith("_D") and not is_hr

        for s in spawners:
            base = s["map_base"]
            coord = (s["x"], s["y"], s["z"])
            if is_hr:
                hr_coords.setdefault(base, []).append(coord)
            elif is_d and any(coord_distance(coord[:2], c[:2]) < 120 for c in hr_coords.get(base, [])):
                continue
            all_spawners.append(s)

    return all_spawners
