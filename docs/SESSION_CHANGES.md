# 2026-07-14 会话修改记录

## 修复 apple-touch-icon 指向旧图标

- **原因**：`index.html` 中 `<link rel="apple-touch-icon">` 仍指向 `/icons/icon-192.png`（旧版无圆角），iOS 添加到主屏幕时显示方形图标
- **修复**：改为 `/icons/icon-192-v2.png`（圆角版）
- **变更文件**：`web/index.html:12`

## 站点描述全面更新

- **原因：** 原描述"游戏数据导航"不够明确，用户要求改为功能标签式描述
- **新描述：** `游戏地图·任务攻略·BOSS掉落·资源点位·寻找宝箱`
- **变更文件：**
  - `web/vite.config.ts` — manifest.description
  - `web/src/pages/HomePage.tsx` — title/meta description/heading 标签栏
  - `web/src/pages/ListPage.tsx` — title
  - `web/src/pages/DetailPage.tsx` — title/og:title
  - `web/src/pages/LootdropDetailPage.tsx` — title/og:title
  - `web/src/pages/DungeonModulesPage.tsx` — title
  - `web/src/pages/DungeonModuleGroupPage.tsx` — title
  - `web/src/pages/DungeonModuleDetailPage.tsx` — title
  - `web/src/pages/QuestItemsPage.tsx` — title
  - `web/src/pages/QuestItemGroupPage.tsx` — title
  - `web/src/pages/QuestNPCPage.tsx` — title
  - `web/src/pages/QuestNPCDetailPage.tsx` — title
  - `web/src/pages/ExplorePage.tsx` — title
- **bili.bi/map 对比：** 该站是多游戏地图导航门户（链接到采蘑菇/游民星空等第三方地图），我们聚焦 Dark and Darker 单一游戏，功能标签已覆盖其核心维度

## PWA 图标优化

- **原因：** PWA 图标上 "dnd" 文字过大，小尺寸看不清；新版图标缺少圆角
- **变更文件：**
  - `web/public/icons/icon-192-v2.png` — 新图标（文字缩小，增加蓝光效果，圆角矩形）
  - `web/public/icons/icon-512-v2.png` — 新图标（同上）
  - `web/public/favicon.ico` — 同步更新
  - `web/vite.config.ts` — manifest 图标引用改为 `-v2` 版本
- **缓存策略：** 文件名带 `v2` 后缀绕过浏览器/OS 图标缓存

# 2026-07-12 会话修改记录

## 性能优化

### lootdrops 模块优化（85s → 28s，省 67%）

| 优化 | commit | 效果 |
|------|--------|------|
| compact JSON | `4109ee1` | 省 15s |
| fuzzy candidate_ids 匹配 | `764acc7` | 省 1s |
| 移除 variant_suffixes 冗余 | `ec15e98` | 省 44s |
| 修复 variant 后缀计算 | `3be3910` | 恢复正确后缀 |
| 修复 _8001 变体显示 | `e2f3e6a` | 恢复神器变体切换 |

### 其他优化

- `drop_rate.py`: 添加 `_get_candidate_ids` 缓存
- `drop_rate.py`: 添加 fuzzy matching（FakeDeath/FromFakeDeath 后缀）

## Bug 修复

### 坐标标签翻译问题
- **commit**: `858cc54`
- **问题**: 坐标标签被 HARDCODED_TRANSLATIONS 翻译为中文（如 "ChestMedium" → "中宝箱"）
- **修复**: `build_coord_out` 中移除翻译，直接使用 `original_keyword`

### 双下划线变体分类
- **commit**: `f137cd5`
- **问题**: `GoldChest__UnderSea`（双下划线）被错误分类为 "other" 类型，添加 "组" 后缀
- **修复**: `_classify_label` 中将 `__` 视为 `_` 进行匹配

### 神器变体切换
- **commit**: `6a89a1b`, `e2f3e6a`
- **问题**: `_8001` 物品没有变体切换按钮
- **修复**: 包含 8001 在 variant_rarity 中，所有变体页面显示完整 8 个按钮

### 变体后缀计算
- **commit**: `3be3910`
- **问题**: 移除 variant_suffixes 后，后缀计算从 1001 开始，但部分物品从 3001 开始
- **修复**: 使用 `raw_name` 中的数字作为起始后缀

### lootdrop 列表页变体前缀
- **commit**: `98265d2`
- **问题**: 列表页显示 "[8变体]" 前缀
- **修复**: 移除变体数量显示

## UI/SEO 改进

### 站名改名
- **commit**: `066194b`
- **修改**: DarkFindV5游戏导航 → 越来越黑暗光速指南 DarkFlashNav

