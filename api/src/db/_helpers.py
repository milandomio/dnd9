import json
import logging
import re
from pathlib import Path
from typing import Any

from config import GAME_ROOT

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


_LOCALE_DISPLAY = {
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "ja": "Japanese",
    "ko": "Korean",
    "pt-BR": "Portuguese (Brazil)",
    "ru": "Russian",
    "zh-Hans": "Chinese (Simplified)",
    "zh-Hant": "Chinese (Traditional)",
}


def locale_display_name(lang: str) -> str:
    return _LOCALE_DISPLAY.get(lang, lang)


VARIANT_RE = re.compile(r"_\d{4}$")
QUALITY_RE = re.compile(r"_(Common|Elite|Nightmare|Unique)$")
MONSTER_SUBTYPE_RE = re.compile(r"_(BoneWall|BonePrison)$", re.IGNORECASE)
DUMMY_SUFFIX_RE = re.compile(r"_Dummy$")


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


_MONSTER_CLASS_RANK = {"Boss": 3, "SubBoss": 2, "Normal": 1, "Passive": 0}
_MONSTER_CLASS_TO_LIST_TYPE = {"Boss": "boss", "SubBoss": "miniboss", "Passive": "misc"}
_PASSIVE_ABILITY_RE = re.compile(
    r"(?:^|_)(?:Death|RunState|RunAway|PeaceAbility|Gesture|"
    r"Idle|Stand|Sit|Lie|Sleep|Howl|Bark|Yawn|Scratch|Smell|"
    r"Look|No|Yes)(?:_|$)",
    re.IGNORECASE,
)
_COMBAT_ABILITY_RE = re.compile(
    r"Attack|Melee|Bite|Shot|Missile|FaceHug|Bleeding|Combat|Dispell|Ultrasonic",
    re.IGNORECASE,
)


def _ability_asset_stem(ability: dict | None) -> str:
    path = (ability or {}).get("AssetPathName") or ""
    return path.rsplit("/", 1)[-1].split(".", 1)[0]


def _ability_is_passive(stem: str) -> bool:
    name = re.sub(r"^Id_(?:Monster|NPC)Ability_", "", stem)
    return bool(_PASSIVE_ABILITY_RE.search(f"_{name}_")) and not _COMBAT_ABILITY_RE.search(name)


def monster_is_passive(properties: dict | None) -> bool:
    """NPC or Normal monsters whose abilities are only death/flee/idle."""
    props = properties or {}
    id_tag = (props.get("IdTag") or {}).get("TagName", "") if isinstance(props.get("IdTag"), dict) else ""
    if id_tag.startswith("Id.NPC."):
        return True
    abilities = props.get("Abilities") or []
    if not abilities:
        return False
    return all(_ability_is_passive(_ability_asset_stem(ability)) for ability in abilities)


def monster_class_from_properties(properties: dict | None) -> str:
    """Map DCMonsterDataAsset ClassType tag to Boss / SubBoss / Normal / Passive."""
    class_type = (properties or {}).get("ClassType")
    tag = class_type.get("TagName", "") if isinstance(class_type, dict) else ""
    suffix = tag.rsplit(".", 1)[-1] if tag else ""
    if suffix not in _MONSTER_CLASS_RANK:
        suffix = ""
    if suffix in ("", "Normal") and monster_is_passive(properties):
        return "Passive"
    return suffix


def preferred_monster_class(current: str, incoming: str) -> str:
    if _MONSTER_CLASS_RANK.get(incoming, -1) > _MONSTER_CLASS_RANK.get(current, -1):
        return incoming
    return current or incoming


def monster_list_type(class_type: str) -> str:
    return _MONSTER_CLASS_TO_LIST_TYPE.get(class_type, "normal")


def monster_race_from_properties(properties: dict | None) -> str:
    """Most specific CharacterTypes suffix, e.g. Type.Character.Undead.Ghost → Ghost."""
    types = (properties or {}).get("CharacterTypes") or []
    tags: list[str] = []
    for entry in types:
        tag = entry.get("TagName", "") if isinstance(entry, dict) else ""
        if tag.startswith("Type.Character."):
            tags.append(tag)
    if not tags:
        return ""
    tags.sort(key=len, reverse=True)
    return tags[0].rsplit(".", 1)[-1]


def preferred_monster_race(current: str, incoming: str) -> str:
    return current or incoming


def extract_props_name(raw_name: str) -> str:
    name = raw_name.removeprefix("Id_Props_")
    name = DUMMY_SUFFIX_RE.sub("", name)
    return name


def extract_dungeon_module_name(raw_name: str) -> str:
    return raw_name.removeprefix("Id_DungeonModule_")


_UE_PATH_RE = re.compile(r"/Game/DungeonCrawler/(.*)\.\w+$")


def ue_to_fs_path(ue_path: str) -> str | None:
    m = _UE_PATH_RE.search(ue_path)
    if not m:
        return None
    return m.group(1)


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
