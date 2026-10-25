# 会话修改记录

当前会话记录写在本文件；历史记录已移至 [`SESSION_CHANGES_ARCHIVE.md`](SESSION_CHANGES_ARCHIVE.md)，按日期保留原始内容。

## 2026-10-25

### chore: 归档【任务物品表】栏目（下线 /quest_items）并调整首页菜单次序

- **改动原因**：用户要求「zh-Hans/quest_items/ 栏目的代码做存档不再使用，该栏目从 home 页面移出」；随后给出新菜单次序「地牢商店、工匠、灯、任务NPC表、物品表、实体表、怪物表、掉落表、地图模块表」。
- **变更文件**：
  - 前端归档：`web/src/pages/QuestItemsPage.tsx` → `web/src/_archived/QuestItemsPage.tsx`（文件头写明恢复步骤）、新增 `web/src/_archived/QuestGroupMode.tsx`（记录被摘除的 `mode="quest_group"` 分支）。
  - 前端活跃：`web/src/AppInner.tsx`、`web/src/main.tsx`、`web/src/components/NavBar.tsx`、`web/src/pages/HomePage.tsx`、`web/src/pages/LootdropDetailPage.tsx`、`web/scripts/ssg.mjs`。
  - 后端归档：新增 `api/src/_archived/quest_items_groups_export.py`（`generate_quest_items_groups()` 原文）。
  - 后端活跃：`api/src/index_export.py`、`api/src/collector.py`、`api/src/locale_builder.py`、`api/tests/test_search_index_entries.py`。
  - 文档：`docs/AGENT_REFERENCE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **前端下线**：`AppInner` 删除 `QuestItemsPage` 引入与 `/:lang/quest_items`、`/:lang/quest_items/:group` 两条路由；`main.tsx` 删除 `hasRouteSsrData()` 的 `quest_items` 分支；`NavBar` 删除 `NAV_LABEL_KEYS.quest_items`（面包屑）与 `PAGE_TAG_KEYS.quest_items`（搜索标签）；`HomePage` 删除 `CARD_THEME.quest_items`、`ui.home.view_quest_items` 分支，并把 `quest_npc` 的「任务数量」副标题判断从「quest_items 或 quest_npc」收窄为只判 `quest_npc`。
  2. **详情页剥离 quest 模式**：`LootdropDetailPage` 移除 `mode` prop、`QuestGroupEntity`/`QuestGroupData` 类型、`normalizeQuestGroup()`、`quest_items_groups` 的 SSR/客户端加载分支、`taskGroupData` 状态，以及标题/SEO 的 `questGroup` 分支；掉落率筛选栏与 `CompositeRate` 不再需要 `!isQuestGroupPage` 条件包裹。掉落详情页行为与原 `mode='lootdrop'` 完全一致。
  3. **SSG 收敛**：`ssg.mjs` 从 `DETAIL_TEMPLATE_PAGES` 与 `SINGLE` 移除 `'quest_items'`；删除 `questGroups` 读取、分组路由生成、`ssrDataMap` 注入、`routeDataKey` 的 `/quest_items` 分支、`localizedQuestGroupTitle()` 与 `GROUP_FLOOR_SUFFIX`、`templateDescription` 的 `quest_items` 分支；sitemap 的 `/quest_` 优先级收窄为 `/quest_npc`。
  4. **后端归档**：`generate_quest_items_groups()`（原 `index_export.py` 第 29-234 行，213 行）移入 `api/src/_archived/quest_items_groups_export.py`；`index_export.py` 删除 `HARDCODED_TRANSLATIONS` / `resolve_group_label` / `resolve_translation_key` 三个随之失效的导入；`collector.py` 移除该函数导入与 `pipe.step("quest_items_groups")` 调用块（同时去掉未使用的 `modules = db.get_dungeon_modules()`）；`locale_builder.py` 的 `subdirs` 去掉 `quest_items_groups`。
  5. **菜单次序**：`index_export.build_and_save_indexes()` 的 `index_data` 与 `search_index.json` 的 `LIST_PAGES` 同步改为「地牢商店 → 工匠 → 灯 → 任务NPC表 → 物品表 → 实体表 → 怪物表 → 掉落表 → 地图模块表」，卡片从 10 项降为 9 项；`build_and_save_indexes()` 的 `quest_items_count` 形参一并移除。
  6. **明确保留（仍活跃）**：DB `quest_items` 表、`db.import_quest_items()` / `get_quest_items()`、`save_quest_data()` 的 `quest_items.json` 导出（交付时 `skip_deliver` 跳过，无消费者）、任务 NPC 页面与 `_iter_quest_objective_entries()`（其 `QUEST_OBJECTIVE_SKIP_TYPES` 常量保留在 `index_export.py`）、`ui.quest_items.*` / `ui.home.view_quest_items` / `ui.home.card_labels.quest_items` / `ui.nav.quest_items` / `ui.search.tag.quest` 文案键与 `seoTemplate` 的 `questItems` / `questGroup` 模板，均保留以便日后恢复。
- **结果**：`index.json` 9 张卡片（无 `quest_items`）；`search_index.json` 3351 条，`quest_items` 命中 0，`_nav` 9 条且与首页同序；管道不再产出 `data/json/quest_items_groups.json` 与 `quest_items_groups/` 目录；SSG 2976 → 页数较上轮 2984 减少 8 页/语言组，`dist/zh-Hans/quest_items/` 不存在，sitemap 与 `_redirects` 均无 `quest_items`。
- **验证**：后端 `python3 -m unittest discover -s tests` 218 项通过、`./api/lint.sh` 通过（70 文件）；前端 `npx tsc --noEmit` 通过、`npm run lint` 0 错误（20 条既有 warning）、`npm run format:check` 通过；`python3 main.py` 管道 40.55s 完成，`[VALIDATE] all module images OK`；`npm run build` 2976 页 / 15338 文件；8081 preview 首页卡片顺序实测为「地牢商店、工匠、灯、任务NPC表、物品表、实体表、怪物表、掉落表、地图模块表」，`/zh-Hans/items/` `/zh-Hans/quest_npc/` `/zh-Hans/dungeon_modules/` `/zh-Hans/lootdrops/BronzeScale/` 均 200。

### fix: 找回寒渊之流第 3 个哥布林走私者，移除 Ruins 稀有模块（Forgotten Plots）

- **改动原因**：用户反馈 The Ice Cavern 2F（The Ice Abyss / 寒渊之流）页面只有 2 个哥布林走私者，实际应有 3 个；同时反馈 7x7 时代的稀有模块 Forgotten Plots（被遗忘的庄园）仍出现在 Ruins 模块列表中。
- **变更文件**：`api/src/db/importers/spawner_coordinates.py`、`api/src/db/importers/modules.py`、`api/tests/test_spawner_coordinates.py`、`api/tests/test_module_entries.py`、`api/data/darkfindv5.db`（重建）、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **D / HR_D 去重补上 Z 轴**：原条件只有 `coord_distance(coord[:2], c[:2]) < 120`，只用 XY 判定重复。`IceAbyss_DeepFlow` 是多层模块，`IceGiantSpider` 位于 z=415、`GoblinSmuggler` 位于 z=-100，二者的 XY 平面距离仅 106.2，走私者被当成重叠行丢弃。现改为 `coord_distance(...) < 120 and abs(coord[2] - c[2]) < 120`，XY 阈值保持 120 不变。
  2. **稀有模块只在声明稀有槽的组内收录**：`ModulesImporter.import_all()` 原先只按 `module_group`（5x5 入口）过滤，Ruins 因新增 5x5 随机地牢而整组 50 个模块全收，其中 17 个 `bIsRare` 模块（`Ruins_Inner_01..05`、`Ruins_Outer_01..12`）根本不存在于该组的随机地牢中。游戏数据里 `Id_Dungeon_RandomRuins_*.json` 的 `NumMaxRares` 全部为空，只有 Crypt 的随机地牢声明了 `NumMaxRares = 1`。新增 `module_is_collectable()`：组必须在 5x5 入口集合内，且稀有模块只能来自 `module_spawn_rate.rare_groups()`（即 `NumMaxRares > 0` 的组）。
  3. **避免稀有模块经地图目录回流**：`_build_path_group_map()` 会为没有可用 `SubLevelAsset` 的模块补行（`extra_rows`）。被稀有规则拒绝的模块名记入 `rare_excluded`，补行循环跳过它们，否则 `Ruins_Passage_Outer_03` 等仍会以空翻译键的形式回到表里。
- **验证**：
  - `dungeon_modules` 中 Ruins 由 50 条降为 33 条（17 个稀有模块全部消失），Forgotten Plots 在 DB、`data/json/dungeon_modules.json`、`search_index.json` 中均已不存在；Crypt 60 条（含 5 个稀有模块）不受影响。
  - `spawners` 表新增 `IceAbyss_DeepFlow_D.json` 的 `GoblinSmuggler`（x=-632.90204, y=716.92523, z=-100.0, yaw=280.0），`coords/Id_NPC_GoblinSmuggler_IceCavern_N.json` 的 IceAbyss 点位由 2 个变 3 个（寒渊之流 / 冰霜之喉 / 冰川）。
  - 去重规则影响面：旧规则 40479 个生成点，新规则 40504 个，恢复 25 个跨楼层误删点（含 `IceAbyss_DeepFlow` 走私者、`Cave_Altar_Center` 的 `PedestalPortal`、`FourWayConnect` 的多层箱子和蜡烛等），其中 11,837 个同层重复仍按原阈值正常去重，无误伤。
  - 前端 SSG 重新构建：2984 页 / 15434 文件，`zh-Hans/dungeon_modules/Ruins/index.html` 只剩 34 个模块名（无 Passage / Forgotten），`IceAbyss_DeepFlow` 详情页已含哥布林走私者；8081 预览返回 200。
  - 后端 `python3 -m unittest discover -s tests` 218 项全通过；`./api/lint.sh` 通过（69 文件）；前端 `npm run lint` 0 错误（20 条既有 warning）、`npm run format:check` 通过。

## 2026-10-24

### fix: 物品表收录自身地面生成器掉落的物品（青铜天秤、坏眼镜等）

- **改动原因**：用户反馈「青铜天秤现在会作为实体生成，为什么没有收录」。排查发现数据链路完整（游戏解包有 `Id_Spawner_Lootdrop_BronzeScale`，DB `spawners` 有 2 行坐标，`coords/BronzeScale.json` 有 2 个点），但被 `export_items()` 的 `5c9d5b62` 规则拦掉：该规则认定「`monsters` 非空且不含 `Ground`」= 仅怪物/箱子产出，移到 `/lootdrops`。而 `BronzeScale` 恰好也被骷髅法师的 `QuestItem_VolcanicAsh` 掉落组引用，导致 `merged_loot["BronzeScale"] = ["SkeletonMage"]`，被误判成怪物掉落物，自身 2 个地面生成点完全不可见。
- **变更文件**：`api/src/db/repositories/lootdrops.py`、`api/src/db/__init__.py`、`api/src/collector.py`、`api/src/entity_export.py`、`api/tests/test_item_export_placement.py`（新增）、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **判定口径**：新增 `LootdropsRepository.get_self_placed_item_keywords()`，取 `spawner_entries.entity_name = ''`（无实体绑定 = 该组就是被放置物本身）**且**在 `spawners` 表里存在真实地图生成器（否则只是纯掉落表，从未在地面刷出）**且** `spawner_type != 'props'`（`Lifeleaf` / `PhantomFlower` / `Wardweed` 同时是 props 实体，归 `/props` 页面）。
  2. **前缀兼容**：部分条目的关键字带 `Spawn_` 前缀而 `spawners` 行没有（`Spawn_FrostWyvernEgg` → `FrostWyvernEgg`），用 `substr` 做第二条 JOIN 补齐，使 `FrostWyvernEgg` 也能收录。
  3. **放行条件**：`export_items()` 过滤改为 `if _mons and "Ground" not in _mons and name not in self_placed`，其余规则不变；`collector.py` 在导出前取一次集合并以第 13 个参数传入。
- **验证**：`data/json/items.json` 30 → 44 条，新增 `Bellows`（风箱）、`BrokenGlasses`（坏眼镜）、`BronzeScale`（青铜天秤）、`CaveTrollsPreciousRock`、`CeremonialDagger`、`ChroniclesoftheCursedCrown`、`FrostWyvernEgg`（冰霜飞龙蛋）、`GoldWaterpot`、`HumanRemains`、`LargeScroll`、`ManuscriptsoftheWarlord`、`RedApple`、`SkullKey`、`SturdyCloth`，无任何条目减少；`BronzeScale` 详情 2 个坐标（`DarkMagicLibrary_Center`、`Ruins_Keep`），`BrokenGlasses` 2 个（`Barracks`、`Ruins_Chapel`）；`search_index.json` 两者同时产出 `/items/…` 与 `/lootdrops/…` 两条记录。新增 7 条单测（`api/tests/test_item_export_placement.py`），后端全量 209 项 OK，`./api/lint.sh` 通过。

## 2026-10-23

### feat: 地图模块改以 5x5 布局为收录入口，并新增边缘/角落属性

- **改动原因**：用户要求「模块信息录入从 5x5 模块为入口」，且「7x7 的 ShipGraveyard 完全不收录到 db 文件」；同时要求模块增加边缘属性，边缘模块在地图名后显示 `(边缘)`，例如「强盗森林(边缘)」。随后明确「角落显示为角落，边缘显示为边缘，二者可进一步区分」，因此拆成 `is_edge` / `is_corner` 两个独立属性。
- **变更文件**：
  - 后端：`api/src/config.py`、`api/src/db/_helpers.py`、`api/src/db/schema.py`、`api/src/db/importers/modules.py`、`api/src/db/repositories/modules.py`、`api/src/module_builder.py`；
  - 前端：`web/src/types/data.ts`、`web/src/utils/mapImage.ts`、`web/src/pages/DungeonModuleGroupPage.tsx`、`web/src/pages/DungeonModuleDetailPage.tsx`、`web/src/i18n/uiLocale.ts`；
  - 测试：`api/tests/test_module_entries.py`（新增）；
  - 文档：`docs/REFERENCE_MAP_MODULES.md`。
- **关键逻辑/映射关系**：
  1. **收录入口改为随机地牢资产**：新增 `config.DUNGEON_DIR` 与 `db/importers/modules.py` 的 `ENTRY_LAYOUT_SIZE = 5`、`_layout_size()`、`load_entry_groups()`。导入时先扫描 `Data/Generated/V2/Dungeon/Dungeon/Id_Dungeon_Random*.json`，读取 `Properties.ModuleType` 与 `Properties.LevelAsset.AssetPathName`，从关卡名 `{区域}_{X}x{Y}_{...}` 解析网格尺寸，仅保留 5x5 的分组；`S2R` 变体地牢整体跳过。
  2. **ShipGraveyard 整组排除**：该组 9 个随机地牢全部指向 `ShipGraveyard_7x7_01_HR_P` / `ShipGraveyard_7x7_02_N_P`（7x7），当前导出中不存在任何 5x5 的 ShipGraveyard 关卡文件。导入结果从 268 条降为 238 条，导出 `dungeon_modules.json` 从 260 条降为 234 条，ShipGraveyard 残留为 0。此排除由数据驱动，游戏若出现 5x5 版本会自动恢复，无需改代码。
  3. **新增放置限制属性**：`db/_helpers.py:module_placement_flags()` 把 `bEdgeOnly` 映射为 `is_edge`、`bCornerOnly` 映射为 `is_corner`，二者互斥。DB `dungeon_modules` 新增同名列（`INTEGER NOT NULL DEFAULT 0`），`schema.py` 增加 `_migrate_dungeon_modules_table()` 做增量迁移。
  4. **前端展示**：`web/src/utils/mapImage.ts:modulePlacementSuffix()` 返回对应后缀，角落优先于边缘（防偶发脏数据）。列表页 `DungeonModuleGroupPage` 与详情页标题 `DungeonModuleDetailPage` 均在翻译名后追加。新增文案键 `ui.module.suffix.edge` / `ui.module.suffix.corner`，10 种语言全部补齐（zh-Hans 为 `(边缘)` / `(角落)`，zh-Hant 为 `(邊緣)` / `(角落)`）。
  5. **附带修正**：`ModuleType` 为空且无法通过前缀推断的模块现在直接跳过，不再写入空分组后被 `DELETE FROM dungeon_modules WHERE module_group = ''` 静默删除。
- **验证**：`python3 -m unittest tests.test_module_entries` 9/9 通过；完整管道 `python3 main.py`（41.34s）通过，`[VALIDATE] all module images OK`；导出 `dungeon_modules.json` 234 条，分组 `Crypt 60 / Ruins 43 / Inferno 27 / IceCavern 27 / GoblinCave 26 / FireDeep 25 / IceAbyss 22`，`is_edge` 20 条、`is_corner` 9 条，ShipGraveyard 0 条；`npx tsc --noEmit`、`npm run format:check`、`npm run lint`（0 错误，20 条既有 warning）均通过。

### fix: spawners 与 dungeon_modules 收录范围对齐，修复 CI 测试硬编码

- **改动原因**：上一个提交把 `dungeon_modules` 收敛到 5x5 入口后，CI 在「Test localized pages」步骤失败。排查确认两类问题：`web/tests/i18n.mjs` 有三处硬编码了 `ShipGraveyard_ShipRest` / `ShipGraveyard_PiratePrison` / `ShipGraveyard_BladehandRefuge`，这些模块已不在收录范围；同时发现 `spawners` 表未随 `dungeon_modules` 一起过滤，残留 8,643 行孤儿坐标（含全部 ShipGraveyard），导致 `Weapon_GoldenRoom` 这类只存在于废弃模块的道具仍被当成掉落源。
- **变更文件**：
  - 后端：`api/src/db/importers/spawners.py`；
  - 测试：`web/tests/i18n.mjs`；
  - 文档：`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **spawners 同步过滤**：新增 `SpawnersImporter._filter_to_collected_modules()`，在 `extract_spawners()` 返回后按 `dungeon_modules.module_name` 白名单过滤 `map_base`。导入顺序本就保证 `import_dungeon_modules` 先于 `extract_and_store_spawners`，因此白名单可用。结果：spawners 从 55,147 降为 46,504，孤儿坐标从 8,643 降为 0，ShipGraveyard 坐标文件从 30 个降为 0。
  2. **密集地图测试改为动态选点**：`denseModuleHoverTarget()` 不再写死 `ShipGraveyard_PiratePrison`，改为遍历全部已收录模块、选取坐标点最多且仍存在 coords 文件者（当前命中 `Crypt_LightlessTomb_01`，578 点），并从模块记录读取 `group` 构造路由。
  3. **模块详情测试改用稳定模块**：`ModuleDetail` 三条测试的路径从 `ShipGraveyard/ShipGraveyard_BladehandRefuge` 改为 `Crypt/Crypt_BlindfallPit`（盲坑，20 实体 / 179 位置点），仍是稀有模块，SEO 描述格式一致。
  4. **黄金房武器断言反转**：`Weapon_GoldenRoom` 只出现在 `ShipGraveyard_ShipRest`，随该模块一并移除；`Weapon_MysticalTreasureRoom` 位于仍在收录的 `Cave_Rooms`，保留。因此 ja / zh-Hant 两条测试中「黄金房武器 (1)」的 `expected` 由 `true` 改为 `false`，并加注释说明原因。