### 标题样式
- **commit**: `453e5c2`, `01fd9f3`
- **修改**: 中文名 26px，DarkFlashNav 16px，分两行显示

### SEO 关键词
- **commit**: `2da772a`, `52d9a2f`
- **关键词**: 越来越黑暗, 越来越黑暗玩家指南, 越来越黑暗光速指南, DarkFlashNav, Dark and Darker, 暗黑地牢, ...

## 2026-07-13 会话修改记录

### 多实体刷怪器坐标误扩展修复
- **commit**: `dfffe3d`
- **问题**: GoblinWarrior 的 DCSpawnerDataAsset 包含 LavaGolem_Nightmare 条目，`load_all_spawner_data` 剥离后缀后得到 2 个不同实体名（GoblinWarrior、LavaGolem），触发多实体展开。所有 GoblinWarrior 地图刷怪点都生成了 keyword="LavaGolem" 的坐标，导致 LavaGolem 页面多了 104 个虚假坐标
- **修复**: `search_engine.py:extract_spawners` 中，展开前判断 spawner 基名是否匹配任一实体基名。若匹配，只保留基名一致的实体；若不匹配（如 Random/Special 生成器），保留全部
- **效果**: LavaGolem 坐标从 105 降为 1（真实坐标）；GoblinMelee_Random、ChestSpecial 等不受影响

### lootdrop score 未乘实体生成概率修复
- **commit**: `7703899`
- **问题**: `lootdrop_builder.py:556` 中 per-coord score 使用 `coord.spawn_rate`（未命中 cache 时默认回退 100），未使用实体级 `entity.spawn_rate`。如迷你宝盒组 group_drop_info 中 spawn_rate=3.0，但每个 coord score = 100×25/100=25.0，模块合计 512.5%。实际应为 3.0×25/100=0.75 per coord
- **修复**: 新增 `_sr_lookup` 从 `_group_drop_info` 提取实体级 spawn_rate，score 公式改为 `entity_spawn_rate × 豪客赛 / 100`
- **效果**: 迷你宝盒组 per-coord score 从 25.0 → 0.75，模块合计 ≈15.375%（512.5%×3%）

### 文案修正
- **commit**: `7703899`, `a5afb3e`
- **问题**: 模块卡片显示"单点综合爆率"，应为"综合爆率"
- **修复**: `LootdropDetailPage.tsx:1359` 模块卡片 + `:844` 调试面板标签，去掉了"单点"前缀

## 待处理问题

### 黄金宝箱(特殊) 缺失
- **问题**: "黄金宝箱(特殊)" 在 group_drop_info 中但不在 monsters 列表中
- **当前状态**: 未修复
- **根因**: ChestSpecial_UnderSea 生成器的坐标没有正确关联

### 容器生成器子分类
- **问题**: 容器生成器（如 ChestSpecial_UnderSea）的子分类按钮（如 "黄金宝箱(特殊)"）没有对应的实体详情页
- **当前状态**: 未修复
- **计划**: 在 `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` 中记录

## 2026-07-14 会话修改记录（2）

### 重构：完全移除内联 `_modules`，统一走 `dungeon_modules.json`

**问题**：`_modules` 包含全部模块字段（rotate/offset/size/group/img_name/sl_base_name），与 `dungeon_modules.json` 完全重复。上次只去掉了翻译字段，剩余字段仍是冗余。

**方案**：
1. `build_coord_out` 通过 `map_to_module` 将 coords 的 `map` 字段解析为模块名，前端直接 `globalModules.get(c.map)` 查模块数据
2. 后端 `_build_inline_modules` 整个删除，实体 JSON 不再有 `_modules`
3. 前端 `DetailPage` / `LootdropDetailPage` 改直接使用 `useDungeonModules()` 的 `globalModules`
4. 类型 `InlineModuleData` 删除，实体接口删除 `_modules` 字段

**涉及文件**：
- `api/src/translator.py:build_coord_out` — 新增 `map_to_module` 参数，解析 map 字段
- `api/src/entity_export.py` — 删除 `_build_inline_modules` 及所有 `_modules` 注入，签名简化去掉 `modules_map`
- `api/src/lootdrop_builder.py` — 删除 `_modules` 注入及 `modules_map` 参数
- `api/src/collector.py` — 更新函数调用签名
- `web/src/types/data.ts` — 删除 `InlineModuleData`，实体接口删除 `_modules`
- `web/src/pages/DetailPage.tsx` — 模块 Map 直接来自 `globalModules.get(c.map)`
- `web/src/pages/LootdropDetailPage.tsx` — 同上

### 重构：移除内联 `_modules` 中的翻译数据，改由共享文件提供

