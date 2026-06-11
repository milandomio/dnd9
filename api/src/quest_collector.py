import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path

from config import HARDCODED_TRANSLATIONS, OUTPUT_DIR
from quest_extractor.quest_extractor import QuestExtractor
from quest_extractor.translator import Translator

_ITEM_SUFFIXES = ["_1001", "_2001", "_3001", "_4001", "_5001", "Pearl"]

_ENTITY_KEY_MAP: dict[str, str] | None = None


def _get_entity_key_map(entity_classification: dict | None = None) -> dict[str, str]:
    """Build {name: translation_key} mapping from entity_classification or entity_index.json."""
    global _ENTITY_KEY_MAP
    if _ENTITY_KEY_MAP is not None:
        return _ENTITY_KEY_MAP
    _ENTITY_KEY_MAP = {}
    if entity_classification:
        for name, info in entity_classification.items():
            tk = info.get("translation_key", "") if isinstance(info, dict) else ""
            if tk:
                _ENTITY_KEY_MAP[name] = tk
    else:
        path = OUTPUT_DIR / "entity_index.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for entry in json.load(f):
                    _ENTITY_KEY_MAP[entry["name"]] = entry.get("translation_key", "")
    return _ENTITY_KEY_MAP


def _translate_item(translator, name_en: str) -> str:
    """Try to translate item name using correct key format."""
    key = f"Text_DesignData_Item_Item_{name_en}"
    translated = translator.translate(key)
    if translated:
        return translated
    for suffix in _ITEM_SUFFIXES:
        translated = translator.translate(f"{key}{suffix}")
        if translated:
            return translated
    props_key = f"Text_DesignData_Props_Props_{name_en}"
    translated = translator.translate(props_key)
    if translated:
        return translated
    skin_key = f"Text_DesignData_ItemSkin_ItemSkin_{name_en}"
    translated = translator.translate(skin_key)
    if translated:
        return translated
    emote_key = f"Text_DesignData_Emote_Emote_{name_en}"
    translated = translator.translate(emote_key)
    if translated:
        return translated
    action_key = f"Text_DesignData_ActionSkin_{name_en}"
    translated = translator.translate(action_key)
    if translated:
        return translated
    return name_en


def run_quest_extraction(entity_classification=None):
    print("\n--- Quest Extraction ---")
    global _ENTITY_KEY_MAP
    _ENTITY_KEY_MAP = None  # reset cache
    if entity_classification:
        _get_entity_key_map(entity_classification)

    translator = Translator(language="zh-Hans")
    extractor = QuestExtractor(translator=translator)
    quests = extractor.load_all_quests()
    print(f"  loaded {len(quests)} quests")

    explore = _extract_explore(translator, extractor, quests)
    print(f"  explore targets: {len(explore)}")

    fetch_items = _extract_fetch(translator, extractor, quests)
    print(f"  quest items: {len(fetch_items)}")

    npcs = _extract_npc_list(translator, extractor, quests)
    total_quests = sum(npc.get("quest_count", 0) for npc in npcs)
    print(f"  active NPCs: {len(npcs)}, total quests: {total_quests}")

    return explore, fetch_items, npcs


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
            clean_module = (
                module_name.rsplit(".", 1)[-1]
                .removesuffix("_A")
                .removesuffix("_D")
                .removesuffix("_S")
                .removesuffix("_HR_D")
                if module_name
                else ""
            )
            key = clean_module or translation
            if key in seen:
                continue
            seen.add(key)
            explore_targets.append(
                {
                    "name": translation,
                    "module_name": clean_module,
                    "quest_id": quest.get("id", ""),
                    "quest_title": quest.get("title_display", ""),
                    "quest_number": quest.get("quest_number", 0),
                    "npc_name": npc_name,
                    "npc_name_display": quest.get("npc_name_display", npc_name),
                }
            )
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
            item_name_en = item_name
            for pfx in [
                "DesignData_Item_Item_",
                "DesignData_Props_Props_",
                "DesignData_Monster_Monster_",
                "Id.Item.",
                "Id.Props.",
                "Id.Monster.",
            ]:
                item_name_en = item_name_en.removeprefix(pfx)
            key = (item_name_en, npc_name, quest.get("quest_number", 0))
            if key in seen:
                continue
            seen.add(key)
            rarity_tag = cd.get("RarityType", {}) or {}
            loot_state = cd.get("ItemLootState", "")
            fetch_items.append(
                {
                    "item_name": item_name_en,
                    "item_translation": _translate_item(translator, item_name_en),
                    "npc_name": npc_name,
                    "npc_name_cn": quest.get("npc_name_display", npc_name),
                    "quest_number": quest.get("quest_number", 0),
                    "count": cd.get("ContentCount", 1),
                    "rarity": rarity_tag.get("TagName", "").removeprefix("Engine.RarityType.") if rarity_tag else "",
                    "is_loot": "是" if loot_state == "Looted" else "",
                }
            )
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
        return "不推荐NPC"
    return "可用NPC"