- **验证**：`python3 -m unittest discover -s tests` 182 个全通过；`api/lint.sh`（ruff + black）通过；完整管道 38.50s 通过，日志含 `filtered 8643 spawners outside collected modules`、`[VALIDATE] all module images OK`；SSG 构建 2979 页 / 13763 HTML；本地 `vite preview` 在 8081 端口运行 `npm run test:i18n` 得 **Pass 29 / Fail 0**。
### feat: 稀有模块生成概率改为按 5x5 收录范围实时计算

- **改动原因**：用户要求 `zh-Hans/items/GrimveilCloak` 显示的模块生成概率 `0.84%` 按 5x5 模块重新计算。排查发现该值原先由前端 `web/src/utils/moduleSpawnRate.ts` 硬编码为常量，稀有池固定 5 个 Crypt 模块，与「收录入口改为 5x5」之后的数据脱钩；同时 17 个 Ruins 的 `bIsRare` 模块会被错误套用 Crypt 的布局统计。
- **变更文件**：
  - 后端：`api/src/module_spawn_rate.py`（新增）、`api/src/module_builder.py`、`api/src/db/_helpers.py`、`api/src/db/schema.py`、`api/src/db/importers/modules.py`、`api/src/db/repositories/modules.py`；
  - 前端：`web/src/utils/moduleSpawnRate.ts`、`web/src/types/data.ts`、`web/src/pages/DetailPage.tsx`、`web/src/pages/LootdropDetailPage.tsx`；
  - 测试：`api/tests/test_module_spawn_rate.py`（新增 8 个用例）、`api/tests/test_module_entries.py`（`_write_dungeon` 支持 `extra`）；
  - 文档：`docs/BLINDFALL_PIT_PROBABILITY_RECORD.md`。
