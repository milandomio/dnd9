#!/usr/bin/env python
"""
文件索引管理
负责扫描并索引任务JSON文件和任务内容文件
"""

import os


class FileIndexer:
    """文件索引器"""

    # 任务文件前缀
    QUEST_FILE_PREFIX = "Id_Quest_"

    # 任务内容类型目录列表
    CONTENT_TYPES = [
        "QuestContentKill",
        "QuestContentFetch",
        "QuestContentExplore",
        "QuestContentProps",
        "QuestContentUseItem",
        "QuestContentDamage",
        "QuestContentEscape",
        "QuestContentHold",
    ]

    def __init__(self, quest_directory, content_directory):
        """
        初始化文件索引器

        Args:
            quest_directory: 任务JSON文件目录路径
            content_directory: 任务内容基础目录路径
        """
        self.quest_directory = quest_directory
        self.content_directory = content_directory
        self.quest_file_map = {}  # 文件名 -> 完整路径
        self.content_file_map = {}  # 内容文件名 -> 完整路径
        self._build_maps()

    def _build_maps(self):
        """建立文件映射"""
        self._build_quest_file_map()
        self._build_content_file_map()

    def _build_quest_file_map(self):
        """扫描并建立任务文件映射"""
        if not os.path.exists(self.quest_directory):
            print(f"警告：任务目录不存在: {self.quest_directory}")
            return

        count = 0
        for root, _, files in os.walk(self.quest_directory):
            for file in files:
                if file.endswith(".json") and file.startswith(self.QUEST_FILE_PREFIX):
                    self.quest_file_map[file] = os.path.join(root, file)
                    count += 1
        print(f"已索引 {count} 个任务文件")

    def _build_content_file_map(self):
        """扫描并建立任务内容文件映射"""
        if not os.path.exists(self.content_directory):
            print(f"警告：任务内容目录不存在: {self.content_directory}")
            return

        count = 0
        for content_type in self.CONTENT_TYPES:
            content_dir = os.path.join(self.content_directory, content_type)
            if os.path.exists(content_dir):
                for file in os.listdir(content_dir):
                    if file.endswith(".json"):
                        self.content_file_map[file] = os.path.join(content_dir, file)
                        count += 1
        print(f"已索引 {count} 个任务内容文件")

    def get_quest_file_path(self, filename):
        """
        获取任务文件完整路径

        Args:
            filename: 任务文件名，如 "Id_Quest_Alchemist_01.json"

        Returns:
            完整路径，未找到返回None
        """
        return self.quest_file_map.get(filename)

    def get_content_file_path(self, filename):
        """
        获取任务内容文件完整路径

        Args:
            filename: 内容文件名，如 "Id_QuestContent_Kill_Goblin_01.json"

        Returns:
            完整路径，未找到返回None
        """
        return self.content_file_map.get(filename)

    def get_all_quest_filenames(self):
        """获取所有任务文件名列表"""
        return list(self.quest_file_map.keys())

    def get_all_content_filenames(self):
        """获取所有内容文件名列表"""
        return list(self.content_file_map.keys())

    def has_quest_file(self, filename):
        """检查任务文件是否存在"""
        return filename in self.quest_file_map

    def has_content_file(self, filename):
        """检查内容文件是否存在"""
        return filename in self.content_file_map
