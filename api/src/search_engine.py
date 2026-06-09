import os
import re
import json
from pathlib import Path
from typing import Any

import ahocorasick

from config import MAPS_DIR, SPAWNER_ALIAS_MAP


_VARIANT_RE = re.compile(r"_\d{4}$")


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
    "_Elite", "_Random", "_2type", "_3type", "_4type", "_5type",
]


def strip_id_prefix(name: str) -> str:
    result = name
    changed = True
    while changed:
        changed = False
        for prefix in _PREFIXES:
            if result.startswith(prefix):
                result = result[len(prefix):].rstrip("'\"")
                changed = True
                break
        if not changed and result.startswith("Id_"):
            result = result[3:]
            changed = True
    for suffix in _SUFFIXES:
        if result.endswith(suffix):
            result = result[:-len(suffix)]
    return result


def _preview_type(asset_path: str) -> str:
    if "/V2/Monster/" in asset_path:
        return "monster"
    if "/V2/Props/" in asset_path:
        return "props"
    if "/V2/LootDrop/" in asset_path:
        return "lootdrop"
    return "unknown"


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


def extract_spawners(map_json_path: Path) -> list[dict]:
    try:
        with open(map_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    spawners: dict[str, dict] = {}
    scene: dict[str, dict] = {}

    for entry in data:
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
            spawner_name = entry.get("Name", "")
            if spawner_name:
                spawners[spawner_name] = {
                    "keyword": keyword,
                    "spawner_type": spawner_type,
                }

        elif t == "SphereComponent" and entry.get("Name") == "SceneComponent":
            outer_raw = entry.get("Outer", "")
            if isinstance(outer_raw, dict):
                outer_raw = (outer_raw or {}).get("ObjectName", "")
            if not outer_raw or not isinstance(outer_raw, str):
                continue
            actor_name = _extract_actor_name(outer_raw)
            if not actor_name:
                continue
            loc = (entry.get("Properties", {}) or {}).get("RelativeLocation", {}) or {}
            scene[actor_name] = {"x": loc.get("X", 0), "y": loc.get("Y", 0), "z": loc.get("Z", 0)}

    results = []
    for name, info in spawners.items():
        coord = scene.get(name, {"x": 0, "y": 0, "z": 0})
        stem = map_json_path.stem
        version = ""
        if stem.endswith("_HR_D"):
            version = ""
        elif stem.endswith("_D"):
            version = "(D)"
        elif stem.endswith("_A"):
            version = "(A)"
        map_base = _sl_base_name(stem)
        results.append({
            "keyword": info["keyword"],
            "original_keyword": info["keyword"],
            "spawner_type": info["spawner_type"],
            "x": coord["x"],
            "y": coord["y"],
            "z": coord["z"],
            "json_filename": map_json_path.name,
            "map_base": map_base,
            "version": version,
        })
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
    for end_index, original_term in auto.iter(kw_lower):
        matched.add(original_term)
    for t in terms:
        t_lower = t.lower()
        if len(t_lower) >= 5:
            continue
        if t_lower == kw_lower:
            matched.add(t)
        elif f"_{t_lower}" in kw_lower:
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
    terms_set = set(t for t in search_terms if t)
    auto = build_automaton(list(terms_set))

    # Phase 1: collect all HR coords first, so D dedup in Phase 2 can see them
    hr_coords: dict[str, list[tuple[float, float, float]]] = {}
    for fp in map_files:
        if fp.stem.endswith("_HR_D"):
            spawners = extract_spawners(fp)
            for s in spawners:
                base = s["map_base"]
                coord = (s["x"], s["y"], s["z"])
                if base not in hr_coords:
                    hr_coords[base] = []
                hr_coords[base].append(coord)

    # Phase 2: process all spawners with dedup (hr_coords now fully populated)
    all_spawners: list[dict] = []
    d_coords: dict[str, list[tuple[float, float, float]]] = {}

    for fp in map_files:
        spawners = extract_spawners(fp)
        stem = fp.stem
        is_hr = stem.endswith("_HR_D")
        is_d = stem.endswith("_D") and not is_hr
        is_a = stem.endswith("_A") and not is_d and not is_hr

        for s in spawners:
            kw = s["keyword"]
            coord = (s["x"], s["y"], s["z"])
            base = s["map_base"]
            if is_a:
                hr_list = hr_coords.get(base, [])
                d_list = d_coords.get(base, [])
                if any(coord_distance(coord[:2], c[:2]) < 120 for c in hr_list + d_list):
                    continue
            elif is_d:
                hr_list = hr_coords.get(base, [])
                if any(coord_distance(coord[:2], c[:2]) < 120 for c in hr_list):
                    continue
                if base not in d_coords:
                    d_coords[base] = []
                d_coords[base].append(coord)
            elif is_hr:
                if base not in hr_coords:
                    hr_coords[base] = []
                hr_coords[base].append(coord)
            all_spawners.append(s)

    matches: dict[str, list[int]] = {}
    for idx, s in enumerate(all_spawners):
        kw = SPAWNER_ALIAS_MAP.get(s["keyword"], s["keyword"])
        matched = match_keyword(kw, terms_set, auto)
        for m in matched:
            if m not in matches:
                matches[m] = []
            matches[m].append(idx)

    return matches, all_spawners
