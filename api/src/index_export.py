"""Index and quest export functions extracted from collector.py."""

import json
import urllib.parse
from pathlib import Path

from config import HARDCODED_TRANSLATIONS


def _save(output_dir: Path, filename: str, data: list | dict):
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_quest_data(db, output_dir: Path) -> tuple[int, int, int, list[dict]]:
    """Export quest data from DB. Returns (explore_count, quest_items_count, quest_npc_count, quest_npcs_data)."""
    explore_data = db.get_explore_targets()
    quest_items_data = db.get_quest_items()
    quest_npcs_data = db.get_quest_npcs()
    explore_count = len(explore_data)
    quest_items_count = len(quest_items_data)
    quest_npc_count = sum(n.get("quest_count", 0) for n in quest_npcs_data)
    _save(output_dir, "explore.json", explore_data)
    _save(output_dir, "quest_items.json", quest_items_data)
    _save(output_dir, "quest_npc.json", quest_npcs_data)
    return explore_count, quest_items_count, quest_npc_count, quest_npcs_data


def generate_quest_items_groups(db, merged_loot, resolve_name, all_coords, modules, output_dir: Path):
    """Generate quest items groups with coordinates."""
    quest_items_path = output_dir / "quest_items.json"
    if not quest_items_path.exists():
        return
    with open(quest_items_path) as f:
        quest_items = json.load(f)

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
            mtrans = resolve_name(mn, None, "monster")
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
                        "type": "monster",
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

    GROUP_LABELS = {  # noqa: N806
        "Crypt": "废墟2层地牢",
        "FireDeep": "哥布林洞穴2层",
        "GoblinCave": "哥布林洞穴1层",
        "IceAbyss": "冰图2层",
        "IceCavern": "冰图1层",
        "Inferno": "废墟3层炼狱",
        "Ruins": "废墟1层",
        "ShipGraveyard": "水图",
        "Swamp": "沼泽",
    }
    groups_index = []
    for gname in sorted(groups):
        g = groups[gname]
        g["group_display"] = GROUP_LABELS.get(gname, gname)
        entities = list(g["entities"].values())
        for e in entities:
            e.pop("_seen_coords", None)
        pos_count = sum(len(e["coords"]) for e in entities)
        groups_index.append(
            {
                "group": gname,
                "group_display": g["group_display"],
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
                "entities": entities,
            },
        )
    _save(output_dir, "quest_items_groups.json", groups_index)


def build_and_save_indexes(
    items_index: list[dict],
    monsters_index: list[dict],
    props_index: list[dict],
    loot_index: list[dict],
    modules_data: list[dict],
    explore_count: int,
    quest_items_count: int,
    quest_npc_count: int,
    quest_npcs_data: list[dict],
    output_dir: Path,
):
    """Build and save index.json + search_index.json."""
    index_data = [
        {
            "_comment": "该文件由 api/src/collector.py 自动生成，请勿手动编辑。如需修改，请编辑 collector.py 中的 index_data 列表。"
        },
        {"page": "items", "label": "物品表", "count": len(items_index)},
        {"page": "props", "label": "实体表", "count": len(props_index)},
        {"page": "monsters", "label": "怪物表", "count": len(monsters_index)},
        {"page": "lootdrops", "label": "掉落表", "count": len(loot_index)},
        {"page": "explore", "label": "任务探索表", "count": explore_count},
        {"page": "quest_items", "label": "任务物品表", "count": quest_items_count},
        {"page": "quest_npc", "label": "任务NPC表", "count": quest_npc_count},
        {"page": "dungeon_modules", "label": "地图模块表", "count": len(modules_data)},
    ]
    _save(output_dir, "index.json", index_data)

    # ── search_index.json ──
    search_index = []
    for entry in items_index:
        search_index.append(
            {
                "name": entry["name"],
                "translation": entry.get("translation", ""),
                "page": "items",
                "url": f"/items/{urllib.parse.quote(entry['name'], safe='')}/",
            }
        )
    for entry in monsters_index:
        search_index.append(
            {
                "name": entry["name"],
                "translation": entry.get("translation", ""),
                "page": "monsters",
                "url": f"/monsters/{urllib.parse.quote(entry['name'], safe='')}/",
            }
        )
    for entry in props_index:
        si_entry = {
            "name": entry["name"],
            "translation": entry.get("translation", ""),
            "page": "props",
            "url": f"/props/{urllib.parse.quote(entry['name'], safe='')}/",
        }
        if entry.get("type"):
            si_entry["type"] = entry["type"]
        search_index.append(si_entry)
    for entry in loot_index:
        si_entry = {
            "name": entry["name"],
            "translation": entry.get("translation", ""),
            "page": "lootdrops",
            "url": f"/lootdrops/{urllib.parse.quote(entry['name'], safe='')}/",
        }
        if entry.get("variant_count") is not None:
            si_entry["variant_count"] = entry["variant_count"]
        if entry.get("monsters"):
            si_entry["monsters"] = entry["monsters"]
        if entry.get("monster_translations"):
            si_entry["monster_translations"] = entry["monster_translations"]
        si_entry["max_score"] = entry.get("max_score", 0.0)
        search_index.append(si_entry)
    for entry in quest_npcs_data:
        search_index.append(
            {
                "name": entry["npc_name"],
                "translation": entry.get("npc_name_display", ""),
                "page": "quest_npc",
                "url": "/quest_npc/",
            }
        )
    dm_groups = sorted({m.get("group") for m in modules_data if m.get("group")})
    GROUP_LABELS = {  # noqa: N806
        "Crypt": "废墟2层地牢",
        "FireDeep": "哥布林洞穴2层",
        "GoblinCave": "哥布林洞穴1层",
        "IceAbyss": "冰图2层",
        "IceCavern": "冰图1层",
        "Inferno": "废墟3层炼狱",
        "Ruins": "废墟1层",
        "ShipGraveyard": "水图",
        "Swamp": "沼泽",
    }
    for g in dm_groups:
        search_index.append(
            {
                "name": g,
                "translation": GROUP_LABELS.get(g, g),
                "page": "dungeon_modules",
                "url": f"/dungeon_modules/{urllib.parse.quote(g, safe='')}/",
            }
        )
    for m in modules_data:
        search_index.append(
            {
                "name": m["name"],
                "translation": m.get("translation", m["name"]),
                "page": "dungeon_modules",
                "tag": GROUP_LABELS.get(m.get("group", ""), m.get("group", "模块")),
                "url": f"/dungeon_modules/{urllib.parse.quote(m.get('group', '') or '', safe='')}/{urllib.parse.quote(m['name'], safe='')}/",
            }
        )
    LIST_PAGES = [  # noqa: N806
        {"name": "items", "translation": "物品表", "page": "_nav", "url": "/items/"},
        {"name": "monsters", "translation": "怪物表", "page": "_nav", "url": "/monsters/"},
        {"name": "props", "translation": "实体表", "page": "_nav", "url": "/props/"},
        {"name": "lootdrops", "translation": "掉落表", "page": "_nav", "url": "/lootdrops/"},
        {"name": "explore", "translation": "任务探索表", "page": "_nav", "url": "/explore/"},
        {"name": "quest_npc", "translation": "任务NPC表", "page": "_nav", "url": "/quest_npc/"},
        {"name": "dungeon_modules", "translation": "地图模块表", "page": "_nav", "url": "/dungeon_modules/"},
    ]
    search_index.extend(LIST_PAGES)
    _save(output_dir, "search_index.json", search_index)
    return index_data
