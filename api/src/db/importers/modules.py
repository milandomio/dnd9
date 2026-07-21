import json
import os
import re
from pathlib import Path

from config import DUNGEON_MODULE_DIR, GROUP_TO_ART_DIR, MAPS_DIR
from layout_utils import load_all_layout_rotations

from .._helpers import (
    extract_dungeon_module_name,
    has_map_file,
    load_json_dir,
    sl_base_name,
    ue_asset_base_name,
    ue_to_fs_path,
)


class ModulesImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        module_rotations = load_all_layout_rotations()
        path_group_map = self._build_path_group_map()
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
            mi_asset = (props.get("MapImage") or {}).get("AssetPathName", "")
            map_image = ue_asset_base_name(mi_asset) or ""
            aliases_json = json.dumps(aliases) if aliases else "[]"
            rot = (
                module_rotations.get(module_name)
                if module_rotations.get(module_name) is not None
                else module_rotations.get(sl_base, 270)
            )
            rows.append((module_name, name_key, module_type, size_x, size_y, sl_base, map_image, aliases_json, rot))
            inserted_names.add(module_name)
        c.executemany(
            "INSERT OR REPLACE INTO dungeon_modules (module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases, rotation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        if skipped_names:
            print(f"  skipped {len(skipped_names)} modules with stale SubLevelAsset: {skipped_names}")
        sl_base_to_key = {r[5]: r[1] for r in rows if r[5]}
        module_name_to_key = {r[0]: r[1] for r in rows if r[1]}
        _variant_suffix_re = re.compile(r"_(Resize|Test|BossTest|DistantView)$")
        extra_rows = []
        for base_name, group in path_group_map.items():
            if base_name not in inserted_names:
                tk = sl_base_to_key.get(base_name, "") or module_name_to_key.get(base_name, "")
                if not tk:
                    stripped = _variant_suffix_re.sub("", base_name)
                    if stripped != base_name:
                        tk = sl_base_to_key.get(stripped, "") or module_name_to_key.get(stripped, "")
                extra_rows.append((base_name, tk, group, 1, 1, "", "", "[]", module_rotations.get(base_name, 270)))
                inserted_names.add(base_name)
        if extra_rows:
            c.executemany(
                "INSERT OR REPLACE INTO dungeon_modules (module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases, rotation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                extra_rows,
            )
        c.execute("DELETE FROM dungeon_modules WHERE module_group = '' OR module_group IS NULL")
        self.conn.commit()
        c.execute("SELECT COUNT(*) FROM dungeon_modules")
        return c.fetchone()[0]

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
