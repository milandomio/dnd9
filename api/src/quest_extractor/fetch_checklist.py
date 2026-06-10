#!/usr/bin/env python
"""
Fetch任务收集清单CSV生成器
"""

import csv
import os


class FetchChecklist:
    """生成Fetch任务收集物品清单CSV"""

    ITEM_SUFFIXES = ["_1001", "_2001", "_3001", "_4001", "_5001", "Pearl"]

    def __init__(self, quest_extractor):
        self.extractor = quest_extractor
        self.translator = quest_extractor.translator

    def generate_csv(
        self, output_path=None, exclude_npcs=None, equipment_npcs=None, preferred_npcs=None, not_recommended_npcs=None
    ):
        if not self.extractor.quests_data:
            self.extractor.load_all_quests()

        exclude_npcs = exclude_npcs or set()
        equipment_npcs = equipment_npcs or set()
        preferred_npcs = preferred_npcs or set()
        not_recommended_npcs = not_recommended_npcs or set()

        # 计算每个NPC最后一个有好感度奖励的任务编号
        last_affinity = self._compute_last_affinity()

        # 分类排序权重: 装备=0, 优选=1, 可用=2, 不推荐=3
        def _category_order(npc_en):
            if npc_en in equipment_npcs:
                return 0
            if npc_en in preferred_npcs:
                return 1
            if npc_en in not_recommended_npcs:
                return 3
            return 2

        def _category_name(npc_en):
            if npc_en in equipment_npcs:
                return "装备NPC"
            if npc_en in preferred_npcs:
                return "优选NPC"
            if npc_en in not_recommended_npcs:
                return "不推荐NPC"
            return "可用NPC"

        rows = []
        for quest in self.extractor.quests_data:
            npc_en = quest.get("npc_name", "")
            if npc_en in exclude_npcs:
                continue
            for content in quest.get("contents", []):
                if content.get("content_type") != "Fetch":
                    continue
                content_data = content.get("content_data", {})
                if not content_data:
                    continue

                npc_cn = quest.get("npc_name_cn", npc_en)
                quest_num = quest.get("quest_number", "")
                target_name = self._resolve_item_name(content_data)
                count = content_data.get("ContentCount", "")
                is_loot = self._resolve_loot_state(content_data)
                rarity = self._resolve_rarity(content_data)
                suggested = last_affinity.get(npc_en, "")
                category = _category_name(npc_en)

                rows.append([npc_cn, npc_en, quest_num, target_name, count, rarity, is_loot, suggested, category])

        rows = [r for r in rows if r[8] != "不推荐NPC"]
        rows.sort(key=lambda r: (_category_order(r[1]), r[0], r[2]))

        if output_path is None:
            output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "fetch_checklist.csv")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "NPC名字",
                    "NPC英文名",
                    "第几个任务",
                    "收集物品名",
                    "物品数量",
                    "稀有度",
                    "是否战利品",
                    "建议完成任务",
                    "分类",
                ]
            )
            writer.writerows(rows)

        print(f"CSV清单已生成: {output_path}")
        print(f"共 {len(rows)} 条记录")
        return output_path

    def _compute_last_affinity(self):
        """返回 {npc_en: 最后一个有好感度奖励的任务编号}"""
        result = {}
        for quest in self.extractor.quests_data:
            npc_en = quest.get("npc_name", "")
            quest_num = quest.get("quest_number", 0)
            rewards = quest.get("rewards") or []
            has_affinity = any(r.get("RewardType") == "EDCRewardType::Affinity" for r in rewards)
            if has_affinity and (npc_en not in result or quest_num > result[npc_en]):
                result[npc_en] = quest_num
        return result

    def _resolve_item_name(self, content_data):
        target_name = ""

        # 优先 TypeTag（物品类型）
        type_tag = content_data.get("TypeTag", {})
        if isinstance(type_tag, dict):
            type_tag_name = type_tag.get("TagName", "")
            if type_tag_name and "Type.Item." in type_tag_name:
                item_type = type_tag_name.split("Type.Item.")[-1]
                type_key = f"Text_Code_DCDataBlueprintLibrary_Type_Item_{item_type}"
                if self.translator:
                    translated = self.translator.translate(type_key)
                    target_name = translated if translated else item_type
                else:
                    target_name = item_type

        # 如果没有 TypeTag，尝试 ItemIdTag（具体物品）
        if not target_name:
            item_tag = content_data.get("ItemIdTag", {}).get("TagName", "")
            if item_tag:
                item_name = item_tag.split(".")[-1] if "." in item_tag else item_tag
                item_key = f"Text_DesignData_Item_Item_{item_name}"
                props_key = f"Text_DesignData_Props_Props_{item_name}"
                if self.translator:
                    translated = self.translator.translate(item_key)
                    if not translated:
                        for suffix in self.ITEM_SUFFIXES:
                            translated = self.translator.translate(f"{item_key}{suffix}")
                            if translated:
                                break
                        if not translated:
                            translated = self.translator.translate(props_key)
                    target_name = translated if translated else item_name
                else:
                    target_name = item_name

        return target_name

    def _resolve_loot_state(self, content_data):
        loot_state_raw = content_data.get("ItemLootState", "")
        if loot_state_raw == "EDCItemLootState::Looted":
            return "是"
        elif loot_state_raw:
            return "否"
        return ""

    def _resolve_rarity(self, content_data):
        rarity_tag = content_data.get("RarityType", {})
        if not isinstance(rarity_tag, dict):
            return ""
        rarity_tag_name = rarity_tag.get("TagName", "")
        if not rarity_tag_name or "Type.Item.Rarity." not in rarity_tag_name:
            return ""
        rarity_name = rarity_tag_name.split("Type.Item.Rarity.")[-1]
        rarity_key = f"Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_{rarity_name}"
        if self.translator:
            translated = self.translator.translate(rarity_key)
            return translated if translated else rarity_name
        return rarity_name
