#!/usr/bin/env python
"""
任务内容文件加载器
负责加载和缓存任务内容JSON文件
"""

import json
import os


class ContentLoader:
    """任务内容加载器"""

    def __init__(self, file_indexer):
        """
        初始化内容加载器

        Args:
            file_indexer: FileIndexer实例，用于查询文件路径
        """
        self.file_indexer = file_indexer
        self._cache = {}  # 缓存已加载的内容

    def load_content(self, content_filename):
        """
        加载单个任务内容文件

        Args:
            content_filename: 任务内容文件名，如 "Id_QuestContent_Explore_Crypt_Chapel_01.json"

        Returns:
            任务内容数据字典（Properties），文件不存在返回None
        """
        # 检查缓存
        if content_filename in self._cache:
            return self._cache[content_filename]

        # 从file_indexer获取文件路径
        file_path = self.file_indexer.get_content_file_path(content_filename)
        if not file_path:
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                raw_data = json.load(f)

            if isinstance(raw_data, list) and len(raw_data) > 0:
                data = raw_data[0]
            else:
                data = raw_data

            properties = data.get("Properties", {})
            self._cache[content_filename] = properties
            return properties
        except Exception as e:
            print(f"加载任务内容文件 {content_filename} 失败: {e}")
            return None

    def load_contents_batch(self, content_filenames):
        """
        批量加载任务内容文件

        Args:
            content_filenames: 内容文件名列表

        Returns:
            字典 {filename: properties}
        """
        results = {}
        for filename in content_filenames:
            results[filename] = self.load_content(filename)
        return results

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    def precache_contents(self, content_filenames):
        """
        预加载内容到缓存

        Args:
            content_filenames: 内容文件名列表
        """
        for filename in content_filenames:
            if filename not in self._cache:
                self.load_content(filename)


class RewardLoader:
    """任务奖励文件加载器"""

    def __init__(self, reward_directory):
        """
        初始化奖励加载器

        Args:
            reward_directory: 奖励JSON文件目录路径
        """
        self.reward_directory = reward_directory
        self._cache = {}

    def load_reward(self, reward_filename):
        """
        加载单个奖励文件

        Args:
            reward_filename: 奖励文件名，如 "Id_Reward_Quest_Alchemist_01.json"

        Returns:
            奖励数据（RewardItemArray列表），文件不存在返回None
        """
        if not reward_filename:
            return None

        if reward_filename in self._cache:
            return self._cache[reward_filename]

        file_path = os.path.join(self.reward_directory, reward_filename)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                raw_data = json.load(f)

            if isinstance(raw_data, list) and len(raw_data) > 0:
                data = raw_data[0]
            else:
                data = raw_data

            reward_array = data.get("Properties", {}).get("RewardItemArray", [])
            self._cache[reward_filename] = reward_array
            return reward_array
        except Exception as e:
            print(f"加载奖励文件 {reward_filename} 失败: {e}")
            return None

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
