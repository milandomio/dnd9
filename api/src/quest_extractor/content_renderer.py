#!/usr/bin/env python
"""
任务内容渲染器
负责渲染各类任务目标的HTML表格
"""

import re
from html import escape as _esc


class ContentRenderer:
    """任务内容渲染器"""

    # 常见物品后缀（用于尝试翻译）
    ITEM_SUFFIXES = ["_1001", "_2001", "_3001", "_4001", "_5001", "Pearl"]

    def __init__(self, quest_extractor, ui_translations=None):
        """
        初始化内容渲染器

        Args:
            quest_extractor: QuestExtractor实例，用于访问翻译器
            ui_translations: UITranslations实例，用于获取UI文本
        """
        self.quest_extractor = quest_extractor
        self.translator = quest_extractor.translator if quest_extractor else None
        self.ui_translations = ui_translations
        self.language = self.translator.language if self.translator else "zh-Hans"

    def render_quest_content_table(self, quest):
        """
        渲染任务目标信息表格

        Args:
            quest: 任务数据字典

        Returns:
            HTML字符串
        """
        contents = quest.get("contents", [])
        if not contents:
            return ""

        OPEN_BRACE = chr(60)  # noqa: N806
        CLOSE_BRACE = chr(62)  # noqa: N806
        SLASH = chr(47)  # noqa: N806

        html_parts = []
        html_parts.append("                " + OPEN_BRACE + 'div class="quest-content-section"' + CLOSE_BRACE)
        html_parts.append(
            "                    "
            + OPEN_BRACE
            + 'div class="quest-content-label"'
            + CLOSE_BRACE
            + "任务目标"
            + OPEN_BRACE
            + SLASH
            + "div"
            + CLOSE_BRACE
        )
        html_parts.append("                    " + OPEN_BRACE + 'table class="quest-content-table"' + CLOSE_BRACE)

        # 检查列需求
        has_loot_state = any(c.get("content_data", {}).get("ItemLootState") for c in contents)
        has_rarity = any(c.get("content_data", {}).get("RarityType") for c in contents)
        has_useitem_dungeon = any(
            c.get("content_type") == "UseItem" and c.get("content_data", {}).get("DungeonIdTags") for c in contents
        )

        # 表头
        type_header = "类型" if self.quest_extractor.translator.language.startswith("zh") else "Type"
        target_header = "目标" if self.quest_extractor.translator.language.startswith("zh") else "Target"
        count_header = "数量" if self.quest_extractor.translator.language.startswith("zh") else "Count"
        loot_state_header = "战利品状态" if has_loot_state else ""
        rarity_header = "稀有度" if has_rarity else ""
        dungeon_type_header = "地牢类型" if has_useitem_dungeon else ""

        html_parts.append("                        " + OPEN_BRACE + "tr" + CLOSE_BRACE)
        html_parts.append(
            "                            "
            + OPEN_BRACE
            + "th"
            + CLOSE_BRACE
            + type_header
            + OPEN_BRACE
            + SLASH
            + "th"
            + CLOSE_BRACE
        )
        html_parts.append(
            "                            "
            + OPEN_BRACE
            + "th"
            + CLOSE_BRACE
            + target_header
            + OPEN_BRACE
            + SLASH
            + "th"
            + CLOSE_BRACE
        )
        if has_loot_state:
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "th"
                + CLOSE_BRACE
                + loot_state_header
                + OPEN_BRACE
                + SLASH
                + "th"
                + CLOSE_BRACE
            )
        if has_rarity:
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "th"
                + CLOSE_BRACE
                + rarity_header
                + OPEN_BRACE
                + SLASH
                + "th"
                + CLOSE_BRACE
            )
        if has_useitem_dungeon:
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "th"
                + CLOSE_BRACE
                + dungeon_type_header
                + OPEN_BRACE
                + SLASH
                + "th"
                + CLOSE_BRACE
            )
        html_parts.append(
            "                            "
            + OPEN_BRACE
            + "th"
            + CLOSE_BRACE
            + count_header
            + OPEN_BRACE
            + SLASH
            + "th"
            + CLOSE_BRACE
        )
        html_parts.append("                        " + OPEN_BRACE + SLASH + "tr" + CLOSE_BRACE)

        # 渲染每一行
        for content in contents:
            content_type = content.get("content_type", "Unknown")
            content_data = content.get("content_data", {})
            asset_path = content.get("asset_path", "")

            # 获取类型名称
            type_key = self._get_type_key(content_type)
            type_name = self._get_type_name(type_key, content_type)

            # 获取数量
            content_count = content_data.get("ContentCount", 1)

            # 渲染目标
            target_name, loot_state, rarity, dungeon_type = self._render_content_target(
                content_type, content_data, asset_path
            )

            # 处理稀有度情况下去掉后缀
            if has_rarity and target_name != "-":
                target_name = re.sub(r"（裂开）", "", target_name)

            # 输出行
            html_parts.append("                        " + OPEN_BRACE + "tr" + CLOSE_BRACE)
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "td"
                + CLOSE_BRACE
                + _esc(type_name)
                + OPEN_BRACE
                + SLASH
                + "td"
                + CLOSE_BRACE
            )
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "td"
                + CLOSE_BRACE
                + _esc(target_name)
                + OPEN_BRACE
                + SLASH
                + "td"
                + CLOSE_BRACE
            )
            if has_loot_state:
                html_parts.append(
                    "                            "
                    + OPEN_BRACE
                    + "td"
                    + CLOSE_BRACE
                    + _esc(loot_state)
                    + OPEN_BRACE
                    + SLASH
                    + "td"
                    + CLOSE_BRACE
                )
            if has_rarity:
                html_parts.append(
                    "                            "
                    + OPEN_BRACE
                    + "td"
                    + CLOSE_BRACE
                    + _esc(rarity)
                    + OPEN_BRACE
                    + SLASH
                    + "td"
                    + CLOSE_BRACE
                )
            if has_useitem_dungeon:
                html_parts.append(
                    "                            "
                    + OPEN_BRACE
                    + "td"
                    + CLOSE_BRACE
                    + _esc(dungeon_type)
                    + OPEN_BRACE
                    + SLASH
                    + "td"
                    + CLOSE_BRACE
                )
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "td"
                + CLOSE_BRACE
                + str(content_count)
                + OPEN_BRACE
                + SLASH
                + "td"
                + CLOSE_BRACE
            )
            html_parts.append("                        " + OPEN_BRACE + SLASH + "tr" + CLOSE_BRACE)

        html_parts.append("                    " + OPEN_BRACE + SLASH + "table" + CLOSE_BRACE)
        html_parts.append("                " + OPEN_BRACE + SLASH + "div" + CLOSE_BRACE)

        return "\n".join(html_parts)

    def _get_type_key(self, content_type):
        """获取内容类型的UI文本键"""
        type_map = {
            "Kill": "kill",
            "Fetch": "fetch",
            "Explore": "explore",
            "Props": "props",
            "UseItem": "use_item",
            "Damage": "damage",
            "Escape": "escape",
            "Hold": "hold",
        }
        return type_map.get(content_type, "Unknown")

    def _get_type_name(self, type_key, content_type):
        """获取类型显示名称"""
        name = self._get_ui_text(type_key)
        return name if name != type_key else content_type

    def _translate_item_name(self, item_key):
        """
        翻译物品名称

        Args:
            item_key: 翻译键，如 "Text_DesignData_Item_Item_Sword"

        Returns:
            翻译后的物品名称，失败返回原始键名
        """
        if not self.translator:
            return item_key.split("_")[-1]

        translated = self.translator.translate(item_key)
        if translated:
            return translated

        # 尝试带后缀的翻译
        for suffix in self.ITEM_SUFFIXES:
            key_with_suffix = f"{item_key}{suffix}"
            translated = self.translator.translate(key_with_suffix)
            if translated:
                return translated

        return item_key.split("_")[-1]

    def _translate_monster_name(self, monster_key):
        """
        翻译怪物名称

        Args:
            monster_key: 怪物名称，如 "Goblin"

        Returns:
            翻译后的怪物名称
        """
        if not self.translator:
            return monster_key

        full_key = f"Text_DesignData_Monster_Monster_{monster_key}"
        translated = self.translator.translate(full_key)
        return translated if translated else monster_key

    def _render_content_target(self, content_type, content_data, asset_path=""):
        """
        渲染内容目标

        Args:
            content_type: 内容类型
            content_data: 内容数据字典
            asset_path: 资源路径（用于Explore等类型）

        Returns:
            (target_name, loot_state, rarity, dungeon_type)
        """
        target_name = ""
        loot_state = ""
        rarity = ""
        dungeon_type = ""

        if content_type == "Kill":
            kill_tag = content_data.get("KillTag", {}).get("TagName", "")
            if kill_tag:
                target_name = kill_tag.split(".")[-1] if "." in kill_tag else kill_tag
                target_name = self._translate_monster_name(target_name)

        elif content_type == "Fetch":
            target_name, loot_state, rarity = self._render_fetch_target(content_data)

        elif content_type == "Props":
            target_name = self._render_props_target(content_data)

        elif content_type == "Explore":
            if self.quest_extractor and asset_path:
                translated = self.quest_extractor.get_explore_target_translation(asset_path)
                if translated:
                    target_name = translated
                else:
                    # Fallback: derive dungeon module name from asset_path filename and try direct translation
                    filename = asset_path.split("/")[-1].split(".")[0]
                    prefix = "Id_QuestContent_Explore_"
                    if filename.startswith(prefix):
                        module_name = filename[len(prefix) :]
                        # Remove trailing numeric suffix (e.g., _01, _02)
                        parts = module_name.split("_")
                        if parts and parts[-1].isdigit():
                            module_name = "_".join(parts[:-1])
                        if self.translator:
                            key1 = f"Text_DesignData_Dungeon_DungeonModule_{module_name}"
                            translated1 = self.translator.translate(key1)
                            if translated1:
                                target_name = translated1
                            else:
                                key2 = f"Text_DesignData_Dungeon_DungeonType_{module_name}"
                                translated2 = self.translator.translate(key2)
                                target_name = translated2 or module_name.replace("_", " ")
                        else:
                            target_name = module_name.replace("_", " ")
                    else:
                        target_name = filename
            else:
                target_name = "-"

        elif content_type == "Hold":
            if self.quest_extractor and asset_path:
                translated = self.quest_extractor.get_hold_target_translation(asset_path)
                if translated:
                    target_name = translated
                else:
                    # Fallback: derive dungeon module name from asset_path filename and try direct translation
                    filename = asset_path.split("/")[-1].split(".")[0]
                    prefix = "Id_QuestContent_Hold_"
                    if filename.startswith(prefix):
                        module_name = filename[len(prefix) :]
                        # Remove trailing numeric suffix (e.g., _01, _02)
                        parts = module_name.split("_")
                        if parts and parts[-1].isdigit():
                            module_name = "_".join(parts[:-1])
                        if self.translator:
                            key1 = f"Text_DesignData_Dungeon_DungeonModule_{module_name}"
                            translated1 = self.translator.translate(key1)
                            if translated1:
                                target_name = translated1
                            else:
                                key2 = f"Text_DesignData_Dungeon_DungeonType_{module_name}"
                                translated2 = self.translator.translate(key2)
                                target_name = translated2 or module_name.replace("_", " ")
                        else:
                            target_name = module_name.replace("_", " ")
                    else:
                        target_name = filename
            else:
                target_name = "-"

        elif content_type == "Escape":
            if self.quest_extractor:
                translated = self.quest_extractor.get_escape_target_translation(content_data)
                target_name = translated if translated else "-"
            else:
                target_name = "-"

        elif content_type == "UseItem":
            target_name, dungeon_type = self._render_useitem_target(content_data)

        else:
            target_name = "-"

        return target_name, loot_state, rarity, dungeon_type

    def _resolve_item_target(self, content_data):
        """
        解析物品目标名称（TypeTag 或 ItemIdTag）。

        Returns:
            target_name: 物品名称
        """
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
                            key_with_suffix = f"Text_DesignData_Item_Item_{item_name}{suffix}"
                            translated = self.translator.translate(key_with_suffix)
                            if translated:
                                break
                        if not translated:
                            translated = self.translator.translate(props_key)
                    target_name = translated if translated else item_name
                else:
                    target_name = item_name

        return target_name

    def _render_fetch_target(self, content_data):
        """
        渲染 Fetch 类型目标

        Returns:
            (target_name, loot_state, rarity)
        """
        target_name = self._resolve_item_target(content_data)
        loot_state = ""
        rarity = ""

        # 战利品状态
        loot_state_raw = content_data.get("ItemLootState", "")
        if loot_state_raw == "EDCItemLootState::Looted":
            loot_state = self._get_ui_text("looted") or "Yes"
        else:
            loot_state = self._get_ui_text("not_looted") or "No"

        # 稀有度
        rarity_tag = content_data.get("RarityType", {})
        if isinstance(rarity_tag, dict):
            rarity_tag_name = rarity_tag.get("TagName", "")
            if rarity_tag_name and "Type.Item.Rarity." in rarity_tag_name:
                rarity_name = rarity_tag_name.split("Type.Item.Rarity.")[-1]
                rarity_key = f"Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_{rarity_name}"
                if self.translator:
                    translated = self.translator.translate(rarity_key)
                    rarity = translated if translated else rarity_name
                else:
                    rarity = rarity_name

        return target_name, loot_state, rarity

    def _render_props_target(self, content_data):
        """渲染 Props 类型目标"""
        # 获取 PropsIdTag（优先）
        props_id_tag = content_data.get("PropsIdTag", {})
        if isinstance(props_id_tag, dict):
            props_id_tag = props_id_tag.get("TagName", "")

        # 如果没有 PropsIdTag，尝试 TagName 或 PropsTag
        if not props_id_tag:
            props_tag = content_data.get("TagName", "") or ""
            if not props_tag:
                props_tag_obj = content_data.get("PropsTag", {})
                if isinstance(props_tag_obj, dict):
                    props_tag = props_tag_obj.get("TagName", "")
            props_id_tag = props_tag

        # 使用 QuestExtractor 查找翻译
        if self.quest_extractor and props_id_tag:
            translated = self.quest_extractor.get_props_target_translation(props_id_tag)
            if translated:
                return translated

        # Fallback: 显示原始标签名
        if props_id_tag:
            if "Id.Props." in props_id_tag:
                return props_id_tag.split("Id.Props.")[-1]
            elif "." in props_id_tag:
                return props_id_tag.split(".")[-1]
            else:
                return props_id_tag

        return "-"

    def _render_useitem_target(self, content_data):
        """
        渲染 UseItem 类型目标

        Returns:
            (target_name, dungeon_type)
        """
        target_name = self._resolve_item_target(content_data)
        dungeon_type = ""

        # 地牢类型（类似 Escape）
        if content_data.get("DungeonIdTags"):
            if self.quest_extractor:
                translated = self.quest_extractor.get_escape_target_translation(content_data)
                dungeon_type = translated if translated else "-"
            else:
                dungeon_type = "-"

        return target_name, dungeon_type

    def _get_ui_text(self, key):
        """获取UI文本"""
        if self.ui_translations:
            return self.ui_translations.get_text(self.language, key)
        return key

    def render_quest_reward_table(self, quest):
        """
        渲染任务奖励信息表格

        Args:
            quest: 任务数据字典

        Returns:
            HTML字符串
        """
        rewards = quest.get("rewards", [])
        if not rewards:
            return ""

        OPEN_BRACE = chr(60)  # noqa: N806
        CLOSE_BRACE = chr(62)  # noqa: N806
        SLASH = chr(47)  # noqa: N806

        type_label = self._get_ui_text("reward_type")
        name_label = self._get_ui_text("reward_item")
        count_label = self._get_ui_text("reward_count")

        html_parts = []
        html_parts.append("                " + OPEN_BRACE + 'div class="quest-reward-section"' + CLOSE_BRACE)
        html_parts.append(
            "                    "
            + OPEN_BRACE
            + 'div class="quest-content-label"'
            + CLOSE_BRACE
            + self._get_ui_text("quest_reward")
            + OPEN_BRACE
            + SLASH
            + "div"
            + CLOSE_BRACE
        )
        html_parts.append("                    " + OPEN_BRACE + 'table class="quest-content-table"' + CLOSE_BRACE)

        # 表头
        html_parts.append("                        " + OPEN_BRACE + "tr" + CLOSE_BRACE)
        html_parts.append(
            "                            "
            + OPEN_BRACE
            + "th"
            + CLOSE_BRACE
            + type_label
            + OPEN_BRACE
            + SLASH
            + "th"
            + CLOSE_BRACE
        )
        html_parts.append(
            "                            "
            + OPEN_BRACE
            + "th"
            + CLOSE_BRACE
            + name_label
            + OPEN_BRACE
            + SLASH
            + "th"
            + CLOSE_BRACE
        )
        html_parts.append(
            "                            "
            + OPEN_BRACE
            + "th"
            + CLOSE_BRACE
            + count_label
            + OPEN_BRACE
            + SLASH
            + "th"
            + CLOSE_BRACE
        )
        html_parts.append("                        " + OPEN_BRACE + SLASH + "tr" + CLOSE_BRACE)

        # 渲染每一行
        for reward in rewards:
            reward_id = reward.get("RewardId", "")
            reward_count = reward.get("RewardCount", 1)

            # 获取翻译后的名称和类型标签
            if self.quest_extractor:
                name, type_key = self.quest_extractor.get_reward_item_info(reward)
            else:
                name = reward_id
                type_key = "item"

            type_display = self._get_reward_type_label(type_key)

            # 好感度奖励行使用淡红色背景
            row_class = ' style="background-color: #ffcccc;"' if type_key == "affinity" else ""
            html_parts.append("                        " + OPEN_BRACE + "tr" + row_class + CLOSE_BRACE)
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "td"
                + CLOSE_BRACE
                + _esc(type_display)
                + OPEN_BRACE
                + SLASH
                + "td"
                + CLOSE_BRACE
            )
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "td"
                + CLOSE_BRACE
                + _esc(name or "")
                + OPEN_BRACE
                + SLASH
                + "td"
                + CLOSE_BRACE
            )
            html_parts.append(
                "                            "
                + OPEN_BRACE
                + "td"
                + CLOSE_BRACE
                + str(reward_count)
                + OPEN_BRACE
                + SLASH
                + "td"
                + CLOSE_BRACE
            )
            html_parts.append("                        " + OPEN_BRACE + SLASH + "tr" + CLOSE_BRACE)

        html_parts.append("                    " + OPEN_BRACE + SLASH + "table" + CLOSE_BRACE)
        html_parts.append("                " + OPEN_BRACE + SLASH + "div" + CLOSE_BRACE)

        return "\n".join(html_parts)

    def _get_reward_type_label(self, type_key):
        """获取奖励类型的显示标签"""
        return self._get_ui_text(f"reward_{type_key}") or type_key
