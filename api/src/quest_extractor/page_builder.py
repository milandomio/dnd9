#!/usr/bin/env python
"""
页面构建器
负责构建各类HTML页面（汇总页、NPC页）
"""

import os
import re

try:
    from .html_template import HTMLTemplate
except ImportError:
    from html_template import HTMLTemplate


class PageBuilder:
    """页面构建器"""

    def __init__(self, output_dir, language, ui_translations, content_renderer, dark_mode=False):
        """
        初始化页面构建器

        Args:
            output_dir: 输出目录路径
            language: 语言代码
            ui_translations: UITranslations实例
            content_renderer: ContentRenderer实例
            dark_mode: 是否使用深色主题
        """
        self.output_dir = output_dir
        self.language = language
        self.ui_text = ui_translations
        self.content_renderer = content_renderer
        self.dark_mode = dark_mode
        os.makedirs(output_dir, exist_ok=True)

    def _get_ui_text(self, key):
        """获取界面文本"""
        return self.ui_text.get_text(self.language, key)

    def _build_search_script(self):
        """生成搜索JavaScript代码"""
        return """
    <script>
        function filterQuests() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const cards = document.querySelectorAll('.quest-card, .npc-card-wrapper');

            cards.forEach(card => {
                const questData = card.getAttribute('data-quest') || card.getAttribute('data-npc');
                if (questData.includes(filter)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        }

        function saveNpcConfirm(el) {
            const key = 'npc_confirm_' + el.getAttribute('data-npc');
            localStorage.setItem(key, el.checked ? '1' : '0');
        }

        function loadNpcConfirm() {
            document.querySelectorAll('.npc-confirm-checkbox').forEach(cb => {
                const key = 'npc_confirm_' + cb.getAttribute('data-npc');
                cb.checked = localStorage.getItem(key) === '1';
            });
        }

        window.addEventListener('DOMContentLoaded', loadNpcConfirm);
    </script>
"""

    def _build_npc_card(self, npc_name, npc_en, quest_count):
        """
        构建NPC卡片HTML

        Args:
            npc_name: NPC显示名称（中文）
            npc_en: NPC英文名称
            quest_count: 任务数量

        Returns:
            HTML字符串
        """
        safe_filename = re.sub(r'[<>:"/\\\\|?*]', "_", npc_en)
        search_data = f"{npc_name.lower()} {npc_en.lower()}"

        npc_en_display = f'<div class="npc-en">{npc_en}</div>' if npc_name != npc_en and self.language == "en" else ""

        return f"""            <div class="npc-card-wrapper" data-npc="{search_data}">
                <input type="checkbox" class="npc-confirm-checkbox" data-npc="{npc_en}" onchange="saveNpcConfirm(this)" onclick="event.stopPropagation()" title="确认已检查">
                <a href="{safe_filename}.html" class="npc-card">
                    <div class="npc-name">{npc_name}</div>
                    <div class="npc-count">{quest_count} {self._get_ui_text("quests")}</div>
                    {npc_en_display}
                </a>
            </div>
"""

    def _build_quest_card(self, quest):
        """
        构建任务卡片HTML

        Args:
            quest: 任务数据字典

        Returns:
            (html_string, search_data)
        """
        # 获取任务显示信息
        display_name = quest.get("display_name", quest.get("title_display", "") or quest.get("title", ""))
        subtitle = quest.get("title_display", "") or quest.get("title", "")
        greeting_display = quest.get("greeting_display", "") or quest.get("greeting_text", "")
        complete_display = quest.get("complete_display", "") or quest.get("complete_text", "")

        # 搜索数据
        search_data = f"{quest['id'].lower()} {quest.get('title', '').lower()} {display_name.lower()}"

        # 构建卡片头部
        html = f"""            <div class="quest-card" data-quest="{search_data}" id="{quest['id']}">
                <div class="quest-id debug-section">{quest['id']}</div>
                <div class="quest-title-main">{display_name}</div>
"""
        # 副标题
        if subtitle and subtitle != display_name:
            html += f"""                <div class="quest-title-sub">{subtitle}</div>
"""
        else:
            html += """                <div class="quest-title-sub" style="border-bottom: 2px solid #4CAF50; margin-bottom: 12px; padding-bottom: 10px;"></div>
"""

        # 任务目标表格（如果QuestExtractor可用）
        quest_content_info = self.content_renderer.render_quest_content_table(quest)
        html += quest_content_info

        # 任务奖励表格
        reward_info = self.content_renderer.render_quest_reward_table(quest)
        html += reward_info

        # 任务描述
        if greeting_display:
            html += f"""                <div class="quest-section debug-section">
                    <div class="quest-label">{self._get_ui_text("quest_description")}</div>
                    <div class="quest-text">{greeting_display}</div>
                </div>
"""
        if complete_display:
            html += f"""                <div class="quest-section debug-section">
                    <div class="quest-label">{self._get_ui_text("complete_description")}</div>
                    <div class="quest-text">{complete_display}</div>
                </div>
"""

        # 前置任务将在HTMLGenerator中处理（需要quest_extractor）
        html += """            </div>
"""
        return html, search_data

    def build_index_page(
        self, grouped_quests, inactive_npcs=None, equipment_npcs=None, preferred_npcs=None, not_recommended_npcs=None
    ):
        """
        构建汇总索引页

        Args:
            grouped_quests: 按NPC分组的任务字典
                           可以是 {npc_name: quest_list} 或 {npc_name: (npc_en, quest_list)}
            inactive_npcs: 失效NPC的英文名集合（可选）
            equipment_npcs: 装备NPC的英文名集合（可选）
            preferred_npcs: 优选NPC的英文名集合（可选）
            not_recommended_npcs: 不推荐NPC的英文名集合（可选）

        Returns:
            生成的文件路径
        """
        inactive_npcs = inactive_npcs or set()
        equipment_npcs = equipment_npcs or set()
        preferred_npcs = preferred_npcs or set()
        not_recommended_npcs = not_recommended_npcs or set()
        filepath = os.path.join(self.output_dir, "index.html")

        html_content = HTMLTemplate.generate_header(
            self._get_ui_text("page_title"),
            include_back_link=True,
            language=self.language,
            ui_translations=self.ui_text,
            dark_mode=self.dark_mode,
            parent_url="../index.html",
            parent_label="返回首页",
        )

        # 搜索框
        html_content += f"""
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="{self._get_ui_text("search_npc")}" onkeyup="filterQuests()">
        </div>
"""

        # 分离五组NPC
        active_items = []
        equipment_items = []
        preferred_items = []
        not_recommended_items = []
        inactive_items = []
        for npc_name, quest_data in sorted(grouped_quests.items()):
            if isinstance(quest_data, tuple) and len(quest_data) == 2:
                npc_en, quests = quest_data
            else:
                npc_en = npc_name
                quests = quest_data

            if npc_en in inactive_npcs:
                inactive_items.append((npc_name, npc_en, quests))
            elif npc_en in equipment_npcs:
                equipment_items.append((npc_name, npc_en, quests))
            elif npc_en in preferred_npcs:
                preferred_items.append((npc_name, npc_en, quests))
            elif npc_en in not_recommended_npcs:
                not_recommended_items.append((npc_name, npc_en, quests))
            else:
                active_items.append((npc_name, npc_en, quests))

        # 渲染装备NPC
        if equipment_items:
            html_content += f"""
        <h2>{self._get_ui_text("equipment_npcs")}</h2>
        <div class="npc-grid" id="npcGridEquipment">
"""
            for npc_name, npc_en, quests in equipment_items:
                html_content += self._build_npc_card(npc_name, npc_en, len(quests))
            html_content += "        </div>\n"

        # 渲染优选NPC
        if preferred_items:
            html_content += f"""
        <h2>{self._get_ui_text("preferred_npcs")}</h2>
        <div class="npc-grid" id="npcGridPreferred">
"""
            for npc_name, npc_en, quests in preferred_items:
                html_content += self._build_npc_card(npc_name, npc_en, len(quests))
            html_content += "        </div>\n"

        # 渲染活跃NPC
        html_content += f"""
        <h2>{self._get_ui_text("active_npcs")}</h2>
        <div class="npc-grid" id="npcGridActive">
"""
        for npc_name, npc_en, quests in active_items:
            html_content += self._build_npc_card(npc_name, npc_en, len(quests))
        html_content += "        </div>\n"

        # 渲染不推荐NPC
        if not_recommended_items:
            html_content += f"""
        <h2>{self._get_ui_text("not_recommended_npcs")}</h2>
        <div class="npc-grid" id="npcGridNotRecommended">
"""
            for npc_name, npc_en, quests in not_recommended_items:
                html_content += self._build_npc_card(npc_name, npc_en, len(quests))
            html_content += "        </div>\n"

        # 渲染失效NPC
        if inactive_items:
            html_content += f"""
        <h2 class="inactive-section">{self._get_ui_text("inactive_npcs")}</h2>
        <div class="npc-grid inactive-grid" id="npcGridInactive">
"""
            for npc_name, npc_en, quests in inactive_items:
                html_content += self._build_npc_card(npc_name, npc_en, len(quests))
            html_content += "        </div>\n"

        # 添加搜索脚本
        html_content += self._build_search_script()

        html_content += HTMLTemplate.generate_footer()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[{self.language}] 已生成汇总页: {filepath}")
        return filepath

    def build_npc_page(self, npc_name, npc_name_en, quests, quest_extractor=None):
        """
        构建单个NPC的任务页面

        Args:
            npc_name: NPC显示名称
            npc_name_en: NPC英文名称
            quests: 该NPC的任务列表
            quest_extractor: QuestExtractor实例（用于获取前置任务显示名）

        Returns:
            生成的文件路径
        """
        safe_filename = re.sub(r'[<>:"/\\\\|?*]', "_", npc_name_en)
        filepath = os.path.join(self.output_dir, f"{safe_filename}.html")

        # 页面标题
        page_title = f"{npc_name}"
        if npc_name != npc_name_en and self.language == "en":
            page_title += f" ({npc_name_en})"

        html_content = HTMLTemplate.generate_header(
            f"{page_title} - {self._get_ui_text('quest_count').rstrip('数量')}列表",
            include_back_link=True,
            language=self.language,
            ui_translations=self.ui_text,
            dark_mode=self.dark_mode,
            parent_url="../index.html",
            parent_label="返回首页",
        )

        html_content += f"""
        <p style="text-align: center; color: #666;">{len(quests)} {self._get_ui_text("quests")}</p>

        <div class="search-box">
            <input type="text" id="searchInput" placeholder="{self._get_ui_text("search_quest")}" onkeyup="filterQuests()">
        </div>

        <div class="quest-grid" id="questGrid">
"""

        for quest in quests:
            quest_card_html, search_data = self._build_quest_card(quest)

            # 前置任务处理（如果提供了quest_extractor）
            required_quest_display = None
            if quest_extractor:
                required_quest_display = quest_extractor.get_required_quest_display_name(quest)

            # 插入前置任务信息
            if required_quest_display:
                insert_pos = quest_card_html.rfind("            </div>")
                before_end = quest_card_html[:insert_pos]
                after_end = quest_card_html[insert_pos:]
                quest_card_html = before_end + f"""                <div class="quest-section">
                    <div class="quest-label">{self._get_ui_text("required_quest")}</div>
                    <div class="quest-text required-quest">{required_quest_display}</div>
                </div>
""" + after_end
            elif quest.get("required_quest"):
                insert_pos = quest_card_html.rfind("            </div>")
                before_end = quest_card_html[:insert_pos]
                after_end = quest_card_html[insert_pos:]
                quest_card_html = before_end + f"""                <div class="quest-section">
                    <div class="quest-label">{self._get_ui_text("required_quest")}</div>
                    <div class="quest-text">{quest['required_quest']}</div>
                </div>
""" + after_end

            html_content += quest_card_html

        html_content += """        </div>"""

        # 搜索脚本
        html_content += self._build_search_script()

        html_content += HTMLTemplate.generate_footer()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[{self.language}] 已生成NPC页面: {filepath}")
        return filepath

    def build_all_pages(
        self,
        grouped_quests,
        quest_extractor=None,
        inactive_npcs=None,
        equipment_npcs=None,
        preferred_npcs=None,
        not_recommended_npcs=None,
        dark_mode=False,
    ):
        """
        构建所有页面

        Args:
            grouped_quests: 按NPC分组的任务字典
            quest_extractor: QuestExtractor实例（可选，用于前置任务）
            inactive_npcs: 失效NPC的英文名集合（可选）
            equipment_npcs: 装备NPC的英文名集合（可选）
            preferred_npcs: 优选NPC的英文名集合（可选）
            not_recommended_npcs: 不推荐NPC的英文名集合（可选）
            dark_mode: 是否使用深色主题

        Returns:
            生成的文件路径列表
        """
        generated_files = []

        # 生成汇总页
        index_path = self.build_index_page(
            grouped_quests,
            inactive_npcs=inactive_npcs,
            equipment_npcs=equipment_npcs,
            preferred_npcs=preferred_npcs,
            not_recommended_npcs=not_recommended_npcs,
        )
        generated_files.append(index_path)

        # 生成各NPC页面
        for npc_name, quest_data in grouped_quests.items():
            if isinstance(quest_data, tuple) and len(quest_data) == 2:
                npc_en, quests = quest_data
            else:
                npc_en = npc_name
                quests = quest_data

            npc_path = self.build_npc_page(npc_name, npc_en, quests, quest_extractor)
            generated_files.append(npc_path)

        print(f"\n[{self.language}] 共生成 {len(generated_files)} 个HTML文件")
        return generated_files