- **关键逻辑/映射关系**：
  1. **稀有槽存在性按组判定**：新增 `rare_groups()`，只认 `DCDungeonDataAsset.Properties.NumMaxRares > 0` 的地图组。当前只有 Crypt 的 9 个随机地牢声明了 `NumMaxRares = 1`，FireDeep / GoblinCave / IceAbyss / IceCavern / Inferno / Ruins 均无该字段，因此只有 Crypt 会产出概率。
  2. **稀有池实时统计**：`rare_pool_sizes()` 按 `module_group` 统计 `is_rare` 模块数。DB 与导出新增 `is_rare` 列（映射资产 `bIsRare`）与 `spawn_rate` 列，当前 Crypt = 5。
  3. **布局因子按组隔离**：`layout_stats()` 从 `DungeonLayout/*.json` 的 `SlotType == Rare` / `Fixed` 统计，文件名第二段作为地图组。资产缺失时退回 `BASELINE_LAYOUT_FACTORS = {"Crypt": (40, 2)}`（实测值），`source` 字段标记 `baseline` / `assets`，游戏恢复布局资产后自动切换。
  4. **覆盖修正实时读取**：`SlotType == Fixed` 指向的模块按 `DungeonModule.Size` 累加占地，`CenterTower` 为 2×2，`(25 - 4) / 25` 系数由资产算出而非写死。
  5. **前端只读不算**：`getRareModuleSpawnRate(module)` 直接返回 `module.spawn_rate`，`applyModuleSpawnRate(rate, module)` 同；两个调用页（物品详情、掉落详情）改为传模块对象而非模块名。
  6. **结果缓存进 DB**：首版实现由前端读 `spawn_rate` 字段，但 CI 没有游戏导出目录，`db_freshness` 跳过导入，导致线上所有模块概率为 0。改为 `ModulesImporter._store_spawn_rates()` 在导入时把概率写回 `dungeon_modules.spawn_rate`，`module_builder` 直接读该列；导入时若资产缺失算不出概率，保留 DB 既有值并打印提示，不清零。
- **验证**：`python3 -m unittest discover -s tests` **190 个全通过**（新增 8 个）；CI 等价环境（把所有 `config` 游戏路径常量指向不存在目录）同样 190 个通过；`api/lint.sh`（ruff + black）通过；完整管道通过，`[VALIDATE] all module images OK`；导出 `dungeon_modules.json` 中恰好 5 个模块带 `spawn_rate = 0.84`（全部 Crypt），Ruins 的 17 个稀有模块为 0；SSG 构建 2979 页；Playwright 实测 `zh-Hans/items/GrimveilCloak/` 显示「盲坑 0.84%」「综合爆率 0.5208%」且无页面错误，`Ruins_Passage_Outer_04` 页面不出现任何百分比；`npm run check` 通过（0 错误，20 条既有 warning）。
### feat: deploy.sh 适配无游戏文件的普通用户，新增 README

- **改动原因**：用户要求「deploy.sh 修改成适合普通用户（无游戏文件）使用的部署脚本，其中 git 提交明显是不合理的，然后增加 README.md 对本项目简单介绍，可以脱离游戏部署」。原 `deploy.sh` 有三个问题：①末尾 `git add -A && git commit -m "chore: deploy $(date)"` 会自动提交工作区全部改动，包括未完成的 WIP 与本地配置，属于破坏性操作；②默认端口 8080 与本机 nginx 冲突；③没有任何环境校验，缺少 DB 或版本过低时只会在管道深处报错。项目此前也没有 README，新用户无法得知「不需要游戏文件」这一关键前提。
- **变更文件**：`deploy.sh`（重写）、`README.md`（新增）、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **移除全部 git 操作**：脚本只做「环境检查 → 导出数据 → 安装依赖 → 构建 → 预览」，不再 `git add/commit`。提交交由开发者按 `docs/DEVELOPMENT_WORKFLOW.md` 手动执行。
  2. **环境预检前置**：新增 Python ≥ 3.10、Node ≥ 20、npm 存在性检查，以及 `api/data/darkfindv5.db` 存在性检查。任一不满足立即 `fail` 并给出可执行的修复提示，不进入管道。
  3. **端口与进程管理**：默认端口改为 8081（8080 被本机 nginx 占用），新增 `--port` 覆盖；启动前用 `lsof` 检测并停止占用该端口的进程，配合 `--strictPort` 避免 vite 静默跳端口。
  4. **新增 `--build-only`**：只构建不启动预览，用于 CI 或上传静态托管。脚本会校验 `web/dist/index.html` 存在后才报告成功。
  5. **依赖安装幂等**：`web/node_modules` 已存在时跳过 `npm ci`，避免重复安装耗时；提示用户删除目录可强制重装。
  6. **README 说明脱离游戏的原理**：核心是 `api/src/db_freshness.py` 的三态决策——数据源完整 → `REBUILD_REQUIRED`；数据源缺失 → `DB_ONLY`（直接用仓库内 47 MB 的 `api/data/darkfindv5.db` 导出 JSON）；两者都缺 → `FAIL_FAST`。普通用户环境没有 `Output/Exports/`，自动走 `DB_ONLY`，几十秒完成。
  7. **README 数据核对**：文中数字均取自当前导出实测——816 物品、732 怪物、570 实体、234 地图模块、524 掉落条目、2980 条路由、13774 个 HTML、10 种语言。
  8. **README 后续调整**：按用户要求删除「快速开始」之前的部分（项目简介、在线站点、特性列表），文档现在直接从 `# 快速开始` 开始；随后再次按用户要求删除「免责声明」章节，理由是其中的版权归属表述对本项目并不成立且容易误导。保留环境要求、一键构建、常用参数、脱游部署原理、项目结构、页面、技术栈、开发、文档索引与许可。
