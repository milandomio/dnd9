"""Index and quest export functions extracted from collector.py."""

import json
import urllib.parse
from pathlib import Path


def _save(output_dir: Path, filename: str, data: list | dict):
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_quest_data(db, output_dir: Path) -> tuple[int, int, list[dict]]:
    """Export quest data from DB. Returns (quest_items_count, quest_npc_count, quest_npcs_data)."""
    quest_items_data = db.get_quest_items()
    quest_npcs_data = db.get_quest_npcs()
    quest_items_count = len(quest_items_data)
    quest_npc_count = sum(n.get("quest_count", 0) for n in quest_npcs_data)
    _save(output_dir, "quest_items.json", quest_items_data)
    _save(output_dir, "quest_npc.json", quest_npcs_data)
    return quest_items_count, quest_npc_count, quest_npcs_data


def _search_url(path: str, params: dict[str, str]) -> str:
    """Append a query string only when at least one param carries a value."""
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
    return f"{path}?{query}" if query else path


def _iter_shop_search_entries(shop_index: dict | None, output_dir: Path) -> list[dict]:
    """One search entry per (region, item) for the goods a dungeon shop sells.

    Shop goods rarely own a detail page, so the entry links to the region page
    and passes the folded item name as ``?item=`` for that page to focus.
    """
    entries: list[dict] = []
    for region in (shop_index or {}).get("regions", []):
        region_id = region.get("region")
        if not region_id:
            continue
        detail_path = output_dir / "dungeon_shops" / f"{region_id}.json"
        if not detail_path.exists():
            continue
        with open(detail_path, encoding="utf-8") as f:
            detail = json.load(f)
        seen: set[str] = set()
        for difficulty in detail.get("difficulties", []):
            for slot in difficulty.get("slots", []):
                for item in slot.get("items", []):
                    item_page = item.get("page") or item.get("name")
                    if not item_page or item_page in seen:
                        continue
                    seen.add(item_page)
                    entry = {
                        "name": item_page,
                        "translation": item.get("translation", item_page),
                        "translation_key": item.get("translation_key", ""),
                        "page": "dungeon_shops",
                        "url": _search_url(
                            f"/dungeon_shops/{urllib.parse.quote(region_id, safe='')}/",
                            {"item": item_page},
                        ),
                    }
                    if region.get("label_key"):
                        entry["tag_translation_key"] = region["label_key"]
                    if region.get("display"):
                        entry["tag"] = region["display"]
                    # A bare region name ("地穴") reads like a map, not a shop;
                    # the frontend prefixes this UI key ("地牢商店-地穴").
                    entry["tag_prefix_key"] = "ui.nav.dungeon_shops"
                    entries.append(entry)
    return entries


def _iter_craft_search_entries(crafts_payload: dict | None) -> list[dict]:
    """Search entries for every crafted product *and* every material it needs.

    Products point at their crafter tab and link with ``?item=<product>`` so the
    card is focused. Materials reuse the same link but carry the product as their
    tag, so a search hit reads "工匠合成 - <product>" — that is how a player
    finds which recipe a herb or ore belongs to.
    """
    entries: list[dict] = []
    if not crafts_payload:
        return entries
    merchants = {merchant.get("name"): merchant for merchant in crafts_payload.get("merchants", [])}
    seen_products: set[tuple[str, str]] = set()
    seen_materials: set[tuple[str, str, str]] = set()
    for recipe in crafts_payload.get("recipes", []):
        merchant_name = recipe.get("merchant")
        item_name = recipe.get("name")
        if not merchant_name or not item_name:
            continue
        merchant = merchants.get(merchant_name, {})
        slug = merchant.get("slug") or merchant_name
        url = _search_url(f"/crafts/{urllib.parse.quote(slug, safe='')}/", {"item": item_name})

        product_key = (merchant_name, item_name)
        if product_key not in seen_products:
            seen_products.add(product_key)
            entry = {
                "name": item_name,
                "translation": recipe.get("translation", item_name),
                "translation_key": recipe.get("translation_key", ""),
                "page": "crafts",
                "url": url,
            }
            if merchant.get("translation_key"):
                entry["tag_translation_key"] = merchant["translation_key"]
            if merchant.get("display"):
                entry["tag"] = merchant["display"]
            # Reads "工匠合成-炼金术师": a crafted item is only reachable
            # through the crafter that makes it.
            entry["tag_prefix_key"] = "ui.search.tag.craft_group"
            entries.append(entry)

        for requirement in recipe.get("requirements") or []:
            material_name = requirement.get("name")
            if not material_name:
                continue
            material_key = (merchant_name, item_name, material_name)
            if material_key in seen_materials:
                continue
            seen_materials.add(material_key)
            material_entry = {
                "name": material_name,
                "translation": requirement.get("translation", material_name),
                "translation_key": requirement.get("translation_key", ""),
                "page": "crafts",
                "url": url,
            }
            if recipe.get("translation_key"):
                material_entry["tag_translation_key"] = recipe["translation_key"]
            if recipe.get("translation"):
                material_entry["tag"] = recipe["translation"]
            # Reads "工匠合成-治疗药水": a material is only searchable through
            # the product it is used for.
            material_entry["tag_prefix_key"] = "ui.search.tag.craft_group"
            entries.append(material_entry)
    return entries


