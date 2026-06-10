#!/usr/bin/env python
"""
任务文件解析器
负责解析任务JSON文件，提取结构化数据
"""

import json
import os
from collections import defaultdict


class QuestParser:
    """任务解析器"""

    def __init__(self, translator=None):
        """
        初始化任务解析器

        Args:
            translator: 翻译器实例，用于翻译任务文本
        """
        self.translator = translator

    @staticmethod
    def _get_filename_from_asset_path(asset_path):
        """从AssetPathName提取文件名"""
        if not asset_path:
            return None
        parts = asset_path.split("/")
        if not parts:
            return None
        filename_part = parts[-1]
        base_name = filename_part.split(".")[0] if "." in filename_part else filename_part
        return f"{base_name}.json"

    @staticmethod
    def _extract_npc_name(quest_id):
        """
        从任务ID中提取NPC名称

        Args:
            quest_id: 任务ID，如 "Id_Quest_Alchemist_01"

        Returns:
            NPC名称，如 "Alchemist"
        """
        parts = quest_id.split("_")
        if len(parts) >= 3 and parts[0] == "Id" and parts[1] == "Quest":
            return parts[2]
        return "Unknown"

    @staticmethod
    def _extract_quest_number(quest_id):
        """
        从任务ID中提取排序键

        Args:
            quest_id: 任务ID，如 "Id_Quest_Alchemist_01"

        Returns:
            (category_priority, number) 元组，用于排序。
            普通任务 (Id_Quest_NPC_01) -> (0, 1)
            子类别任务 (Id_Quest_NPC_Extra_01) -> 按类别分配不同优先级
        """
        parts = quest_id.split("_")
        if len(parts) >= 4:
            # 检查NPC名字后第一个段（index 3）
            after_npc = parts[3]

            # 普通任务: Id_Quest_Weaponsmith_01
            if after_npc.isdigit():
                return (0, int(after_npc))

            # 子类别任务: Id_Quest_Weaponsmith_Extra_01
            # 取最后一个部分作为序号
            last_part = parts[-1]
            if last_part.isdigit():
                num = int(last_part)
                priority_map = {
                    "Tuto": -1,  # 教程优先
                    "Extra": 1,  # 额外任务在普通任务之后
                    "Final": 2,  # 最终任务
                    "Daily": 3,  # 每日任务
                    "Weekly": 4,  # 每周任务
                    "Seasonal": 5,  # 季节任务
                }
                priority = priority_map.get(after_npc, 10)
                return (priority, num)

            # 尝试倒数第二个部分
            if len(parts) >= 5:
                part = parts[-2]
                if part.isdigit():
                    return (10, int(part))
        return (99, 0)

    def _generate_quest_display_name(self, quest, language=None):
        """
        为任务生成显示名称

        Args:
            quest: 任务数据（包含npc_name, quest_number等）
            language: 语言代码

        Returns:
            任务显示名称
        """
        npc_name = quest.get("npc_name_display", quest["npc_name"])
        quest_number = quest.get("quest_number", 0)

        # 根据语言生成不同格式的名称
        if language and language.startswith("zh"):
            return f"{npc_name}第{quest_number}个任务"
        else:
            return f"{npc_name} Quest {quest_number}"

    def _generate_quest_display_names(self, quests, language=None):
        """
        为任务列表生成显示名称

        Args:
            quests: 任务列表
            language: 语言代码
        """
        # 按NPC分组
        npc_quests = defaultdict(list)
        for quest in quests:
            npc = quest["npc_name"]
            npc_quests[npc].append(quest)

        # 为每个NPC的任务排序并生成显示名称
        for _npc, quest_list in npc_quests.items():
            # 按任务ID中的序号排序
            quest_list.sort(key=lambda q: self._extract_quest_number(q["id"]))

            # 生成显示名称（使用任务ID中的序号）
            for quest in quest_list:
                _, num = self._extract_quest_number(quest["id"])
                quest["quest_number"] = num
                quest["npc_name_display"] = quest.get("npc_name_cn", quest["npc_name"])
                quest["display_name"] = self._generate_quest_display_name(quest, language)

    def parse_quest_file(self, file_path, content_loader=None):
        """
        解析单个任务文件

        Args:
            file_path: 任务文件路径
            content_loader: ContentLoader实例，用于加载任务内容

        Returns:
            解析后的任务数据字典，失败返回None
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                raw_data = json.load(f)

            data = raw_data[0] if isinstance(raw_data, list) and len(raw_data) > 0 else raw_data

            properties = data.get("Properties", {})
            quest_id = data.get("Name", "")

            # 提取任务文本对象
            title_text_obj = properties.get("TitleText", {})
            greeting_text_obj = properties.get("GreetingText", {})
            complete_text_obj = properties.get("CompleteText", {})

            # 获取SourceString/Key
            title_key = title_text_obj.get("Key", "") or title_text_obj.get("SourceString", "")
            greeting_key = greeting_text_obj.get("Key", "") or greeting_text_obj.get("SourceString", "")
            complete_key = complete_text_obj.get("Key", "") or complete_text_obj.get("SourceString", "")

            # 查找翻译
            title_translated = self.translator.translate(title_key) if self.translator else None
            greeting_translated = self.translator.translate(greeting_key) if self.translator else None
            complete_translated = self.translator.translate(complete_key) if self.translator else None

            # 获取最终显示的文本（优先翻译，其次LocalizedString）
            title_display = title_translated or title_text_obj.get("LocalizedString", "")
            greeting_display = greeting_translated or greeting_text_obj.get("LocalizedString", "")
            complete_display = complete_translated or complete_text_obj.get("LocalizedString", "")

            # 提取任务基本信息
            npc_name_en = self._extract_npc_name(quest_id)
            npc_name_cn = self.translator.translate_npc(npc_name_en) if self.translator else npc_name_en

            quest_info = {
                "id": quest_id,
                "filename": os.path.basename(file_path),
                "npc_name": npc_name_en,
                "npc_name_cn": npc_name_cn,
                "title": title_text_obj.get("LocalizedString", ""),
                "title_translated": title_translated,
                "title_display": title_display,
                "title_key": title_key,
                "greeting_text": greeting_text_obj.get("LocalizedString", ""),
                "greeting_translated": greeting_translated,
                "greeting_display": greeting_display,
                "greeting_key": greeting_key,
                "complete_text": complete_text_obj.get("LocalizedString", ""),
                "complete_translated": complete_translated,
                "complete_display": complete_display,
                "complete_key": complete_key,
                "required_quest": self._get_filename_from_asset_path(
                    properties.get("RequiredQuest", {}).get("AssetPathName", "")
                ),
                "quest_reward": self._get_filename_from_asset_path(
                    properties.get("QuestReward", {}).get("AssetPathName", "")
                ),
                "contents": [],
            }

            # 提取任务内容
            quest_contents = properties.get("QuestContents", [])
            for content in quest_contents:
                asset_path = content.get("AssetPathName", "")
                content_filename = self._get_filename_from_asset_path(asset_path)
                content_info = {
                    "asset_path": asset_path,
                    "content_type": self._get_content_type(asset_path),
                    "content_filename": content_filename,
                    "content_data": None,  # 延迟加载，使用content_loader
                }
                quest_info["contents"].append(content_info)

            # 如果有content_loader，立即加载内容
            if content_loader:
                for content_info in quest_info["contents"]:
                    content_info["content_data"] = content_loader.load_content(content_info["content_filename"])

            return quest_info

        except Exception as e:
            print(f"加载任务文件 {file_path} 失败: {e}")
            return None

    @staticmethod
    def _get_content_type(asset_path):
        """
        从AssetPathName判断任务内容类型

        Args:
            asset_path: 资源路径

        Returns:
            内容类型字符串
        """
        if not asset_path:
            return "Unknown"

        if "QuestContentKill" in asset_path:
            return "Kill"
        elif "QuestContentFetch" in asset_path:
            return "Fetch"
        elif "QuestContentExplore" in asset_path:
            return "Explore"
        elif "QuestContentProps" in asset_path:
            return "Props"
        elif "QuestContentUseItem" in asset_path:
            return "UseItem"
        elif "QuestContentDamage" in asset_path:
            return "Damage"
        elif "QuestContentEscape" in asset_path:
            return "Escape"
        elif "QuestContentHold" in asset_path:
            return "Hold"
        else:
            return "Unknown"