- **验证**：`bash -n deploy.sh` 语法通过；`./deploy.sh --help` 输出完整说明；实际运行 `./deploy.sh` 全流程通过——`[DB] state=DB_ONLY` 正确识别无游戏源、管道导出成功、SSG 2980 页、`[5/5]` 返回 HTTP 200；模拟普通用户（将所有 `config` 游戏路径指向不存在目录）调用 `inspect_database()` 得到 `state=DB_ONLY / import_required=False`，确认无需游戏文件即可构建；README 内 7 个文档链接与 3 条命令均校验存在。
### chore: 补丁部署（同步游戏数据、全量重建 DB）

- **改动原因**：用户要求执行补丁流程（更新部署），按 `docs/BUILD_AND_DEPLOY.md` 的「更新部署」章节执行：同步最新游戏解包 → 全量重建 SQLite → 提交含新 DB 的 `main`。**按用户明确要求不推送远程**。
- **变更文件**：`api/data/darkfindv5.db`（全量重建）、`data/json/**`（管道导出，未跟踪）。
- **关键逻辑/映射关系**：
  1. 同步：`~/sync_fmod.sh`（rsync 362 MB 增量，总数据 1.79 GB）。同步后发现游戏端 `Data/Generated/V2/Dungeon/` 仍只有 Dungeon / DungeonCard / DungeonGrade / DungeonModule / DungeonType 五个子目录，`DungeonLayout` 与 `Random*` 的 `Layouts` 字段依旧缺失，`0.84%` 概率继续使用 `BASELINE_LAYOUT_FACTORS` 兜底。
  2. 重建：`rm -f api/data/darkfindv5.db && python3 main.py --rebuild-db`，36.47s，`[VALIDATE] all module images OK`。新 digest `656f063e…`（旧 `42fcb3e1…`），说明有实质数据更新。
  3. 数据变化：modules 238（不变）、spawners 46,504 → 46,725（+221）、items 816（不变）、monsters 732 → 742（+10）、spawn_rate>0 仍为 5（Crypt 稀有池）、ShipGraveyard 仍为 0（5x5 收录规则持续生效）。
  4. 首次同步时发现 `~/fmod/Output/Exports` 曾被清空（FModel 日志显示用户在 Windows 端重新导出），第二次同步恢复完整数据。
- **验证**：`pragma integrity_check` = ok；`data/json/**` 已重新交付；`dungeon_shops/Crypts.json` 仍为 11 槽 72 物品（装备槽问题与本次数据无关，仍未修复）。
### feat: 地牢商店新增装备槽（Equip 共享库存）

- **改动原因**：用户反馈 `zh-Hans/dungeon_shops/Crypts/` 应该出现装备售卖。排查确认游戏资产里每个地区的哥布林走私者 Schedule 都引用了 3 个 `Equip` StockBuy 文件（`GoblinSmuggler_Equip_{N,HR}_01/02/03`，每文件 631 条，三份内容完全相同），但项目导入器只按文件名归属 region，`Equip` 没有对应 Schedule 定义、也没有 `REGION_LABEL_KEY` 条目，导致 1893×2 条装备库存躺在 DB 里却从未导出。
- **变更文件**：`api/src/db/importers/merchants.py`、`api/src/merchant_builder.py`、`web/src/pages/DungeonShopDetailPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **按 Schedule 引用归属库存**：新增 `InGameMerchantImporter._schedule_stock_refs()`，读取每个 Schedule 的 `StockBuy` 引用列表，建立 StockBuy 资产 → 引用它的 variant 列表映射。`Equip_*` 三个文件被 Crypts/Goblin/IceCavern 的全部 6 个 Schedule 引用，其库存行按归属复制到每个地区 variant（`GoblinSmuggler_Equip_N` 的 1893 行 → Crypts_N/Goblin_N/IceCavern_N 各得一份）。
  2. **槽位重映射**：Equip 文件名后缀 `01/02/03` 是文件序号而非商店槽位，且三份内容相同（逐字节比对为 True）；文件名解析出的 slot=1 会与各地区治疗药水槽冲突，统一映射到 **slot 90**。普通 StockBuy 仍按文件名槽位归属。
  3. **装备槽展示语义**：631 条 = 207 款装备 × Rare(300)/Epic(190)/Legend(10) 三档价格权重 + 10 条 `_5001` 特殊品（rate 105，Stock 1）。这是**明码标价的在售列表**而非概率池，`DungeonShopDetailPage` 对 slot 90 关闭 `showChance`（新增 `EQUIPMENT_SLOT = 90` 常量），卡片只显示名称/稀有度/价格。
  4. **翻译 fallback 修正**：装备类商品（如 `GrimveilCloak_5001`）只有品质后缀形态的资产，不在 lootdrop 索引里；`merchant_builder` 的翻译 fallback 原来只试 `Text_DesignData_Item_Item_{page}`，现在追加试 `Text_DesignData_Item_Item_{row.item_name}`（带 `_5001` 的完整名），631 条装备翻译缺失从 611 降到 0。
  5. **新增 i18n**：`ui.shops.slot.equipment`（装备 / Equipment / Ausrüstung / 装備 …10 语言），前端 `SLOT_LABEL_KEYS` 增加 `90` 映射。
- **验证**：API 192 测试全通过；`api/lint.sh` 通过；`npm run check`（0 错误，20 条既有 warning）；重建管道 26.53s，`[VALIDATE] all module images OK`；导出后 Crypts/Goblin/IceCavern 的 N/HR 六个难度全部出现 `slot 90: 631 items`；Playwright 实测 `zh-Hans/dungeon_shops/Crypts/` 渲染「装备」标题 + 631 张卡片（冒险者长靴/披风/外衣等），装备卡不显示百分比，页面无错误。
## 2026-10-22

### fix: 【工匠】页保护药水显示护盾值与持续时间

- **改动原因**：用户反馈「https://dnd9.icetar.com/zh-Hans/crafts/ 中的 保护药水，没有显示关键属性抵挡多少伤害持续多长时间」。工匠页此前只渲染物品的 `primary` 属性（护甲/伤害等），而药水类物品的数值不在 `ItemProperty` 资产里，而在其饮用能力指向的状态效果资产中，因此保护药水卡片只有「移动速度 -10」这一项。
- **变更文件**：
  - 后端：`api/src/consumable_effects.py`、`api/src/db/importers/effects.py`、`api/src/craft_builder.py`、`api/src/collector.py`；
  - 测试：`api/tests/test_consumable_effects_fixed.py`（新增）、`api/tests/test_craft_builder_effects.py`（新增）、`api/tests/test_merchant_builder.py`；
  - 前端：`web/src/pages/CraftsPage.tsx`、`web/src/types/data.ts`、`web/src/i18n/uiLocale.ts`。
- **关键逻辑/映射关系**：
  1. **数据链路**：保护药水的数值来自 `Id_ActorStatusEffect_ProtectionPotionConsumeShield_XXXX`（`MaxPhysicalShield` 20/25/30/35、`duration` 24000ms），魔法保护药水同理走 `MaxMagicalShield`。这些资产只能由导入阶段读取，因此扩展 `consumable_effects.py`：
     - 新增 `load_fixed_effects()`：保留所有带追踪字段或 `duration` 的状态效果，`duration` 由毫秒除以 1000 转为「持续时间」秒数（24000 → 24 秒，与游戏内 tooltip 一致）；
     - `resolve_item_effects()` 改为**从物品资产的 `Abilities` 列表**解析能力资产名（`Id_Item_ProtectionPotion_5001` 的能力是 `Id_ItemAbility_ProtectionPotionConsume_5001`，不能由物品名推导），先试加权随机（幸运药水），再回退到固定 `Effects` 列表（保护药水）。
  2. **导入范围**：`ItemEffectsImporter` 原本只处理地牢商店在售商品；保护药水只出现在工匠配方中，因此额外并入 `craft_recipes` 的 `output_raw_name`。
  3. **导入顺序**：`import_item_effects` 原先跑在 `import_craft_recipes` 之前，导致读取配方表时它还是空的。已在 `collector.py` 中把 `import_craft_recipes` 前移，并加注释说明依赖关系。
  4. **导出**：`craft_builder.py` 新增 `item_effects` 参数，为每个配方附加 `effect: { values: [...], random: bool }`；字段显示名复用游戏自身的 `SetByCaller` 翻译键（`Text_Code_DCDataBlueprintLibrary_Data_SetByCaller_MaxPhysicalShield` → 最大物理护盾），10 种语言均可本地化；`Duration` 带 `seconds: true` 标记。
  5. **前端**：`CraftsPage.tsx` 新增 `CraftEffectLine` 组件与 `formatEffectValue`，渲染为「效果：最大物理护盾 30 ｜ 持续时间 24 秒」；随机效果（幸运药水）追加「随机效果」标记。新增 `ui.crafts.effect` / `ui.crafts.effect_random` 四条语言文案。
- **CI 失败修复**：首次推送后 GitHub Actions 在「Run API unit tests」步骤失败（`test_consumable_effects.ResolveItemEffectsTest.test_item_name_maps_through_its_ability_asset` → `KeyError: 'LuckPotion_5001'`）。原因是 `resolve_item_effects()` 改为从物品资产的 `Abilities` 列表读取能力名后，旧测试的 fixture 只建了 `ItemAbility` 目录、未建 `Item` 目录，本地因有游戏解包目录而通过，CI 无解包目录故返回空。修复：为该测试补 `_make_item_dir()` fixture 并在 `_resolve` 与 `MissingSourceTest` 中显式传入 `item_dir`，使测试不再依赖真实解包目录。
- **CI 等价环境验证**：用脚本把 `config` 的所有解包路径常量改写到不存在的临时路径下（`GAME_ROOT exists: False`）后重跑整套测试，173 个全部通过 —— 与 CI 环境等价。
- **验证**：
  - 后端：`python3 -m unittest discover -s tests` 173 个测试全部通过；`./lint.sh`（ruff + black）通过；
  - 管道：`python main.py --rebuild-db` 全量重建成功，`import_item_effects` 由 9 项增至 81 项；
  - 产物：`data/json/crafts.json` 中 8 条保护药水配方全部带 `effect`（物理 20/25/30/35、魔法 20/25/30/35，持续时间均 24 秒），`translation` 为「最大物理护盾」/「最大魔法护盾」/「持续时间」；
  - 前端：`npx tsc --noEmit` 通过，`npm run lint` 0 error，`npm run format:check` 通过；8081 preview HTTP 200，Playwright 实测炼金术士页 8 张药水卡片均显示「效果 / 最大物理护盾 20~35 / 持续时间 24 秒」，`test:i18n` Pass 29 / Fail 0。

## 2026-10-21

### feat: 地图分组下拉按标签排序（同地牢各层相邻）

- **改动原因**：用户要求「地图分组显示的列表应该用首字排序，比如废墟1、2、3层排在一起」。此前顺序沿用地图网格的「综合爆率/坐标数」排序，同一地牢的楼层会被拆散。
- **变更文件**：`web/src/components/GroupFilter.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **排序键**：直接按**本地化后的标签**排序，而不是按分组 id（id 如 `Crypt`/`FireDeep` 与显示名不同序）。标签形如「废墟2层（地穴）」，因此同地牢的楼层自然相邻。
  2. **数字感知比较**：`compareGroupLabels` 用 `/\d+|\D+/g` 切分后逐段比较，数字段转 `Number` 比较，避免字典序把 10 层排在 2 层前面；非数字段按码点比较。
  3. **不用 `Intl.Collator`**：选项在 SSG 阶段由 Node 预渲染，若 ICU 数据与浏览器不同会导致 hydration 时 `<option>` 顺序重排；手写比较器在两端结果一致。
  4. **不入库**：排序只在组件内对传入的 `groups` 做一次副本排序，页面自身的爆率/坐标排序逻辑不受影响；分组数据本身顺序不变。
  5. **补充文案**：`UI_EXTRA_LOCALE` 的 `ja` / `zh-Hant` 原先缺少 `ui.filter.group`、`ui.filter.all_groups`（会直接显示 key），本次补齐；同时补上两国语言的 `ui.search.tag.craft_group`（此前的搜索前缀在 ja/zh-Hant 也回落成 key）。
