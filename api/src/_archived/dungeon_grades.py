"""
归档：DungeonGrade 分组代码表和解析器。

曾用于从 DungeonGrade 数值反查模式/分组/楼层，
以及提供 GRADE_DISPLAY_NAMES 硬编码显示名。

迁移日期：2026-07-14
迁移原因：所有函数均无外部调用，实为死代码。
         分组显示名已改为动态从 Game.json 翻译键推导。

注意：MODULE_GROUP_FLOOR_SUFFIXES（在 config.py 中）
      仍在使用，它的 base_code 编码规则与 DUNGEON_GROUP_GRADES 一致。
"""

# ── 地图分组代码表 ────────────────────────────────────────────
# 编码规则（参考 v4 的 LootDropRate.py 的 DUNGEON_GRADE_MAP）：
#   第1位 = 模式（1=PVE, 2=普通, 3=豪客赛, 4=逆袭赛）
#   第2位 = 地图（0=哥布林, 1=冰图, 2=废墟, 3=水图）
#   第3-4位 = 层（01=1层, 02=2层, 03=3层）
# 示例：3001 → 豪客赛+哥布林+1层
#
# 每个 group key 对应 base_code（去掉模式位的后3位）和楼层数。
# 通过 base_code + mode*1000 可计算出完整 DungeonGrade。

DUNGEON_GROUP_GRADES = {
    # group_key        base_code  floors
    "GoblinCave": {"base": 1, "floors": 2, "label": "哥布林洞穴"},
    "FireDeep": {"base": 1, "floors": 2, "label": "哥布林洞穴"},
    "IceCavern": {"base": 11, "floors": 2, "label": "寒冰洞穴"},
    "IceAbyss": {"base": 11, "floors": 2, "label": "寒冰洞穴"},
    "Ruins": {"base": 21, "floors": 3, "label": "废墟"},
    "Crypt": {"base": 21, "floors": 3, "label": "废墟"},
    "Inferno": {"base": 21, "floors": 3, "label": "废墟"},
    "ShipGraveyard": {"base": 31, "floors": 2, "label": "沉船墓场"},
}

# 模式常量
DUNGEON_MODE_PVE = 1
DUNGEON_MODE_NORMAL = 2
DUNGEON_MODE_HIGHROLLER = 3
DUNGEON_MODE_REVERSAL = 4

DUNGEON_MODE_NAMES = {
    DUNGEON_MODE_PVE: "PVE",
    DUNGEON_MODE_NORMAL: "普通",
    DUNGEON_MODE_HIGHROLLER: "豪客赛",
    DUNGEON_MODE_REVERSAL: "逆袭赛",
}

# 反向映射：base_code → group_key（用于从 grade 快速查找分组）
# 注意：多个组共享同一 base_code 时后覆盖，导致碰撞
_BASE_TO_GROUP: dict[int, str] = {}
for _gk, _gv in DUNGEON_GROUP_GRADES.items():
    for _f in range(_gv["floors"]):
        _BASE_TO_GROUP[_gv["base"] + _f] = _gk

# 已知 grade → 中文名
GRADE_DISPLAY_NAMES: dict[int, str] = {
    3001: "豪客哥布林1层",
    3002: "豪客哥布林2层",
    3011: "豪客冰图1层",
    3012: "豪客冰图2层",
    3021: "豪客废墟1层",
    3022: "豪客废墟2层",
    3023: "豪客废墟3层",
    3031: "豪客水图1层",
    3032: "豪客水图2层",
    4002: "逆袭哥布林2层",
    4012: "逆袭冰图2层",
    4023: "逆袭废墟3层",
}

# 参考项目路径（爆率数据来源）
LOOTDROP_RATE_REFERENCE = (
    "Output/Exports/DungeonCrawler/Content/DungeonCrawler/Data/Generated/V2/LootDrop/LootDropRate.py"
)


def parse_grade(grade: int | str) -> dict:
    """
    解析 DungeonGrade 数值，返回模式、地图分组、层级信息。
    所有分组数据来自 DUNGEON_GROUP_GRADES。
    """
    try:
        g = int(grade)
    except (ValueError, TypeError):
        return {
            "grade": grade,
            "mode": 0,
            "mode_name": "未知",
            "group": "",
            "group_label": "未知",
            "floor": 0,
            "display": str(grade),
        }
    mode = g // 1000
    base = g % 1000

    group_key = _BASE_TO_GROUP.get(base)
    if group_key is None:
        return {
            "grade": g,
            "mode": mode,
            "mode_name": DUNGEON_MODE_NAMES.get(mode, f"未知模式{mode}"),
            "group": "",
            "group_label": f"未知({base})",
            "floor": 0,
            "display": GRADE_DISPLAY_NAMES.get(g, f"未知副本{g}"),
        }

    grp = DUNGEON_GROUP_GRADES[group_key]
    floor = base - grp["base"] + 1
    mode_name = DUNGEON_MODE_NAMES.get(mode, f"未知模式{mode}")
    display = GRADE_DISPLAY_NAMES.get(g, f"{mode_name}{grp['label']}{floor}层")

    return {
        "grade": g,
        "mode": mode,
        "mode_name": mode_name,
        "group": group_key,
        "group_label": grp["label"],
        "floor": floor,
        "display": display,
    }


def get_mode(grade: int | str) -> int:
    """提取模式编号（第1位数字）：1=PVE, 2=普通, 3=豪客赛, 4=逆袭赛"""
    return int(grade) // 1000


def get_mode_name(grade: int | str) -> str:
    """提取模式中文名"""
    return DUNGEON_MODE_NAMES.get(get_mode(grade), "未知")


def get_group_for_grade(grade: int | str) -> str:
    """提取对应的 GROUP_TO_ART_DIR key"""
    return parse_grade(grade)["group"]


def get_display_name(grade: int | str) -> str:
    """提取完整中文显示名"""
    return parse_grade(grade)["display"]


def iter_all_grades() -> list[int]:
    """返回所有已知的 DungeonGrade 数值"""
    return sorted(GRADE_DISPLAY_NAMES.keys())


def build_mode_group_map() -> dict[str, list[dict]]:
    """
    按模式分组，返回所有已知 grade 的解析结果。
    """
    result: dict[str, list[dict]] = {}
    for g in iter_all_grades():
        info = parse_grade(g)
        result.setdefault(info["mode_name"], []).append(info)
    return result
