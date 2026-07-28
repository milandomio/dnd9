# 地图分组名 i18n 修复计划

## 问题

`LootdropDetailPage` 上每个地图分组标题（如"废墟2层（地穴）"）在 en 页仍显示中文。后端在构建时将 slot_key 翻译成中文后拼接为 `group_display` 字符串，前端直接渲染该字符串无法 i18n。

## 根因

1. `locale_builder.py` 的 `_load_used_keys()` 只扫描 entity JSON 的 `translation_key`，从不扫描 `dungeon_modules.json`，`Text_UI_WB_DungeonSlot_*` 从未进入 locale。
2. 构建阶段把 slot_key 拼成中文字符串，前端无法按语言切换。

## 已定策略（2026-07-26）

- **全量修复**：所有 `group_display` 渲染点（含 `ssg.mjs`）改为 `formatGroupLabel`
- **保留 `group_display` 作 fallback**：`DEFAULT_LANG=zh-Hans` 不加载 locale 时，用中文 `group_display` 兜底
- **显示公式**：`{t(group_key)}{group_floor}{ui.common.floor}[（{t(group_sub_key)}）]`

## 修复方案

### 后端：存 key + 保留中文 fallback

1. **`translator.py`** ✅ — `resolve_group_label(group) -> dict|None`
   ```python
   return {"slot_key": slot_key, "floor": floor, "sub_key": sub_key}
   ```

2. **`collector.py`** ✅（待补双写）— 注入三字段 + `_resolve_group_display()` 辅助
   ```python
   _mod["group_key"] / group_floor / group_sub_key
   _mod["group_display"] = _resolve_group_display(_g, translations)  # 待补
   ```

3. **`module_builder.py`** ⏳ — 确认 `build_and_save_modules_data()` `.copy()` 透传四字段到 `dungeon_modules.json`

4. **`index_export.py`** ⏳ — `quest_items_groups` 写入 `group_key`/`group_floor`/`group_sub_key`（保留 `group_display`）；search_index tag 暂继续用中文 resolver

5. **`locale_builder.py`** ⏳ — 扫描 `dungeon_modules.json` 的 `group_key` + `group_sub_key` 进 used_keys

### 前端

6. **`web/src/types/data.ts`** ⏳ — 新增 `group_key`/`group_floor`/`group_sub_key`，**保留** `group_display`

7. **`web/src/utils/formatGroupLabel.ts`** ⏳（新）— 统一组装逻辑 + fallback

8. **`web/src/i18n/uiLocale.ts`** ⏳ — 各语言 `ui.common.floor`

9. **全量页面** ⏳：
   | 文件 | 渲染点 |
   |------|--------|
   | LootdropDetailPage | 分组标题、debug 表 |
   | DetailPage | 分组标题、debug 表 |
   | DungeonModuleDetailPage | groupLabel |
   | DungeonModuleGroupPage | groupLabel |
   | DungeonModulesPage | 分组摘要 |
   | QuestItemsPage | 分组卡片 |
   | QuestItemGroupPage | 页头 + 模块分组 |
   | ExplorePage | 分组标签 |

10. **`web/scripts/ssg.mjs`** ⏳ — SSR 分组摘要携带三 key 字段 + group_display

## 当前进度

| 步骤 | 状态 |
|------|------|
| translator.py | ✅ |
| collector.py 三字段 | ✅ |
| collector.py 双写 group_display | ✅ |
| module_builder 透传确认 | ✅（.copy() 无需改） |
| index_export quest 三字段 | ✅ |
| locale_builder 扫描 | ✅ |
| types + formatGroupLabel + ui.floor | ✅ |
| 8 页面 + ssg.mjs | ✅ |
| TSC + Prettier + SESSION_CHANGES | ✅ |
| 管线 python main.py 验证 | ✅ EXIT:0；locale/en 含 8 个 DungeonSlot key；en=`The Ruins2F（The Crypt）` |

## 验证

- `python main.py` 后 `dungeon_modules.json` 含四字段
- `locale/en.json` 出现 `Text_UI_WB_DungeonSlot_*`
- en 页分组标题非「废墟2层」；zh-Hans 仍为中文
- TSC + Prettier 通过

## 涉及文件

| 文件 | 改动 |
|------|------|
| `api/src/translator.py` | resolve_group_label 返回对象 |
| `api/src/collector.py` | 三字段 + group_display 双写 |
| `api/src/module_builder.py` | 透传确认（可能无需改） |
| `api/src/index_export.py` | quest 分组写 key 字段 |
| `api/src/locale_builder.py` | 扫描 dungeon_modules |
| `web/src/types/data.ts` | 接口新增字段 |
| `web/src/utils/formatGroupLabel.ts` | 新建 |
| `web/src/i18n/uiLocale.ts` | ui.common.floor |
| `web/src/pages/*`（8 页） | formatGroupLabel |
| `web/scripts/ssg.mjs` | SSR 分组字段 |
