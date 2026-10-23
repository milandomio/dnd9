"""稀有模块在地牢中的出现概率。

公式（`docs/BLINDFALL_PIT_PROBABILITY_RECORD.md`）::

    P = 含 Rare 槽的布局数 / 布局总数
      x 1 / 同组 bIsRare 模块数
      x ((LayoutSize^2 - 固定模块占用格) / LayoutSize^2)

三部分的数据来源：

1. **稀有槽是否存在**：`DCDungeonDataAsset.Properties.NumMaxRares`。只有声明了
   该字段（且 > 0）的地图组才有 Rare 槽机制；未声明的组（FireDeep、Ruins 等）
   直接不产生稀有模块概率，不会借用别组的布局统计。
2. **布局因子**：`DCDungeonLayoutDataAsset` 中 `SlotType == Rare` 的槽位分布在
   多少个布局里。该资产目录在当前游戏导出中缺失，缺失时退回
   `BASELINE_LAYOUT_FACTORS` 记录的历史实测值并在管道日志中告警。
3. **稀有池**：同 `ModuleType` 下 `bIsRare == true` 且已被 5x5 收录的模块数，
   按均匀抽取处理。该值随收录规则自动变化。

覆盖修正用的固定模块占用格按 `DungeonModule.Size` 实时累加。
"""

import json
import re

from config import DATA_DIR, DUNGEON_MODULE_DIR, GAME_ROOT

LAYOUT_DIR = GAME_ROOT / "Data" / "Generated" / "V2" / "Dungeon" / "DungeonLayout"
DUNGEON_DIR = DATA_DIR / "Dungeon" / "Dungeon"

_SLOT_RARE = "EDCDungeonLayoutSlotType::Rare"
_SLOT_FIXED = "EDCDungeonLayoutSlotType::Fixed"
_MODULE_NAME_RE = re.compile(r"'(Id_DungeonModule_[^']+)'")

# 布局资产缺失时的回退：group -> (布局总数, 含 Rare 槽的布局数)。
# 数据来自 docs/BLINDFALL_PIT_PROBABILITY_RECORD.md 对 Crypt 5x5 的实测。
# 只描述布局层；稀有槽存在性、稀有池、覆盖修正始终由资产实时计算。
BASELINE_LAYOUT_FACTORS = {"Crypt": (40, 2)}
# 回退模式下仍占据地图格的固定模块；尺寸从 DungeonModule 资产实时读取。
BASELINE_FIXED_MODULES = ("CenterTower",)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _module_sizes(module_dir) -> dict:
    sizes = {}
    if not module_dir.exists():
        return sizes
    for fp in module_dir.glob("*.json"):
        data = _read_json(fp)
        for entry in data if isinstance(data, list) else [data]:
            props = (entry or {}).get("Properties") or {}
            size = props.get("Size") or {}
            sizes[fp.stem.replace("Id_DungeonModule_", "")] = (
                size.get("X") or 1,
                size.get("Y") or 1,
            )
    return sizes


def _module_ref(slot_type: dict) -> str:
    module = (slot_type or {}).get("Module") or {}
    match = _MODULE_NAME_RE.search(str(module.get("ObjectName", "")))
    if not match:
        return ""
    return match.group(1).replace("Id_DungeonModule_", "")


def rare_groups(dungeon_dir=DUNGEON_DIR) -> set:
    """地图组中声明了 NumMaxRares > 0 的组，即真正存在 Rare 槽机制的组。"""
    groups = set()
    if not dungeon_dir.exists():
        return groups
    for fp in dungeon_dir.glob("*.json"):
        data = _read_json(fp)
        for entry in data if isinstance(data, list) else [data]:
            props = (entry or {}).get("Properties") or {}
            if (props.get("NumMaxRares") or 0) <= 0:
                continue
            group = (props.get("ModuleType") or "").removeprefix("EDCDungeonModuleType::")
            if group:
                groups.add(group)
    return groups


def layout_stats(module_dir=DUNGEON_MODULE_DIR, layout_dir=LAYOUT_DIR) -> dict:
    """group -> {source, layouts, rare_layouts, grid, fixed_cells}.

    `source` is `"assets"` when real layout assets were read, `"baseline"`
    when the documented fallback for that group is used.
    """
    files = sorted(layout_dir.glob("*.json")) if layout_dir.exists() else []
    sizes = _module_sizes(module_dir)
    baseline_cells = [sx * sy for sx, sy in (sizes.get(name, (1, 1)) for name in BASELINE_FIXED_MODULES)]

    def _baseline(group):
        layouts, rare_layouts = BASELINE_LAYOUT_FACTORS.get(group, (0, 0))
        return {
            "source": "baseline",
            "layouts": layouts,
            "rare_layouts": rare_layouts,
            "grid": 5,
            "fixed_cells": [sum(baseline_cells)],
        }

    if not files:
        return {g: _baseline(g) for g in rare_groups(module_dir.parent / "Dungeon")}

    # 布局文件名形如 Id_DungeonLayout_Crypt_5x5_01，用第二段作为地图组。
    per_group = {}
    for fp in files:
        parts = fp.stem.replace("Id_DungeonLayout_", "").split("_")
        group = parts[0] if parts else ""
        data = _read_json(fp)
        if data is None:
            continue
        entry = (data[0] if isinstance(data, list) else data) or {}
        props = entry.get("Properties") or {}
        size = props.get("Size") or {}
        bucket = per_group.setdefault(
            group, {"layouts": 0, "rare_layouts": 0, "grid": size.get("X") or 5, "fixed_cells": []}
        )
        bucket["layouts"] += 1
        layout_rare = 0
        layout_cells = 0
        for slot in props.get("Slots") or []:
            for slot_type in slot.get("SlotTypes") or []:
                kind = slot_type.get("SlotType", "")
                if kind == _SLOT_RARE:
                    layout_rare += 1
                elif kind == _SLOT_FIXED:
                    sx, sy = sizes.get(_module_ref(slot_type), (1, 1))
                    layout_cells += sx * sy
        if layout_rare:
            bucket["rare_layouts"] += 1
        bucket["fixed_cells"].append(layout_cells)

    stats = {}
    for group, bucket in per_group.items():
        if not bucket["rare_layouts"]:
            continue
        stats[group] = {"source": "assets", **bucket}
    for group in rare_groups(module_dir.parent / "Dungeon"):
        stats.setdefault(group, _baseline(group))
    return stats


def rare_pool_sizes(modules: list) -> dict:
    """group -> number of collected bIsRare modules in that group."""
    pool = {}
    for module in modules:
        if not module.get("is_rare"):
            continue
        group = module.get("module_group") or ""
        if group:
            pool[group] = pool.get(group, 0) + 1
    return pool


def compute_spawn_rates(modules: list, stats: dict | None = None) -> dict:
    """module name -> appearance probability in percent, rounded to 2 decimals."""
    if stats is None:
        stats = layout_stats()
    pool = rare_pool_sizes(modules)
    rates = {}
    for module in modules:
        group = module.get("module_group") or ""
        members = pool.get(group) or 0
        info = stats.get(group) or {}
        layouts = info.get("layouts") or 0
        rare_layouts = info.get("rare_layouts") or 0
        if not module.get("is_rare") or not members or not layouts or not rare_layouts:
            continue
        grid = info.get("grid") or 5
        grid_cells = grid * grid
        fixed = info.get("fixed_cells") or []
        covered = sum(fixed) / len(fixed) if fixed else 0
        coverage = max(grid_cells - covered, 0) / grid_cells
        rates[module["module_name"]] = round(100 * (rare_layouts / layouts) / members * coverage, 2)
    return rates
