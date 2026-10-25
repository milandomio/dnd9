"""归档：【任务物品表】分组导出逻辑。

迁移日期：2026-10-25
迁移原因：用户要求把【任务物品表】栏目的代码存档、不再使用，并从主页移除入口。
         前端列表页归档在 `web/src/_archived/QuestItemsPage.tsx`，分组详情页的
         quest_group 模式归档在 `web/src/_archived/QuestGroupMode.tsx`。

被摘除的内容（原位置 → 本文件对应函数）：
  1. `index_export.generate_quest_items_groups()`（原 index_export.py 第 29-234 行）
     → 本文件同名函数，原样保留。
  2. `collector.py` 中的 `with pipe.step("quest_items_groups")` 调用。

未归档（仍在活跃使用，禁止删除）：
  - DB 的 `quest_items` 表、`db.import_quest_items()`、`db.get_quest_items()`；
  - `index_export.save_quest_data()` 仍导出 `quest_items.json`（管道内部文件，
    已无消费者，保留以便恢复）。

恢复方式：
  1. 把本文件内容并回 `api/src/index_export.py`（需要恢复
     `from config import HARDCODED_TRANSLATIONS` 与
     `from translator import resolve_group_label, resolve_translation_key`）；
  2. `collector.py` 恢复 `from index_export import generate_quest_items_groups`
     与 `with pipe.step("quest_items_groups")` 调用块；
  3. `locale_builder.py` 的 `subdirs` 恢复 `quest_items_groups`；
  4. 前端按 `QuestItemsPage.tsx` / `QuestGroupMode.tsx` 头部说明恢复路由与 SSG。
"""

import json
from pathlib import Path

from config import HARDCODED_TRANSLATIONS
from translator import resolve_group_label, resolve_translation_key


