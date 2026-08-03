import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from config import HARDCODED_TRANSLATIONS, OUTPUT_DIR, hardcoded_translation_key
from quest_extractor.quest_extractor import QuestExtractor
from quest_extractor.translator import Translator

_ITEM_SUFFIXES = ["_1001", "_2001", "_3001", "_4001", "_5001", "Pearl"]

_INACTIVE_NPCS = frozenset(
    {
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
)


def _get_entity_key_map(entity_classification: dict | None = None) -> dict[str, str]:
    """Build {name: translation_key} mapping from entity_classification or entity_index.json."""
    if not hasattr(_get_entity_key_map, "_cache"):
        _get_entity_key_map._cache = {}
    cache = _get_entity_key_map._cache
    if cache:
        return cache
    if entity_classification:
        for name, info in entity_classification.items():
            tk = info.get("translation_key", "") if isinstance(info, dict) else ""
            if tk:
                cache[name] = tk
    else:
        path = OUTPUT_DIR / "entity_index.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for entry in json.load(f):
                    cache[entry["name"]] = entry.get("translation_key", "")
    return cache


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


def run_quest_extraction(db, entity_classification=None):
    print("\n--- Quest Extraction ---")
    if hasattr(_get_entity_key_map, "_cache"):
        _get_entity_key_map._cache = {}  # reset cache
    if entity_classification:
        _get_entity_key_map(entity_classification)

    translator = Translator(language="zh-Hans", db=db)
    extractor = QuestExtractor(translator=translator, db=db)
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
            content_data = content.get("content_data") or {}
            module_asset_path = extractor.match_asset_path_to_module(asset_path, content_data) or ""
            translation = extractor.get_explore_target_translation(module_asset_path) or ""
            module_name = module_asset_path
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
                    "module_translation_key": extractor.get_source_string_from_asset_path(module_asset_path)
                    or content.get("translation_key", ""),
                    "quest_id": quest.get("id", ""),
                    "quest_title": quest.get("title_display", ""),
                    "quest_translation_key": quest.get("title_key", ""),
                    "quest_number": quest.get("quest_number", 0),
                    "npc_name": npc_name,
                    "npc_name_display": quest.get("npc_name_display", npc_name),
                    "npc_translation_key": f"Text_DesignData_Merchant_Merchant_{npc_name}",
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
    equipment = {"Alchemist", "Armourer", "Goldsmith", "Leathersmith", "Tailor", "Weaponsmith"}
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
    translation_key = ""
    type_tag = cd.get("TypeTag", {}) or {}
    tag_name = type_tag.get("TagName", "")
    if tag_name and "Type.Item." in tag_name:
        item_type = tag_name.split("Type.Item.")[-1]
        type_key = f"Text_Code_DCDataBlueprintLibrary_Type_Item_{item_type}"
        translated = translator.translate(type_key) if translator else ""
        item_name = translated or item_type
        translation_key = type_key if translated else ""
    if not item_name:
        item_tag = cd.get("ItemIdTag", {}) or {}
        tag_name = item_tag.get("TagName", "")
        if tag_name:
            en = tag_name.split(".")[-1] if "." in tag_name else tag_name
            item_name = _translate_item(translator, en) if translator else en
            candidates = [
                f"Text_DesignData_Item_Item_{en}",
                f"Text_DesignData_Props_Props_{en}",
                f"Text_DesignData_ItemSkin_ItemSkin_{en}",
                f"Text_DesignData_Emote_Emote_{en}",
                f"Text_DesignData_ActionSkin_{en}",
            ]
            candidates.extend(f"Text_DesignData_Item_Item_{en}{suffix}" for suffix in _ITEM_SUFFIXES)
            for key in candidates:
                if translator and translator.translate(key):
                    translation_key = key
                    break
    loot_state = "是" if cd.get("ItemLootState") == "EDCItemLootState::Looted" else ""
    rarity_tag = cd.get("RarityType", {}) or {}
    rarity_name = ""
    rarity_key = ""
    if isinstance(rarity_tag, dict):
        rn = rarity_tag.get("TagName", "")
        if rn and "Type.Item.Rarity." in rn:
            rarity_raw = rn.split("Type.Item.Rarity.")[-1]
            rarity_key = f"Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_{rarity_raw}"
            translated = translator.translate(rarity_key) if translator else ""
            rarity_name = translated or rarity_raw
    result = {"target": item_name, "count": cd.get("ContentCount", 1)}
    if translation_key:
        result["translation_key"] = translation_key
    if loot_state:
        result["loot_state"] = loot_state
    if rarity_name:
        result["rarity"] = rarity_name
        result["rarity_translation_key"] = rarity_key
    return result


def _get_dungeon_type_key(translator, content_data):
    """Return the first game locale key used for a quest's dungeon target."""
    dungeon_id_tags = content_data.get("DungeonIdTags", []) if content_data else []
    if not dungeon_id_tags or not isinstance(dungeon_id_tags[0], dict):
        return ""
    tag_name = dungeon_id_tags[0].get("TagName", "")
    dungeon_name = tag_name.split(".")[-1]
    type_key = f"Text_DesignData_Dungeon_DungeonType_{dungeon_name}"
    candidates = [
        f"Text_DesignData_Dungeon_DungeonType_Group_{dungeon_name}",
        type_key,
        *(f"{type_key}{suffix}" for suffix in ("_A", "_N", "_HR", "_AHR")),
    ]
    return next((key for key in candidates if translator.translate(key)), "")


def _get_kill_target_info(translator, tag_name: str) -> tuple[str, str]:
    """Resolve a kill target through its entity key or Type.Character tag key."""
    monster = tag_name.split(".")[-1] if tag_name else ""
    translation_key = f"Text_DesignData_Monster_Monster_{monster}"
    translated = translator.translate(translation_key) if monster else ""
    if not translated and tag_name.startswith("Type.Character."):
        type_name = tag_name.removeprefix("Type.Character.").replace(".", "_")
        type_key = f"Text_Code_DCDataBlueprintLibrary_Type_Character_{type_name}"
        translated = translator.translate(type_key)
        if translated:
            translation_key = type_key
    if not translated and monster in HARDCODED_TRANSLATIONS:
        translated = HARDCODED_TRANSLATIONS[monster]
        translation_key = hardcoded_translation_key(monster) or ""
    # entity_index fallback (for example SmallJellyfish -> GiantJellyfish key)
    if not translated and monster:
        entity_key = _get_entity_key_map().get(monster, "")
        if entity_key and entity_key != translation_key:
            translated = translator.translate(entity_key) or ""
            if translated:
                translation_key = entity_key
    return translated or monster, translation_key if translated else ""


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
                rname, rtype_key, translation_key = extractor.get_reward_item_info(ri)
                rewards.append(
                    {
                        "type": ri.get("RewardType", ""),
                        "name": rname,
                        "type_key": rtype_key,
                        "translation_key": translation_key,
                        "count": ri.get("RewardCount", 0),
                    }
                )
            contents = []
            for c in q.get("contents", []) or []:
                ct = c.get("content_type", "")
                cd = c.get("content_data", {}) or {}
                ap = c.get("asset_path", "")
                item = {"type": ct}
                dungeon_type = extractor.get_dungeon_type_translation(cd)
                if dungeon_type:
                    item["dungeon_type"] = dungeon_type
                    item["dungeon_translation_key"] = _get_dungeon_type_key(translator, cd)
                if ct == "Kill":
                    kill_tag = cd.get("KillTag", {})
                    tag_name = kill_tag.get("TagName", "") if isinstance(kill_tag, dict) else ""
                    target, translation_key = _get_kill_target_info(translator, tag_name)
                    item["target"] = target
                    if translation_key:
                        item["translation_key"] = translation_key
                    item["count"] = cd.get("ContentCount", 1)
                elif ct == "Fetch":
                    item.update(_parse_fetch_content(translator, cd))
                elif ct == "Explore":
                    module_asset_path = extractor.match_asset_path_to_module(ap, cd) or ap
                    item["target"] = extractor.get_explore_target_translation(module_asset_path) or ""
                    key = extractor.get_source_string_from_asset_path(module_asset_path)
                    if key and translator.translate(key):
                        item["translation_key"] = key
                    item["count"] = cd.get("ContentCount", 1)
                elif ct == "Props":
                    props_tag = cd.get("PropsIdTag", {})
                    tag_name = props_tag.get("TagName", "") if isinstance(props_tag, dict) else ""
                    key, _fallback = extractor.get_props_target_info(tag_name)
                    item["target"] = extractor.get_props_target_translation(tag_name) if tag_name else ""
                    if key:
                        item["translation_key"] = key
                    item["count"] = cd.get("ContentCount", 1)
                elif ct == "UseItem":
                    item.update(_parse_fetch_content(translator, cd))
                elif ct == "Hold":
                    item["target"] = extractor.get_hold_target_translation(cd) or ct
                elif ct == "Escape":
                    item["target"] = extractor.get_escape_target_translation(cd) or ct
                    key = _get_dungeon_type_key(translator, cd)
                    if key:
                        item["translation_key"] = key
                    item["count"] = cd.get("ContentCount", 1)
                else:
                    item["target"] = ct
                    item["count"] = cd.get("ContentCount", 1)
                contents.append(item)
            quests_out.append(
                {
                    "id": q.get("id", ""),
                    "title": q.get("title_display", ""),
                    "translation_key": q.get("title_key", ""),
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
    return npc_name not in _INACTIVE_NPCS