- **验证**：`npm run format` + `npm run check`（0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页；8081 preview HTTP 200；`test:i18n` Pass 29 / Fail 0；Playwright 实测「火把」详情页各语言选项顺序：
  - zh-Hans：哥布林洞穴1层 / 哥布林洞穴2层 / 寒冰洞穴1层 / 寒冰洞穴2层 / **废墟1层 / 废墟2层 / 废墟3层** / 沉船墓场1层；
  - en / ja / zh-Hant / de 均按各自译文正确分组（The Ruins1F/2F/3F、廃墟1階/2階/3階、廢墟1層/2層/3層、Die Ruinen1E/2E/3E），数字按数值升序；无 pageerror。

### feat: 实体/掉落详情页新增「地图分组显示」筛选（非调试模式）

- **改动原因**：用户要求「参考『爆率显示』组件，在非调试模式提供『地图分组显示』：默认选择全部分组，选中其他分组时只显示对应分组」。
- **变更文件**：`web/src/components/GroupFilter.tsx`（新增）、`web/src/pages/DetailPage.tsx`、`web/src/pages/LootdropDetailPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **组件**：`GroupFilter` 渲染「地图分组显示：<select>」，第一项是「全部分组」（value `''`），其余选项来自当前页面的 `sortedGroups`，标签复用 `formatGroupLabel`（如「废墟2层（地穴）」）；`aria-label` 与可见标签一致；分组数 < 2 时不渲染，避免单地图页面出现无意义控件。
  2. **位置**：放在 `<Disclaimer />` 之后、地图网格之前，**不在 `debug` 条件内**——普通用户即可按地牢筛选；调试面板里的「爆率显示 / 隐藏0爆率坐标」保持原位不变。
  3. **过滤**：`DetailPage` 由 `sections` 派生 `visibleSections`，`LootdropDetailPage` 由 `sortedGroups` 派生 `displayGroups`，映射与统计用的循环、地图识别模板、底部「N 个坐标 / M 张地图」统计全部改用派生集合，保证切组后计数同步。
  4. **选择有效性**：选中的分组在新数据里不存在时自动按「全部分组」处理（`DetailPage` 用 `activeGroupFilter` 计算值，`LootdropDetailPage` 在 `displayGroups` 的 `useMemo` 里过滤）。最初用 `useEffect` 重置，但 `DetailPage` 的 `useEffect` 位于提前 `return` 之后，触发 `react-hooks/rules-of-hooks`，改为纯计算派生，无副作用。
  5. **文案**：`UI_EXTRA_LOCALE` 增补中英 `ui.filter.group`（地图分组显示 / Map group）与 `ui.filter.all_groups`（全部分组 / All groups）。
- **验证**：`npm run format` + `npm run check`（0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页；8081 preview HTTP 200；`test:i18n` Pass 29 / Fail 0；Playwright 实测：
  - `/zh-Hans/items/Torch/` 出现 9 个选项（全部分组 + 8 个地牢分组），默认「全部分组」；选中「废墟2层（地穴）」后页面只剩该分组（正文 8260 → 1922 字符，地图卡片只剩 4 张）；
  - `/zh-Hans/lootdrops/Torch/` 同样生效（5208 → 1633 字符）；
  - 单地图条目（如 `/zh-Hans/items/Ale/`、`/zh-Hans/monsters/Goblin/`）不渲染该控件；无 pageerror。

### feat: 爆率「全部」模式默认不再显示 PvE 爆率

- **改动原因**：用户要求「爆率显示：全部，这个模式不再显示 pve 爆率，即所有页面默认都不显示 pve 爆率」。
- **变更文件**：`web/src/utils/dropRate.ts`、`web/src/pages/DetailPage.tsx`、`web/src/pages/LootdropDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **单一开关**：`dropRate.ts` 新增 `HIDDEN_DROP_RATE_MODES = new Set(['PVE'])`；`filterDropRates` 在**未指定 modeFilter**（即「全部」）时跳过该集合中的模式，显式选择 PvE 时仍照常返回 PvE 数据。
  2. **可见性判断统一**：新增 `hasVisibleDropRate(drop_rates, modeFilter)`，语义为「按当前筛选，是否存在可展示的 >0 爆率」。两个详情页原来的本地 `hasAnyRate` 全部替换（`DetailPage` 内嵌版直接删除），共 11 处调用点，覆盖坐标过滤、分组是否有可见项、地图识别模板、隐藏 0 爆率开关等分支。
  3. **拼接字符串处**：`DetailPage` 的变体分组 `subLabel` 用 `Object.entries(drop_rates)` 手工拼 `[模式:爆率%]`，改用 `HIDDEN_DROP_RATE_MODES` 过滤；`LootdropDetailPage` 里图例旁的爆率拼接改用 `filterDropRates(...)` 的结果渲染。
  4. **数据层不动**：`drop_rates.PVE` 仍完整保留在导出的 JSON 中，仅在展示层隐藏；综合爆率、评分等计算（继续使用「豪客赛」）不受影响。
