"""稀有模块在地牢中的出现概率。

数据来源：`DCDungeonDataAsset.Properties.RareChance`。

1. **稀有组**：只有 `NumMaxRares > 0` 的地图组存在 Rare 槽机制；未声明的组
   （FireDeep、Ruins 等）不产生稀有模块概率。
2. **出现概率**：同组内 `bIsRare == true` 且已被 5x5 收录的模块，统一取该组的
   `RareChance`（百分比）。

历史背景：2026-10-16 之后的游戏导出已不再包含 `DungeonLayout` 资产，
`Id_Dungeon_Random*.json` 也移除了 `Layouts` 字段，原先按
「含 Rare 槽布局数 / 布局总数」统计的布局模型失去数据来源。因此当前改为直接
使用 `RareChance`。该字段的精确作用域（按局还是按槽判定）仍待游戏内实测确认，
确认后只需调整本模块。
"""

import json

from config import DUNGEON_DIR


def _dungeon_properties(dungeon_dir):
    """Yield Properties of every DCDungeonDataAsset in the random dungeon dir."""
    if not dungeon_dir.exists():
        return
    for fp in sorted(dungeon_dir.glob("*.json")):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        for entry in data if isinstance(data, list) else [data]:
            if not isinstance(entry, dict):
                continue
            yield entry.get("Properties") or {}


def _group(props: dict) -> str:
    return (props.get("ModuleType") or "").removeprefix("EDCDungeonModuleType::")


def rare_groups(dungeon_dir=DUNGEON_DIR) -> set:
    """地图组中声明了 NumMaxRares > 0 的组，即真正存在 Rare 槽机制的组。"""
    groups = set()
    for props in _dungeon_properties(dungeon_dir):
        if (props.get("NumMaxRares") or 0) <= 0:
            continue
        group = _group(props)
        if group:
            groups.add(group)
    return groups


def rare_chances(dungeon_dir=DUNGEON_DIR) -> dict:
    """group -> RareChance percentage for every group declaring rare slots.

    All mode variants of a group currently share the same value; if they ever
    diverge, the highest one wins so the result stays deterministic.
    """
    chances: dict[str, float] = {}
    for props in _dungeon_properties(dungeon_dir):
        if (props.get("NumMaxRares") or 0) <= 0:
            continue
        chance = props.get("RareChance")
        if chance is None:
            continue
        group = _group(props)
        if not group:
            continue
        value = float(chance)
        if value > chances.get(group, 0.0):
            chances[group] = value
    return chances


def compute_spawn_rates(modules: list, chances: dict | None = None) -> dict:
    """module name -> appearance probability in percent, rounded to 2 decimals."""
    if chances is None:
        chances = rare_chances()
    rates = {}
    for module in modules:
        if not module.get("is_rare"):
            continue
        group = module.get("module_group") or ""
        chance = chances.get(group)
        if not chance or chance <= 0:
            continue
        rates[module["module_name"]] = round(float(chance), 2)
    return rates