**问题**：每个实体 JSON 的 `_modules` 内联了 `translation`/`group_display`，全站重复存储这些字段（1000+ 实体 × 5-15 模块），浪费带宽。

**改动**：
1. **后端**：`entity_export.py` / `lootdrop_builder.py` — 从内联 `_modules` 移除 `translation`、`group_display`
2. **类型**：`InlineModuleData` 移除这两个字段
3. **前端**：`DetailPage.tsx` / `LootdropDetailPage.tsx` — `translation`/`group_display` 改为从 `useDungeonModules()` 查询共享的 `dungeon_modules.json`
4. **预加载**：`index.html` 加 `<link rel="preload">`，`AppInner.tsx` 调用 `useDungeonModules()` 主动提前 fetch，确保模块数据优先于实体 JSON 加载

**涉及文件**：
- `api/src/entity_export.py:33-45` — 移除 `translation`/`group_display`
- `api/src/lootdrop_builder.py:698-710` — 同上
- `web/src/types/data.ts:75-87` — `InlineModuleData` 移除两个字段
- `web/src/pages/DetailPage.tsx:53-78` — `globalModules.get(mapName)` 获取翻译
- `web/src/pages/LootdropDetailPage.tsx:162-187` — 同上
- `web/index.html:12` — `<link rel="preload">`
- `web/src/AppInner.tsx:24,30` — 主动预取模块数据

### Bug 修复：内联 `_modules` 未提取 `group_display`

**问题**：`DetailPage.tsx` 和 `LootdropDetailPage.tsx` 从实体 JSON 内联 `_modules` 构建模块 Map 时，漏掉了 `group_display` 字段。导致 `mod?.group_display` 始终为 `undefined`，fallback 显示英文字段名（"Crypt"）。

**修复**：两文件在构造 `DungeonModule` 对象时添加 `group_display: data.group_display`。

**涉及文件**：
- `web/src/pages/DetailPage.tsx:63` — 新增 `group_display: data.group_display`
- `web/src/pages/LootdropDetailPage.tsx:171` — 新增 `group_display: modData.group_display`

**不受影响**：`QuestItemGroupPage` / `DungeonModulesPage` / `DungeonModuleGroupPage` / `DungeonModuleDetailPage` 使用 `useDungeonModules()`（直接从 `dungeon_modules.json` 加载 Map），`group_display` 正常。

---

## 2026-07-14 会话修改记录（先前）

### 修复：地图分组翻译不显示（data/ 交付遗漏）

**问题**：上一次管道运行时 `_deliver()` 可能被中断，`data/json/` 为空。前端 fetch 不到 `dungeon_modules.json`，fallback 显示英文 `group` 名（如 "Crypt"）。

**修复**：重新运行 `python main.py`，确保完整交付到 `data/json/`。

**涉及文件**：无代码改动，仅重新执行管道 + 前端构建

---

## 2026-07-14 会话修改记录

### PWA 图标改为 DND + 圆角
- **修改**: PWA 图标从纯蓝正方形改为圆角蓝底白字 "DND"
- **favicon**: 新增 `web/public/favicon.ico`（16/32/48 三尺寸），`index.html` 添加 `<link rel="icon">`

---

# 2026-07-14 会话修改记录

## 分组名动态化：移除全部硬编码 GROUP_LABELS

**目标**：用 Game.json 的 `Text_UI_WB_DungeonSlot_*_NthFloor` / `Text_WB_DungeonSlot_*_1stFloor` 翻译键动态推导分组显示名，替换后端和前端共 8 处硬编码。

### 映射规则

| 代码库 group | 基础键 | 公式 | 结果示例 |
|---|---|---|---|
| GoblinCave | `Slot_GoblinCave_1stFloor` | base + "1层" | 哥布林洞穴1层 |
| FireDeep | `Slot_GoblinCave_1stFloor` | base + "2层（`_2ndFloor`）" | 哥布林洞穴2层（赤焰深窟） |
| IceCavern | `Slot_IceCavern_1stFloor` | base + "1层" | 寒冰洞穴1层 |
| IceAbyss | `Slot_IceCavern_1stFloor` | base + "2层（`_2ndFloor`）" | 寒冰洞穴2层（寒冰深渊） |
| Ruins | `Slot_TheCrypts_1stFloor` | base + "1层" | 废墟1层 |
| Crypt | `Slot_TheCrypts_1stFloor` | base + "2层（`_2ndFloor`）" | 废墟2层（地穴） |
| Inferno | `Slot_TheCrypts_1stFloor` | base + "3层（`_3rdFloor`）" | 废墟3层（炼狱） |
| ShipGraveyard | `Text_WB_DungeonSlot_ShipGraveyard_1stFloor` | base + "1层" | 沉船墓场1层 |