def _save(output_dir: Path, filename: str, data: list | dict):
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_quest_items_groups(
    db,
    merged_loot,
    resolve_name,
    all_coords,
    modules,
    output_dir: Path,
    group_label_resolver=None,
):
    """Generate quest items groups with coordinates."""
    import logging

    quest_items_path = output_dir / "quest_items.json"
    if not quest_items_path.exists():
        logging.getLogger(__name__).warning("quest_items.json not found, skipping quest items groups")
        return
    with open(quest_items_path) as f:
        quest_items = json.load(f)

    entity_classification = db.get_entity_classification()
    entity_classification_lower = {name.lower(): value for name, value in entity_classification.items()}

    def entity_meta(name: str) -> dict:
        exact = entity_classification.get(name) or entity_classification_lower.get(name.lower())
        if exact:
            return exact
        name_lower = name.lower()
        for candidate in sorted(entity_classification, key=len):
            if candidate.lower().startswith(f"{name_lower}_"):
                metadata = entity_classification[candidate]
                if metadata.get("translation_key"):
                    return metadata
        return {}

    def entity_type_and_scope(name: str) -> tuple[str, str]:
        types = entity_meta(name).get("types", [])
        if "monster" in types:
            return "monster", "monster"
        if "props" in types:
            return "props", "props"
        if "item" in types:
            return "item", "item"
        return "monster", "monster"

    # Build map_base -> module_group lookup
    map_to_group = {}
    for m in modules:
        g = m.get("module_group", "") or ""
        if g:
            map_to_group[m["module_name"]] = g
            if m.get("sl_base_name"):
                map_to_group[m["sl_base_name"]] = g

    item_names = sorted(set(qi["item_name"] for qi in quest_items))
    quest_map = {}
    for qi in quest_items:
        quest_map.setdefault(qi["item_name"], []).append(qi)

    _COLORS = [  # noqa: N806
        "#E74C3C",
        "#3498DB",
        "#2ECC71",
        "#E67E22",
        "#9B59B6",
        "#1ABC9C",
        "#F39C12",
        "#2980B9",
        "#D35400",
        "#C0392B",
        "#7F8C8D",
        "#27AE60",
        "#16A085",
        "#8E44AD",
        "#2C3E50",
        "#F1C40F",
    ]

    groups = {}
    ci = 0
    for item_name in item_names:
        info_list = quest_map.get(item_name, [])
        trans = info_list[0]["item_translation"] if info_list else item_name
        item_translation_key = resolve_translation_key(item_name, entity_meta(item_name).get("translation_key"))

        icoords = all_coords.get(item_name, [])
        mnames = merged_loot.get(item_name, [])
        for c in icoords:
            mb = c["map_base"]
            mt = map_to_group.get(mb, "")
            if not mt:
                continue
            groups.setdefault(mt, {"group": mt, "entities": {}})
            ek = f"item::{item_name}"
            if ek not in groups[mt]["entities"]:
                groups[mt]["entities"][ek] = {
                    "name": item_name,
                    "translation": trans,
                    "translation_key": item_translation_key,
                    "type": "item",
                    "color": _COLORS[ci % len(_COLORS)],
                    "coords": [],
                    "quest_npcs": [
                        {
                            "npc_name": qi["npc_name"],
                            "npc_name_cn": qi["npc_name_cn"],
                            "quest_number": qi["quest_number"],
                            "count": qi["count"],
                        }
                        for qi in info_list
                    ],
                }
                ci += 1
            groups[mt]["entities"][ek]["coords"].append(
                {
                    "x": c["x"],
                    "y": c["y"],
                    "z": c["z"],
                    "yaw": c.get("yaw", 0),
                    "map": mb,
                    "file": c["json_filename"],
                    "version": c["version"],
                    "label": HARDCODED_TRANSLATIONS.get(c["original_keyword"], c["original_keyword"]),
                }
            )
        for mn in sorted(mnames):
            if mn == item_name:
                continue
            entity_type, scope = entity_type_and_scope(mn)
            raw_translation_key = entity_meta(mn).get("translation_key")
            mtrans = resolve_name(mn, raw_translation_key, scope)
            monster_translation_key = resolve_translation_key(mn, raw_translation_key)
            mcoords = all_coords.get(mn, [])
            for c in mcoords:
                mb = c["map_base"]
                mt = map_to_group.get(mb, "")
                if not mt:
                    continue
                groups.setdefault(mt, {"group": mt, "entities": {}})
                ek = f"monster::{mn}"
                if ek not in groups[mt]["entities"]:
                    groups[mt]["entities"][ek] = {
                        "name": mn,
                        "translation": mtrans,
                        "translation_key": monster_translation_key,
                        "type": entity_type,
                        "color": _COLORS[ci % len(_COLORS)],
                        "coords": [],
                        "quest_items": [item_name],
                        "_seen_coords": set(),
                    }
                    ci += 1
                else:
                    if item_name not in groups[mt]["entities"][ek]["quest_items"]:
                        groups[mt]["entities"][ek]["quest_items"].append(item_name)
                coord_key = (c["x"], c["y"], c["z"], mb, c["json_filename"])
                if coord_key not in groups[mt]["entities"][ek]["_seen_coords"]:
                    groups[mt]["entities"][ek]["_seen_coords"].add(coord_key)
                    groups[mt]["entities"][ek]["coords"].append(
                        {
                            "x": c["x"],
                            "y": c["y"],
                            "z": c["z"],
                            "yaw": c.get("yaw", 0),
                            "map": mb,
                            "file": c["json_filename"],
                            "version": c["version"],
                            "label": HARDCODED_TRANSLATIONS.get(c["original_keyword"], c["original_keyword"]),
                        }
                    )

    groups_index = []
    for gname in sorted(groups):
        g = groups[gname]
        g["group_display"] = group_label_resolver(gname) if group_label_resolver else gname
        gl = resolve_group_label(gname)
        group_key = gl["slot_key"] if gl else gname
        group_floor = gl["floor"] if gl else 1
        group_sub_key = gl["sub_key"] if gl else None
        entities = list(g["entities"].values())
        for e in entities:
            e.pop("_seen_coords", None)
        pos_count = sum(len(e["coords"]) for e in entities)
        groups_index.append(
            {
                "group": gname,
                "group_display": g["group_display"],
                "group_key": group_key,
                "group_floor": group_floor,
                "group_sub_key": group_sub_key,
                "entity_count": len(entities),
                "position_count": pos_count,
            }
        )
        _save(
            output_dir,
            f"quest_items_groups/{gname}.json",
            {
                "group": gname,
                "group_display": g["group_display"],
                "group_key": group_key,
                "group_floor": group_floor,
                "group_sub_key": group_sub_key,
                "entities": entities,
            },
        )
    _save(output_dir, "quest_items_groups.json", groups_index)
