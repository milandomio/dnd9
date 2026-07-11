#!/usr/bin/env python
"""
翻译模块
用于加载和查询游戏翻译数据
支持多语言
"""

import json
import os
import re


class Translator:
    """游戏翻译器"""

    # 默认Localization根目录 - 从 api/src/quest_extractor 向上3级到项目根
    _PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "..", ".."))
    DEFAULT_LOCALIZATION_ROOT = os.path.join(
        _PROJECT_ROOT, "Output", "Exports", "DungeonCrawler", "Content", "Localization", "Game"
    )

    # 默认语言
    DEFAULT_LANGUAGE = "zh-Hans"

    def __init__(self, language=None, localization_root=None):
        """
        初始化翻译器

        Args:
            language: 语言代码，如 "zh-Hans", "en"
            localization_root: Localization根目录路径
        """
        self.language = language or self.DEFAULT_LANGUAGE
        self.localization_root = localization_root or self.DEFAULT_LOCALIZATION_ROOT
        self.translation_file = self._get_translation_file_path()
        self.translations = {}
        self._load_translations()

    def _get_translation_file_path(self):
        """获取翻译文件路径"""
        return os.path.join(self.localization_root, self.language, "Game.json")

    def _load_translations(self):
        """加载翻译文件"""
        if not os.path.exists(self.translation_file):
            print(f"警告：翻译文件不存在: {self.translation_file}")
            return

        try:
            with open(self.translation_file, encoding="utf-8") as f:
                data = json.load(f)
                # 翻译数据在 "DC" 键下
                if "DC" in data:
                    self.translations = data["DC"]
                else:
                    self.translations = data
                # 清洗：去掉翻译值中的（裂开）后缀
                cracked_re = re.compile(r"（裂开）")
                self.translations = {
                    k: cracked_re.sub("", v) for k, v in self.translations.items() if isinstance(v, str)
                }
            print(f"[{self.language}] 已加载 {len(self.translations)} 条翻译")
        except Exception as e:
            print(f"[{self.language}] 加载翻译文件失败: {e}")

    def translate(self, key):
        """
        翻译指定键

        Args:
            key: 翻译键

        Returns:
            翻译后的字符串，如果未找到返回None
        """
        return self.translations.get(key)

    def translate_npc(self, npc_name):
        """
        翻译NPC名称

        Args:
            npc_name: NPC英文名称，如 "Alchemist"

        Returns:
            翻译后的名称，如果未找到返回原名称
        """
        key = f"Text_DesignData_Merchant_Merchant_{npc_name}"
        translation = self.translate(key)
        return translation if translation else npc_name

    def get_all_npc_translations(self):
        """
        获取所有NPC翻译

        Returns:
            NPC翻译字典 {英文名称: 翻译后名称}
        """
        npc_translations = {}
        prefix = "Text_DesignData_Merchant_Merchant_"
        for key, value in self.translations.items():
            if key.startswith(prefix):
                suffix = key[len(prefix) :]
                if "_" not in suffix:
                    npc_translations[suffix] = value
        return npc_translations

    @staticmethod
    def get_available_languages(localization_root=None):
        """
        获取可用的语言列表

        Args:
            localization_root: Localization根目录路径

        Returns:
            语言代码列表，如 ["en", "zh-Hans"]
        """
        root = localization_root or Translator.DEFAULT_LOCALIZATION_ROOT
        if not os.path.exists(root):
            return []

        languages = []
        for item in os.listdir(root):
            item_path = os.path.join(root, item)
            if os.path.isdir(item_path):
                game_json = os.path.join(item_path, "Game.json")
                if os.path.exists(game_json):
                    languages.append(item)

        return sorted(languages)


def main():
    """测试函数"""
    # 显示可用语言
    languages = Translator.get_available_languages()
    print(f"可用语言: {languages}")

    # 测试每种语言
    for lang in languages:
        print(f"\n--- {lang} ---")
        translator = Translator(language=lang)

        # 测试翻译几个NPC
        test_npcs = ["Alchemist", "Armourer", "Huntress", "TavernMaster"]
        for npc in test_npcs:
            print(f"  {npc} -> {translator.translate_npc(npc)}")


if __name__ == "__main__":
    main()