# Quest objectives with no seekable target of their own (a raw damage or hold
# event); they would only add noise to the nav search.
QUEST_OBJECTIVE_SKIP_TYPES = frozenset({"Damage", "Hold"})


def _iter_quest_objective_entries(quest_npcs_data: list[dict]) -> list[dict]:
    """One search entry per quest objective, so an item is searchable by who takes it.

    The row reads "quest title (objective) [NPC]", mirroring the quest NPC search
    bar; the link opens that NPC page with the quest highlighted.
    """
    entries: list[dict] = []
    for npc in quest_npcs_data or []:
        npc_name = npc.get("npc_name")
        if not npc_name:
            continue
        for quest in npc.get("quests", []):
            quest_number = quest.get("quest_number")
            for content in quest.get("contents", []):
                if content.get("type") in QUEST_OBJECTIVE_SKIP_TYPES:
                    continue
                entry = {
                    "name": quest.get("id", ""),
                    "translation": quest.get("title", ""),
                    "translation_key": quest.get("translation_key", ""),
                    "subtitle": content.get("target", ""),
                    "subtitle_key": content.get("translation_key", ""),
                    "page": "quest_npc",
                    "url": _search_url(
                        f"/quest_npc/{urllib.parse.quote(npc_name, safe='')}/",
                        {"quest": str(quest_number)},
                    ),
                }
                if npc.get("translation_key"):
                    entry["tag_translation_key"] = npc["translation_key"]
                if npc.get("npc_name_display"):
                    entry["tag"] = npc["npc_name_display"]
                # Reads "任务-珠宝匠": the NPC alone reads like a merchant row.
                entry["tag_prefix_key"] = "ui.search.tag.quest"
                entries.append(entry)
    return entries


