import json
import math
import os
import re
from pathlib import Path

from config import (
    DUNGEON_DIR,
    DUNGEON_MODULE_DIR,
    GROUP_TO_ART_DIR,
    LAYOUT_DIR,
    MAPS_DIR,
)
from module_spawn_rate import compute_spawn_rates, rare_groups

from .._helpers import (
    extract_dungeon_module_name,
    has_map_file,
    load_json_dir,
    module_is_rare,
    module_placement_flags,
    sl_base_name,
    ue_asset_base_name,
    ue_to_fs_path,
)

# 收录入口：只接受 5x5 随机地牢引用的关卡尺寸
ENTRY_LAYOUT_SIZE = 5
_LAYOUT_SIZE_RE = re.compile(r"_(\d)x(\d)_")


def _load_layout_rotations(layout_root: Path) -> dict[str, int]:
    rotations: dict[str, int] = {}
    if not layout_root.exists():
        return rotations
    for dirpath, _, filenames in os.walk(layout_root):
        for filename in filenames:
            if not filename.endswith(".json") or not filename.startswith("ShipGraveyard_"):
                continue
            try:
                with open(Path(dirpath) / filename, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for entry in data:
                if not isinstance(entry, dict) or entry.get("Type") != "LevelStreamingAlwaysLoaded":
                    continue
                props = entry.get("Properties", {}) or {}
                asset = (props.get("WorldAsset") or {}).get("AssetPathName", "")
                if not asset:
                    continue
                rotation = (props.get("LevelTransform") or {}).get("Rotation", {}) or {}
                yaw_rad = 2 * math.atan2(rotation.get("Z", 0), rotation.get("W", 1))
                base = asset.rsplit("/", 1)[-1].split(".", 1)[0]
                for suffix in ("_A", "_D", "_S", "_HR", "_HR_D"):
                    if base.endswith(suffix):
                        base = base[: -len(suffix)]
                        break
                rotations[base] = round((math.degrees(yaw_rad) - 90) % 360, 1)
    return rotations


def _layout_size(level_asset: str) -> int | None:
    """Extract the grid size from a LevelAsset name such as Crypt_5x5_HR_R_P."""
    match = _LAYOUT_SIZE_RE.search(level_asset or "")
    if not match:
        return None
    return int(match.group(1))


def load_entry_groups(dungeon_dir: Path = DUNGEON_DIR) -> dict[str, int]:
    """Return module_group -> layout size for every random dungeon using ENTRY_LAYOUT_SIZE.

    Only groups whose random dungeons are built on a 5x5 level are collected;
    larger levels (e.g. the legacy ShipGraveyard 7x7) are excluded entirely.
    """
    groups: dict[str, int] = {}
    if not dungeon_dir.exists():
        return groups
    for fp in sorted(dungeon_dir.glob("*.json")):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for entry in data:
            if not isinstance(entry, dict):
                continue
            props = entry.get("Properties") or {}
            name = entry.get("Name") or ""
            if not name.startswith("Id_Dungeon_Random"):
                continue
            if "S2R" in name:
                continue
            group = (props.get("ModuleType") or "").removeprefix("EDCDungeonModuleType::")
            if not group:
                continue
            asset = (props.get("LevelAsset") or {}).get("AssetPathName", "")
            size = _layout_size(asset)
            if size == ENTRY_LAYOUT_SIZE:
                groups[group] = size
    return groups


def module_is_collectable(
    module_type: str,
    is_rare: bool,
    entry_groups: dict[str, int],
    active_rare_groups: set[str],
) -> bool:
    """Whether a module belongs to the collected 5x5 pool.

    Two data-driven conditions: the group must own a 5x5 random dungeon, and a
    rare module may only come from a group declaring rare slots
    (NumMaxRares > 0). Groups without rare slots still ship their whole rare
    module set, which is not part of the 5x5 pool.
    """
    if entry_groups and module_type not in entry_groups:
        return False
    return not (is_rare and module_type not in active_rare_groups)


class ModulesImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        module_rotations = _load_layout_rotations(LAYOUT_DIR)
        path_group_map = self._build_path_group_map()
        entry_groups = load_entry_groups()
        if entry_groups:
            path_group_map = {k: v for k, v in path_group_map.items() if v in entry_groups}
        # Rare modules only spawn in groups that declare rare slots
        # (DCDungeonDataAsset.NumMaxRares > 0). A group that merely gained a 5x5
        # random dungeon still ships its whole rare module set; those modules are
        # not part of the 5x5 pool and must stay off the site
        # (e.g. Ruins_ForgottenPlots, a rare module from the 7x7 layout era).
        active_rare_groups = rare_groups()
        files = load_json_dir(DUNGEON_MODULE_DIR)
        c = self.conn.cursor()
        c.execute("DELETE FROM dungeon_modules")
        type_map: dict[str, str] = {}
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            module_name = extract_dungeon_module_name(raw_name)
            module_type = (props.get("ModuleType") or "").removeprefix("EDCDungeonModuleType::")
            if module_type:
                type_map[module_name] = module_type
        # Pre-index which module_names have their own file (for alias conflict detection)
        own_module_names: set[str] = set()
        for raw_name in files:
            own_module_names.add(extract_dungeon_module_name(raw_name))
        rows = []
        inserted_names: set[str] = set()
        skipped_names: list[str] = []
        # Modules rejected by the rare-pool rule must not come back through the
        # map-directory sweep below, which only exists for modules that had no
        # usable DungeonModule asset.
        rare_excluded: set[str] = set()
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = (props.get("Name") or {}).get("Key", "")
            module_type = (props.get("ModuleType") or "").removeprefix("EDCDungeonModuleType::")
            size_x = (props.get("Size") or {}).get("X", 1) or 1
            size_y = (props.get("Size") or {}).get("Y", 1) or 1
            module_name = extract_dungeon_module_name(raw_name)
            if "_SR" in module_name or "_BossTest" in module_name or "_Resize" in module_name or "_Test" in module_name:
                continue
            sl_base = ""
            found_valid = False
            for variant in ["SubLevelAssetD_HR", "SubLevelAssetD", "SubLevelAssetA"]:
                asset = (props.get(variant) or {}).get("AssetPathName", "")
                if not asset:
                    continue
                if variant in ("SubLevelAssetD_HR", "SubLevelAssetD") and not has_map_file(asset):
                    break
                base = ue_asset_base_name(asset) or ""
                sl_base = sl_base_name(base)
                if variant in ("SubLevelAssetD_HR", "SubLevelAssetD") and sl_base:
                    fs_path = ue_to_fs_path(asset)
                    if fs_path:
                        dir_name = fs_path.rsplit("/", 1)[0].rsplit("/", 1)[-1] if "/" in fs_path else ""
                        if (
                            dir_name
                            and sl_base.lower() not in dir_name.lower()
                            and dir_name.lower() not in sl_base.lower()
                        ):
                            skipped_names.append(module_name)
                            sl_base = ""
                            break
                found_valid = True
                break
            if not found_valid:
                skipped_names.append(module_name)
                continue
            aliases = []
            if sl_base and sl_base != module_name:
                if sl_base in own_module_names:
                    pass  # separate modules sharing the same image; keep independent
                else:
                    aliases.append(module_name)
                    module_name = sl_base
            path_group = path_group_map.get(module_name, "")
            if path_group:
                module_type = path_group
            if not module_type and sl_base:
                module_type = type_map.get(sl_base, "")
            if not module_type:
                for prefix, group in [
                    ("ShipGraveyard", "ShipGraveyard"),
                    ("Shipgraveyard", "ShipGraveyard"),
                    ("GoblinCave", "GoblinCave"),
                    ("GoblinJail", "GoblinCave"),
                    ("GoblinMine", "GoblinCave"),
                    ("Goblin", "GoblinCave"),
                    ("Firedeep", "FireDeep"),
                    ("FireDeep", "FireDeep"),
                    ("IceCavern", "IceCavern"),
                    ("IceAbyss", "IceAbyss"),
                    ("IceCave", "IceCavern"),
                    ("Crypt", "Crypt"),
                    ("Inferno", "Inferno"),
                    ("Ruins", "Ruins"),
                    ("Swamp", "Crypt"),
                    ("Cave_", "GoblinCave"),
                    ("CorridorCrypt", "Crypt"),
                    ("Cemetery", "Crypt"),
                    ("SpiderCave", "GoblinCave"),
                    ("Prison", "Ruins"),
                ]:
                    if module_name.lower().startswith(prefix.lower()):
                        module_type = group
                        break
            if not module_type:
                skipped_names.append(module_name)
                continue
            is_rare = module_is_rare(props)
            if not module_is_collectable(module_type, is_rare, entry_groups, active_rare_groups):
                skipped_names.append(module_name)
                if is_rare and module_type in entry_groups:
                    rare_excluded.add(module_name)
                continue
            mi_asset = (props.get("MapImage") or {}).get("AssetPathName", "")
            map_image = ue_asset_base_name(mi_asset) or ""
            aliases_json = json.dumps(aliases) if aliases else "[]"
            rot = (
                module_rotations.get(module_name)
                if module_rotations.get(module_name) is not None
                else module_rotations.get(sl_base, 270)
            )
            is_edge, is_corner = module_placement_flags(props)
            rows.append(
                (
                    module_name,
                    name_key,
                    module_type,
                    size_x,
                    size_y,
                    sl_base,
                    map_image,
                    aliases_json,
                    rot,
                    int(is_edge),
                    int(is_corner),
                    int(is_rare),
                )
            )
            inserted_names.add(module_name)
        c.executemany(
            "INSERT OR REPLACE INTO dungeon_modules (module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases, rotation, is_edge, is_corner, is_rare) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        if skipped_names:
            print(f"  skipped {len(skipped_names)} modules with stale SubLevelAsset: {skipped_names}")
        sl_base_to_key = {r[5]: r[1] for r in rows if r[5]}
        module_name_to_key = {r[0]: r[1] for r in rows if r[1]}
        _variant_suffix_re = re.compile(r"_(Resize|Test|BossTest|DistantView)$")
        extra_rows = []
        for base_name, group in path_group_map.items():
            if base_name in rare_excluded:
                continue
            if base_name not in inserted_names:
                tk = sl_base_to_key.get(base_name, "") or module_name_to_key.get(base_name, "")
                if not tk:
                    stripped = _variant_suffix_re.sub("", base_name)
                    if stripped != base_name:
                        tk = sl_base_to_key.get(stripped, "") or module_name_to_key.get(stripped, "")
                extra_rows.append(
                    (base_name, tk, group, 1, 1, "", "", "[]", module_rotations.get(base_name, 270), 0, 0, 0)
                )
                inserted_names.add(base_name)
        if extra_rows:
            c.executemany(
                "INSERT OR REPLACE INTO dungeon_modules (module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases, rotation, is_edge, is_corner, is_rare) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                extra_rows,
            )
        c.execute("DELETE FROM dungeon_modules WHERE module_group = '' OR module_group IS NULL")
        self._store_spawn_rates()
        self.conn.commit()
        c.execute("SELECT COUNT(*) FROM dungeon_modules")
        return c.fetchone()[0]

    def _store_spawn_rates(self, stats: dict | None = None) -> None:
        """Cache each rare module's spawn rate in the DB.

        The rate depends on layout assets and the collected rare pool, but CI runs
        without the game export tree. Storing the value here keeps exports stable
        across environments instead of silently degrading to 0.

        ``stats`` exists so tests can inject layout statistics without the game tree.
        """
        c = self.conn.cursor()
        c.execute("SELECT module_name, module_group, is_rare FROM dungeon_modules")
        modules = [{"module_name": row[0], "module_group": row[1], "is_rare": bool(row[2])} for row in c.fetchall()]
        rates = compute_spawn_rates(modules, stats)
        if rates:
            c.executemany(
                "UPDATE dungeon_modules SET spawn_rate = ? WHERE module_name = ?",
                [(rate, name) for name, rate in rates.items()],
            )
        else:
            print("  spawn rates unavailable (layout assets missing); keeping stored values")

    def _build_path_group_map(self) -> dict[str, str]:
        path_group: dict[str, str] = {}
        if not MAPS_DIR.exists():
            return path_group
        dir_to_group: dict[str, str] = {}
        for group, art_dir in GROUP_TO_ART_DIR.items():
            dir_to_group[art_dir] = group
        for dirpath, _, filenames in os.walk(MAPS_DIR):
            rel = Path(dirpath).relative_to(MAPS_DIR)
            group = dir_to_group.get(rel.parts[0], "") if rel.parts else ""
            if not group:
                continue
            for fn in filenames:
                if not fn.endswith(("_HR_D.json", "_D.json", "_A.json")):
                    continue
                stem = fn.rsplit(".", 1)[0]
                if "_SR" in stem or "_Arena" in stem or "_BossTest" in stem or "_Resize" in stem or "_Test" in stem:
                    continue
                base = sl_base_name(stem)
                if base not in path_group:
                    path_group[base] = group
        return path_group
