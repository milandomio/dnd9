# 任务内容限定地图（dungeon_type）

## 背景

所有任务内容（Kill、Props、Fetch、Explore、UseItem、Hold、Escape）在游戏数据中都有 `DungeonIdTags` 字段，指明该任务目标必须在哪个地图类型中完成。

例如 #13 "闪亮的秘密"（打开狮头宝箱×2）的 `QuestContentProps` 数据：
```json
"DungeonIdTags": [{ "TagName": "Id.Dungeon.Goblin" }]
```

## 改动

### 后端

1. **`api/src/quest_extractor/quest_extractor.py`**：新增 `get_dungeon_type_translation(content_data)`，从 `DungeonIdTags` 提取并翻译地图类型名称（逻辑与 `get_escape_target_translation` 相同）。
2. **`api/src/quest_collector.py`**：在所有内容类型分支中，调用 `get_dungeon_type_translation(cd)`，将结果存入 `item["dungeon_type"]`。

### 类型

**`web/src/types/quest.ts`**：`QuestContent` 新增 `dungeon_type?: string`。

### 前端

**`web/src/pages/QuestNPCDetailPage.tsx`**：任务目标表格中新增"目标地图"列（仅当有内容条目包含 `dungeon_type` 时显示）。

## 效果

- #13 的目标行会显示：类型「道具」 目标「狮头宝箱」 目标地图「苍炎岭」 数量「2」
- 凡是有 `DungeonIdTags` 限定的任务目标（Kill / Props / Fetch 等）都会显示对应地图
- 无限定的条目（`dungeon_type` 为空）该列留空