- **验证**：`npm run format` + `npm run check`（0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页；8081 preview HTTP 200；`test:i18n` Pass 29 / Fail 0；Playwright 实测：
  - `/zh-Hans/items/Ale/` 显示 `[普通:4%][豪客赛:15%][逆袭赛:15%]`，无 PvE；
  - `/zh-Hans/lootdrops/HealingPotion/` 页面文本中 PvE 只出现在筛选下拉的 `<option>`，爆率区无 PvE；
  - 手动把筛选切到「PvE」仍正常显示 `[PvE:4%]`，切回「全部」恢复三种 PvP 模式；
  - `/en/items/Ale/` 显示 `[Normal:4%][Squire Royale:15%]`，无 PvE；无 pageerror；
  - 数据统计：items + lootdrops 共 6737 条 group_drop_info，其中「仅 PvE 有爆率」的条目为 0，因此本次隐藏不会让任何条目意外消失。

### fix: 搜索命中当前页时不再"点了没反应"，重新触发滚动定位

- **改动原因**：用户反馈「当搜索的工匠合成物品刚好在本页时，没有触发滚动跳转到对应物品位置」。原因是 `NavBar.handleSelect` 只做 `navigate(target)`；目标 URL 与当前 `pathname + search` 完全相同时 React Router 不产生变化，页面的 `useSearchParams` 不会更新，`?item=`/`?quest=` 的滚动 effect 也就不会重跑。
- **变更文件**：`web/src/hooks/useSearchTargetSignal.ts`（新增）、`web/src/components/NavBar.tsx`、`web/src/pages/CraftsPage.tsx`、`web/src/pages/DungeonShopDetailPage.tsx`、`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **同页判定**：`handleSelect` 先算出本地化目标 URL 并与 `location.pathname + location.search` 比较；相同则不再 `navigate`，改为 `window.dispatchEvent(new CustomEvent(SEARCH_TARGET_EVENT))`。
  2. **信号 hook**：新增 `useSearchTargetSignal()`，监听 `df5:search-target` 并返回自增计数；消费页面把它加进定位 effect 的依赖数组，事件到达时 effect 重新执行 `scrollIntoView({behavior:'smooth', block:'center'})`。
  3. **接入页面**：`CraftsPage`（`[data-craft-item]`）、`DungeonShopDetailPage`（`[data-shop-item]`）、`QuestNPCDetailPage`（`[data-quest-num]`）三处，覆盖搜索结果里所有带定位参数的页面。
  4. 非同页时行为不变，仍走 `navigate`（浏览器地址更新 + 页面 effect 正常触发）。
- **验证**：`npm run format` + `npm run check`（0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页；8081 preview HTTP 200；`test:i18n` Pass 29 / Fail 0；Playwright 用「URL 已等于命中目标」的真实同页场景实测——
  - 工匠：`/zh-Hans/crafts/alchemist/?item=ClarityPotion` 先把页面滚回顶部，再搜「清晰药水」点「工匠合成-炼金术师」→ 页面滚到 y=50，目标卡片 `top=310`、2px accent 高亮；
  - 商店：`/zh-Hans/dungeon_shops/Crypts/?item=GoldenKey` 滚回顶部后搜「黄金钥匙」→ 滚到 y=1549，卡片 `top=321` 并高亮；
  - 任务：`/zh-Hans/quest_npc/Alchemist/?quest=4` 滚回顶部后搜「乱成一团」→ 滚动到 y=507；
  - 全程无 pageerror。

### feat: 搜索条目成品与任务统一加语义前缀

- **改动原因**：用户反馈两处——「生命之叶成品搜索时只显示『炼金术师』，应完整显示『工匠合成-炼金术师』」；「任务也应该显示前缀，比如金锭显示为『珠宝匠』，应显示为『任务-珠宝匠』」。
- **变更文件**：`api/src/index_export.py`、`api/tests/test_search_index_entries.py`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **工匠成品**：`_iter_craft_search_entries` 的成品条目补 `tag_prefix_key = "ui.search.tag.craft_group"`，显示为「工匠合成-炼金术师」，与其原料条目前缀一致（原料条目是「工匠合成-治疗药水」，成品条目是「工匠合成-炼金术师」，一个答"谁做的"、一个答"做什么用"）。
  2. **任务目标**：`_iter_quest_objective_entries` 补 `tag_prefix_key = "ui.search.tag.quest"`（既有键，10 语言均已存在：任务/Quest/クエスト/…），显示为「任务-珠宝匠」。
  3. 前缀渲染仍由前端 `NavBar` 统一处理（`ut(tag_prefix_key) + "-" + tag`），不需要新增文案键。
- **结果**：`search_index.json` 中 `ui.search.tag.craft_group` 前缀条目 879 条、`ui.search.tag.quest` 518 条。
- **验证**：`cd api && python3 -m unittest tests.test_search_index_entries` 8/8 OK（新增成品前缀与任务前缀断言）；`TMPDIR=<workspace>/.tmp python3 main.py` 导出无 error；`npm run build` 3125 页；8081 HTTP 200；`test:i18n` Pass 29 / Fail 0；Playwright 实测：
  - 搜「治疗药水」→「地牢商店-地穴 / 工匠合成-炼金术师 / 任务-炼金术师」；
  - 搜「生命之叶」→「工匠合成-清晰药水 / 治疗药水 / 毒药瓶 / 手术包」+「任务-女猎手 / 任务-皮革匠」；
  - 搜「金锭」→「工匠合成-黄金武装盔 …」等 10 条原料条目；无 pageerror。

### feat: 搜索索引补全商店/工匠语义标签，并为合成原料建索引

- **改动原因**：用户反馈「黄金钥匙在搜索栏显示为『地穴』，实际是哥布林走私者卖的，应完整显示为『地牢商店-地穴』」；同时要求「像合成原料『生命之叶』也应该添加为『工匠合成-治疗药水』，即成品和原料都要索引」。
- **变更文件**：`api/src/index_export.py`、`api/tests/test_search_index_entries.py`、`web/src/hooks/useSearchIndex.ts`、`web/src/components/NavBar.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **标签前缀键**：搜索条目新增可选字段 `tag_prefix_key`。前端渲染规则为 `tag_prefix_key ? ut(tag_prefix_key) + "-" + tag : tag`，因此同一个 `tag` 在不同页面可复用不同前缀，避免把展示文案写死进索引。
  2. **商店条目**：`_iter_shop_search_entries` 为每条商品加 `tag_prefix_key = "ui.nav.dungeon_shops"`（=「地牢商店」），页面显示为「地牢商店-地穴」；`tag` 仍取区域 `display`，`tag_translation_key` 不变，10 语言自动本地化。
  3. **工匠成品条目**：保持原逻辑（`tag` = 工匠名，如「炼金术师」）。
  4. **新增工匠原料条目**：`_iter_craft_search_entries` 在原「按 (merchant, item) 去重」之外，再遍历每份配方的 `requirements`，为每个原料生成一条 `page="crafts"` 的条目——`name/translation/translation_key` 取原料本身，`tag` 取成品名、`tag_translation_key` 取成品翻译键、`tag_prefix_key = "ui.search.tag.craft_group"`（=「工匠合成」），`url` 复用成品的 `/crafts/{slug}/?item={成品}`，点击后打开该工匠标签并高亮用到该原料的配方卡片（`CraftsPage` 的 `data-craft-item` 高亮逻辑无需改动）。去重键为 `(merchant, 成品, 原料)`，因此一个原料用于多个配方会各出现一条。
  5. **文案**：`uiLocale.ts` 的 `UI_EXTRA_LOCALE` 增补中英两条 `ui.search.tag.craft_group`（「工匠合成」/「Crafting」），其余语言回落英文。
- **结果**：`search_index.json` 2213 → 2837 条；`crafts` 条目 255 → 879，`dungeon_shops` 147 条带前缀；`search_index/{lang}.json` 同步重新生成。
- **验证**：`api/lint.sh` + `black --check` 通过；`cd api && python3 -m unittest discover -s tests` 163/163 OK（新增商店前缀断言、原料条目断言与素材，并同步 `pages.count("crafts")` 由 2 改 3）；`npm run check`（0 error / 20 既有 warning、Prettier、tsc）通过；`TMPDIR=<workspace>/.tmp python3 main.py` 导出 29.31s 无 error；`npm run build` 3125 页；8081 preview HTTP 200；Playwright 实测：
  - 搜「黄金钥匙」→ 第二行为「地牢商店-地穴」，点击进入 `/zh-Hans/dungeon_shops/Crypts/?item=GoldenKey`；
  - 搜「生命之叶」→ 出现「工匠合成-清晰药水 / 治疗药水 / 毒药瓶 / 手术包」四条（另有原掉落、实体、任务条目）；
  - 点击「工匠合成-治疗药水」→ `/zh-Hans/crafts/alchemist/?item=HealingPotion`，目标卡片带 2px accent 高亮；
  - `/en/` 搜 Lifeleaf → 「Crafting-Potion of Healing」等英文标签正确；全程无 pageerror。
- **附注**：`python3 main.py` 首次运行报 `sqlite3.OperationalError: unable to open database file`，原因是本机 `/tmp` 对 SQLite 排序临时文件不可写；用 `TMPDIR=<workspace>/.tmp` 重跑即通过（`.tmp/` 已由 gitignore 忽略）。

