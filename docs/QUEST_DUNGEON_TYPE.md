# 任务内容限定地图（dungeon_type）

## 背景

所有任务内容（Kill、Props、Fetch、Explore、UseItem、Hold、Escape）在游戏数据中都有 `DungeonIdTags` 字段，指明该任务目标必须在哪个地图类型中完成。

例如 #13 "闪亮的秘密"（打开狮头宝箱×2）的 `QuestContentProps` 数据：
```json
"DungeonIdTags": [{ "TagName": "Id.Dungeon.Goblin" }]
```

此前只在 Escape 类型中提取了地图信息，其他类型均丢弃了这个字段。

## 改动

### 1. `api/src/quest_extractor/quest_extractor.py:307-344`

新增 `get_dungeon_type_translation(content_data) → str|None`，从 `DungeonIdTags` 提取并翻译地图类型名称。

```python
def get_dungeon_type_translation(self, content_data):
    """从 content_data 中提取 DungeonIdTags 并翻译为地图类型名称。"""
    if not content_data:
        return None
    dungeon_id_tags = content_data.get("DungeonIdTags", [])
    ...
    # 翻译优先级：Group key → Type key → Type key + _A/_N/_HR/_AHR → 回退 dungeon_name
```

原有的 `get_escape_target_translation` 改为委托此方法。翻译键格式：
- `Text_DesignData_Dungeon_DungeonType_Group_{name}` — 组名（如 "苍炎岭"）
- `Text_DesignData_Dungeon_DungeonType_{name}` — 类型名
- `Text_DesignData_Dungeon_DungeonType_{name}_A` / `_N` / `_HR` / `_AHR` — 带后缀的 fallback

### 2. `api/src/quest_collector.py:263-265`

在 `_extract_npc_list` 的内容循环中，对所有内容类型（Kill / Fetch / Explore / Props / UseItem / Hold / Escape）统一提取 `dungeon_type`：

```python
dungeon_type = extractor.get_dungeon_type_translation(cd)
if dungeon_type:
    item["dungeon_type"] = dungeon_type
```

### 3. `web/src/types/quest.ts:7`

```typescript
export interface QuestContent {
  type: string;
  target: string;
  count: number;
  loot_state?: string;
  rarity?: string;
  dungeon_type?: string;  // 新增
}
```

### 4. `web/src/pages/QuestNPCDetailPage.tsx`

- **第 371 行**：`hasDungeonType` 检测（`q.contents.some(c => c.dungeon_type)`）
- **第 430-442 行**：条件渲染 `<th>目标地图</th>`（宽度 5em，紧跟"目标"列后）
- **第 548-556 行**：条件渲染 `<td>{c.dungeon_type || ''}</td>`（蓝色字体，color: #42a5f5 / 浅色: #1565c0）

列仅在当前任务的任意内容条目标包含 `dungeon_type` 时显示；无限定的条目该列留空。

## 数据流

```
游戏 QuestContent JSON（含 DungeonIdTags）
  → quest_collector._extract_npc_list()
    → extractor.get_dungeon_type_translation(cd)
      → translator.translate("Text_DesignData_Dungeon_DungeonType_...")
  → DB quest_npcs.quests_json
  → data/json/quest_npc.json（含 dungeon_type）
  → QuestNPCDetailPage 表格渲染
```

## 效果

- #13 "闪亮的秘密"：**道具 · 狮头宝箱 · 苍炎岭 · ×2**
- #16 "幸运之羽"：**击杀 · 蛇尾鸡 · 被遗忘的城堡 · ×5**
- #3/#4/#9/#19 等无 `DungeonIdTags` 的任务不显示"目标地图"列
- Escape 类型的行为不变（`target` 依然是地图名，`dungeon_type` 与 `target` 相同）