### 后端改动

- `translator.py` — 新增 `resolve_group_label()` + `DUNGEON_SLOT_KEY_MAP` / `DUNGEON_SUBFLOOR_SLOT_KEY` / `DUNGEON_FLOOR_NUMBER`
- `config.py` — `DUNGEON_GROUP_GRADES` label 改为 1stFloor slot 基础值
- `collector.py` — `modules_map` 注入 `group_display`；传给 `generate_quest_items_groups` 和 `build_and_save_indexes`
- `entity_export.py` / `lootdrop_builder.py` — inline `_modules` 包含 `group_display`
- `index_export.py` — 移除全局 `GROUP_LABELS`，改用 `group_label_resolver` 回调

### 前端改动

7 个页面移除硬编码 `GROUP_LABELS`，改用 `mod.group_display`：
- `DetailPage.tsx`、`LootdropDetailPage.tsx`、`DungeonModuleDetailPage.tsx`
- `DungeonModulesPage.tsx`、`DungeonModuleGroupPage.tsx`
- `QuestItemGroupPage.tsx`、`ExplorePage.tsx`

`types/data.ts` — `DungeonModule` + `InlineModuleData` 添加 `group_display?: string`

### 验证

- 后端 pipeline 输出全部 8 个分组名正确
- `search_index.json` 中 tag 字段已更新为新格式
- 前端 tsc + SSG 构建全通过

## 清理死代码：DungeonGrade 分组代码表归档

**问题**：`dungeon_mode.py`（`parse_grade` 等 7 个函数）、`GRADE_DISPLAY_NAMES`、`_BASE_TO_GROUP`、`DUNGEON_GROUP_GRADES`、`DUNGEON_MODE_PVE~REVERSAL` 常量、`LOOTDROP_RATE_REFERENCE` 均无外部调用，属于 v4 参考项目遗留死代码。

**处理**：移入 `api/src/_archived/dungeon_grades.py`，从 `config.py` 中删除。

**保留**：`MODULE_GROUP_FLOOR_SUFFIXES`（仍被 `drop_rate.py`、`enrichment.py` 使用）、`DUNGEON_MODE_NAMES`（改为内联整数键 `{1: "PVE", 2: "普通", ...}`）。

## 文档更新

- `docs/FIX_ARTIFACT_VARIANT_SWITCH.md` - 神器变体切换修复文档
- `docs/PERF_LOOTDROPS_OPTIMIZATION.md` - lootdrops 性能优化记录
- `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` - 容器生成器实体页计划

# 2026-07-14 会话修改记录

## Bug 修复

### Coffin_06 爆率重复显示（"皇家棺材" + "皇家棺材组"）

**原因**：`_classify_label('Coffin_R', 'Coffin_06')` 返回 `"other"`，因为 `Coffin_R` 不以 `Coffin_06_` 开头，错误归类为"组"，导致同一个实体产生两种标签（`皇家棺材` + `皇家棺材组`）。

**修复**：在 `api/src/lootdrop_builder.py:_classify_label` 中添加兜底匹配——当实体名含尾部数字后缀（如 `Coffin_06`）时，剥离后缀为 `Coffin`，检查标签是否以 `Coffin_` 开头。`Coffin_R` → `"direct"`，正确合并到唯一入口。

**变更文件**：`api/src/lootdrop_builder.py`（`_classify_label` 函数）

### Coffin_06 变体系数导致 spawn_rate 虚高

**问题**：`Ruins_ForsakenCloister` 模块的坐标 `variant_count=3`（3 种选 1），但 group_drop_info 中 spawn_rate=100% 未除以 3，页面显示 `100% (3种选1)` 应为 `33.3333%`。

**修复**：
1. **前端** `DetailPage.tsx:720-724` — 变体模块显示区域新增 `adjRate()`，将 `info.spawn_rate` 除以 `forcedVc.variant_count`，保留 4 位小数。
2. **精度规范** — `drop_rate.py:_round_rate` 从 3 位改为 4 位小数；`enrichment.py` 中 `round(x, 2)` 替换为 `_round_rate(x)`。
3. **文档** — `docs/REFERENCE.md` 添加精度要求说明。

**变更文件**：
- `web/src/pages/DetailPage.tsx`（变体 spawn_rate 除以 variant_count）
- `api/src/drop_rate.py`（`_round_rate` 3 位→4 位）
- `api/src/enrichment.py`（`round(x,2)` → `_round_rate(x)`）
- `docs/REFERENCE.md`（Decimal 精度规范说明）
