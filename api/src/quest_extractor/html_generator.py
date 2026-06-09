#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML生成器（精简协调器）
聚合PageBuilder, ContentRenderer, UITranslations，提供统一接口
"""

import os
from pathlib import Path

try:
    from .translator import Translator
    from .ui_translations import UITranslations
    from .html_template import HTMLTemplate
    from .page_builder import PageBuilder
    from .content_renderer import ContentRenderer
except ImportError:
    from translator import Translator
    from ui_translations import UITranslations
    from html_template import HTMLTemplate
    from page_builder import PageBuilder
    from content_renderer import ContentRenderer


class HTMLGenerator:
    """HTML页面生成器（协调器）"""

    def __init__(self, output_dir=None, quest_extractor=None, language="zh-Hans", dark_mode=False):
        """
        初始化HTML生成器

        Args:
            output_dir: 输出根目录路径
            quest_extractor: QuestExtractor实例，用于解析前置任务和探索目标等
            language: 语言代码
            dark_mode: 是否使用深色主题
        """
        self.language = language
        self.quest_extractor = quest_extractor
        self.dark_mode = dark_mode
        self.output_root = output_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        self.output_dir = os.path.join(self.output_root, language)
        os.makedirs(self.output_dir, exist_ok=True)

        # 初始化子组件
        self.ui_translations = UITranslations()
        self.content_renderer = ContentRenderer(
            quest_extractor,
            ui_translations=self.ui_translations
        ) if quest_extractor else None
        self.page_builder = PageBuilder(
            output_dir=self.output_dir,
            language=language,
            ui_translations=self.ui_translations,
            content_renderer=self.content_renderer,
            dark_mode=dark_mode
        )

    def generate_all_pages(self, grouped_quests, inactive_npcs=None, equipment_npcs=None, preferred_npcs=None, not_recommended_npcs=None, dark_mode=False):
        """
        生成所有页面

        Args:
            grouped_quests: 按NPC分组的任务字典
                           格式: {npc_name: (npc_name_en, [quest_list])}
            inactive_npcs: 失效NPC的英文名集合（可选）
            equipment_npcs: 装备NPC的英文名集合（可选）
            preferred_npcs: 优选NPC的英文名集合（可选）
            not_recommended_npcs: 不推荐NPC的英文名集合（可选）
            dark_mode: 是否使用深色主题

        Returns:
            生成的文件路径列表
        """
        generated_files = self.page_builder.build_all_pages(
            grouped_quests, self.quest_extractor,
            inactive_npcs=inactive_npcs, equipment_npcs=equipment_npcs, preferred_npcs=preferred_npcs, not_recommended_npcs=not_recommended_npcs,
            dark_mode=dark_mode
        )
        return generated_files