### feat: 容器宽度随视口线性缩放到 1400px + 导航栏品牌名居中

- **改动原因**：用户要求「把页面适配成 1920px 宽度，内容（比如导航栏组件总宽度）1400px，宽度变化时等比例缩放，页面宽度 1200 以下还是进入平板/手机模式（保持之前的样子）」；随后追加「越来越黑暗闪电指南 DarkFlashNav 这个组件能否居中显示」。
- **变更文件**：`web/index.html`、`web/src/AppInner.tsx`、`web/src/components/NavBar.tsx`、`web/scripts/ssg.mjs` 以及 14 个页面容器（`pages/*.tsx`）、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **宽度变量**：`index.html` 的 `:root` 新增 `--shell-max: min(1400px, calc(1200px + (100vw - 1200px) * 0.27778))`。1200px 视口时 = 1200px，1920px 时 = 1400px，两点之间线性插值，>1920px 封顶 1400px；<1200px 时计算值大于视口，行为等同原先的满宽，既有 950/750/600 断点完全不变。
  2. **外层外壳**：`AppInner` 的根容器 `maxWidth` 改为 `calc(var(--shell-max) + 32px)`——它自身有 `padding: 16px` 且 `box-sizing: border-box`，加 32px 后**内容区**正好等于 `--shell-max`，从而与导航栏内宽对齐（1920 下导航栏 1400、内容区 1400）。
  3. **统一替换**：`NavBar` 的 `.navbar-shell` 与 14 个页面的 `maxWidth: 1200` 全部改为 `var(--shell-max)`；SSG 的详情占位页（`scripts/ssg.mjs`）同步改为 `calc(var(--shell-max) + 32px)`，避免首屏占位与 React 渲染后宽度跳变。
  4. **品牌名居中**：`.navbar-brand-slot` 由 `flex: 1 1 auto` 改为绝对定位 `left: 50%` + `translateX(-50%)`，在导航栏内水平居中（导航栏补 `position: relative`）；`max-width: 40%` 防止长语言名溢出。**≤1100px 时回退为静态流式布局**（此时居中会撞到搜索框/操作区），≤600px 仍按原移动端规则独占一行。
- **验证**：`npm run format` + `npm run check`（0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页；8081 preview HTTP 200；`BASE_URL=http://localhost:8081 npm run test:i18n` Pass 29 / Fail 0；Playwright 逐宽度实测——
  - 导航栏宽度：1920→1400、1680→1333、1440→1267、1200→1168、1024→992、768→736、390→358，全部水平居中（`navCenterOffset=0`），无横向滚动；
  - 首页网格列数：≥1200 四列（4/4/2）、768 三列、390 两列，与改动前一致；
  - 品牌名居中误差：1920/1600/1440/1200 均为 **0px**，且与搜索框、操作区均无重叠；≤1100 自动回到流式布局；
  - 详情页 `/zh-Hans/items/Ale/` 在 1440 下内容区与导航栏同为 1267px。

## 2026-10-20

### feat: 站点名移入导航栏（搜索框右侧），全站可见

- **改动原因**：用户要求「把首页的 越来越黑暗闪电指南 DarkFlashNav 移动到导航栏上，放在搜索框右边，这样每个页面都能知道站点名字」。
- **变更文件**：`web/src/components/AppName.tsx`、`web/src/components/NavBar.tsx`、`web/src/pages/HomePage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **位置**：`NavBar` 在搜索框 `.navbar-search-container` 与右侧操作区 `.navbar-actions` 之间新增 `.navbar-brand-slot` 包裹 `<AppName />`；桌面端品牌名紧贴搜索框右侧、操作区靠右，移动端（≤600px）导航栏竖向排列，品牌独占一行位于搜索框下方、操作区上方。
  2. **组件改造**：`AppName` 由首页居中大标题改为导航栏品牌链接——文字取 `ui.brand.name`，`Link` 指向当前语言首页（`zh-Hans` → `/`，其余 → `/{lang}/`），色值用 `tokens.accent`；仅在首页渲染为 `<h1 class="navbar-brand">`（首页原本无其他 h1），其余页面渲染为 `<div>`，避免与页面内容 h1 重复。
  3. **首页去重**：`HomePage` 删除 `<AppName />` 与该引入，首页大标题由导航栏品牌名承担；`<title>` / meta 的 `ui.brand.name` 逻辑不变。
  4. **响应式**：品牌单行 `nowrap + ellipsis`，小屏字号 17 → 15px，390px 视口下宽度 318px 不溢出、无横向滚动。
- **验证**：`npm run format` + `npm run check`（eslint 0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页；8081 preview HTTP 200；SSR 产物校验：首页 `<h1 class="navbar-brand">` 且仅 1 个 h1，详情页品牌为 div、页面自身标题仍是唯一 h1；`BASE_URL=http://localhost:8081 npm run test:i18n` Pass 29 / Fail 0；Playwright 实测 `/zh-Hans/`、`/zh-Hans/items/Ale/`、`/zh-Hans/monsters/`、`/en/`、`/ja/crafts/` 均显示品牌且紧贴搜索框右侧（brand.x 444 > search.right 436），点击 `/ja/crafts/` 品牌跳 `/ja/`、`/en/items/Ale/` 跳 `/en/`，无 pageerror（仅云朵统计 CORS 噪音）。

### feat: 导航栏新增录屏用「自动滚动」播放按钮

- **改动原因**：用户要求「给导航栏增加一个播放按钮，点击播放按钮画面会慢慢滚动到最底部，用于页面录制视频使用」。
- **变更文件**：`web/src/components/AutoScrollButton.tsx`（新增）、`web/src/components/NavBar.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **按钮挂载**：`NavBar` 的 `.navbar-actions` 内、语言选择器之前挂载 `<AutoScrollButton />`，与主题/语言控件同排；SSG 与客户端共用同一组件树，SSR 只输出停止态。
  2. **匀速滚动**：`requestAnimationFrame` 循环按 `SCROLL_SPEED = 60` CSS px/s（与屏幕刷新率无关，每帧用 `dt` 累加，`dt` 上限 50ms 防切标签页后跳变）写 `window.scrollTo`，到 `scrollHeight - innerHeight` 自动停止；再次在底部点击则先回到顶部重新播放。
  3. **交互中止**：运行中按钮切换为暂停图标（`aria-pressed` 同步），再点即暂停；用户 `wheel` / `touchstart` / 方向键、PageUp/PageDown、Home/End、空格会立即暂停自动滚动；路由 `pathname` 变化也会重置为停止态。
  4. **文案**：新增 `ui.autoscroll.play` / `ui.autoscroll.pause`，在 `UI_EXTRA_LOCALE` 的 `zh-Hans`、`en` 中提供，其余语言回落到英文（`extraUiDict` 既有回落逻辑）；中文含「（录屏用）」说明用途。
- **验证**：`npm run format` + `npm run check`（eslint 0 error / 20 既有 warning、Prettier、tsc）通过；`npm run build` 3125 页成功；8081 preview HTTP 200；Playwright 实测：`/zh-Hans/monsters/` 点击播放 2s 内滚动 120px 且按钮变为「暂停自动滚动」，滚轮介入立即暂停、按钮点击可暂停、`/zh-Hans/` 短页面滚动到 12px 底部后自动回到播放态、在底部再次点击从顶部重播，`/en/` 显示英文标签，路由切换后回到停止态；全过程无 pageerror。

## 2026-10-19

### chore: 补丁部署（跳过 FMOD 同步，删库重建并推送含 DB 的 main）

- **改动原因**：用户要求「进行补丁部署（不包括 ~ 的同步脚本）」，即按 `docs/BUILD_AND_DEPLOY.md` 的「更新部署」流程执行，但跳过第 1 步 `~/sync_fmod.sh`（沿用现有 `~/fmod/Output` 解包源）。
- **变更文件**：`docs/SESSION_CHANGES.md` + 临时跟踪的 `api/data/darkfindv5.db`（推送后立即 `reset` 并恢复 `skip-worktree`）。
- **关键逻辑/映射关系**：`rm -f api/data/darkfindv5.db` → `cd api && nohup python main.py > pipeline.log 2>&1 &` 全量重建（`[DB] state=REBUILD_REQUIRED: DB missing`，耗时 50.52s，`[VALIDATE] all module images OK`，日志 0 error/0 traceback）。本流程不跑 `npm run build` / `vite preview`，前端 SSG 交给 GitHub Actions。本次推送内容涵盖四个未推送提交：`3f44a95ead`【工匠】属性区间（含 DB 新表）、`dc5580b44b` 搜索纳入商店/工匠/任务目标物、`78f956d279` 归档【任务探索表】、`f98ca08a5b`【工匠】标签路由。
- **DB 校验**：新 DB 49,500,160 字节、md5 `43c7801756951a4e226ea7c94dd65bca`；`pipeline_meta.generator_version = db-lifecycle-v13-item-properties`、`import_complete=1`；47 张表（含新增 `item_properties` 1876 行、`item_property_pools` 14 行）；`spawners` 55147 / `spawner_entries` 2291 / `props_entities` 592 / `craft_recipes` 332 / `craft_merchants` 9 / `quest_npcs` 14 / `explore_targets` 9。
- **导出产物校验**：`data/json/crafts.json` 9 个标签 slug（含 `ores`）；`search_index.json` 255 条工匠条目全部为标签路由（`/crafts/alchemist/?item=…`）；`index.json` / `search_index.json` 均无 `explore` 条目、`data/json/explore.json` 已不再产出。
- **部署结果**：临时跟踪 DB 并以 `75b296cf57 chore: update DB`（Bin 48308224 → 49500160 bytes）推送成功（`7f0c5f5291..75b296cf57 main -> main`）；推送后按文档 `git reset HEAD~1` 去掉本地临时 DB 提交、删除 `/tmp/darkfindv5.db` 并恢复 `skip-worktree`。GitHub Actions「Build & Deploy」3 分钟内 `completed success`（run 39180291320，`75b296cf57`），前端 SSG 由 Actions 用新 DB 完成。
- **推送异常与处理**：本轮 github.com:443 长时间不可达——DNS 把 `github.com` 解析到 `20.205.243.166`，连续出现 123s `connect timeout`、`GnuTLS recv error (-110)`、`Failure when receiving data from the peer`；而 `140.82.112.3/113.3/121.3` 可达（`curl --resolve github.com:443:140.82.113.3` 返回 200）。本机无代理、`sudo` 需密码（无法改 `/etc/hosts`），故改用临时本机 CONNECT 代理 `/tmp/opencode/gh_proxy.py`（监听 `127.0.0.1:8899`，把 `github.com` 钉到 `140.82.113.3`，隧道内仍是端到端 TLS、SNI/Host 保持 github.com），`git -c http.proxy=http://127.0.0.1:8899 push` 一次成功。属本机 DNS/网络问题，与仓库配置无关。
- **线上抽查**（`https://dnd9.icetar.com`，带随机 `cb` 参数绕 Cloudflare 缓存）：`/zh-Hans/` 200 且主页已无「任务探索表」；`/zh-Hans/crafts/` 200；`/zh-Hans/crafts/goldsmith/` 200 且 SSR 直出「獾吊坠」（= 标签路由页命中珠宝匠标签）；`/zh-Hans/crafts/tailor/` 200 且含「属性」（= 新 DB 的 `item_properties` 已上线）；`/en/crafts/ores/` 200 含 `Brimstone Powder`；`/ja/crafts/weaponsmith/` 200 含「正義の刃」；`/zh-Hans/quest_npc/Goldsmith/` 200 含「物资常缺」；已下线的 `/zh-Hans/explore/` 返回 404。

