import json
import logging
import re
from pathlib import Path
from typing import Any

from config import GAME_JSON, GAME_ROOT

log = logging.getLogger(__name__)


def load_json_dir(directory: Path) -> dict[str, Any]:
    result = {}
    if not directory.exists():
        return result
    for fp in sorted(directory.glob("*.json")):
        try:
            with open(fp, encoding="utf-8") as f:
                result[fp.stem] = json.load(f)
        except Exception as e:
            log.warning("failed to load %s: %s", fp.name, e)
    return result


def load_game_json() -> dict[str, str]:
    if not GAME_JSON.exists():
        return {}
    try:
        with open(GAME_JSON, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for v in raw.values():
                if isinstance(v, dict):
                    return v
        return {}
    except Exception as e:
        log.warning("failed to load game JSON %s: %s", GAME_JSON, e)
        return {}


VARIANT_RE = re.compile(r"_\d{4}$")
QUALITY_RE = re.compile(r"_(Common|Elite|Nightmare|Unique)$")
MONSTER_SUBTYPE_RE = re.compile(r"_(BoneWall|BonePrison)$", re.IGNORECASE)


def strip_ids_prefix(name: str, prefix: str) -> str:
    return (
        name.removeprefix(prefix)
        .removeprefix("Id_Item_")
        .removeprefix("Id_Monster_")
        .removeprefix("Id_Props_")
        .removeprefix("Id_DungeonModule_")
        .removeprefix("ID_Lootdrop_")
        .removeprefix("ID_LootDropGroup_")
        .removeprefix("Id_Spawner_New_Monster_")
        .removeprefix("Id_Spawner_New_Props_")
        .removeprefix("Id_Spawner_New_LootDrop_")
    )


def extract_translation_key(name: str, prefix: str) -> str:
    key = name.removeprefix(prefix)
    key = QUALITY_RE.sub("", key)
    key = VARIANT_RE.sub("", key)
    return key


def extract_item_name(raw_name: str) -> str:
    name = raw_name.removeprefix("Id_Item_")
    name = VARIANT_RE.sub("", name)
    return name


def extract_monster_name(raw_name: str) -> str:
    name = raw_name.removeprefix("Id_Monster_")
    name = QUALITY_RE.sub("", name)
    name = MONSTER_SUBTYPE_RE.sub("", name)
    return name


def extract_props_name(raw_name: str) -> str:
    name = raw_name.removeprefix("Id_Props_")
    name = re.sub(r"_Dummy$", "", name)
    return name


def extract_dungeon_module_name(raw_name: str) -> str:
    return raw_name.removeprefix("Id_DungeonModule_")


_UE_PATH_RE = re.compile(r"/Game/DungeonCrawler/(.*)\.\w+$")


def ue_to_fs_path(ue_path: str) -> str | None:
    m = _UE_PATH_RE.search(ue_path)
    if not m:
        return None
    return m.group(1).replace("/", "/")


def ue_asset_base_name(ue_path: str) -> str | None:
    stem = ue_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return stem


_SL_SUFFIX_RE = re.compile(r"_(HR_D|D|A)$")


def sl_base_name(asset_name: str) -> str:
    return _SL_SUFFIX_RE.sub("", asset_name)


def has_map_file(ue_path: str) -> bool:
    fs = ue_to_fs_path(ue_path)
    if not fs:
        return False
    parts = fs.rsplit("/", 1)
    if len(parts) < 2:
        return False
    dir_rel = parts[0]
    return (GAME_ROOT / dir_rel).is_dir()
