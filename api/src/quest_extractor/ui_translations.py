#!/usr/bin/env python
"""
UI界面文本管理
提供多语言UI字符串
"""


class UITranslations:
    """UI界面文本管理"""

    UI_TRANSLATIONS = {
        "en": {
            "page_title": "Quest Information",
            "npc_list": "NPC List",
            "search_npc": "Search NPC or quest...",
            "search_quest": "Search quest...",
            "back_to_index": "Back to Index",
            "stats": "Statistics",
            "npc_name": "NPC Name",
            "english_name": "English Name",
            "quest_count": "Quest Count",
            "total": "Total",
            "quests": "quests",
            "quest_description": "Quest Description",
            "complete_description": "Complete Description",
            "required_quest": "Required Quest",
            "quest_content": "Quest Content",
            "content_type": "Type",
            "content_count": "Count",
            "loot_state": "Loot State",
            "rarity": "Rarity",
            "looted": "Yes",
            "not_looted": "No",
            "dungeon_type": "Dungeon Type",
            "explore": "Explore",
            "fetch": "Fetch",
            "kill": "Kill",
            "props": "Props",
            "use_item": "Use Item",
            "damage": "Damage",
            "escape": "Escape",
            "hold": "Hold",
            "debug": "Debug",
            "hide_debug": "Hide Debug",
            "active_npcs": "Active NPCs",
            "equipment_npcs": "Equipment NPCs",
            "preferred_npcs": "Preferred NPCs",
            "not_recommended_npcs": "Not Recommended NPCs",
            "inactive_npcs": "Inactive NPCs",
            "quest_reward": "Quest Rewards",
            "reward_type": "Type",
            "reward_item": "Item",
            "reward_exp": "Experience",
            "reward_affinity": "Affinity",
            "reward_random": "Random Reward",
            "reward_count": "Count",
        },
        "zh-Hans": {
            "page_title": "任务信息汇总",
            "npc_list": "NPC列表",
            "search_npc": "搜索NPC或任务...",
            "search_quest": "搜索任务...",
            "back_to_index": "返回汇总页",
            "stats": "统计信息",
            "npc_name": "NPC名称",
            "english_name": "英文原名",
            "quest_count": "任务数量",
            "total": "总计",
            "quests": "个任务",
            "quest_description": "任务描述",
            "complete_description": "完成描述",
            "required_quest": "前置任务",
            "quest_content": "任务目标",
            "content_type": "类型",
            "content_count": "数量",
            "loot_state": "战利品状态",
            "rarity": "稀有度",
            "looted": "是",
            "not_looted": "否",
            "dungeon_type": "地牢类型",
            "explore": "探索",
            "fetch": "收集",
            "kill": "击杀",
            "props": "道具",
            "use_item": "使用物品",
            "damage": "造成伤害",
            "escape": "逃脱",
            "hold": "坚守",
            "debug": "调试",
            "hide_debug": "隐藏调试",
            "active_npcs": "可用NPC",
            "equipment_npcs": "装备NPC",
            "preferred_npcs": "优选NPC",
            "not_recommended_npcs": "不推荐NPC",
            "inactive_npcs": "失效NPC",
            "quest_reward": "任务奖励",
            "reward_type": "类型",
            "reward_item": "物品",
            "reward_exp": "经验值",
            "reward_affinity": "好感度",
            "reward_random": "随机奖励",
            "reward_count": "数量",
        },
    }

    @staticmethod
    def get_text(language, key):
        """
        获取指定语言的UI文本

        Args:
            language: 语言代码，如 "zh-Hans", "en"
            key: 文本键

        Returns:
            对应的文本，如果未找到返回key本身
        """
        return UITranslations.UI_TRANSLATIONS.get(language, {}).get(key, key)