def build_and_save_indexes(
    items_index: list[dict],
    monsters_index: list[dict],
    props_index: list[dict],
    loot_index: list[dict],
    modules_data: list[dict],
    quest_npc_count: int,
    quest_npcs_data: list[dict],
    output_dir: Path,
    group_label_resolver=None,
    shop_index: dict | None = None,
    light_count: int = 0,
    crafts_payload: dict | None = None,
):
    """Build and save index.json + search_index.json."""
    shop_regions = len((shop_index or {}).get("regions", []))
    craft_count = (crafts_payload or {}).get("count", 0)
    index_data = [
        {
            "_comment": "该文件由 api/src/collector.py 自动生成，请勿手动编辑。如需修改，请编辑 collector.py 中的 index_data 列表。"
        },
        {"page": "dungeon_shops", "label": "地牢商店", "count": shop_regions},
        {"page": "crafts", "label": "工匠", "count": craft_count},
        {"page": "lights", "label": "灯", "count": light_count},
        {"page": "quest_npc", "label": "任务NPC表", "count": quest_npc_count},
        {"page": "items", "label": "物品表", "count": len(items_index)},
        {"page": "props", "label": "实体表", "count": len(props_index)},
        {"page": "monsters", "label": "怪物表", "count": len(monsters_index)},
        {"page": "lootdrops", "label": "掉落表", "count": len(loot_index)},
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
                "translation_key": entry.get("translation_key", ""),
                "page": "items",
                "url": f"/items/{urllib.parse.quote(entry['name'], safe='')}/",
            }
        )
    for entry in monsters_index:
        si_entry = {
            "name": entry["name"],
            "translation": entry.get("translation", ""),
            "translation_key": entry.get("translation_key", ""),
            "page": "monsters",
            "url": f"/monsters/{urllib.parse.quote(entry['name'], safe='')}/",
        }
        if entry.get("type"):
            si_entry["type"] = entry["type"]
        if entry.get("race"):
            si_entry["race"] = entry["race"]
        if entry.get("races"):
            si_entry["races"] = entry["races"]
        search_index.append(si_entry)
    for entry in props_index:
        si_entry = {
            "name": entry["name"],
            "translation": entry.get("translation", ""),
            "translation_key": entry.get("translation_key", ""),
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
            "translation_key": entry.get("translation_key", ""),
            "page": "lootdrops",
            "url": f"/lootdrops/{urllib.parse.quote(entry['name'], safe='')}/",
        }
        if entry.get("variant_count") is not None:
            si_entry["variant_count"] = entry["variant_count"]
        if entry.get("monsters"):
            si_entry["monsters"] = entry["monsters"]
        if entry.get("monster_translations"):
            si_entry["monster_translations"] = entry["monster_translations"]
        if entry.get("monster_translation_keys"):
            si_entry["monster_translation_keys"] = entry["monster_translation_keys"]
        si_entry["max_score"] = entry.get("max_score", 0.0)
        if entry.get("hr100"):
            si_entry["hr100"] = True
        for key in (
            "item_type",
            "item_category_key",
            "item_category_translation",
            "item_subtype_keys",
            "item_subtype_translations",
        ):
            if entry.get(key):
                si_entry[key] = entry[key]
        search_index.append(si_entry)
    for entry in quest_npcs_data:
        search_index.append(
            {
                "name": entry["npc_name"],
                "translation": entry.get("npc_name_display", ""),
                "translation_key": entry.get("translation_key", ""),
                "page": "quest_npc",
                "url": "/quest_npc/",
            }
        )
    search_index.extend(_iter_quest_objective_entries(quest_npcs_data))
    search_index.extend(_iter_shop_search_entries(shop_index, output_dir))
    search_index.extend(_iter_craft_search_entries(crafts_payload))
    dm_groups = {}
    for module in modules_data:
        group = module.get("group")
        if group and group not in dm_groups:
            dm_groups[group] = module.get("group_key", "")
    for g, group_key in sorted(dm_groups.items()):
        search_index.append(
            {
                "name": g,
                "translation": group_label_resolver(g) if group_label_resolver else g,
                "translation_key": group_key,
                "page": "dungeon_modules",
                "url": f"/dungeon_modules/{urllib.parse.quote(g, safe='')}/",
            }
        )
    for m in modules_data:
        search_index.append(
            {
                "name": m["name"],
                "translation": m.get("translation", m["name"]),
                "translation_key": m.get("translation_key", ""),
                "page": "dungeon_modules",
                "tag": (
                    group_label_resolver(m.get("group", "")) if group_label_resolver else (m.get("group", "") or "模块")
                ),
                "tag_translation_key": m.get("group_key", ""),
                "url": f"/dungeon_modules/{urllib.parse.quote(m.get('group', '') or '', safe='')}/{urllib.parse.quote(m['name'], safe='')}/",
            }
        )
    # 顺序与首页菜单一致（index.json 的 index_data 同序）。
    LIST_PAGES = [  # noqa: N806
        {"name": "dungeon_shops", "translation": "地牢商店", "page": "_nav", "url": "/dungeon_shops/"},
        {"name": "crafts", "translation": "工匠", "page": "_nav", "url": "/crafts/"},
        {"name": "lights", "translation": "灯", "page": "_nav", "url": "/lights/"},
        {"name": "quest_npc", "translation": "任务NPC表", "page": "_nav", "url": "/quest_npc/"},
        {"name": "items", "translation": "物品表", "page": "_nav", "url": "/items/"},
        {"name": "props", "translation": "实体表", "page": "_nav", "url": "/props/"},
        {"name": "monsters", "translation": "怪物表", "page": "_nav", "url": "/monsters/"},
        {"name": "lootdrops", "translation": "掉落表", "page": "_nav", "url": "/lootdrops/"},
        {"name": "dungeon_modules", "translation": "地图模块表", "page": "_nav", "url": "/dungeon_modules/"},
    ]
    search_index.extend(LIST_PAGES)
    _save(output_dir, "search_index.json", search_index)
    return index_data
