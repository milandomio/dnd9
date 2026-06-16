"""爆率计算模块 — 从 DB 查询 spawner 条目和爆率数据。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from db_manager import DatabaseManager


def get_spawn_rate_for_keyword(db: DatabaseManager, keyword: str) -> int:
    """获取某 keyword 的生成概率（百分比，0~100）。"""
    entries = db.get_spawner_entries_for_keyword(keyword)
    if not entries:
        return 100
    return max(e["spawn_rate"] for e in entries)


def get_drop_rates_for_item(
    db: DatabaseManager,
    item_name: str,
    monster_name: str,
    map_base_to_group: dict[str, str],
    module_group_floor_suffixes: dict[str, list[int]],
    mode_names: dict[int, str],
) -> dict[str, float]:
    """计算某物品在某怪物各模式下的爆率（百分比）。返回 {mode_name: rate%}。"""
    entries = db.get_spawner_entries_for_keyword(monster_name)
    if not entries:
        return {}

    # 取第一个有 lootdrop_group_id 的条目
    ldg_id = ""
    for e in entries:
        if e["lootdrop_group_id"]:
            ldg_id = e["lootdrop_group_id"]
            break
    if not ldg_id:
        return {}

    # 从 monster 的坐标推断 module_group（需要外部传入）
    # 这里简化：对所有模式+楼层组合查询，取最大值
    mode_rates: dict[str, float] = {}
    for mode_id, mode_name in mode_names.items():
        if mode_id == 4:  # 跳过逆袭赛
            continue
        best_rate = 0.0
        for _group, suffixes in module_group_floor_suffixes.items():
            for suffix in suffixes:
                full_grade = mode_id * 1000 + suffix
                rate = db.get_item_drop_rate(ldg_id, item_name, full_grade)
                if rate > best_rate:
                    best_rate = rate
        if best_rate > 0:
            mode_rates[mode_name] = round(best_rate * 100, 1)
    return mode_rates


def get_drop_rates_for_item_with_coords(
    db: DatabaseManager,
    item_name: str,
    monster_name: str,
    coords: list[dict],
    map_base_to_group: dict[str, str],
    module_group_floor_suffixes: dict[str, list[int]],
    mode_names: dict[int, str],
) -> dict[str, float]:
    """计算某物品在某怪物各模式下的爆率（百分比），基于坐标推断楼层。"""
    entries = db.get_spawner_entries_for_keyword(monster_name)
    if not entries:
        return {}

    ldg_id = ""
    for e in entries:
        if e["lootdrop_group_id"]:
            ldg_id = e["lootdrop_group_id"]
            break
    if not ldg_id:
        return {}

    # 从坐标推断涉及的 module_group
    groups_seen: set[str] = set()
    for c in coords:
        g = map_base_to_group.get(c.get("map", ""), "")
        if g:
            groups_seen.add(g)

    # 物品不在坐标对应的 map group 中 → 该坐标无效，不显示爆率
    if not groups_seen:
        return {}

    mode_rates: dict[str, float] = {}
    for mode_id, mode_name in mode_names.items():
        if mode_id == 4:
            continue
        best_rate = 0.0
        for g in groups_seen:
            suffixes = module_group_floor_suffixes.get(g, [])
            for suffix in suffixes:
                full_grade = mode_id * 1000 + suffix
                rate = db.get_item_drop_rate(ldg_id, item_name, full_grade)
                if rate > best_rate:
                    best_rate = rate
        if best_rate > 0:
            mode_rates[mode_name] = round(best_rate * 100, 1)
    return mode_rates
