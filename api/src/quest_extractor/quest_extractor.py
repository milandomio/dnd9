#!/usr/bin/env python
"""
任务数据提取器（精简协调器）
聚合FileIndexer, QuestParser, ContentLoader，提供统一接口
"""

import json
import os
import re
from collections import defaultdict

try:
    from .content_loader import ContentLoader, RewardLoader
    from .file_indexer import FileIndexer
    from .quest_parser import QuestParser
    from .translator import Translator
except ImportError:
    from content_loader import ContentLoader, RewardLoader
    from file_indexer import FileIndexer
    from quest_parser import QuestParser
    from translator import Translator


class QuestExtractor:
    """任务数据提取器（协调器）"""

    # 默认路径常量 - 从 api/src/quest_extractor 向上3级到项目根
    _PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", ".."))
    BASE_DATA_PATH = os.path.join(
        _PROJECT_ROOT, "Output", "Exports", "DungeonCrawler", "Content", "DungeonCrawler", "Data", "Generated", "V2"
    )
    DEFAULT_QUEST_PATH = os.path.join(BASE_DATA_PATH, "Quest", "Quest")
    DEFAULT_CONTENT_PATH = os.path.join(BASE_DATA_PATH, "Quest")
    DEFAULT_EXPORT_ROOT = os.path.join(
        _PROJECT_ROOT, "Output", "Exports", "DungeonCrawler", "Content", "DungeonCrawler"
    )
    DEFAULT_PROPS_PATH = os.path.join(BASE_DATA_PATH, "Props", "Props")
    DEFAULT_REWARD_PATH = os.path.join(BASE_DATA_PATH, "Quest", "QuestReward")

    def __init__(self, quest_directory=None, translator=None, content_directory=None):
        """
        初始化任务提取器

        Args:
            quest_directory: 任务JSON文件目录路径
            translator: 翻译器实例
            content_directory: 任务内容JSON文件目录路径
        """
        self.translator = translator or Translator()
        self.quest_directory = quest_directory or self.DEFAULT_QUEST_PATH
        self.content_directory = content_directory or self.DEFAULT_CONTENT_PATH
        self.reward_directory = self.DEFAULT_REWARD_PATH

        # 初始化子组件
        self.file_indexer = FileIndexer(self.quest_directory, self.content_directory)
        self.quest_parser = QuestParser(translator=self.translator)
        self.content_loader = ContentLoader(self.file_indexer)
        self.reward_loader = RewardLoader(self.reward_directory)

        self.quests_data = []
        self.quest_id_map = {}

    def load_all_quests(self):
        """
        加载所有任务文件

        Returns:
            任务数据列表
        """
        self.quests_data = []
        self.quest_id_map = {}

        filenames = self.file_indexer.get_all_quest_filenames()
        for filename in sorted(filenames):
            file_path = self.file_indexer.get_quest_file_path(filename)
            quest_data = self.quest_parser.parse_quest_file(file_path, self.content_loader)
            if quest_data:
                # 加载奖励数据
                quest_data["rewards"] = self.reward_loader.load_reward(quest_data.get("quest_reward", ""))
                self.quests_data.append(quest_data)
                self.quest_id_map[quest_data["id"]] = quest_data

        # 生成显示名称
        self._generate_quest_display_names()

        print(f"成功加载 {len(self.quests_data)} 个任务")
        return self.quests_data

    def _generate_quest_display_names(self):
        """为所有任务生成显示名称"""
        # 按NPC分组
        npc_quests = defaultdict(list)
        for quest in self.quests_data:
            npc = quest["npc_name"]
            npc_quests[npc].append(quest)

        # 为每个NPC的任务排序并生成显示名称
        for _npc, quests in npc_quests.items():
            quests.sort(key=lambda q: self.quest_parser._extract_quest_number(q["id"]))

            for i, quest in enumerate(quests, 1):
                quest["quest_number"] = i
                quest["npc_name_display"] = quest.get("npc_name_cn", quest["npc_name"])
                quest["display_name"] = self.quest_parser._generate_quest_display_name(quest, self.translator.language)

    def group_quests_by_npc(self, use_translated_names=True):
        """
        按NPC分组任务

        Args:
            use_translated_names: 是否使用翻译后的NPC名称作为键

        Returns:
            按NPC分组的任务字典 {npc_name: [quest_data, ...]}
        """
        if not self.quests_data:
            self.load_all_quests()

        grouped = defaultdict(list)
        for quest in self.quests_data:
            npc = quest.get("npc_name_cn", quest["npc_name"]) if use_translated_names else quest["npc_name"]
            grouped[npc].append(quest)

        return dict(grouped)

    def get_quest_by_id(self, quest_id):
        """
        根据任务ID获取任务数据

        Args:
            quest_id: 任务ID

        Returns:
            任务数据字典，未找到返回None
        """
        if not self.quests_data:
            self.load_all_quests()

        return self.quest_id_map.get(quest_id)

    def get_quest_display_name(self, quest_id):
        """
        根据任务ID获取任务显示名称

        Args:
            quest_id: 任务ID

        Returns:
            任务显示名称
        """
        quest = self.get_quest_by_id(quest_id)
        if quest:
            return quest.get("display_name", quest_id)
        return quest_id

    def get_required_quest_display_name(self, quest):
        """
        获取任务的前置任务显示名称

        Args:
            quest: 任务数据

        Returns:
            前置任务显示名称，如果没有前置任务返回None
        """
        required_quest_file = quest.get("required_quest", "")
        if not required_quest_file:
            return None

        # 从文件名提取任务ID（去掉.json后缀）
        quest_id = required_quest_file[:-5] if required_quest_file.endswith(".json") else required_quest_file

        return self.get_quest_display_name(quest_id)

    def search_quests(self, keyword):
        """
        搜索任务（标题或ID中包含关键词）

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的任务列表
        """
        if not self.quests_data:
            self.load_all_quests()

        keyword = keyword.lower()
        results = []
        for quest in self.quests_data:
            if (
                keyword in quest["id"].lower()
                or keyword in quest.get("title_display", "").lower()
                or keyword in quest.get("title", "").lower()
            ):
                results.append(quest)
        return results

    # 路径转换方法（保持不变）
    @staticmethod
    def AssetPathName_to_json(asset_path):  # noqa: N802
        """将AssetPathName转换为JSON文件路径"""
        if not asset_path:
            return None
        if not asset_path.startswith("/Game/"):
            return None
        relative_path = asset_path[6:]
        if "." in relative_path:
            relative_path = relative_path.rsplit(".", 1)[0]
        if relative_path.startswith("DungeonCrawler/"):
            relative_path = relative_path[len("DungeonCrawler/") :]
        json_path = f"{QuestExtractor.DEFAULT_EXPORT_ROOT}/{relative_path}.json"
        return json_path

    def match_asset_path_to_module(self, asset_path):
        """
        将AssetPathName匹配到对应的JSON文件，并返回ModuleId的AssetPathName
        """
        if not asset_path:
            return asset_path

        filename_part = asset_path.split("/")[-1]
        if "." in filename_part:
            parts = filename_part.split(".")
            base_name = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]
        else:
            base_name = filename_part

        json_filename = f"{base_name}.json"

        if json_filename in self.file_indexer.content_file_map:
            file_path = self.file_indexer.get_content_file_path(json_filename)
            return self._read_module_id_from_file(file_path, asset_path)

        file_path = self.AssetPathName_to_json(asset_path)
        if file_path and os.path.exists(file_path):
            return self._read_module_id_from_file(file_path, asset_path)

        return asset_path

    def _read_module_id_from_file(self, file_path, original_asset_path):
        """从JSON文件读取ModuleId的AssetPathName"""
        try:
            with open(file_path, encoding="utf-8") as f:
                raw_data = json.load(f)
            data = raw_data[0] if isinstance(raw_data, list) and len(raw_data) > 0 else raw_data
            properties = data.get("Properties", {})
            module_id = properties.get("ModuleId", {})
            if isinstance(module_id, dict):
                module_asset_path = module_id.get("AssetPathName", "")
                return module_asset_path if module_asset_path else original_asset_path
        except Exception as e:
            print(f"读取模块ID失败 {file_path}: {e}")
        return original_asset_path

    def get_source_string_from_asset_path(self, asset_path):
        """从AssetPathName对应的JSON文件中提取SourceString"""
        if not asset_path:
            return None
        json_path = self.AssetPathName_to_json(asset_path)
        if not json_path or not os.path.exists(json_path):
            return None
        try:
            with open(json_path, encoding="utf-8") as f:
                raw_data = json.load(f)
            data = raw_data[0] if isinstance(raw_data, list) and len(raw_data) > 0 else raw_data
            properties = data.get("Properties", {})

            # 查找SourceString或Key
            source_string = properties.get("SourceString", "")
            if source_string:
                return source_string
            key = properties.get("Key", "")
            if key:
                return key

            for field_name in ["Name", "DisplayName", "Title", "Description", "DescriptionText"]:
                field_value = properties.get(field_name, {})
                if isinstance(field_value, dict):
                    value = (
                        field_value.get("SourceString", "")
                        or field_value.get("LocalizedString", "")
                        or field_value.get("Key", "")
                    )
                    if value:
                        return value

            filename = asset_path.split("/")[-1].split(".")[0]
            return filename
        except Exception as e:
            print(f"读取SourceString失败 {json_path}: {e}")
        return None

    def get_explore_target_translation(self, explore_asset_path):
        """获取探索任务的翻译目标"""
        module_asset_path = self.match_asset_path_to_module(explore_asset_path)
        if not module_asset_path or module_asset_path == explore_asset_path:
            return None
        source_string = self.get_source_string_from_asset_path(module_asset_path)
        if not source_string:
            return None
        if self.translator:
            translated = self.translator.translate(source_string)
            return translated if translated else source_string
        return source_string

    def get_escape_target_translation(self, content_data):
        """获取逃脱任务的翻译目标"""
        if not content_data:
            return None
        dungeon_id_tags = content_data.get("DungeonIdTags", [])
        if not dungeon_id_tags or not isinstance(dungeon_id_tags, list):
            return None
        first_tag = dungeon_id_tags[0]
        if not isinstance(first_tag, dict):
            return None
        tag_name = first_tag.get("TagName", "")
        if not tag_name:
            return None

        if "Id.Dungeon." in tag_name:
            dungeon_name = tag_name.split("Id.Dungeon.")[-1]
        elif "." in tag_name:
            dungeon_name = tag_name.split(".")[-1]
        else:
            dungeon_name = tag_name

        group_key = f"Text_DesignData_Dungeon_DungeonType_Group_{dungeon_name}"
        type_key = f"Text_DesignData_Dungeon_DungeonType_{dungeon_name}"

        if self.translator:
            translated = self.translator.translate(group_key)
            if translated:
                return translated
            translated = self.translator.translate(type_key)
            if translated:
                return translated
            for suffix in ["_A", "_N", "_HR", "_AHR"]:
                key_with_suffix = f"{type_key}{suffix}"
                translated = self.translator.translate(key_with_suffix)
                if translated:
                    return translated

        return dungeon_name

    def get_reward_item_info(self, reward_item):
        """
        获取奖励物品的翻译名称和类型

        Args:
            reward_item: 奖励项字典，包含 RewardType, RewardId, RewardCount

        Returns:
            (translated_name, reward_type_key) 元组
            reward_type_key: "item" | "exp" | "affinity" | "random"
        """
        reward_type = reward_item.get("RewardType", "")
        reward_id = reward_item.get("RewardId", "")
        name = ""
        type_key = "item"

        if reward_type == "EDCRewardType::Exp":
            type_key = "exp"
            name = ""
        elif reward_type == "EDCRewardType::Affinity":
            type_key = "affinity"
            # 翻译NPC名称作为好感度对象
            if reward_id and self.translator:
                if "Id_Merchant_" in reward_id:
                    merchant_name = reward_id.split("Id_Merchant_")[-1]
                    name = self.translator.translate(f"Text_DesignData_Merchant_Merchant_{merchant_name}")
                    if not name:
                        name = merchant_name
                else:
                    name = reward_id
            else:
                name = reward_id
        elif reward_type == "EDCRewardType::Random":
            type_key = "random"
            if reward_id and self.translator:
                # 从 Id_RandomReward_Quest_{Category}_{Rarity}_{Num} 构建键
                # 映射: Text_Reward_Quest_Random_{CategoryPlural}_{Rarity}
                parts = reward_id.split("_")
                category_map = {
                    "Armor": "Armors",
                    "Weapon": "Weapons",
                    "Accessory": "Accessories",
                    "Gem": "Gems",
                    "Gems": "Gems",
                }
                if len(parts) >= 5:
                    category_raw = parts[3]  # Armor
                    rarity_raw = parts[4]  # Uncommon
                    category_plural = category_map.get(category_raw, category_raw + "s")
                    key = f"Text_Reward_Quest_Random_{category_plural}_{rarity_raw}"
                    name = self.translator.translate(key) or reward_id
                else:
                    name = reward_id
            else:
                name = reward_id
        else:
            # EDCRewardType::Item 或其他
            type_key = "item"
            if reward_id and self.translator:
                # 根据 ID 类型构建翻译键
                if "Id_Item_" in reward_id:
                    item_name = reward_id.split("Id_Item_")[-1]
                    key = f"Text_DesignData_Item_Item_{item_name}"
                    name = self.translator.translate(key)
                    # 带后缀尝试
                    suffixes = ["_1001", "_2001", "_3001", "_4001", "_5001", "Pearl"]
                    if not name:
                        for suffix in suffixes:
                            name = self.translator.translate(f"{key}{suffix}")
                            if name:
                                break
                    # 剥离 _NNNN 变体后缀重试（如 LuckPotion_3001 → LuckPotion）
                    if not name and (m := re.match(r"^(.+)_(\d{4})$", item_name)):
                        base_name = m.group(1)
                        base_key = f"Text_DesignData_Item_Item_{base_name}"
                        name = self.translator.translate(base_key)
                        if not name:
                            for suffix in suffixes:
                                name = self.translator.translate(f"{base_key}{suffix}")
                                if name:
                                    break
                    if not name:
                        name = item_name
                elif "Id_Props_" in reward_id:
                    props_name = reward_id.split("Id_Props_")[-1]
                    key = f"Text_DesignData_Props_Props_{props_name}"
                    name = self.translator.translate(key)
                    if not name and (m := re.match(r"^(.+)_(\d{4})$", props_name)):
                        base_key = f"Text_DesignData_Props_Props_{m.group(1)}"
                        name = self.translator.translate(base_key)
                    if not name:
                        name = props_name
                elif "Id_ItemSkin_" in reward_id:
                    skin_name = reward_id.split("Id_ItemSkin_")[-1]
                    key = f"Text_DesignData_ItemSkin_ItemSkin_{skin_name}"
                    name = self.translator.translate(key)
                    if not name:
                        name = skin_name
                elif "Id_Emote_" in reward_id:
                    emote_name = reward_id.split("Id_Emote_")[-1]
                    key = f"Text_DesignData_Emote_Emote_{emote_name}"
                    name = self.translator.translate(key)
                    if not name:
                        name = emote_name
                elif "Id_ActionSkin_" in reward_id:
                    action_name = reward_id.split("Id_ActionSkin_")[-1]
                    key = f"Text_DesignData_ActionSkin_{action_name}"
                    name = self.translator.translate(key)
                    if not name:
                        name = action_name
                else:
                    name = reward_id
            else:
                name = reward_id

        return name, type_key

    def get_gold_bag_npc_names(self):
        """
        扫描奖励文件，返回提供金币袋子奖励的NPC英文名集合。
        检测 GoldCoinBag, GoldCoinChest, GoldCoinPouch 类型的奖励。

        Returns:
            set of English NPC names
        """
        gold_bag_npcs = set()
        gold_ids = {"Id_Item_GoldCoinBag", "Id_Item_GoldCoinChest", "Id_Item_GoldCoinPouch"}

        if not os.path.exists(self.reward_directory):
            return gold_bag_npcs

        for filename in os.listdir(self.reward_directory):
            if not filename.endswith(".json"):
                continue
            parts = filename.replace(".json", "").split("_")
            if len(parts) < 4 or parts[0] != "Id" or parts[1] != "Reward" or parts[2] != "Quest":
                continue
            npc_name = parts[3]

            filepath = os.path.join(self.reward_directory, filename)
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    data = data[0] if data else {}
                rewards = data.get("Properties", {}).get("RewardItemArray", [])
                for reward in rewards:
                    if reward.get("RewardId") in gold_ids:
                        gold_bag_npcs.add(npc_name)
                        break
            except Exception:
                pass

        return gold_bag_npcs

    def get_hold_target_translation(self, content_data):
        """获取坚守任务的翻译目标 - 使用ModuleId获取模块级翻译"""
        if not content_data:
            return None
        module_id = content_data.get("ModuleId", {})
        if not isinstance(module_id, dict):
            return None
        asset_path = module_id.get("AssetPathName", "")
        if not asset_path:
            return None
        # 从AssetPathName提取模块名: /Game/.../Id_DungeonModule_IceCave_Maze.Id_DungeonModule_IceCave_Maze
        # -> Id_DungeonModule_IceCave_Maze -> IceCave_Maze
        parts = asset_path.rsplit("/", 1)[-1].split(".")[0]
        if not parts.startswith("Id_DungeonModule_"):
            return None
        module_name = parts[len("Id_DungeonModule_") :]
        # 翻译模块名
        key = f"Text_DesignData_Dungeon_DungeonModule_{module_name}"
        if self.translator:
            translated = self.translator.translate(key)
            if translated:
                return translated
        # 尝试去掉后缀（_A, _B, _C等）再翻译
        for suffix in ["_A", "_B", "_C", "_D", "_S", "_HR", "_HR_D", "_AHR"]:
            if module_name.endswith(suffix):
                base = module_name[: -len(suffix)]
                key_base = f"Text_DesignData_Dungeon_DungeonModule_{base}"
                if self.translator:
                    translated = self.translator.translate(key_base)
                    if translated:
                        return translated
                break
        # 回退：从模块JSON读取Name.Key作为翻译键
        module_name_key, module_name_display = self._get_module_name_key(asset_path)
        if module_name_key and self.translator:
            translated = self.translator.translate(module_name_key)
            if translated:
                return translated
        return module_name_display or module_name

    def _get_module_name_key(self, asset_path):
        """从DungeonModule JSON读取Name字段的翻译键和显示名"""
        if not asset_path:
            return None, None
        json_path = self.AssetPathName_to_json(asset_path)
        if not json_path or not os.path.exists(json_path):
            return None, None
        try:
            with open(json_path, encoding="utf-8") as f:
                raw_data = json.load(f)
            data = raw_data[0] if isinstance(raw_data, list) and len(raw_data) > 0 else raw_data
            name = data.get("Properties", {}).get("Name", {})
            if isinstance(name, dict):
                return name.get("Key", ""), name.get("LocalizedString", "")
        except Exception:
            pass
        return None, None

    def get_props_target_translation(self, props_id_tag):
        """
        获取道具任务的翻译目标

        Args:
            props_id_tag: 道具标签，如 "Id.Props.Statue.Health"

        Returns:
            翻译后的道具名称，失败返回None
        """
        if not props_id_tag:
            return None

        # 在 Props 目录中搜索包含该标签的文件
        props_path = self.DEFAULT_PROPS_PATH
        if not os.path.exists(props_path):
            return None

        for filename in os.listdir(props_path):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(props_path, filename)
            try:
                with open(filepath, encoding="utf-8") as f:
                    data_list = json.load(f)

                # 处理单个对象或数组
                data_list = data_list if isinstance(data_list, list) else [data_list]

                for data in data_list:
                    properties = data.get("Properties", {})
                    id_tag = properties.get("IdTag", {})
                    if isinstance(id_tag, dict):
                        tag_name = id_tag.get("TagName", "")
                        if tag_name == props_id_tag:
                            # 找到匹配的文件，提取翻译键
                            name = properties.get("Name", {})
                            if isinstance(name, dict):
                                key = name.get("Key", "")
                                if key and self.translator:
                                    translated = self.translator.translate(key)
                                    if translated:
                                        return translated
                            return None
            except Exception as e:
                print(f"读取Props文件失败 {filepath}: {e}")

        return None


def main():
    """测试函数"""
    from translator import Translator

    languages = Translator.get_available_languages()
    print(f"可用语言: {languages}")
    for lang in languages:
        print(f"\n--- {lang} ---")
        translator = Translator(language=lang)
        extractor = QuestExtractor(translator=translator)
        quests = extractor.load_all_quests()
        print("\n前3个任务:")
        for i, quest in enumerate(quests[:3]):
            print(f"{i+1}. {quest['display_name']} - {quest['title_display']}")


if __name__ == "__main__":
    main()