### feat: 【工匠】分页标签改为路由（`/crafts/:merchant`），搜索直达标签页

- **改动原因**：用户要求「为 `zh-Hans/crafts/` 页面的不同分页标签添加路由，使搜索结果能直接跳到路由的标签页而不是自己翻找」。原实现里标签只是组件内 state（`activeTab`），搜索跳转只能落 `/crafts/?item=X` 再由 `useEffect` 猜测并切换标签。
- **变更文件**：`api/src/craft_builder.py`、`api/src/index_export.py`、`api/tests/test_craft_builder_properties.py`、`api/tests/test_search_index_entries.py`、`web/src/types/data.ts`、`web/src/AppInner.tsx`、`web/src/pages/CraftsPage.tsx`、`web/scripts/ssg.mjs`、`docs/AGENT_REFERENCE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **商品标签 slug**：`craft_builder._merchant_slug()` 生成语言无关的稳定 slug——NPC 用 `merchant_name.lower()`（`Alchemist` → `alchemist`），合成矿石标签 `__ores__` 映射为 `ores`；`crafts.json` 的 `merchants[]` 新增 `slug` 字段（前端类型 `CraftMerchant.slug` 同步）。
  2. **搜索直达**：`_iter_craft_search_entries()` 的 url 由 `/crafts/?item=X` 改为 `/crafts/{slug}/?item=X`，搜索结果点击后直接命中该工匠标签路由，无需再猜标签。
  3. **路由与标签同源**：`AppInner` 新增 `/:lang/crafts/:merchant`；`CraftsPage` 用 `useParams` 取 `merchant` 并与 `merchant.slug` 匹配决定选中标签（找不到回落首个），删除 `activeTab` state；标签按钮由 `<button onClick>` 改为 `<Link to="/{lang}/crafts/{slug}/">`（带 `aria-current="page"`），可被爬虫跟随、支持新标签页打开，切换标签不再残留 `?item=`。
  4. **兼容旧链接**：`/crafts/?item=X`（无标签段）在 `?item=` 命中的配方所属工匠与当前标签不一致时，用 `navigate(..., { replace: true })` 重定向到 `/crafts/{slug}/?item=X`，随后照旧高亮 + 平滑滚动。
  5. **SSG**：`ssg.mjs` 按 `crafts.json` 的 `merchants[].slug` 为每个标签生成 `/{lang}/crafts/{slug}/` 页面（`routeDataKey` 让所有标签页共享 `crafts` 数据，SSR 阶段即渲染对应标签），sitemap 给 `/crafts/*` 提升为 `['0.5','weekly']`；非语言前缀 URL（`/crafts/weaponsmith`）由既有 step 5c/5d 机制自动生成 meta-refresh + `_redirects` 301。
- **结果**：每语言新增 9 个标签页（10 语言共 +90 页，另 +9 个无语言前缀重定向页）；SSG 3116 → 3125 页、dist 17148 → 17247 文件、sitemap 13400 → 13490 URL；`crafts.json` 9 个 slug（`alchemist/surgeon/armourer/weaponsmith/woodsman/tailor/leathersmith/goldsmith/ores`），`search_index.json` 255 条工匠条目的 url 全部改为标签路由（`/crafts/ores/?item=BrimstonePowder` 等，无 `__ores__` 残留）。

### feat: 地牢商店装备槽按稀有度 + 饰品/护甲/武器汇总显示

- **改动原因**：用户要求装备槽（slot 90）按 lootdrops 的「饰品 / 护甲 / 武器」继续合并，组标题里的 `Unique` 等英文改走游戏 i18n，含「血缚」的 10 件组改名「小型神器」；随后要求这些类别只显示汇总行（`护甲 ×144 · 累计 1.3773% 500 金`），不罗列具体物品名。
- **变更文件**：`api/src/merchant_builder.py`、`api/src/collector.py`、`api/tests/test_merchant_builder.py`、`web/src/types/data.ts`、`web/src/utils/shopEquipment.ts`、`web/src/pages/DungeonShopDetailPage.tsx`、`web/src/i18n/uiLocale.ts`、`docs/plans/DUNGEON_SHOP_EQUIPMENT_GROUPING.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **类别来源**：DB `item_entities` 的 `item_type` / `item_category_key`（787 行，631 件商店装备全命中）。`collector.py` 构造 `shop_item_categories` 传入 `build_shop_data()`；不能用 `loot_index`（524 条），GrimveilCloak 不在其中。

### fix: 小型神器组恢复物品卡片并标注单件爆率

### chore: 补丁部署——全量重建 DB 并推送 main（跳过 ~/sync_fmod.sh）

- **改动原因**：用户要求按补丁部署流程推送 `main` 与 DB 到远程，并明确跳过 `~/sync_fmod.sh` 的 FMOD 同步步骤。
- **变更文件**：`api/data/darkfindv5.db`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  1. **流程裁剪**：原文 1. `~/sync_fmod.sh` 按用户要求跳过；其余步骤按 `docs/BUILD_AND_DEPLOY.md`「更新部署」执行——删除本地 DB 强制全量重建 → 后台跑管道 → 确认 DB 可读 → 提交含 DB 的 `main` 并推送 `origin/main`。
  2. **全量重建**：`rm -f api/data/darkfindv5.db` 后 `[DB] state=REBUILD_REQUIRED: DB missing`，管道写入 `.building` 再 `os.replace` 原子替换，耗时 57.75s。
  3. **DB 校验**：47 张表、`item_entities` 816 行、`ingame_merchant_stock` 4365 行、`pipeline_meta.import_complete = 1`。
  4. **导出校验**：`data/json/dungeon_shops/Crypts.json` 装备槽 631 项全部带 `item_category_key`，`pool` 为 `tier 621 / mini_artifact 10`，小型神器累计 1.0043%，示例 `Bloodbound_5001`（血缚）显示 `史诗 / 武器 / 500`。
  5. **不跑前端**：按流程不在本次执行 `npm run build` / `vite preview`，SSG 由 GitHub Actions 拿到新 DB 后完成。
- **验证**：后端 202 项单测全部 OK；`./api/lint.sh` 通过（ruff + black）；DB 表数与大表行数正常；导出 JSON 字段与增长后一致。
