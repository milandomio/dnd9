# 多语言支持方案

## 概述

通过前端额外加载目标语言的 Game.json 翻译映射，实现在不增加 SSG 构建复杂度的情况下切换显示语言。

## 核心机制

```
pipeline:
  Game.json(zh-Hans) ─→ NameResolver 模糊匹配 ─→ (翻译值, 翻译键)
  现在只存 translation，改为同时存 translation_key

运行时:
  URL ?lang=en → fetch data/lang/en.json → 用 translation_key 查表
  → 替换页面所有显示文本
  没有 key / 查不到 → 回退中文（默认）
```

**关键前提已验证**：en 与 zh-Hans Game.json 的 Key 完全一致（如 `Text_DesignData_Item_Item_Bandage_1001`），仅 value 不同。因此中文 pipeline 解析出的 `translation_key` 可直接用于任何语言查表。

## URL 策略

- 参数 `?lang=en` / `?lang=ja` 跟在任何路由后面
- 无参数 = zh-Hans（默认）
- SSG 仍只生成中文 HTML，hydrate 后读 `?lang=` 加载对应语言
- 复制任意 URL 即带语言参数，分享即用

```
/items/Bandage/           → 中文
/items/Bandage/?lang=en   → 英文
/monsters/?lang=ja        → 日文
```

## 状态同步规则

```
优先级：URL ?lang= > localStorage > 默认 zh-Hans

URL → 状态：useEffect 监听 location.search
状态 → URL：setLanguage() 调用 navigate('...?lang=en', { replace: true })
```

导航后自动补 `?lang=`：当 language !== zh-Hans 且当前 URL 无 `?lang` 时自动补上。

## 改造范围

### 后端（pipeline 时）

| 文件 | 改动 |
|------|------|
| `config.py` | 新增 `LOCALIZATION_PARENT_DIR` 指向 `Localization/Game/` 根目录（不含语言后缀） |
| `db/_helpers.py` | `load_game_json()` 增加 `language` 参数，可加载任意语言 Game.json |
| `entity_export.py` | items/monsters/props 三个 export 函数的 entity_data 和 index 都增加 `"translation_key"` 字段 |
| `lootdrop_builder.py` | `build_loot_index()` index 条目 + `build_and_save_lootdrop_details()` detail dict 增加 `translation_key` |
| `index_export.py` | search_index 所有实体 entry 增加 `translation_key` 字段；nav 页面标签（"物品表"等）不加 |
| `collector.py` | pipeline 末尾（enrichment 之后）调用 `export_language_maps()` |
| **NEW** `export_language_map.py` | 扫描 `Localization/Game/` 下所有含 Game.json 的目录，跳过 zh-Hans，输出 `data/json/lang/{code}.json`（key→value 映射）和 `data/json/lang/index.json` |

### 前端

| 文件 | 改动 |
|------|------|
| **NEW** `context/LanguageContext.tsx` | Provider + `useLanguage()` hook。URL ↔ localStorage 双向同步、lang map fetch/缓存、模块级 listeners 通知模式（参考 useDataVersion） |
| **NEW** `hooks/useEntityTranslation.ts` | 导出一个函数 `t(entity: {translation, translation_key?})`，在非中文时查 lang map 返回对应翻译 |
| `components/NavBar.tsx` | 添加 Ant Design `<Select>` 语言选择下拉框（右端，与主题切换并列） |
| `App.tsx` + `ssr.tsx` | Provider 链中插入 `<LanguageProvider>`（SSRDataContext.Provider 之后、BrowserRouter 之前，两端对齐） |
| `DetailPage.tsx` | ~28 处 `.translation` → `t(entity)` 替换 |
| `LootdropDetailPage.tsx` | ~38 处 `.translation` → `t(entity)` 替换 |
| `pages/ListPage.tsx` | 列表项翻译显示改用 `t()` |
| `pages/DungeonModuleDetailPage.tsx` | ~6 处模块名/标题翻译 |
| `pages/DungeonModuleGroupPage.tsx` | 模块名称翻译 |
| `pages/QuestItemGroupPage.tsx` | ~8 处实体名/map label |
| `pages/DungeonModulesPage.tsx` | 分组名称翻译（`group_display` 也需加 `translation_key`） |
| `pages/ExplorePage.tsx` | 探索列表翻译 |
| `pages/QuestNPCDetailPage.tsx` | 任务标题/npc 名称 |
| `components/DebugCoordTable.tsx` | 行内翻译 |
| `components/MapPanel.tsx` | tooltip/label 翻译 |
| `hooks/useSearchIndex.ts` | search_entry 类型增加 `translation_key`，搜索结果显示用 `t()` |
| `hooks/useDungeonModules.ts` | 模块数据增加 `translation_key` 类型 |
| `types/data.ts` | 实体接口增加 `translation_key?: string` |
| `vite.config.ts` | PWA runtime cache 加 `df5-lang` 策略（NetworkFirst，少量条目）；manifest lang 改为动态 |

## 边界情况

| 情况 | 行为 |
|------|------|
| `translation_key` 为空（HARDCODED_TRANSLATIONS 实体） | 保持中文回退 |
| 目标语言 Game.json 无此 key | 回退中文 |
| zh-Hans（默认） | 走现有逻辑，不加载 lang map，无额外请求 |
| 首次访问（无 URL 参数、无 localStorage） | 中文，无请求 |
| 切换语言 | 第一次 fetch lang map（`data/lang/{code}.json`），之后内存缓存 |
| 新增语言 | 只需在 `Localization/Game/{code}/Game.json` 放文件 + 重跑 pipeline |

## dungeon group_display 处理

`resolve_group_label()` 使用 UI slot key（`Text_UI_WB_DungeonSlot_GoblinCave_1stFloor` 等）生成分组名。
这些 key 也存在于各语言 Game.json 中。

- `entities.json`（模块坐标文件）中的 `translation` 字段
- `dungeon_modules.json` 中的 `group_display` 字段

方案：在 `dungeon_modules.json` 中增加 `group_display_key` 字段存储对应的 UI slot key，
前端查 lang map 翻译显示。或者为求简单，`group_display` 保持中文，暂不做多语言。
（可在实施时与中文翻译一起按需处理）

## 引用

- 参考 `useDataVersion` 的模块级 listeners 通知模式
- 参考 `quest_extractor/translator.py` 的 `get_available_languages()` 方法
- en Game.json: `12,718 keys` vs zh-Hans: `11,212 keys`
- `.translation` 引用 ~97 处分布在 11+ 个前端文件中
