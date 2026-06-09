import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from quest_extractor.translator import Translator
from quest_extractor.quest_extractor import QuestExtractor

from config import OUTPUT_DIR


def run_quest_extraction():
    print("\n--- Quest Extraction ---")
    translator = Translator(language="zh-Hans")
    extractor = QuestExtractor(translator=translator)
    quests = extractor.load_all_quests()
    print(f"  loaded {len(quests)} quests")

    explore = _extract_explore(translator, extractor, quests)
    _save_json("explore.json", explore)
    print(f"  explore targets: {len(explore)}")

    fetch_items = _extract_fetch(translator, extractor, quests)
    _save_json("quest_items.json", fetch_items)
    print(f"  quest items: {len(fetch_items)}")

    npcs = _extract_npc_list(translator, extractor, quests)
    _save_json("quest_npc.json", npcs)
    print(f"  active NPCs: {len(npcs)}")

    return len(explore), len(fetch_items), len(npcs)


def _extract_explore(translator, extractor, quests):
    explore_targets = []
    seen = set()
    for quest in quests:
        npc_name = quest.get("npc_name", "")
        if not _is_npc_active(npc_name):
            continue
        for content in quest.get("contents", []):
            if content.get("content_type") != "Explore":
                continue
            asset_path = content.get("asset_path", "")
            if not asset_path:
                continue
            translation = extractor.get_explore_target_translation(asset_path) or ""
            module_name = extractor.match_asset_path_to_module(asset_path) or ""
            if not translation and not module_name:
                continue
            clean_module = module_name.rsplit(".", 1)[-1].removesuffix("_A").removesuffix("_D").removesuffix("_S").removesuffix("_HR_D") if module_name else ""
            key = clean_module or translation
            if key in seen:
                continue
            seen.add(key)
            explore_targets.append({
                "name": translation,
                "module_name": clean_module,
                "quest_id": quest.get("id", ""),
                "quest_title": quest.get("title_display", ""),
                "quest_number": quest.get("quest_number", 0),
                "npc_name": npc_name,
                "npc_name_display": quest.get("npc_name_display", npc_name),
            })
    explore_targets.sort(key=lambda x: (x["quest_number"], x["npc_name"]))
    return explore_targets


def _extract_fetch(translator, extractor, quests):
    fetch_items = []
    seen = set()
    for quest in quests:
        npc_name = quest.get("npc_name", "")
        if not _is_npc_active(npc_name):
            continue
        for content in quest.get("contents", []):
            if content.get("content_type") != "Fetch":
                continue
            cd = content.get("content_data", {}) or {}
            item_name = ""
            type_tag = cd.get("TypeTag", {}) or {}
            tag_name = type_tag.get("TagName", "")
            if tag_name and "Type.Item." in tag_name:
                item_name = tag_name.split("Type.Item.")[-1]
            if not item_name:
                item_tag = cd.get("ItemIdTag", {}) or {}
                item_name = item_tag.get("TagName", "")
            if not item_name:
                continue
            item_name_en = item_name.removeprefix("DesignData_Item_Item_").removeprefix("DesignData_Props_Props_").removeprefix("DesignData_Monster_Monster_")
            key = (item_name_en, npc_name, quest.get("quest_number", 0))
            if key in seen:
                continue
            seen.add(key)
            rarity_tag = cd.get("RarityType", {}) or {}
            loot_state = cd.get("ItemLootState", "")
            fetch_items.append({
                "item_name": item_name_en,
                "item_translation": translator.translate(item_name) or item_name_en,
                "npc_name": npc_name,
                "npc_name_cn": quest.get("npc_name_display", npc_name),
                "quest_number": quest.get("quest_number", 0),
                "count": cd.get("ContentCount", 1),
                "rarity": rarity_tag.get("TagName", "").removeprefix("Engine.RarityType.") if rarity_tag else "",
                "is_loot": "是" if loot_state == "Looted" else "",
            })
    fetch_items.sort(key=lambda x: (x["npc_name"], x["quest_number"]))
    return fetch_items


def _get_npc_category(npc_en):
    equipment = {"Armourer", "Goldsmith", "Leathersmith", "Tailor", "Weaponsmith"}
    preferred = {"GoblinMerchant", "TavernMaster"}
    not_recommended = {"Squire", "Dealmaker", "Cockatrice", "Huntress"}
    if npc_en in equipment:
        return "装备NPC"
    if npc_en in preferred:
        return "优选NPC"
    if npc_en in not_recommended:
        return ""
    return "可用NPC"

def _extract_npc_list(translator, extractor, quests):
    grouped_en = extractor.group_quests_by_npc(use_translated_names=False)
    result = []
    for npc_en, quest_list in sorted(grouped_en.items()):
        if not _is_npc_active(npc_en):
            continue
        npc_display = translator.translate_npc(npc_en) or npc_en
        quests_out = []
        for q in quest_list:
            rewards = []
            for ri in q.get("rewards", []) or []:
                rtype = ri.get("RewardType", "")
                rid = ri.get("RewardId", {}) or {}
                rname = rid.get("AssetPathName", "") if isinstance(rid, dict) else str(rid)
                rewards.append({
                    "type": rtype,
                    "id": rname.split("/")[-1].split(".")[0] if rname else rtype,
                    "count": ri.get("RewardCount", 0),
                })
            quests_out.append({
                "id": q.get("id", ""),
                "title": q.get("title_display", ""),
                "quest_number": q.get("quest_number", 0),
                "greeting": q.get("greeting_display", ""),
                "complete": q.get("complete_display", ""),
                "rewards": rewards,
                "required": q.get("required_quest", ""),
            })
        result.append({
            "npc_name": npc_en,
            "npc_name_display": npc_display,
            "quest_count": len(quests_out),
            "category": _get_npc_category(npc_en),
            "quests": quests_out,
        })
    return result


def _is_npc_active(npc_name):
    inactive = {
        "FortuneTeller", "JackOLantern", "Krampus", "Miner",
        "Navigator", "Nicholas", "NightmareMummy", "SkeletonFootman",
        "Surgeon", "Treasurer", "Valentine",
    }
    return npc_name not in inactive


def _save_json(filename, data):
    path = Path(OUTPUT_DIR) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
