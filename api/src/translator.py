"""Name resolution and coordinate utilities extracted from collector.py."""

import re

from config import (
    HARDCODED_TRANSLATIONS,
    MODULE_NAME_OVERRIDE,
    TRANSLATION_ALIAS_MAP,
)

# ── Regex constants ──

VARIANT_RE = re.compile(r"^(.+)_\d{4}$")
HARD_SUFFIX_RE = re.compile(r"_(Hard|VeryHard)$")
UNIQUE_SUFFIX_RE = re.compile(r"Unique$")
QUALITY_RE = re.compile(r"_(Common|Elite|Nightmare|Unique)$")
ORE_QUALITY_RE = re.compile(r"^(?:Ore_)?(.+?)(?:_)?(?:High|Med|Low|VeryLow|Random)$")
ORE_ITEM_COORD_RE = re.compile(r"^(Cobalt|Copper|FrostStone|Gold|Iron|Obsidian|Rubysilver|Tidestone)Ores$")
RESOLVE_STRIP_RE = re.compile(r"_(?:\d+|Common|Elite|Nightmare|Hard|VeryHard|Unique|VeryLow|Low|Med|High|Random)$")
RESOLVE_FUZZY_RE = re.compile(
    r"(?:"
    r"_[Rr]"  # _R（棺材变体）
    r"|_On$|_Off$"  # 开关状态
    r"|_Lit$|_Unlit$"  # 灯光状态
    r"|__UnderSea$"  # 海底变体（双下划线）
    r"|_UnderSea$"  # 海底变体
    r"|Random$"  # 随机变体（含 BlackRoseRandom 无下划线前缀）
    r"|_(?:Elite|Nightmare)$"  # 难度变体
    r"|(?:_0[1-9])$"  # 编号后缀 _01~_09
    r")"
)
RESOLVE_FUZZY_PASS2_RE = re.compile(
    r"(?:"
    r"_On$|_Off$"  # 尾部 On/Off
    r"|_Lit$|_Unlit$"  # 尾部灯光
    r"|_[A-Z](?!\w)$"  # 单字母后缀 _A _B
    r"|_\w+_(?:On|Off|Lit|Unlit)$"  # 中间段+状态 Torch02_Purple_On
    r"|_\d+(?:_(?:On|Off|Lit|Unlit))?$"  # 尾部数字+可选状态 _03_On
    r"|_\d+(?:On|Off|ON|OFF)$"  # 尾部数字+状态（无间隔）_01ON
    r"|(?:\d+(?:On|Off|ON|OFF))$"  # 无下划线数字+状态 Roaster07On
    r"|(?:\d+)$"  # 尾部纯数字（剥离 On 后残留）Torch03
    r"|_Ruins$|_Cave$|_Crypt$"  # 地图变体后缀
    r")"
)
DEBUG_VARIANT_RE = re.compile(r"_(?:Resize|Test|BossTest|DistantView)$")
LOCKED_RE = re.compile(r"_Locked$")

_TRANSLATION_PREFIXES = (
    "Text_DesignData_Item_Item_",
    "Text_DesignData_Monster_Monster_",
    "Text_DesignData_Props_Props_",
    "Text_DesignData_Dungeon_DungeonModule_",
    "Text_DesignData_Emote_Emote_",
    "Text_DesignData_ActionSkin_",
)

# ── 地牢分组显示名解析 ──
# 映射 module_group → 该 dungeon 的 1 层 Slot 键
DUNGEON_GROUP_SLOT_KEY: dict[str, str] = {
    "GoblinCave": "Text_UI_WB_DungeonSlot_GoblinCave_1stFloor",
    "FireDeep": "Text_UI_WB_DungeonSlot_GoblinCave_1stFloor",
    "IceCavern": "Text_UI_WB_DungeonSlot_IceCavern_1stFloor",
    "IceAbyss": "Text_UI_WB_DungeonSlot_IceCavern_1stFloor",
    "Ruins": "Text_UI_WB_DungeonSlot_TheCrypts_1stFloor",
    "Crypt": "Text_UI_WB_DungeonSlot_TheCrypts_1stFloor",
    "Inferno": "Text_UI_WB_DungeonSlot_TheCrypts_1stFloor",
    "ShipGraveyard": "Text_WB_DungeonSlot_ShipGraveyard_1stFloor",
}
# 子楼层组 → 该楼层的 Slot 键（括号内原名）
DUNGEON_SUBFLOOR_SLOT_KEY: dict[str, str] = {
    "FireDeep": "Text_UI_WB_DungeonSlot_GoblinCave_2ndFloor",
    "IceAbyss": "Text_UI_WB_DungeonSlot_IceCavern_2ndFloor",
    "Crypt": "Text_UI_WB_DungeonSlot_TheCrypts_2ndFloor",
    "Inferno": "Text_UI_WB_DungeonSlot_TheCrypts_3rdFloor",
}
DUNGEON_FLOOR_NUMBER: dict[str, int] = {
    "GoblinCave": 1,
    "FireDeep": 2,
    "IceCavern": 1,
    "IceAbyss": 2,
    "Ruins": 1,
    "Crypt": 2,
    "Inferno": 3,
    "ShipGraveyard": 1,
}