def _parse_fetch_content(translator, cd):
    """Parse Fetch/UseItem content data to extract target name and count."""
    item_name = ""
    type_tag = cd.get("TypeTag", {}) or {}
    tag_name = type_tag.get("TagName", "")
    if tag_name and "Type.Item." in tag_name:
        item_type = tag_name.split("Type.Item.")[-1]
        type_key = f"Text_Code_DCDataBlueprintLibrary_Type_Item_{item_type}"
        translated = translator.translate(type_key) if translator else ""
        item_name = translated or item_type
    if not item_name:
        item_tag = cd.get("ItemIdTag", {}) or {}
        tag_name = item_tag.get("TagName", "")
        if tag_name:
            en = tag_name.split(".")[-1] if "." in tag_name else tag_name
            item_name = _translate_item(translator, en) if translator else en
    loot_state = "是" if cd.get("ItemLootState") == "EDCItemLootState::Looted" else ""
    rarity_tag = cd.get("RarityType", {}) or {}
    rarity_name = ""
    if isinstance(rarity_tag, dict):
        rn = rarity_tag.get("TagName", "")
        if rn and "Type.Item.Rarity." in rn:
            rarity_raw = rn.split("Type.Item.Rarity.")[-1]
            rarity_key = f"Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_{rarity_raw}"
            translated = translator.translate(rarity_key) if translator else ""
            rarity_name = translated or rarity_raw
    result = {"target": item_name, "count": cd.get("ContentCount", 1)}
    if loot_state:
        result["loot_state"] = loot_state
    if rarity_name:
        result["rarity"] = rarity_name
    return result


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
                rname, rtype_key = extractor.get_reward_item_info(ri)
                rewards.append(
                    {
                        "type": ri.get("RewardType", ""),
                        "name": rname,
                        "type_key": rtype_key,
                        "count": ri.get("RewardCount", 0),
                    }
                )
            contents = []
            for c in q.get("contents", []) or []:
                ct = c.get("content_type", "")
                cd = c.get("content_data", {}) or {}
                ap = c.get("asset_path", "")
                item = {"type": ct}
                if ct == "Kill":
                    kill_tag = cd.get("KillTag", {})
                    tag_name = kill_tag.get("TagName", "") if isinstance(kill_tag, dict) else ""
                    monster = ""
                    if tag_name:
                        if tag_name.startswith("Id.Monster.") or tag_name.startswith("Type.Character."):
                            monster = tag_name.split(".")[-1]
                        else:
                            monster = tag_name.split(".")[-1] if "." in tag_name else tag_name
                    translated = translator.translate(f"Text_DesignData_Monster_Monster_{monster}") if monster else ""
                    if not translated and monster in HARDCODED_TRANSLATIONS:
                        translated = HARDCODED_TRANSLATIONS[monster]
                    # entity_index 兜底（如 SmallJellyfish → GiantJellyfish 翻译键）
                    if not translated and monster:
                        entity_key = _get_entity_key_map().get(monster, "")
                        if entity_key and entity_key != f"Text_DesignData_Monster_Monster_{monster}":
                            translated = translator.translate(entity_key) or ""
                    item["target"] = translated or monster
                    item["count"] = cd.get("ContentCount", 1)
                elif ct == "Fetch":
                    item.update(_parse_fetch_content(translator, cd))
                elif ct == "Explore":
                    item["target"] = extractor.get_explore_target_translation(ap) or ""
                    item["count"] = cd.get("ContentCount", 1)
                elif ct == "Props":
                    props_tag = cd.get("PropsIdTag", {})
                    tag_name = props_tag.get("TagName", "") if isinstance(props_tag, dict) else ""
                    item["target"] = extractor.get_props_target_translation(tag_name) if tag_name else ""
                    item["count"] = cd.get("ContentCount", 1)
                elif ct == "UseItem":
                    item.update(_parse_fetch_content(translator, cd))
                elif ct == "Hold":
                    item["target"] = extractor.get_hold_target_translation(cd) or ct
                elif ct == "Escape":
                    item["target"] = extractor.get_escape_target_translation(cd) or ct
                    item["count"] = cd.get("ContentCount", 1)
                else:
                    item["target"] = ct
                    item["count"] = cd.get("ContentCount", 1)
                contents.append(item)
            quests_out.append(
                {
                    "id": q.get("id", ""),
                    "title": q.get("title_display", ""),
                    "quest_number": q.get("quest_number", 0),
                    "contents": contents,
                    "rewards": rewards,
                    "required": q.get("required_quest", ""),
                }
            )
        quests_out.sort(key=lambda q: q["quest_number"])
        result.append(
            {
                "npc_name": npc_en,
                "npc_name_display": npc_display,
                "quest_count": len(quests_out),
                "category": _get_npc_category(npc_en),
                "quests": quests_out,
            }
        )
    return result


def _is_npc_active(npc_name):
    inactive = {
        "FortuneTeller",
        "JackOLantern",
        "Krampus",
        "Miner",
        "Navigator",
        "Nicholas",
        "NightmareMummy",
        "SkeletonFootman",
        "Surgeon",
        "Treasurer",
        "Valentine",
    }
    return npc_name not in inactive


def _save_json(filename, data):
    path = Path(OUTPUT_DIR) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
