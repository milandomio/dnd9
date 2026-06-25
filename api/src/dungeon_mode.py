"""
DungeonGrade 解析器：从 config.DUNGEON_GROUP_GRADES 读取分组代码表。

用法：
    from dungeon_mode import parse_grade
    info = parse_grade(3001)
    # → {"grade": 3001, "mode": 3, "mode_name": "豪客赛",
    #    "group": "GoblinCave", "group_label": "哥布林洞穴",
    #    "floor": 1, "display": "豪客哥布林1层"}
"""

from __future__ import annotations

from config import (
    _BASE_TO_GROUP,
    DUNGEON_GROUP_GRADES,
    DUNGEON_MODE_NAMES,
    GRADE_DISPLAY_NAMES,
)


def parse_grade(grade: int | str) -> dict:
    """
    解析 DungeonGrade 数值，返回模式、地图分组、层级信息。
    所有分组数据来自 config.DUNGEON_GROUP_GRADES。
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
    用于后端输出 JSON 供前端使用。
    """
    result: dict[str, list[dict]] = {}
    for g in iter_all_grades():
        info = parse_grade(g)
        result.setdefault(info["mode_name"], []).append(info)
    return result