def resolve_group_label(group: str, translations: dict[str, str]) -> str:
    """从 Game.json 翻译键推导分组显示名。

    主组（如 GoblinCave）格式："{1层名}{层数}层"
    子楼层组（如 FireDeep）格式："{1层名}{层数}层（{该层原名}）"
    """
    slot_key = DUNGEON_GROUP_SLOT_KEY.get(group)
    if not slot_key:
        return group
    base = translations.get(slot_key, group)
    floor = DUNGEON_FLOOR_NUMBER.get(group, 1)
    if group in DUNGEON_SUBFLOOR_SLOT_KEY:
        sub_key = DUNGEON_SUBFLOOR_SLOT_KEY[group]
        sub_name = translations.get(sub_key, "")
        return f"{base}{floor}层（{sub_name}）"
    return f"{base}{floor}层"


# Props 目录中的 _Dummy 实体同时也是怪物
DUMMY_AS_MONSTER = {
    "LivingArmor",
    "LivingStatue",
    "LivingArmor_Elite",
    "LivingArmor_Nightmare",
    "LivingStatue_Elite",
    "LivingStatue_Nightmare",
}

# Ore quality ordering
_ORE_QUALITY_ORDER = {"VeryLow": 0, "Low": 1, "Med": 2, "High": 3}


class NameResolver:
    """Resolves entity names to display translations."""

    def __init__(self, translations: dict[str, str]):
        self._translations = translations
        self._cracked_re = re.compile(r"（裂开）")

    def resolve(self, name: str, translation_key: str | None = None, scope: str = "item") -> str:
        result = self._resolve_inner(name, translation_key, scope)
        return self._cracked_re.sub("", result)

    def _resolve_inner(self, name: str, translation_key: str | None, scope: str) -> str:
        translations = self._translations
        if translation_key and translation_key in translations:
            return translations[translation_key]
        alias_name = TRANSLATION_ALIAS_MAP.get(name, name)
        for prefix in _TRANSLATION_PREFIXES:
            alias_key = prefix + alias_name
            if alias_key in translations:
                return translations[alias_key]
        if name in HARDCODED_TRANSLATIONS:
            return HARDCODED_TRANSLATIONS[name]
        # 模糊后缀剥离后重试 Game.json 前缀匹配
        fuzzy = RESOLVE_FUZZY_RE.sub("", name)
        if fuzzy != name:
            fuzzy_alias = TRANSLATION_ALIAS_MAP.get(fuzzy, fuzzy)
            for prefix in _TRANSLATION_PREFIXES:
                fuzzy_key = prefix + fuzzy_alias
                if fuzzy_key in translations:
                    return translations[fuzzy_key]
        # 第二轮模糊：On/Off+数字/中间段 组合剥离（迭代直到稳定）
        prev = name
        fuzzy2 = name
        while True:
            fuzzy2 = RESOLVE_FUZZY_PASS2_RE.sub("", fuzzy2)
            if fuzzy2 == prev:
                break
            prev = fuzzy2
        if fuzzy2 != name and fuzzy2 != fuzzy:
            fuzzy2_alias = TRANSLATION_ALIAS_MAP.get(fuzzy2, fuzzy2)
            for prefix in _TRANSLATION_PREFIXES:
                fuzzy2_key = prefix + fuzzy2_alias
                if fuzzy2_key in translations:
                    return translations[fuzzy2_key]
        # 剥离末尾数字/难度/矿石品质后缀后重试翻译
        stripped = RESOLVE_STRIP_RE.sub("", name)
        if stripped != name:
            if stripped in HARDCODED_TRANSLATIONS:
                return HARDCODED_TRANSLATIONS[stripped]
            stripped_alias = TRANSLATION_ALIAS_MAP.get(stripped, stripped)
            for prefix in _TRANSLATION_PREFIXES:
                stripped_key = prefix + stripped_alias
                if stripped_key in translations:
                    return translations[stripped_key]
        if scope == "module":
            if name in MODULE_NAME_OVERRIDE:
                return MODULE_NAME_OVERRIDE[name]
            for group_prefix in [
                "Firedeep_",
                "Inferno_",
                "Crypt_",
                "Ruins_",
                "GoblinCave_",
                "Goblin_",
                "IceCavern_",
                "IceCave_",
                "IceAbyss_",
                "ShipGraveyard_",
                "Shipgraveyard_",
                "Swamp_",
                "Cave_",
            ]:
                if name.startswith(group_prefix):
                    stripped = name[len(group_prefix) :]
                    if stripped:
                        alias_key = "Text_DesignData_Dungeon_DungeonModule_" + stripped
                        if alias_key in translations:
                            return translations[alias_key]
        # 剥离地牢分组前缀（Inferno_、Crypt_ 等）后重试翻译
        for group_prefix in [
            "Inferno_",
            "Crypt_",
            "Ruins_",
            "GoblinCave_",
            "Goblin_",
            "IceCavern_",
            "IceCave_",
            "IceAbyss_",
            "ShipGraveyard_",
            "Shipgraveyard_",
            "Swamp_",
            "Cave_",
            "Firedeep_",
            "FireDeep_",
        ]:
            if name.startswith(group_prefix):
                bare = name[len(group_prefix) :]
                if bare in HARDCODED_TRANSLATIONS:
                    return HARDCODED_TRANSLATIONS[bare]
                bare_alias = TRANSLATION_ALIAS_MAP.get(bare, bare)
                for prefix in _TRANSLATION_PREFIXES:
                    bare_key = prefix + bare_alias
                    if bare_key in translations:
                        return translations[bare_key]
                break
        return name


def build_coord_out(c: dict, vc: dict, map_to_module: dict | None = None) -> dict:
    """构建坐标输出 dict，附带变体信息。
    map 字段解析为 dungeon_modules.json 中的模块名（通过 map_to_module 映射）。
    """
    _gp = c.get("group_parent", "")
    _mb = c["map_base"]
    if map_to_module:
        _mb = map_to_module.get(_mb, _mb)
    out = {
        "x": c["x"],
        "y": c["y"],
        "z": c["z"],
        "yaw": c.get("yaw", 0),
        "map": _mb,
        "file": c["json_filename"],
        "version": c["version"],
        "label": c["original_keyword"],
    }
    if _gp:
        out["group_parent"] = _gp
    _sgp = c.get("sub_group_parent", "")
    if _sgp:
        out["sub_group_parent"] = _sgp
    vc_info = vc.get((c["map_base"], c["json_filename"], _gp))
    if vc_info and vc_info[0] > 1:
        out["variant_count"] = vc_info[0]
        out["variant_names"] = vc_info[1]
    _qm = re.search(r"_(VeryLow|Low|Med|High)$", c.get("keyword", "")) or re.search(
        r"_(VeryLow|Low|Med|High)$", c.get("original_keyword", "")
    )
    if _qm:
        out["quality"] = _qm.group(1)
    return out


def filter_coords(coords: list[dict], entity_names: set[str], is_prop: bool = False) -> list[dict]:
    """Keep only coords whose search_term belongs to the target entity type."""

    def _match(c):
        kw = c.get("keyword") or c.get("search_term", "")
        st = c.get("spawner_type", "")
        return bool(kw in entity_names or (is_prop and kw.startswith("Ore_")) or (is_prop and st == "props"))

    return [c for c in coords if _match(c)]


def base_monster_name(name: str) -> str:
    """Strip quality/variant suffixes to get base name."""
    base = HARD_SUFFIX_RE.sub("", name)
    base = QUALITY_RE.sub("", base)
    base = UNIQUE_SUFFIX_RE.sub("", base)
    return base


def ore_quality_key(name: str) -> tuple:
    """Sort key for ore quality variants."""
    m = re.search(r"_(High|Med|Low|VeryLow)$", name)
    return _ORE_QUALITY_ORDER.get(m.group(1), 99) if m else 99
