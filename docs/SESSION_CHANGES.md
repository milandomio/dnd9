# 会话修改记录

当前会话记录写在本文件；历史记录已移至 [`SESSION_CHANGES_ARCHIVE.md`](SESSION_CHANGES_ARCHIVE.md)，按日期保留原始内容。

## 2026-08-11

### fix: 稳定首屏布局并增加 CLS Playwright 基线

- **改动原因**：CLS 基线显示详情页、lootdrop 页和移动端在首帧到数据稳定期间存在明显布局位移；根因包括 body 默认 8px margin、locale 整页 loading 替换、详情 loading 高度过小、导航自动换行以及动态识图预览无尺寸。
- **变更文件**：`web/index.html`、`web/src/hooks/useTheme.tsx`、`web/src/AppInner.tsx`、`web/src/i18n/antdLocale.ts`、`web/src/pages/DetailPage.tsx`、`web/src/pages/LootdropDetailPage.tsx`、`web/src/pages/DungeonModuleDetailPage.tsx`、`web/src/components/NavBar.tsx`、`web/src/components/MapImageRecognitionPanel.tsx`；新增 `web/tests/cls.mjs` 并在 `web/package.json` 增加 `test:cls`；同步修正 `web/tests/map-recognition-consent.mjs` 对 Ant Design 按钮文本的空格容错。
- **关键逻辑/映射关系**：`index.html` 首屏直接 reset html/body/root margin、padding 和 box sizing；主题 effect 不再负责移除 body margin；locale 未完成时保留 AppRoutes/NavBar/Footer 外壳，仅以 `aria-busy` 标记页面；AntD locale 按当前语言同步派生；详情和模块详情 loading 分支保留 60vh 与标题/地图比例骨架；详情模板不再删除入口 reset/style，确保静态 placeholder 首帧也具备相同的 reset；NavBar 增加稳定最小高度和移动端明确纵向布局；识图预览增加 16:9 容器、宽高属性和 object-fit。
- **验证**：`npm run format:check`、`npm run lint`（0 errors，既有 warnings）、`npx tsc --noEmit`、`npm run build`、preview HTTP 200、`BASE_URL=http://localhost:8080 npm run test:i18n`（27/27）、`BASE_URL=http://localhost:8080 npm run test:map-recognition`（通过）、`BASE_URL=http://localhost:8080 npm run test:cls`（27 cases，13 cases over 0.1 告警，脚本默认非硬失败）。CLS 归因显示剩余主要位移来自详情异步内容/引用坐标与 Footer mounted/unmounted，而非 body margin。

### feat: 为 5 个 Crypt 盲盒模块注入十语言名称，替换游戏占位符 "?"

- **改动原因**：DB 重建后详情页（如 `zh-Hans/items/GrimveilCloak/`）地图模块名显示为 `?`。核查确认游戏导出 `Localization/Game/{lang}/Game.json` 中 `Text_DesignData_Dungeon_DungeonModule_{BlindfallPit,LightlessChamber_01,LightlessTomb_01,MadCorridors,TorchboundVault}` 这 5 个稀有（盲盒）模块的官方翻译就是占位符 `?`——开发方有意隐藏其名字。作为攻略站不能向玩家只展示问号，故以人工翻译覆盖。
- **变更文件**：`api/src/config.py`；`api/src/module_builder.py`；`api/src/locale_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：新增 `RARE_MODULE_TRANSLATIONS: dict[str, dict[str, str]]` 提供 10 语言人工名（zh-Hans/zh-Hant 复用 dist 旧数据确认值：盲坑/无光密室/无光陵墓/失心长廊/炬封宝库，其余语言取自旧 locale 快照）；`locale_builder.py` 在 `hardcoded_locale_entries` 之后按 `translation_key ∈ used_keys` 覆盖 `filtered[tk]`；`module_builder.py` 生成 `dungeon_modules.json` 时 `translation` 字段优先取 `RARE_MODULE_TRANSLATIONS[translation_key]["zh-Hans"]`（作为默认语言 fallback），否则回落 `resolve_name()`。同时在 import 顶部加入 `RARE_MODULE_TRANSLATIONS`。
- **验证**：`python -m py_compile api/src/config.py api/src/module_builder.py api/src/locale_builder.py` 通过；完整 `python main.py` 管道通过（26.32s，无 ERROR/Traceback，`[VALIDATE] all module images OK`）；`data/json/locale/zh-Hans.json` 中 5 个 key 输出为 `盲坑/无光密室/无光陵墓/失心长廊/炬封宝库`；`data/json/dungeon_modules.json` 对应模块 `translation` 同步正确；quick SSG 构建成功（3073 页、12061 本地化 HTML）；`vite preview` 8080 启动，`zh-Hans/items/GrimveilCloak/` HTTP 200，Playwright 实测页面标题改为「盲坑 0.84%」及「包含地图：盲坑」。

## 2026-08-06

### docs: 登记生成概率未校验楼层登记的 Bug

- **改动原因**：用户反馈 `SoulDevotedFolio` 页面「生成概率 普通 0.05%」存疑——游戏里根本没有 2002 的生成登记。核查确认：爆率 100% 正确（`lootdrop_groups` 对 2002 登记了 `ID_Lootdrop_Quest_FlameButterfly → ID_Droprate_UniqueMonsterDrop`），但生成概率存在一致性缺陷，需先登记留档。
- **变更文件**：`docs/SPAWN_RATE_GRADE_MISMATCH_ISSUE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：FlameButterfly 坐标全部落在 `Firedeep_*` 模块（分组 FireDeep），游戏 `Id_Dungeon_FloorRule_Firedeep.json` 的 `DefaultDungeonGrade=2002`；但其 spawner（`Id_Spawner_Monster_FlameButterfly.json`）的 `DungeonGrades` 白名单（0.05 那条 = `[2001,2011,2012,2021,2022,2023,2031,3001,3002,…]`）**不含 2002**，普通模式唯独缺 suffix=2。根因：生成概率按「模式聚合、与楼层无关」（`drop_rate.py:238-275` 只按 grade 千位分模式），坐标归属按「map_base → 分组」（`lootdrop_builder.py:798-839`），两者间缺少用 spawner `dungeon_grades` 对分组对应楼层（FireDeep→2002）的二次校验。修复方向记录为待评估（先全量交叉核对，再决定置 0/剔除或补数据）。
- **验证**：未改生产代码；`git diff --check` 通过。

### fix: 全 10 种语言页面双向补全 hreflang 并加 x-default

- **改动原因**：用户反馈 en 系列带语言前缀的页面「几乎不被 Google 收录」。排查确认根因是 hreflang 信号单向且缺 `x-default`：`ssg.mjs` 生成默认语言（zh-Hans）页面时以 `includeAlternates=false` 跳过 hreflang（实测 zh-Hans 列表/详情页 `hreflang=0`），而非默认语言页面却注入全部 10 个 alternate；加之 `alternateLinks` 未输出 `x-default`，Google 无法把 10 个语言版本确认成互认的 hreflang 簇，于是把 en 等变体当作主语言的翻译近重复而不单独收录。另确认详情页（如 `/lootdrops/FlameButterfly/`）为 JS 空壳（`__SSR_DATA__=0`、body 正文仅 23 字节），加剧搜索引擎对 133k 页面的渲染缺失。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`alternateLinks()` 在 10 个 `<link rel="alternate" hreflang="{lang}">` 之后追加 `hreflang="x-default"`，指向默认语言版本 `localizedPath(path, DEFAULT_LANG)`；主循环为默认语言生成页面时 `localizePage(..., includeAlternates=true)`，使 10 种语言的每个页面都输出一致的 11 条 hreflang（10 语言 + x-default），形成双向互认的完整 hreflang 簇；sitemap 生成处每个 `<url>` 的 `alts` 同样追加 `x-default` 指向 `/zh-Hans/…`，让 HTML 与 10 个 `sitemap-{lang}.xml` 保持一致（根 `sitemap.xml` 为合并结果自动同步）。
- **验证**：`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 错误，20 条既有 warning）均通过；quick SSG 构建成功（3067 路由、12007 本地化 HTML、`sitemap.xml` 13340 URL）；核实 10 种语言的 `/props/LavaMushroom/`、`/lootdrops/` 页面 11 条 hreflang 一致（zh-Hans 由 0 → 11），`sitemap-en.xml` 首块含 `x-default`；`BASE_URL=http://localhost:8080 npm run test:i18n` 通过（27/27）；`git diff --check` 通过。真机收录效果需部署后 Google 重新抓取生效。

## 2026-08-05

### docs: 优化测试通过后的 Git 本地提交流程

- **改动原因**：原流程同时要求改动前创建 checkpoint、任务完成立即 commit，并在构建前提交 `WIP`，容易让未经过功能验证的改动被提前提交，也可能混入无关工作区文件；正式提交时机应改为适用功能测试通过后。
- **变更文件**：`CLAUDE.md`；`docs/DEVELOPMENT_WORKFLOW.md`；`docs/BUILD_AND_DEPLOY.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：干净工作区只检查状态、不创建空 checkpoint；已有本任务 WIP 或测试失败/会话中断时才使用 `wip:` 保存进度。实现后按改动范围运行静态预检和功能测试，测试通过后追加 SESSION_CHANGES，精确 stage 本任务文件并正式 commit；明确 pre-commit 只做静态检查，不替代单测、数据管道、SSG、HTTP 或 Playwright 回归。
- **验证**：已用 `rg` 核对旧 checkpoint/构建前提交表述，执行 `git diff --check`；本次仅修改流程文档，不运行数据管道、构建或 Playwright。


### fix: 地图截图识别每次开启都重新显示 PVE 协议

- **改动原因**：地图截图识别的协议同意状态此前通过 localStorage 持久化，用户同意一次后当前页面及其他页面均不再弹出提示；需求改为每次打开识别功能时都必须确认。
- **变更文件**：`web/src/components/MapImageRecognition.tsx`；`web/tests/map-recognition-consent.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：移除 `darkfind.map-recognition.pve-consent.v1` 的 localStorage 读写及永久同意状态；每次勾选“地图截图识别”均打开协议 Modal，取消不加载识图资源，同意后才启用识别面板。测试同时验证取消不启用、同意后启用，以及关闭后再次打开仍重新弹出协议。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 和 `git diff --check` 通过；地图识别 Playwright 测试未执行（当前 `localhost:8080` 未启动）。


### fix: 修复任务 NPC 探索目标再次丢失 i18n 键

- **改动原因**：`/zh-Hans/quest_npc/TavernMaster/` 等任务 NPC 详情页重新出现 `Crypt_FourWayConnect`、`HangingShip`、`FloatingVillage`、`CircleIsland`、`RockIsland` 等原始模块名；任务 NPC 导出分支没有复用 `ModuleId` 对应的真实模块资源，且部分编号模块在匹配 DB 模块记录前就剥掉了 `_01/_02` 后缀，导致 `translation_key` 丢失。
- **变更文件**：`api/src/quest_collector.py`；`api/src/quest_extractor/quest_extractor.py`；`api/tests/test_quest_i18n.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：任务 NPC 的 `Explore` 内容改为先用 `match_asset_path_to_module(asset_path, content_data)` 读取 `content_data.ModuleId.AssetPathName`，再从真实模块路径解析目标名称和 `translation_key`；模块查询改为同时尝试完整模块名与去编号后的规范名，既保留 `IceCave_Hut_03`、`Ruins_Square_01`、`Ruins_Cemetery_01` 这类编号模块的官方 key，也允许 `Ruins_Chapel` 通过既有 `EXPLICIT_TRANSLATION_KEY_OVERRIDES` 回退到 `Text_DesignData_Dungeon_DungeonModule_Abandoned_Sanctuary`。
- **验证**：完整 `python main.py --rebuild-db` 成功，`quest_npc.json` 的 Explore 漏 key 数降为 0；`Crypt_FourWayConnect`、`HangingShip` 等原始名不再出现在任务 NPC 数据中，对应条目已写入 `中心祭坛`、`吊船`、`水上村落`、`环形岛`、`岩岛` 及官方模块 key。`python -m unittest tests/test_quest_i18n.py tests/test_hardcoded_i18n.py`、`python -m py_compile`、`npm run format`、`npm run format:check`、`npx tsc --noEmit`、quick SSG、`vite preview` HTTP 200 和 `npm run test:i18n` 27/27 通过。

### docs: 同步会话日志与活跃计划文档状态

- **改动原因**：近期实现已完成任务物品分组模板复用、LocationStats i18n、地图分组 i18n 和详情壳 preload 调整，但活跃计划仍引用已删除的 `QuestItemGroupPage.tsx`、旧的完整 SSR 状态，或把 `index.json`/`search_index.json` 全局 preload 标为已实施；两处历史日志也未注明 25/27 失败已被后续修复。
- **变更文件**：`docs/SESSION_CHANGES.md`；`docs/plans/SSG_DETAIL_TEMPLATE.md`；`docs/plans/LOCATION_STATS_I18N.md`；`docs/plans/DUNGEON_GROUP_I18N.md`；`docs/CACHE_OPTIMIZATION_PLAN.md`。
- **关键逻辑/映射关系**：保留历史 `25/27` 验证事实并补充 2026-08-03 已复测 `27/27`；将任务分组统一记为 `LootdropDetailPage(mode="quest_group")`，标明其使用详情轻量壳但当前没有专用 preload；将 LocationStats 与地图分组计划的完成状态、旧页面归属和实现事实回写；将 index/search 全局 preload 标为当前未实施，并记录详情壳保留 `meta.json`、过滤公共 preload 的实际行为。
- **验证**：`git diff --check`、`web` 下 `npm run format:check`、`npx tsc --noEmit` 通过；未修改生产代码或归档历史记录。

## 2026-08-03

### fix: 让 i18n 测试等待 lootdrop 详情页异步加载完成

- **改动原因**：i18n 测试没有等待 lootdrop 详情页的异步基础数据和引用坐标加载完成，过早读取 SEO 元数据及来源文案。
- **变更文件**：`web/tests/i18n.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：lootdrop 详情页的 `aria-busy` 标记位于 `#root` 内的应用布局后代节点，不是 `#root` 的直接子节点；测试改用 `#root [aria-busy="true"]`，使其在详情页输出 `aria-busy="false"` 后再执行断言。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、quick SSG（3,067 路由、15,202 个 HTML）和根路径 HTTP 200 通过；`npm run test:i18n` 为 27/27，Spellbook unique 与 CastillonDagger 日语、繁中断言均通过。

### feat: 为地图截图识别增加 PVE 协议同意门禁并补充首页关键词

- **改动原因**：地图截图识别会加载 OpenCV 和模板资源，需要在首次使用前明确展示 PVE 协议；首页同时需要保留 `dnd闪电指南` 关键词以支持中文搜索入口。
- **变更文件**：`web/src/components/MapImageRecognition.tsx`；`web/src/i18n/uiLocale.ts`；`web/src/pages/HomePage.tsx`；`web/tests/map-recognition-consent.mjs`；`web/tests/i18n.mjs`；`web/package.json`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：使用 `darkfind.map-recognition.pve-consent.v1` 持久化同意状态；未同意时只显示协议弹窗，不触发识图组件、OpenCV 或模板资源加载；同意后才懒加载 `MapImageRecognitionPanel` 并执行原有识图流程。协议提供十种语言翻译，品牌名 `越来越黑暗闪电指南 DarkFlashNav` 保持不翻译；首页追加 `dnd闪电指南`，i18n 测试增加关键词断言。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过；ESLint 0 error、20 条既有 warning；quick SSG 生成 3,067 路由、15,202 个 HTML、17,011 个文件，根路径 HTTP 200；`npm run test:map-recognition` 通过，确认同意前无识图资源请求、同意后产生 2 个识图资源请求。`npm run test:i18n` 当时为 25/27，两条 CastillonDagger 多语言文案断言失败，与本次改动无关；该历史失败已由后续等待 lootdrop 详情页就绪的修复解决，2026-08-03 复测为 27/27，见本文件最新 i18n 测试条目。

### fix: 修复 lootdrop 与任务地图来源实体的硬编码 i18n 回退

- **改动原因**：日语任务物品页将 `Potion`、`Ground`、宝箱和部分怪物来源显示为 `技術オブジェクト: ...`；部分来源虽然已有官方十语言 Game key，却因导出层未应用别名而错误生成 `df5.hardcoded.*`。
- **变更文件**：`api/src/config.py`；`api/tests/test_hardcoded_i18n.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`Armor`、`BlueMarlin`、`Coin`、`Gems`、`Trinkets`、`Weapon` 及 Dwarf/Pirate/Tidewalker/Stingray 来源改用已验证的官方 translation key；`Potion`、`Ground`、`Accessory_OldRustRoom`、普通/海底宝箱和 `SkeletonWoodenBarrel` 保留合成 key，并补齐十语言覆盖。测试同时约束官方 key 映射和无官方 key 来源的完整 locale 集合。
- **验证**：两次 DB-only 数据管道成功，10 种 locale/search index 生成；任务与 lootdrop 产物中的来源 key 已切换或覆盖，日语不再对目标来源生成技术前缀；35 个 Python 单测、Ruff、Black、Prettier、TypeScript、ESLint（0 error）通过；quick SSG 生成 3,067 路由、15,202 个 HTML、17,011 个文件；`http://localhost:8080/` 与日语任务页均 HTTP 200。

### feat: 任务物品分组页复用掉落详情模板并补齐 i18n

- **改动原因**：任务物品分组页独立维护了一套与 lootdrop 详情页高度重复的地图、分类按钮和调试布局，且任务实体导出缺少真实 `translation_key`，多语言页面的分类按钮回退为中文。
- **变更文件**：`web/src/AppInner.tsx`；`web/src/pages/LootdropDetailPage.tsx`；删除 `web/src/pages/QuestItemGroupPage.tsx`；`web/scripts/ssg.mjs`；`api/src/index_export.py`；`api/src/locale_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`/:lang/quest_items/:group` 直接路由到 `LootdropDetailPage mode="quest_group"`；`QuestGroupData` 适配为统一的实体/坐标详情模型，复用分类按钮、地图卡片懒加载、调试坐标表、位置统计和地图识图，任务模式隐藏掉落率过滤与综合爆率。管道通过 DB 实体分类写入物品、怪物和 props 的真实翻译 key，并为 `Bookshelf` 等基名匹配变体实体 key；locale 导出扫描 `quest_items_groups`，SSG 为任务分组生成多语言 title/description。
- **验证**：数据管道成功完成并交付 JSON/locale；所有 `quest_items_groups/*.json` 实体均有 `translation_key`；quick SSG 生成 3,067 路由、15,202 个 HTML、17,011 个文件；目标任务页和 `Bandage_4001` 详情页 HTTP 200；Playwright 验证中文/英文任务页详情标题、英文 `Ash Pile` 分类按钮、无掉落率 UI、无页面错误；Prettier、TypeScript、Ruff、Black 通过，ESLint 0 error、20 条既有 warning。

### fix: 修复中文分组页标题重复括号

- **改动原因**：地图模块分组页和任务物品分组页由页面组件统一输出 `【名称】`，简体中文与繁体中文 locale 模板又重复包含括号，导致标题出现多余的 `【】`。
- **变更文件**：`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：移除 `ui.module_group.title`、`ui.module_detail.title`、`ui.quest_group.title` 在简体中文和繁体中文中的内层括号，保留组件输出的 `【名称】`，标题恢复为 `【名称】地图模块` 或 `【名称】任务物品`。
- **验证**：`npm run format`、`npm run format:check`、`npm run lint`、`npx tsc --noEmit` 通过；Lint 为 0 error、20 条既有 warning；locale 中不再存在 `【{...}】` 模板。

### fix: 移除首页入口的暂停维护文案

- **改动原因**：多语言首页的地图模块预览和任务物品入口带有“暂停维护”状态文案，导致搜索引擎将整个网站误判为暂停维护。
- **变更文件**：`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：保留 `ui.home.view_explore` 与 `ui.home.view_quest_items` 两个 key 及其首页入口，仅移除简体中文、繁体中文和其他 8 种语言翻译中的暂停状态后缀。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过；`web/src` 中未发现暂停维护及对应多语言暂停状态词残留。

### perf: 排查并修复其他详情页的渐进加载问题

- **改动原因**：lootdrop 详情页改为渐进加载后，items/monsters/props 共用的 `DetailPage` 仍会一次实例化所有地图图片，路由切换和 Quick/CSR 数据壳也可能短暂显示旧实体或不完整数据；其他详情页还存在相同的版本等待和旧请求覆盖风险。
- **变更文件**：`web/src/pages/DetailPage.tsx`；`web/src/pages/QuestItemGroupPage.tsx`；`web/src/pages/DungeonModuleDetailPage.tsx`；`web/src/pages/QuestNPCDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`DetailPage` 仅接受带 `coords` 的完整 SSR 实体，按当前 URL 校验实体名称，数据请求使用 `AbortController`；地图卡片沿用 lootdrop 的 `IntersectionObserver` 和 `600px` 预加载范围，未进入视口时保留固定比例占位。Quest 物品组在 Quick 模式的 `entities: []` 壳下等待完整 JSON；地图模块详情只有坐标就绪后结束 loading，并忽略旧路由响应；NPC 详情等待 `dataVersion` 后再生成版本化 URL。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过；ESLint 0 error、20 条既有 warning；quick SSG 生成 3,067 路由、12,007 个多语言 HTML、17,011 个文件，预览根路径 HTTP 200。Playwright 验证 `GoldChest` 详情 41 张地图卡首屏仅创建 10 个 `MapPanel`、无页面错误，`Ale → GoldChest` 延迟切换不残留旧实体。`test:i18n` 当时为 25/27，两条 CastillonDagger 多语言文案断言失败；该历史失败已由后续等待 lootdrop 详情页就绪的修复解决，2026-08-03 复测为 27/27，见本文件最新 i18n 测试条目。

## 2026-08-02

### fix: 防止 LiteLLM 缺少 `.env` 时 systemd 重启风暴

- **改动原因**：用户安装并启用 `litellm.service` 后，systemd 无法读取不存在的 `/home/mio/litellm/.env`，按 `Restart=on-failure` 每 5 秒重复启动并报告 `Result: resources`。
- **变更文件**：`/home/mio/litellm/litellm.service`；`/home/mio/CLAUDE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：在 `[Unit]` 增加 `ConditionPathExists=/home/mio/litellm/.env`；真实 `.env` 存在前服务跳过启动，存在后继续读取 `EnvironmentFile` 并使用 `/home/mio/litellm/config.yaml`。
- **验证**：journal 已确认根因是 `Failed to load environment files: No such file or directory`；更新后的服务模板通过 `systemd-analyze verify`。当前已安装的 system unit 仍需重新安装模板后才包含保护条件。

### wip: 准备 LiteLLM 随 WSL 启动的 systemd 服务

- **改动原因**：需要让独立的 LiteLLM 网关在 WSL 启动后自动运行，并统一使用 `/home/mio/litellm/` 配置。
- **变更文件**：`/home/mio/litellm/litellm.service`；`/home/mio/CLAUDE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：服务以 `mio` 用户运行，读取 `/home/mio/litellm/.env`，加载 `/home/mio/litellm/config.yaml`，绑定 `127.0.0.1:4000`，失败自动重启；安装目标为 `/etc/systemd/system/litellm.service`。
- **当前阻塞**：真实 `.env` 尚未创建，当前没有 endpoint/key；本次会话的 `sudo` 需要交互密码，尚未将模板安装到系统 unit 目录，因此尚未启用或手动启动服务。
- **验证**：`systemd-analyze verify /home/mio/litellm/litellm.service` 通过；当前 `systemd` 正常运行，但 `litellm.service` 不存在。

### perf: lootdrop 关联坐标改为串行渐进加载

- **改动原因**：`GoldBangle1J_5001` 等掉落详情页的分类来源较多，一次性请求全部关联实体 JSON 会在高延迟网络下长时间阻塞整页；需要按爆率优先顺序逐个加载并逐个渲染。
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：关联引用去重后按 `max_score` 降序排列，`REF_FETCH_BATCH_SIZE = 1` 使每次只请求一个 `/data/{version}/json/{page}/{name}.json`；每个请求完成后立即写入 `refCoords`，移除关联坐标未全部完成时的整页阻塞，保留全局缓存、请求去重和失败后继续后续请求。
- **验证**：`npm run format`、`format:check`、TypeScript、ESLint 无 error；quick SSG 生成 3,067 路由、12,007 个多语言 HTML、17,011 个文件；目标页 HTTP 200；Playwright 验证最大同时在途关联请求数为 1、5 秒内渲染 66 个按钮且无浏览器错误。

### perf: 详情页提前预加载数据版本

- **改动原因**：详情页模板删除了 `meta.json` preload，客户端必须等 React 启动后才发起版本请求，导致第一个关联实体 JSON 额外等待一次网络往返。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：详情页继续移除通用的模块、索引和搜索索引 preload，但保留 `/data/json/meta.json` preload，使数据版本探测与基础 lootdrop JSON 并行；版本号准备后仍由 `dataUrl()` 请求版本化关联 JSON。
- **验证**：quick SSG 生成 3,067 路由、12,007 个多语言 HTML、17,011 个文件；目标页 HTML 含 `meta.json` preload 且 HTTP 200；模拟 300ms 网络延迟时第一个关联 JSON 约 345ms 发起；TypeScript、Prettier、ESLint 无 error。

### fix: 非默认语言先加载字典再渲染页面

- **改动原因**：模板详情页首轮将 `__ssrLang` 错设为默认中文且没有注入 locale 字典，客户端会先用中文回退文本渲染，再切换到目标语言，造成实体名称闪动。
- **变更文件**：`web/src/AppInner.tsx`；`web/src/i18n/useLocale.ts`；`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：详情 HTML 预加载 `/data/{version}/json/locale/{lang}.json`，SSG 注入真实路由语言；`useLocale()` 通过 `loadedLang` 和 `localeReady` 管理字典生命周期；非默认语言在 locale 就绪前只渲染当前语言的加载提示，字典完成后才挂载导航、页面和实体翻译。
- **验证**：TypeScript、Prettier、ESLint 无 error；quick SSG 生成 3,067 路由、12,007 个多语言 HTML、17,011 个文件；英文详情页 locale preload、`__ssrLang: en` 和 HTTP 200 正常；locale 延迟 500ms 时首屏无中文实体文本，加载后直接显示英文。

### chore: 清理项目内 LiteLLM 提交历史

- **改动原因**：LiteLLM 是 WSL 工作区环境配置，不属于 `DarkFindV5` 项目管理范围；其本地提交链应从项目分支移除。
- **变更文件**：`docs/SESSION_CHANGES.md`；移除本地分支中的 `7fec0c01` 至 `305da1e9` 共 8 个 LiteLLM 相关提交。
- **关键逻辑/映射关系**：`main` 从 `305da1e9` 回退至共同基线 `335bf70b`，使用 mixed reset 保留当前前端改动；项目内 `litellm/` 文件和对应会话记录均不再存在，`origin/main` 未改动。
- **验证**：`git log` 的当前分支不再包含 LiteLLM 提交；项目内无 `litellm` 文件；当前仅保留本次前端改动和会话记录差异。

### fix: 恢复地图模块分组页 SSR hydrate

- **改动原因**：`dungeon_modules/{group}` 页面注入的是分组专用 SSR 数据键，但客户端路由判定只检查列表键，导致页面虽然内容正常却每次走 `createRoot()` 重挂载。
- **变更文件**：`web/src/main.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：在地图模块详情键判断之后增加 `dungeon_modules/${group}` 精确键判断，保留模块详情页优先匹配，分组页命中后使用 `hydrateRoot()`。
- **验证**：Prettier、TypeScript、ESLint（0 error）、quick SSG（3,067 路由、17,011 个文件）、根路径/分组页/模块详情页 HTTP 200、i18n 回归 27/27 通过。

### docs: 明确 lootdrop 变体 SSG 与 CSR 范围

- **改动原因**：避免普通 lootdrop 的非默认变体扩大静态 HTML 产物范围，明确默认变体、神器变体和 CSR 路由的边界。
- **变更文件**：`docs/REFERENCE_FRONTEND_DATA.md`；`docs/BUILD_AND_DEPLOY.md`；`docs/AGENT_REFERENCE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：普通变体仅默认后缀生成 SSG 实体文件，非默认普通变体由 `main.tsx` 使用 CSR 加载基底 JSON；`_8001` 神器独立保留 SSG；不可用后缀只生成无实体数据的提示壳。
- **验证**：文档内容与 `web/scripts/ssg.mjs` 的 `generateStatic`、`web/src/main.tsx` 的 SSR 数据判定保持一致。

### fix: 详情页至少点亮一个掉落分类

- **改动原因**：详情页默认显示阈值高于所有掉落分类的 `max_score` 时，分类按钮会全部熄灭，页面默认没有可显示的来源。
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：初始化、SSR 数据切换和异步数据加载时，若没有分类达到默认阈值，则按分类按钮的 `max_score` 降序取第一个分类作为新的显示阈值；手动调试阈值仍可正常隐藏全部分类。
- **验证**：Prettier、format:check、TypeScript 通过；ESLint 0 error，保留 19 条既有 warning。

### fix: 恢复神器与普通变体的双向稀有度链接

- **改动原因**：`Spellbook_7001` 等普通变体页缺少 `8001` 神器入口，`Spellbook_8001` 等独立神器页又因切换组件依赖 `variants` 而无法显示低等级变体入口。
- **变更文件**：`api/src/lootdrop_builder.py`；`api/tests/test_drop_rate.py`；`web/src/components/VariantSwitch.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`web/src/main.tsx`；`web/tests/i18n.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：普通变体的 `variant_rarity` 保留真实掉落后缀中的 `8001`，但合并后的 `variants` 数据仍排除独立神器；前端按 `variant_rarity` 渲染跨详情页链接，使普通页指向 `*_8001`、神器页指向 `*_1001~7001`；客户端根据当前 URL 是否存在匹配的 SSR 数据，区分正常 hydrate 和首页 fallback 的 CSR，避免未静态化变体路由触发 hydration 错误。
- **验证**：后端掉落率单测 15/15、Python 编译、Ruff、Black、Prettier、TypeScript 通过；DB-only 管道成功生成 478 个 lootdrop；quick SSG 生成 3,067 路由、12,007 个多语言 HTML、17,011 个 dist 文件；首页、`Spellbook_7001` 和 `Spellbook_8001` HTTP 200，Playwright/i18n 回归 27/27 通过且无 hydration 错误。

### fix: 点击外部自动收起语言菜单

- **改动原因**：原生 `details` 默认只响应自身的开关，点击页面其他区域不会像 Ant Design `Select` 一样自动失焦收起。
- **变更文件**：`web/src/components/NavBar.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：为语言菜单增加 `pointerdown` 文档监听；事件目标不在语言 `details` 内且菜单处于打开状态时，将 `open` 设为 `false`，菜单内部点击和语言锚点导航保持不变。
- **验证**：Prettier、TypeScript 和 quick SSG 通过；用户实测点击外部区域后菜单自动收回，构建生成 3,067 路由和 12,007 个多语言 HTML。

### style: 缩短语言选择框宽度

- **改动原因**：上一版将语言框从 `7em` 增大到 `8em` 后视觉偏长，需要调整为更紧凑的宽度。
- **变更文件**：`web/src/components/NavBar.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：语言触发器宽度从 `8em` 调整为 `6em`，下拉菜单通过 `minWidth: 100%` 同步宽度；菜单高度、深色背景和可爬取锚点保持不变。
- **验证**：Prettier、TypeScript 通过；quick SSG 生成 3,067 路由、12,007 个多语言 HTML；Playwright 实测触发器宽度 `96px`、菜单 `clientHeight=scrollHeight=328px`、10 个语言锚点，首页和 NPC 页 HTTP 200。

### style: 增大语言下拉菜单并统一深色背景

- **改动原因**：语言菜单高度过小，10 个语言选项可能出现滚动条；未展开的语言框颜色也比菜单背景更亮，需要统一视觉。
- **变更文件**：`web/src/components/NavBar.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：触发器宽度从 `7em` 调整为 `8em`，菜单最大高度从 `320px` 调整为 `420px`，深色主题下触发器和菜单统一使用 `#141414`；锚点和 URL 逻辑不变。
- **验证**：Prettier、TypeScript 通过；quick SSG 生成 3,067 路由、12,007 个多语言 HTML；Playwright 实测菜单 `clientHeight=scrollHeight=328px`、触发器 `128x24px`、10 个语言锚点，首页和 NPC 页 HTTP 200。

### style: 用标准锚点模拟 Select 视觉

- **改动原因**：需要尝试不依赖 Ant Design `Select` 的 SEO 兼容方案，同时保持语言栏原有下拉框外观。
- **变更文件**：`web/src/components/NavBar.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：语言选项继续使用 SSR 可爬取的 `<a href>`，通过原生 `details/summary` 和内联样式模拟 Select 的 7em 宽度、24px 高度、边框、下拉菜单、选中态、悬停态和打开态；链接仍由 `withLangPrefix()` 生成并统一补尾斜杠。
- **验证**：Prettier、TypeScript 通过；quick SSG 生成 3,067 路由、12,007 个多语言 HTML；Playwright 实测触发器约 `112x24px`、菜单包含 10 个语言锚点，首页和 NPC 页 HTTP 200。

### fix: 拆分多子类型并合并未分类 lootdrop

- **改动原因**：多标签物品被错误合并成 `魔法物品、杖` 等独立分类，且不同无翻译子类型产生多个“未分类”按钮；同时标签不需要中括号。
- **变更文件**：`web/src/pages/ListPage.tsx`；`docs/plans/LOOTDROP_ITEM_TYPE_GROUPING.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：一个物品的多个有效子类型分别写入对应大类子组；无有效翻译的子类型统一使用空子类型键合并；显示格式改为 `⚔️武器：`、`斧(6)`，特殊组为 `🏺神器(28)`，移除所有 `【】`。
- **验证**：Prettier、ESLint（0 error）、TypeScript 和 quick SSG 通过；`/zh-Hans/lootdrops/` HTTP 200；Playwright 验证无组合组、每个大类只有一个未分类按钮，点击 `斧(6)` 显示 6 项。

### style: lootdrop 标签改为紧凑大类前缀格式

- **改动原因**：大类已独立成行后，子分类按钮仍重复显示大类名称并带有空格；需要改为行首大类标签和紧凑子类按钮。
- **变更文件**：`web/src/pages/ListPage.tsx`；`web/src/i18n/uiLocale.ts`；`docs/plans/LOOTDROP_ITEM_TYPE_GROUPING.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：动态行显示 `图标【大类：】`，子类显示 `【子类(count)】`；特殊分组显示 `图标【分组(count)】`，新增 `ui.list.item_group_prefix` 支持多语言冒号格式。
- **验证**：Prettier、ESLint（0 error）、TypeScript 和 quick SSG 通过；`/zh-Hans/lootdrops/` HTTP 200；Playwright 验证分类文本无空格，`⚔️【武器：】【斧(5)】` 格式正确，点击斧分类显示 5 项。

### fix: 合并含未分类大类中的单项子分类

- **改动原因**：某个一级大类已经存在“未分类”时，数量为 1 的独立子分类按钮信息量过低，单独展示会造成分类栏过碎。
- **变更文件**：`web/src/pages/ListPage.tsx`；`docs/plans/LOOTDROP_ITEM_TYPE_GROUPING.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：先按一级分类寻找空子类型的“未分类”组；仅当该组存在时，将同大类中 `items.length === 1` 的子类型组的物品移入未分类，并按物品名去重后删除原按钮；没有未分类组的大类不受影响。
- **验证**：Prettier、ESLint（0 error）、TypeScript、quick SSG 和 HTTP 200 通过；Playwright 验证辅助道具、杂项的未分类组正常显示，武器无未分类组时单项 `火器(1)` 仍保留。

### style: lootdrop 分组按钮放大 1.5 倍

- **改动原因**：当前分类按钮尺寸偏小，需要整体放大以提高可读性和点击区域。
- **变更文件**：`web/src/pages/ListPage.tsx`；`docs/plans/LOOTDROP_ITEM_TYPE_GROUPING.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：分组按钮最小高度从 `36px` 调整为 `54px`，内边距从 `4px 8px` 调整为 `6px 12px`，字体从 `15px` 调整为 `22.5px`，圆角从 `6px` 调整为 `9px`；分组逻辑和内容宽度布局保持不变。
- **验证**：Prettier、ESLint（0 error）、TypeScript、quick SSG 和 HTTP 200 通过；Playwright 实测按钮高度 `54px`、字体 `22.5px`、内边距 `6px 12px`、圆角 `9px`。

### style: lootdrop 分类按钮改为内容宽度

- **改动原因**：分类按钮使用可增长 flex 配置，导致一行按钮不足时被拉伸填满整行；需要保持按钮自身内容宽度。
- **变更文件**：`web/src/pages/ListPage.tsx`；`docs/plans/LOOTDROP_ITEM_TYPE_GROUPING.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：将按钮 flex 从可增长布局改为 `0 1 auto`，保留大类分行和行内自动换行，按钮只按文字、数量和 padding 占用宽度。
- **验证**：Prettier、ESLint（0 error）、TypeScript 和 quick SSG 通过；`/zh-Hans/lootdrops/` HTTP 200；Playwright 在 1200px 宽度下验证首行三个按钮总占用 365px、容器宽 1168px，未被拉伸。

### feat: 按物品大类分行显示 lootdrop 标签

- **改动原因**：类型标签全部处于同一 flex 行流中，饰品和护甲等不同一级大类之间没有明确换行。
- **变更文件**：`web/src/pages/ListPage.tsx`；`docs/plans/LOOTDROP_ITEM_TYPE_GROUPING.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：按 `itemCategoryName(item_category_key)` 将标签聚合为行；同一 `ItemType` 的子类型共享一行，一级大类变化时创建新行，神器/小型神器/稀有掉落保留特殊首行。
- **验证**：Prettier、ESLint（0 error）、TypeScript 和 quick SSG 通过；`/zh-Hans/lootdrops/` HTTP 200；Playwright 验证 `饰品：戒指（7）` 位于 `护甲：布甲（64）` 上一行，点击护甲后显示 64 项。

### feat: 按物品真实类型重分组 lootdrop

- **改动原因**：原 `物品 / 饰品 / 武器装备` 分组依赖 `variant_count` 和爆率分数猜测，无法反映游戏资产中的 `ItemType`、`ArmorType`、`MiscType`、`UtilityType`、`AccessoryType` 和 `WeaponTypes`。
- **变更文件**：`api/src/db/schema.py`；`api/src/db/importers/items.py`；`api/src/db/repositories/items.py`；`api/src/db_freshness.py`；`api/src/lootdrop_builder.py`；`api/src/index_export.py`；`api/src/search_index_builder.py`；`api/src/locale_builder.py`；`api/src/collector.py`；`api/tests/test_item_type_metadata.py`；`web/src/pages/ListPage.tsx`；`web/src/i18n/uiLocale.ts`；`docs/plans/LOOTDROP_ITEM_TYPE_GROUPING.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：导入阶段将 `ItemType` 映射为 `Text_Code...Category_*`，将 Gameplay Tag 映射为 `Text_Code...Type_Item_*`，写入 DB 后传递到 lootdrop 和 SSR 搜索索引；前端按稳定翻译键组合分组并显示如 `辅助道具：消耗品`、`护甲：皮甲`，神器/小型神器/稀有掉落保持特殊分组。旧 DB 缺字段时返回默认值，源可用时通过生成器版本变化触发重建。
- **验证**：31 个后端测试、Ruff、Black、Prettier、TypeScript 通过；完整管道生成 787 条类型记录、478 个 lootdrop 和 10 种 locale；quick SSG 生成 3,067 路由、12,007 个多语言 HTML、17,011 个 dist 文件；`/zh-Hans/lootdrops/` HTTP 200，Playwright 验证 46 个标签、默认神器 28 项、切换辅助道具消耗品 15 项，中英文缺失翻译均回退为多语言未分类文案。

### fix: 恢复稀有掉落分组优先级

- **改动原因**：类型元数据分组判断早于原有 `max_score` 稀有掉落判断，导致带物品类型的稀有掉落被错误归入普通类型标签，页面看不到“稀有掉落”分组。
- **变更文件**：`web/src/pages/ListPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：保持 `神器`、`小型神器`、`稀有掉落` 的特殊分组优先级；只有未命中特殊分组的条目才进入 `ItemType + subtype` 类型分组。

### style: 恢复语言栏下拉框视觉

- **改动原因**：可爬取链接改造后语言栏变成普通文本菜单，偏离原 Ant Design `Select` 的下拉框视觉；需要保留标准锚点，同时恢复原来的边框框体外观。
- **变更文件**：`web/src/components/NavBar.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：保留 `details/nav/a` 结构，在原地球图标旁将 `summary` 设置为约 `7em` 宽、24px 高、边框、圆角和下拉箭头的 Select 风格，菜单链接和尾斜杠 URL 逻辑不变。
- **验证**：Prettier、TypeScript 通过；quick SSG 生成 3,067 路由、12,007 个多语言 HTML；Playwright 实测触发器尺寸约 `112x24px`、边框 `1px`、圆角 `6px`，菜单可展开且包含 10 个语言锚点；首页和 NPC 页 HTTP 200。

### feat: 语言切换器改为可爬取链接

- **改动原因**：语言栏原使用 Ant Design `Select` 和脚本跳转，语言选项不是标准 `<a href>`，不利于搜索引擎发现对应语言页面；需要按 canonical 尾斜杠规则提供可爬取的内部链接。
- **变更文件**：`web/src/components/NavBar.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：使用原生 `details/nav` 菜单渲染十种语言的标准 `<a>`；通过 `withLangPrefix()` 保留当前页面路径，并统一补充尾斜杠，同时保留 query/hash，设置 `hrefLang`、`lang` 和语言名称锚文本。
- **验证**：Prettier、TypeScript、完整前端格式检查通过；ESLint 0 error（19 条既有 warning）；quick SSG 生成 3,067 路由、12,007 个多语言 HTML；`Woodsman` 页面包含 10 个带尾斜杠语言链接，预览首页和 NPC 页 HTTP 200。

### feat: lootdrops 列表改为分类标签切换

- **改动原因**：`zh-Hans/lootdrops/` 原先同时展开所有掉落分类，页面内容过长；需要改为类似 Excel 工作表的分类切换，只展示当前选中分类。
- **变更文件**：`web/src/pages/ListPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：复用既有 `groupLootdrops()` 分类顺序和数量，在原“神器（28）”标题位置渲染分类标签按钮；默认选择第一个分类，点击标签更新 `activeLootGroup`，`tabpanel` 只渲染对应分类的掉落卡片，其他列表页保持原逻辑。
- **验证**：Prettier、ESLint（0 error）、TypeScript 通过；quick SSG 生成 3,067 路由、12,007 个多语言 HTML；`/zh-Hans/lootdrops/` HTTP 200，Playwright 验证标签数 6，默认“神器（28）”显示 28 项，切换“小型神器（8）”显示 8 项。

### perf: 完成 DB freshness 生命周期与 item 坐标链索引优化

- **改动原因**：DB 存在但解包源未变化时仍会重复完整 importer；`item_coord_chain_map` 还会执行约 10 秒三表 JOIN，且 source 不可用时 DB-only 连接可能触发 schema migration。
- **变更文件**：`api/main.py`；`api/src/collector.py`；`api/src/db_freshness.py`；`api/src/db/__init__.py`；`api/src/db/schema.py`；`api/src/drop_rate.py`；`api/tests/test_db_freshness.py`；`api/tests/test_drop_rate.py`；`docs/plans/DB_FRESHNESS_AND_IMPORT_LIFECYCLE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：入口以 metadata-only manifest 决定 `DB_READY`、`DB_ONLY`、`REBUILD_REQUIRED` 或 `FAIL_FAST`；完整导入写入 `.building`，核心表校验和 `pipeline_meta` 完成后用 `os.replace()` 替换正式 DB；DB-only 使用 SQLite read-only 连接。`DropRateEngine.preload()` 的 `base_item -> spawner set` 索引替换 `lootdrop_rate_items -> lootdrop_groups -> spawner_entries` JOIN，并排除旧 JOIN 不会返回的空 spawner key。
- **验证**：27 个后端测试、Ruff、Black、Python 编译、Prettier、TypeScript 全通过；final full rebuild `38.45s`，hot DB-only `24.84s`。旧 SQL 与内存索引均为 529 keys，坐标链阶段低于日志显示精度。quick SSG 生成 3,067 routes、12,007 localized HTML、17,011 dist files，`http://localhost:8080/` 返回 HTTP 200。

### verify: 完成优化前后 data 产物零差异对照

- **改动原因**：需要证明移除三表 JOIN 后不仅性能改善，后端管线生成物也没有业务语义或字节差异。
- **变更文件**：`api/src/drop_rate.py`；`api/src/collector.py`；`api/tests/test_drop_rate.py`；`docs/plans/DB_FRESHNESS_AND_IMPORT_LIFECYCLE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：在 `bdb055e3` 优化前 worktree 和最终优化 worktree 中，用同一外部源、`--rebuild-db` 和 `PYTHONHASHSEED=0` 生成产物；索引预加载按旧 SQL 的 `rate_items -> lootdrop_groups -> spawner_entries` 行序构造 set，直接复用 set，保持 `export_items()` 首个 fallback spawner 的既有选择。
- **验证**：优化前 `53.36s`，优化后 `39.48s`；`data` 两侧各 1,782 文件，包含 255 个非 JSON 图片文件，`diff -qr` 返回零差异，代表性 JSON SHA-256 相同。首次对照发现并修复了 fallback set 重建造成的 7 个 item 坐标差异，最终对照已清零。

### feat: 详情页静态壳注入地图模块和真实 WebP

- **改动原因**：详情页原本只注入标题、`#####` 和三张 `RareModule_1x1` 占位图，搜索引擎和禁用 JavaScript 的用户无法看到页面实际包含哪些地图模块；需要保留轻量壳的性能优势，同时提供可索引的正文内容。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SSG 根据实体坐标或 lootdrop 来源坐标解析 `dungeon_modules.json` 的模块别名，构建仅含名称、翻译键、图片名和尺寸的 `templateModules` 摘要；详情壳将摘要渲染为响应式模块卡片，使用 `/data/img/{img_name}.webp` 和模块名 `alt`，跳过 `RareModule_1x1`、`UnderConstruction_1x1` 及无图模块。多语言壳复用模块翻译字典，并保留客户端后续加载完整 JSON 的流程。
- **验证**：Prettier、TypeScript、ESLint（0 error，19 条既有 warning）通过；quick SSG 生成 3,067 路由、12,007 个多语言 HTML；`GoldCoins`、`Abomination` 详情壳均包含真实模块名和 WebP，目标 HTML 未发现占位图或 `#####`；预览根路径、详情页和图片 URL 分别返回 HTTP 200。

### perf: 延迟加载详情壳地图图片

- **改动原因**：详情壳已包含真实地图 WebP，但无 JavaScript 页面也可能在首屏同时请求大量图片，和客户端 JS、详情 JSON 竞争网络资源。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：详情壳地图 `<img>` 增加原生 `loading="lazy"` 和 `decoding="async"`；不依赖 JavaScript，现代浏览器接近视口时加载图片，旧浏览器忽略属性后仍能正常显示。
- **验证**：详情 HTML 包含 `loading="lazy" decoding="async"`；quick SSG 生成 3,067 路由、12,007 个多语言 HTML；预览首页、详情页和地图图片 URL 均返回 HTTP 200。全局 `format:check` 仍受工作区已有未格式化的 `web/src/pages/ListPage.tsx` 阻塞，本次 `ssg.mjs` 无格式问题。

### fix: 恢复武器掉落来源十语言实体翻译

- **改动原因**：硬编码实体接入 `df5.hardcoded.*` 后，`Weapon_GoldenRoom`、`Weapon_MysticalTreasureRoom` 等掉落来源未补实体 locale 覆盖，日语和繁中错误回退为 `技術オブジェクト:` / `技術物件：` 加英文资产名。
- **变更文件**：`api/src/config.py`；`api/tests/test_hardcoded_i18n.py`；`web/tests/i18n.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：为 CastillonDagger 实际使用的 8 个武器掉落来源补齐 `HARDCODED_LOCALE_OVERRIDES` 十语言词条，保持 `df5.hardcoded.{实体名}` key 不变；浏览器回归锁定 `ja/zh-Hant` 目标文案，并排除语言切换器当前 URL 对变体链接断言的干扰。
- **验证**：完整数据管道、quick SSG（3,067 路由、12,007 个多语言 HTML）、HTTP 200、3 个后端 i18n 单测、Black、Prettier、TypeScript 和 Playwright i18n 回归 25/25 通过。

## 2026-08-01

### docs: 制定 DB 新旧判断与导入生命周期修复方案

- **改动原因**：当前 `collector.py` 用 `GAME_ROOT.exists()` 直接开启全量 importer，DB 存在也重复导入；历史 `_is_db_stale()` 在 DB-only 改造中被移除，导致 freshness、首次导入和 DB-only 模式没有明确边界。
- **变更文件**：`docs/plans/DB_FRESHNESS_AND_IMPORT_LIFECYCLE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：方案恢复“打开 SQLite 前判断 DB 状态”的入口，使用 `pipeline_meta` source manifest 区分 missing/fresh/stale，采用 building DB + 完成标记 + 原子替换避免半成品 DB；`GAME_ROOT` 仅表示源可用，不再决定是否导入。方案同时记录当前约 10s 的 `item_coord_chain_map` 三表 JOIN，要求复用 `DropRateEngine._base_item_spawners` 并修正计时边界。
- **验证**：已对照当前 `main.py`、`collector.py`、DB importer、schema、历史提交 `78d04b3b` 与 `2bd1438b`；本次仅新增方案文档，未改生产逻辑。

### docs: 增加源目录不可用时禁止删除 DB 的硬性保护

- **改动原因**：需要避免游戏目录缺失、挂载失败或源目录部分缺失时，stale 判断把“无法读取源”误判为空源，进而删除有效 DB 或创建空 DB。
- **变更文件**：`docs/plans/DB_FRESHNESS_AND_IMPORT_LIFECYCLE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：新增 `SOURCE_UNAVAILABLE` 状态及保护矩阵：有效 DB + 源不可用只走 DB-only；无效/缺失 DB + 源不可用直接 fail fast；`--rebuild-db` 同样必须先通过 source_available；stale 检查只返回状态，不执行 `DB_PATH.unlink()`，正式 DB 只在 building DB 导入完成并校验后通过 `os.replace()` 替换。
- **验证**：已检查当前 `main.py` 的 `_pre_cleanup()` 仅删除 `data/json`，当前生产代码没有 DB unlink；方案测试矩阵新增 DB inode/mtime/大小不变、部分 source root 缺失和强制重建拒绝用例。本次仍仅修改方案与会话文档，未改生产逻辑。

### wip: 开始实施 DB freshness 与原子重建生命周期

- **改动原因**：开始落实 DB 生命周期方案，先消除 `GAME_ROOT` 存在即重复 importer 的隐式分支，并防止 source 不可用时误删或创建空 DB。
- **变更文件**：`api/src/db_freshness.py`；`api/main.py`；`api/src/collector.py`；`api/src/db/__init__.py`；`api/src/db/schema.py`；`docs/plans/DB_FRESHNESS_AND_IMPORT_LIFECYCLE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：新增 metadata-only source manifest 和 `pipeline_meta`；入口先得到 DB 决策，再选择 DB-only 或写入 `darkfindv5.db.building` 的 full import；full import 完成后写 manifest/`import_complete`，关闭连接后 `os.replace()` 替换正式 DB。source 不可用时只允许复用有效 DB，强制重建也拒绝执行。
- **当前状态**：已完成静态实现但尚未写生命周期测试、未跑完整管道；`item_coord_chain_map` 的重复 JOIN 仍未替换。此 checkpoint 仅保存可继续开发的 WIP，后续必须先完成测试与四路径管道验证。

### perf: 缓存 lootdrop 来源实体坐标骨架并完成前后对照

- **改动原因**：最新 profile 中 `source_coords` 为 `9.293s`，同一来源实体会被多个 lootdrop 重复执行坐标回退、Spawner 过滤、label 分类、坐标转换和 spawn rate 查找，需要验证按实体复用坐标骨架的实际收益。
- **变更文件**：`api/src/lootdrop_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：在详情循环内增加 `source_name -> prepared_coords_by_type` 缓存。首次遇到实体时完成 `all_coords` 多级回退、`entity_spawners` 过滤、`classify_label`、坐标字段组装、variant 元数据、spawn rate 和质量识别；后续物品只复制不含 `score` 的坐标骨架，保留每个物品独立计算 score 的语义。缓存 `18,361` 命中、`295` 未命中，命中率 `98.4%`。
- **验证**：同一数据集、同一当前代码基线对照：详情构建 `25.608s -> 21.210s`（减少 `4.398s`，17.2%）；其中 `source_coords` `9.293s -> 2.209s`（减少 `7.084s`，76.2%）；`lootdrops` 步骤 `26.21s -> 22.01s`（减少 `4.20s`，16.0%）；全管道 `53.97s -> 50.58s`（减少 `3.39s`，6.3%，受其他阶段波动影响）。Ruff、Black、Python 编译、16 个单元测试、完整管道和 quick SSG 通过；生成 3,067 路由、12,007 多语言 HTML，`/`、`/zh-Hans/items/Bandage/` 均 HTTP 200。日志：`/tmp/darkfindv5-coord-cache-before.log`、`/tmp/darkfindv5-coord-cache-after.log`。

### perf: 重跑 lootdrop 并确认缓存后的新热点

- **改动原因**：基底物品匹配缓存上线后，需要在同一当前版本重新运行 lootdrop，确认原概率计算热点消失后最耗时的阶段。
- **变更文件**：`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：478 个 lootdrop 详情最新构建耗时 `25.506s`：源实体坐标收集/转换 `9.168s`（35.9%）最高，变体详情生成 `7.676s`（30.1%）第二，缓存后的基础 `group_rates` `3.946s`（15.5%），坐标规范化/评分 `2.211s`（8.7%），详情 JSON 写入 `2.184s`（8.6%）。源坐标阶段包含坐标回退、Spawner 过滤、label 分类、坐标对象转换、spawn rate 查找和质量正则；变体阶段包含来源 ref 解析及每个品质/地图组/来源反复调用 `get_variant_group_drop_rates()`。原 `_find_rate_item()` 线性扫描已不再是热点。
- **验证**：完整管道成功，`lootdrops` 步骤 `26.06s`、总计 `52.59s`；quick SSG 生成 3,067 路由和 12,007 多语言 HTML，`/`、`/zh-Hans/items/Bandage/` 均 HTTP 200。日志：`/tmp/darkfindv5-lootdrop-rerun.log`，构建日志：`/tmp/darkfindv5-lootdrop-rerun-build.log`。

### perf: 缓存 LootDrop 基底物品优选变体查询

- **改动原因**：基础 `group_rates` 中 `_find_rate_item()` 会为每个无后缀基底物品反复扫描完整掉落池，profile 显示其占该阶段 93.3%。
- **变更文件**：`api/src/drop_rate.py`；`api/tests/test_drop_rate.py`；`docs/plans/PERF_RATE_ITEM_LOOKUP_CACHE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`DropRateEngine.preload()` 将每个 `lootdrop_id` 的变体族预先映射为 `base_item_name -> 优选 luck-grade 条目`；`_resolve_rate_item()` 保持精确项优先，带后缀项缺失仍返回 `None`，只有无后缀基底使用 `_5001` 优先、否则最高真实品质的缓存值，且 `_8001` 不参与。未预加载的手工 engine 仍回退原 `_find_rate_item()` 扫描。
- **验证**：恢复点为 `f2253c1f`；Ruff、Black、Python 编译和 16 个单元测试通过。完整管道成功，基础 `group_rates` 从 `72.368s` 降至 `4.391s`（-93.9%），lootdrop 详情从 `93.819s` 降至 `28.979s`（-69.1%），`lootdrops` 从 `94.39s` 降至 `29.59s`（-68.7%）；quick SSG 生成 3,067 路由和 12,007 多语言 HTML，`/`、`/zh-Hans/items/Bandage/` 均 HTTP 200。

### docs: 补充掉落率缓存计划的计算链与 I/O 边界

- **改动原因**：需要明确此次性能优化实际替换的是哪段概率计算，以及是否改变 DB、JSON 或解包数据的 I/O。
- **变更文件**：`docs/plans/PERF_RATE_ITEM_LOOKUP_CACHE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：文档列出 `lootdrop detail -> group rates -> group/grade -> lootdrop -> rate items -> resolver -> luck-grade 权重` 计算链，并列出 `SQLite preload -> 内存索引 -> 内存计算 -> 既有 JSON 写盘` I/O 链；确认索引将导出期重复的 `rate_items.items()` 内存扫描前移至 `preload()` 单次内存遍历，不新增 SQL、JSON 或解包文件 I/O。
- **验证**：文档与 `DropRateEngine.preload()`、`_build_preferred_base_items()`、`_resolve_rate_item()`、`compute_drop_rate()` 当前实现逐段对照；本次仅文档补充，不重跑管道。

### docs: 制定 LootDrop 基底物品匹配缓存优化方案

- **改动原因**：profile 确认 `_find_rate_item()` 的候选池线性扫描占基础 `group_rates` 的主要时间，需要在实现前固定语义、索引范围、测试和回退路径。
- **变更文件**：`docs/plans/PERF_RATE_ITEM_LOOKUP_CACHE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：方案在 `DropRateEngine.preload()` 中构建 `lootdrop_id -> base_item_name -> 既有 luck-grade 条目` 的优选变体索引；查询仍先精确命中，基底回退优先 `_5001`、否则最高真实品质、忽略 `_8001`。DB 当前有 395 个池、44,459 行、6,682 个变体族，索引只保存既有列表引用；未预加载的手工 engine 继续使用原始扫描以兼容测试。
- **验证**：已复核 `REFERENCE_DROP_RATES.md` 的变体规则、`drop_rate.py` 调用链和现有 `test_drop_rate.py`；计划阶段不修改生产逻辑，待实施时执行完整管道 A/B 与 JSON 语义对照。

### perf: 增加 lootdrop 分项计时并定位概率计算热点

- **改动原因**：总计时只能显示 `lootdrops` 耗时，无法判断坐标整理、掉落概率计算、变体处理、JSON 序列化或 enrichment 的实际占比。
- **变更文件**：`api/src/collector.py`；`api/src/lootdrop_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`collector.py` 分别记录索引、详情和 enrichment；`build_and_save_lootdrop_details()` 以 `perf_counter()` 累计 setup、源坐标、基础 GDI 概率、坐标规范化/评分、ref/坐标预算、变体 GDI、详情 JSON、索引回写和未归类时间。实测 478 个 lootdrop：详情 `94.568s`，其中基础 `group_rates` 为 `73.068s`（77.3%），源坐标 `8.881s`，变体 `7.887s`，详情 JSON `2.138s`；enrichment 为 `0.527s`。因此后续优化应优先减少 `DropRateEngine.get_group_drop_rates()` 的重复计算，而非继续压缩 JSON I/O。
- **验证**：Ruff、Black、Python 编译和 11 个后端单元测试通过；完整管道成功，`lootdrops=95.16s`、总计 `120.83s`，日志为 `/tmp/darkfindv5-lootdrop-profile.log`；预览根路径 HTTP 200。

### perf: 拆解基础 group_rates 的概率计算时间

- **改动原因**：第一层分项显示基础 `group_rates` 占 lootdrop 详情的大多数时间，仍需明确其内部是候选组定位、模式/楼层遍历、掉落表匹配还是权重计算造成。
- **变更文件**：`api/src/drop_rate.py`；`api/src/lootdrop_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`build_and_save_lootdrop_details()` 将共享 profile 传给 `get_group_drop_rates()`；后者分别累计候选 LDG 解析、模式/楼层调度及 `compute_drop_rate()`，后者再累计分级表查询、`_find_rate_item()`、权重累加和其余循环。实测基础 `group_rates=72.368s`：`get_group_drop_rates=69.870s`、调用端 `2.498s`；其中 `compute_drop_rate=68.599s`，而 `_find_rate_item()` 为 `67.507s`，占基础 group_rates `93.3%`。其未命中基础物品时会扫描整个 `rate_items` 并匹配变体，是后续缓存 `(lootdrop_id, item_name)` 查询结果的唯一优先热点。
- **验证**：Ruff、Black、Python 编译和 11 个后端单元测试通过；完整管道成功，`lootdrops=94.39s`、总计 `127.44s`，日志为 `/tmp/darkfindv5-group-rates-profile.log`；预览根路径 HTTP 200。

### perf: 验证 \_find_rate_item 的候选扫描热点

- **改动原因**：`_find_rate_item()` 占基础 `group_rates` 的 93.3%，需要确认是精确字典查询、候选池扫描、正则匹配还是变体选择造成。
- **变更文件**：`api/src/drop_rate.py`（临时插入后回退）；`api/src/lootdrop_builder.py`（临时插入后回退）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：临时 profile 显示 `_find_rate_item=126.026s`，候选池线性扫描 `124.254s`（98.6%）；该扫描的正则匹配、基础名/`_8001` 条件和循环分别记录为 `63.353s/29.017s/31.884s`。后两项含逐候选 `perf_counter()` 的测量成本，不能作为绝对性能值；可以确定的是未命中时的整池扫描才是热点，变体选择仅 `0.404s`。临时细粒度计时会令 lootdrop 从约 `94s` 上升至 `157s`，已完整回退，不影响日常管道。
- **验证**：临时 profile 的完整管道成功，日志为 `/tmp/darkfindv5-find-rate-profile.log`；回退后将重新运行 Python 预检，预览根路径保持 HTTP 200。

### perf: enrichment 改为内存传递并单次写实体详情

- **改动原因**：`enrichment.py` 在 lootdrop 详情生成后再次解析 lootdrop、items、monsters、props 派生 JSON，再写回实体详情；该二次 I/O 不需要重新访问 DB 或解包数据。
- **变更文件**：`api/src/collector.py`；`api/src/entity_export.py`；`api/src/lootdrop_builder.py`；`api/src/enrichment.py`；`api/tests/test_enrichment.py`；`docs/plans/PERF_ENRICHMENT_IN_MEMORY.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：实体导出将详情对象暂存为 `entity_data_by_type`；lootdrop 详情生成将基础条目的 `group_drop_info` 暂存为 `lootdrop_group_info_by_item`；enrichment 直接消费两者，执行直接生成实体的 GDI、怪物/props GDI 注入和零率清理，最后统一写出每个实体详情一次。`entity_page_map` 同时作为变体 ref 的可用页面集合，允许实体详情延后落盘。
- **验证**：Ruff、Black、Python 编译、11 个后端单元测试、runtime I/O guard、前端 Prettier 与 TypeScript 通过；完整数据管道成功，items/monsters/props 含 GDI 详情数为 `95/134/45`；quick SSG 生成 3,067 路由和 12,007 多语言 HTML；`/`、`/zh-Hans/items/Bandage/` 均 HTTP 200。

### docs: 新增 Blindfall Pit 概率计算链英文版

- **改动原因**：用户需要一份更易阅读的英文文档来说明稀有模块从 Dungeon、DungeonLayout、DungeonModule 到 `0.84%` 的完整计算链，同时保留原中文文档不变。
- **变更文件**：`docs/BLINDFALL_PIT_PROBABILITY_RECORD_EN.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：英文版将布局层 `2/40`、Crypt 稀有模块池 `1/5`、基础概率 `1%` 和 CenterTower `2x2` 覆盖修正 `21/25` 分章节说明，最终公式仍为 `1% × 21/25 = 0.84%`；同时整理资产链、模式差异、均匀抽取假设、失效条件和重算检查清单。原文件 `docs/BLINDFALL_PIT_PROBABILITY_RECORD.md` 未修改。
- **验证**：英文文档 Prettier 检查、`npm run format`、`npm run format:check`、`npx tsc --noEmit` 和 `git diff --check` 均通过。

## 2026-07-31

### fix: 为地图校准输入增加未识别占位文案

- **改动原因**：地图起点 X、Y 和模块像素输入为空时没有状态提示，用户无法直观看出可以等待系统自动识别。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：三个数字输入复用 `ui.map_recognition.grid_unknown` 作为 `placeholder`，简体中文显示“未识别”；输入值、自动校准回填和手动编辑逻辑不变。
- **验证**：`npm run format:check`、`npx tsc --noEmit`、`npm run lint` 和 quick SSG 构建通过；`npm run test:i18n` 通过 23/23；目标页 HTTP 200，Playwright 确认三个校准输入的 `placeholder` 均为“未识别”。

### fix: 将地图分组空选项改为未选择

- **改动原因**：地图分组下拉的空值选项原显示“全部”，无法明确提示用户需要主动选择地图分组。
- **变更文件**：`web/src/i18n/uiLocale.ts`；`web/src/components/MapImageRecognitionPanel.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：新增 `ui.map_recognition.group_unselected`，替代地图分组下拉中的全站 `ui.filter.all`；简体中文为“未选择”，其他 9 种语言同步提供对应文案，空值仍表示未指定分组。
- **验证**：`npm run format:check`、`npx tsc --noEmit`、`npm run lint` 和 quick SSG 构建通过；`npm run test:i18n` 通过 23/23；Playwright 确认地图分组空选项显示“未选择”，全站其他“全部”文案不受影响。

### fix: 为地图规模下拉增加介绍标题

- **改动原因**：`3x3/4x4/5x5/7x7` 网格选择下拉缺少与“识别精度”一致的可见说明标题。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：网格下拉包裹为带 `ui.map_recognition.grid_size` 文案的标签，简体中文显示“地图规模”；网格值、`gridType` 状态和识别校准逻辑保持不变。
- **验证**：`npm run format`、`npx tsc --noEmit`、`npm run lint` 和 quick SSG 构建通过；目标页 HTTP 200，Playwright 确认识图面板中“地图规模”存在且 `地图规模/3x3/4x4/5x5/7x7` 下拉可用。

### fix: 明确地图识图校准起点输入标签

- **改动原因**：识图面板中的网格起点输入仅显示 `X/Y`，无法直观看出其为地图起点坐标。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：网格参数行的可见标签由 `X/Y` 改为“地图起点X/地图起点Y”，输入值、`gridX/gridY` 状态及校准参数传递保持不变。
- **验证**：`npm run format`、`npx tsc --noEmit`、`npm run lint` 和 quick SSG 构建通过；目标页 HTTP 200，Playwright 确认“地图起点X/地图起点Y”显示且输入控件仍可用。

### fix: 为地图分组下拉增加红色选择提示

- **改动原因**：地图分组下拉缺少像“识别精度”一样的可见介绍标题，用户需要明显提醒进行地图选择。
- **变更文件**：`web/src/i18n/uiLocale.ts`；`web/src/components/MapImageRecognitionPanel.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：简体中文 `ui.map_recognition.group_select` 改为“选择地图”；地图分组下拉保留在识别精度行最左侧，并包裹可见标题，标题使用 `#d4380d`、13px、700 字重的大红色样式；`selectedGroup`、`handleGroupChange()` 和筛选逻辑不变。
- **验证**：`npm run format`、`npx tsc --noEmit`、`npm run lint` 和 quick SSG 构建通过；目标页 HTTP 200，Playwright 确认“选择地图”标题为红色样式，并与识别精度下拉处于同一行。

### fix: 将地图分组选择移到识别精度左侧

- **改动原因**：地图分组选择框原位于识图面板标题行右上角，用户需要它与识别精度控件处于同一行并位于其左侧。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：标题行保留模板数量；`ui.map_recognition.group_select` 对应的下拉框移动到精度行最左侧，顺序变为“地图分组 → 识别精度 → 精度阈值”，`selectedGroup` 和 `handleGroupChange()` 行为不变。
- **验证**：`npm run format`、`npx tsc --noEmit`、`npm run lint` 和 quick SSG 构建通过；目标页 HTTP 200，Playwright 确认地图分组下拉位于识别精度左侧且两者 `y` 坐标一致。

### fix: 调整地图识图精度预设中文文案

- **改动原因**：识别精度下拉框原先使用“标准/高召回/极高召回”，用户要求改为按精度等级直观显示。
- **变更文件**：`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：简体中文 `ui.map_recognition.precision_standard` →“高精度”、`precision_high` →“中精度”、`precision_maximum` →“低精度”；预设阈值 `0.52/0.45/0.38`、英文及其他语言文案保持不变。
- **验证**：`npm run format:check`、`npx tsc --noEmit` 和 `npm run lint` 通过；lint 保持 19 条既有 warning、0 error。`npm run test:i18n` 因未启动 `localhost:8080` 服务全部报 `fetch failed`，未进入页面断言。

### chore: 集中忽略地图识图测试图片

- **改动原因**：根目录下的 4 张地图识图测试图片属于本地测试数据，不应继续作为未跟踪文件散落在仓库根目录。
- **变更文件**：`.gitignore`；`test-data/test-cap-7x7.png`；`test-data/test-cap-dy.png`；`test-data/test-cap.png`；`test-data/test-cap1.png`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：图片统一移动到根目录 `test-data/`，新增 `/test-data/` 忽略规则，使该目录及其内容整体不参与 Git 状态和提交。
- **验证**：已确认 4 张图片均位于 `test-data/`，根目录不再显示这些文件；待提交前复核忽略状态。

### docs: 记录 Blindfall Pit 从 Dungeon/Layout/Module 到 0.84% 的完整计算链

- **改动原因**：`Blindfall Pit` 的基础 `1%` 不应仅以 `moduleSpawnRate.ts` 中的固定值表达，需要保留从 `Id_Dungeon_RandomCrypt_N_Solo` 的布局引用、Rare 槽统计、Crypt 稀有模块池到中心塔覆盖修正的可复算路径。
- **变更文件**：`docs/BLINDFALL_PIT_PROBABILITY_RECORD.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`Id_Dungeon_RandomCrypt_N_Solo.json.Properties.Layouts[]` 引用 40 个 `Crypt_5x5` 布局；`DungeonLayout.Properties.Slots[].SlotTypes[].SlotType` 统计出 2 个含 `Rare` 槽布局；`NumMaxRares=1` 确认当前每局最多一次稀有抽取；`DungeonModule` 中 `ModuleType=Crypt && bIsRare=true` 得到 5 个稀有模块，故基础概率为 `(2/40)×(1/5)=1%`；`CenterTower` 的 `2x2` 尺寸在 `5x5` 网格覆盖 4 格，最终为 `1%×(25-4)/25=0.84%`。文档同时记录字段、文件链、假设、模式差异和布局变更后的重算检查项。
- **验证**：已根据游戏解包资产和历史提交 `501d7b59` / `4a469816` 复核文件链与数值；本次仅文档改动，未运行数据管道或前端构建。

### fix: 将中心塔覆盖概率计入稀有模块出现率

- **改动原因**：地穴稀有模块先以 1% 概率落入 5x5 网格，随后 2x2 的 `CenterTower_HR_D` 会覆盖其中 4 格；此前页面仍按 1% 计算，导致综合爆率偏高。
- **变更文件**：`web/src/utils/moduleSpawnRate.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：五个 `Crypt_*` 稀有模块共享的出现率改为 `1% × (25 - 4) / 25 = 0.84%`；`getRareModuleSpawnRate()` 同时驱动模块标题出现率，`applyModuleSpawnRate()` 继续将该值折算到物品/怪物/容器详情页和掉落详情页的综合爆率。
- **验证**：`npm run format`、`npm run format:check` 与 `npx tsc --noEmit` 通过。

### perf: 延迟加载地图截图识别资源

- **改动原因**：关闭识图开关时，详情页仍静态加载识图组件并构造模板描述数组；虽然未加载 OpenCV 和模板图片，仍存在不必要的脚本与计算开销。
- **变更文件**：`web/src/components/MapImageRecognition.tsx`；`web/src/components/MapImageRecognitionPanel.tsx`；`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：保留的轻量开关通过 `React.lazy` 在开启后才请求识图面板 chunk；面板 chunk 再按原逻辑动态导入 OpenCV，并请求当前页面模板图片。详情页和掉落页仅在开关开启时构造模板描述数组，关闭时不遍历识图模板。关闭开关会卸载面板。
- **验证**：Prettier 与 TypeScript 通过，quick SSG 通过；Playwright 在关闭开关的初始加载记录中未发现 `MapImageRecognitionPanel` 或 `opencv` 请求，开启并等待引擎就绪后才依次请求面板 chunk 和 OpenCV chunk。

### perf: 提高地图识别工作分辨率

- **改动原因**：1920px 截图缩到 600px 后，5x5 单元仅约 42px，Cistern 的细墙和小型标记损失严重。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`MAX_WORKING_EDGE` 从 `600` 提高到 `1200`，1920px 截图中的单元工作尺寸约从 42px 提升到 84px；识别流程和原图坐标换算不变。
- **验证**：1200px 下 Cistern 固定单元分数由约 `0.329` 提升到 `0.766`；Inferno 标准模式回归为 5 个真值，`InfernoMouth` 分数 `0.639`。移除低分辨率阶段的 `-0.25` 固定单元阈值补偿，改为合并标准高置信锚点与固定单元结果；锚点在合并前会从初始 ROI 局部坐标映射到校准地图局部坐标，以中心落入地图范围判断保留，避免边缘模块被裁剪过滤。

### fix: 共生子池不再显示为互斥选项

- **改动原因**：`BP_GameObjectLinker` 内的成员会共同生成；此前详情页和掉落页将其错误显示为“实体 N 种选 M、位置选 1”，幽鬼、阴森帷幕披风与风箱页面均受影响。
- **变更文件**：`api/src/collector.py`；`api/src/translator.py`；`web/src/types/data.ts`；`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：同一 `(map, file, group_parent)` 的 `sub_group_parent` 数量导出为 `parent_pool_size`；详情页按父池中包含当前实体的子组数计算出现率，子组成员则统一显示为“共生组合：成员列表 · N 点”，不再把成员数或点数视为互斥分母。每个父池首次出现时显示“随机组合池：N组中选1组”；掉落页的坐标分数按父池规模分摊，并跳过共生坐标旧的 `variant_count` 除法。
- **验证**：`python main.py`、`npm run format`、`npm run format:check`、`npx tsc --noEmit`、quick SSG 构建及 `HTTP 200` 均通过；Playwright 确认幽鬼、阴森帷幕披风和风箱页面出现“共生组合”，且不再含“幽鬼、阴森帷幕披风2种选”；披风页仅显示一次“随机组合池：6组中选1组”并保留全部 6 个组合。

### fix: 明确地图识别精度阈值标签

- **改动原因**：识别精度后的“阈值”含义不够明确，需要直接标注为精度阈值。
- **变更文件**：`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：简体中文改为“精度阈值”，繁体中文同步为“精度閾值”；阈值数值和识别逻辑不变。

### feat: 使用可编辑网格缓存执行固定单元识别

- **改动原因**：此前将亮度 ROI 直接均分为 5x5/7x7，忽略地图外围留白，并仍在 seed 周围搜索模板；用户需要先用标准匹配确定地图原点和模块步距，再直接裁出地图、切分固定单元并与页面模板比较。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`web/src/components/MapImageRecognition.tsx`；`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：第一阶段以最高 `0.50` 的阈值获取锚点，通过锚点坐标差拟合网格步距，并推导原图 `X/Y`；缓存对象为 `gridType + x + y + cellSize`。第二阶段按缓存裁出 `cellSize × gridSize` 地图，固定切成所有单元，每格与当前页面模板的四个旋转及 `94%-100%` 尺度比较，每格最多返回一个最佳模块。界面新增默认“未识别”的 `3x3/4x4/5x5/7x7` 下拉框、`X/Y/模块像素` 三个输入框和按缓存重新识别按钮；有缓存时跳过全图扫描。最终预览和导出图片只保留地图区域。
- **验证**：Inferno 标准 `0.52` 自动校准约为 `X=630、Y=211、单元=132-134px`，固定 25 单元恰好命中 5 个已知真值，包含 `InfernoMouth`；Prettier、TypeScript 和 quick SSG 通过。Ruins 7x7 测试入口连续两次在识图开关出现前超时，未进入算法，按熔断规则停止重复测试。

### fix: 保留网格细化失败的原始候选

- **改动原因**：启用固定网格后，细化函数返回的结果会整体替换低阈值 seed；部分单元细化失败时，原本已识别的模块因此被丢弃，导致识别率低于未使用网格的版本。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：按模板和网格单元逐项处理；单元内二次匹配成功使用细化结果，失败则回退到该单元保留的最高分 seed，避免整体替换造成漏报。
- **验证**：Prettier、TypeScript、构建和 HTTP 预览通过；Inferno 极高召回返回 7 个结果，5 个已知真值模块（包括 `InfernoMouth`）全部保留，另有 2 个 `InfernoRooms` 低分候选。

### fix: 让网格识别遮罩覆盖完整单元

- **改动原因**：固定网格二次匹配后的绿色遮罩仍按模板内容框绘制，Inferno 5x5 中遮罩尺寸小于网格单元，视觉上未与网格对齐。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：存在 5x5/7x7 网格时，根据匹配框中心和 ROI 局部坐标计算列/行，遮罩改为绘制对应完整网格单元；无网格提示时继续使用模板匹配框。
- **验证**：Prettier 和 TypeScript 检查通过；待重新构建后验证 Inferno 预览图的实际视觉位置。

### feat: 增加固定网格单元二次匹配

- **改动原因**：低阈值全图扫描可以定位 Inferno `1-5` 的 `InfernoMouth`，但跨模块相似区域会产生候选；按已推断的 5x5/7x7 网格单元重新匹配，降低跨单元误报并保留低阈值 seed 的召回能力。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：有网格提示时先用 `min(用户阈值, 0.38)` 扫描 seed，再按 seed 中心归属固定网格单元，在单元内使用 seed 尺度附近的旋转/缩放模板进行二次匹配；二次匹配无结果时保留 seed，避免细化阶段清空已有候选。新增区域裁剪函数，修正 ROI 内按 `(x, y, width, height)` 截取网格单元。
- **验证**：Prettier 格式检查和 TypeScript 通过；重新构建并启动 `8080` 预览后，Inferno 极高召回识别到 8 个模块，`InfernoMouth` 命中分数 `0.4734`，方法为 `template-inner`。标准阈值 `0.52` 仍不会确认该模块，因为当前最高分低于标准阈值；这不是固定网格流程可单独解决的分数问题。

### feat: 增加地图识别精度预设与自定义阈值

- **改动原因**：GoldChest 炼狱测试图已知包含 `1-3`、`1-5`、`2-4`、`3-3`、`3-4` 共 5 个黄金箱子模块，固定 `0.52` 阈值只能识别 2 个，需要由用户在误报率和召回率之间选择。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`web/src/components/MapImageRecognition.tsx`；`web/src/i18n/uiLocale.ts`；`docs/plans/游戏内地图识别优化.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：模板匹配阈值改为每次识别参数；面板新增标准 `0.52`、高召回 `0.45`、极高召回 `0.38`、自定义四档下拉框，以及范围 `0.20-0.90` 的可编辑数值输入；手动修改自动切换自定义，越界值失焦或识别前自动归一化。阈值变化不重新加载 OpenCV 或模板。
- **验证**：Inferno 分组 5 张模板下，炼狱图标准/高召回/极高召回依次识别 2/4/5 个，自定义 `0.32` 识别 6 个并出现疑似误报；四方向 TreasureRoom 裁剪图在标准档均保持 1 个命中；OldRustyKey 7x7 图高召回识别 2 个、极高召回 3 个且网格分类正确。

### docs: 完善地图识别后续开发计划并暂停执行

- **改动原因**：按用户要求将后续准确率、性能、自动建议、测试矩阵和验收标准形成完整计划；在用户明确说“继续执行”前停止新增功能。
- **变更文件**：`docs/plans/游戏内地图识别优化.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：后续固定按 P1 结果可观测性与边界真值 → P2 Web Worker/模板缓存 → P3 自动分组建议 → P4 自动化截图回归推进；阈值调优必须使用边界真值，不能只比较识别数量。
- **验证**：计划已记录当前架构、三张完整图与四方向裁剪图结果、最终验收标准、风险、暂停点和恢复顺序；当前代码保持已构建可运行状态。

### feat: 增加地图识别结果明细与调试报告

- **改动原因**：仅显示最终数量无法确认结果是否对应人工真值，也无法定位粗筛、阈值和 NMS 导致的漏报或误报。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`web/src/components/MapImageRecognition.tsx`；`web/src/i18n/uiLocale.ts`；`docs/plans/游戏内地图识别优化.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：每个最终结果显示模块名、模板/ORB 方法、置信度和原图边界；调试 JSON 版本 1 记录分组、阈值、网格、原图/ROI、粗筛与精匹配模板分数、NMS 前后框及阶段耗时。算法内部坐标先补 ROI 偏移，再统一换算为原图像素。
- **验证**：GoldChest + Inferno + `test-cap-dy.png` 极高召回导出 5 个已知模块，NMS 由 9 个候选归并为 5 个真值框，算法约 1.1 秒；桌面与 390px 移动视口明细正常，移动明细宽度 336px 且自身无横向溢出；Prettier、TypeScript、i18n 23/23、ESLint 0 error、quick SSG 15,290 HTML、目标路由 HTTP 200 通过。

### wip: 调查 InfernoMouth 标准档漏报

- **改动原因**：用户确认炼狱截图包含 `InfernoMouth_HR_D.json` 对应的恶魔之口模块，但标准 `0.52` 未识别；DB 和原始资产确认该子关卡正确共用 `InfernoMouth` 地图模板。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`web/src/components/MapImageRecognition.tsx`；`docs/plans/游戏内地图识别优化.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：接近阈值的完整模板增加忽略 12% 外圈的内区匹配，并按完整模板边界回写；5x5 尺度增加 `0.52`。当前结果方法区分 `template`、`template-inner`、`orb`。
- **验证与阻塞**：quick SSG 生成 15,290 HTML，TypeScript 和 Prettier 通过；标准档由 2 个增至 3 个，但恶魔之口分数仍为 `0.432`，扩展尺度没有改善。连续两次修改未解决目标漏报，按熔断规则停止；后续必须先采集每个旋转/尺度/裁剪的分数矩阵，当前改动作为 WIP checkpoint，不视为修复完成。

### perf: 增加地图识别 ROI、网格与动态分组筛选

- **改动原因**：完整截图全屏遍历所有模板、旋转和尺度约需 51 秒；通用 GoldChest 页面包含 40 张模板，还需要用户按当前截图地图分组缩小识别范围，并区分 5x5/7x7 地图。
- **变更文件**：`web/src/utils/mapImageRecognition.ts`；`web/src/components/MapImageRecognition.tsx`；`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`web/src/i18n/uiLocale.ts`；`docs/plans/游戏内地图识别优化.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：亮度密度自动定位大地图 ROI，匹配边界补回 ROI 偏移后映射到原图；ROI 比例与模块中位尺寸推断 5x5/7x7，并缩窄尺度；大模板集合先半尺寸粗筛到 18 个；ORB 场景描述子全模板共享；分组下拉框实时使用当前页面可见模板的 `DungeonModule.group`，默认全部。
- **验证**：三张 1920x1080 截图均正确分类网格（废墟 1 层 7x7，地穴/炼狱 5x5）；OldRustyKey 的 7x7 图识别到 1 个目标；GoldChest 分组选项实时显示 8 个当前页面分组且默认“全部”。炼狱 5 个已知目标当前仅识别 2 个，固定阈值调优记录在独立优化计划，下一 checkpoint 实施精度选项。

### feat: 新增游戏内地图截图本地识别

- **改动原因**：用户需要在详情页粘贴 Windows `PrtScn` 游戏截图，自动标出截图中属于当前页面的地图模块，并在浏览器本地预览和导出绿色标注图。
- **变更文件**：`web/src/components/MapImageRecognition.tsx`；`web/src/utils/mapImageRecognition.ts`；`web/src/utils/mapImage.ts`；`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`web/src/i18n/uiLocale.ts`；`web/package.json`；`web/package-lock.json`；`web/vite.config.ts`；`docs/plans/游戏内地图识别.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：“隐藏0爆率坐标”后新增默认关闭滑动开关；开启后动态加载 `@techstark/opencv-js` 和当前过滤结果内全部地图 WebP，按 `0/90/180/270°` 多尺度模板匹配，未命中模板使用 ORB + RANSAC 单应性兜底；重叠边界去重后在原尺寸截图绘制 50% 透明绿色蒙版并导出 PNG。掉落页模板预加载独立于 `IntersectionObserver`，覆盖滚动后可见但尚未加载的地图卡片；OpenCV 动态 chunk 不进入 Workbox 安装时预缓存。
- **验证**：`test-cap1.png` 四个 90° 方向均识别到 1 个 `TreasureRoom_01` 模块，绿色变化像素均为 7,044；完整 `test-cap.png` 在 `/zh-Hans/lootdrops/GoldenKey/` 的 11 个模板中识别到 5 个模块，预览和导出正常、无页面错误。Prettier、TypeScript、ESLint（0 error、19 条既有 warning）、i18n 23/23、quick SSG（15,290 HTML）通过，目标路由 HTTP 200。

## 2026-07-30

### docs: 建立游戏内地图识别执行计划

- **改动原因**：为详情页新增本地截图识图功能，先固定懒加载范围、识别算法优先级、页面接入点和验收标准，避免影响现有 React SSG/PWA 架构。
- **变更文件**：`docs/plans/游戏内地图识别.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：识图组件挂在两个详情页爆率控制框；模板来自当前页面全部地图模块；OpenCV.js 多尺度模板匹配优先、ORB 特征匹配兜底；截图只在浏览器本地生成绿色蒙版并导出。
- **验证**：已确认工作区干净、当前分支为 `main`，并核对 `ReferenceDropRates` 控制框、`MapPanel` 图片路径和掉落页 `IntersectionObserver` 懒加载实现。

### chore: 推送 main 并同步本地数据库快照

- **改动原因**：按请求核对线上 `origin/main` 与本地 `main`；远程数据库哈希为 `13e6c6b2ea8be492de3ee3c3b5860ce8c4fe8725`，本地数据库哈希为 `ea3b6fcc1e110a3539bb3b78a60cdb8b5372c180`，存在差异，需要将本地新快照随 `main` 推送。
- **变更文件**：`api/data/darkfindv5.db`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：数据库按 `BUILD_AND_DEPLOY.md` 规则临时纳入提交并推送到 `origin/main`，推送后恢复本地 `skip-worktree` 状态；数据库仍是 Actions 无游戏源时导出前端数据的唯一来源。
- **验证**：已通过 Git 远程对象哈希确认线上线下数据库不同；推送后复核远程 `refs/heads/main` 已更新，远程数据库哈希与本地新快照一致；本地按规则保留在临时 DB 提交之前并恢复 `skip-worktree`。

### fix: 将超级宝藏堆箱体坐标纳入掉落分组爆率

- **改动原因**：超级宝藏堆来源注入仅匹配 `Hoard01_9` 与 `HoardChest01`，漏掉沉船墓场的 `HoardChest01_9`；其对应 `SuperHoardChest01_9` 因此未进入掉落详情，地图显示箱体坐标而 `group_drop_info` 未生成对应参考爆率。
- **变更文件**：`api/src/lootdrop_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：掉落索引将 `HoardChest01_9 -> SuperHoardChest01_9` 与既有 `Hoard01_9 -> SuperHoard01_9` 一同注入；两者共享 `ID_LootDropGroup_SuperHoard` 和“超级宝藏堆”显示名，后续合并坐标并为 `ShipGraveyard_ShipRest` 生成 GDI。
- **验证**：Python 编译、`tests.test_drop_rate`（6 项）、Black 与 pre-commit Ruff 通过；完整数据管道（190.15 秒）和 quick SSG（69.5 秒）通过，`/zh-Hans/lootdrops/WarMaul_8001/` HTTP 200；Playwright 点击“超级宝藏堆”后确认沉船墓场渲染 `超级宝藏堆100%[PvE:0%][普通:0%][豪客赛:0.0036%][逆袭赛:0%]`。

### fix: 将稀有模块出现率计入综合爆率

- **改动原因**：稀有模块标题虽显示 1% 出现率，但 Composite Rate 未乘入该前置概率，导致全局综合爆率被高估。
- **变更文件**：`web/src/utils/moduleSpawnRate.ts`；`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`applyModuleSpawnRate()` 对已配置稀有模块按 `综合爆率 × 模块出现率 / 100` 折算，普通模块保持原值；物品详情与掉落详情共用该函数，掉落详情的模块排序也同步使用折算结果。
- **验证**：Prettier、TypeScript 和 ESLint（0 error、19 条既有 warning）通过；quick SSG 生成 15,290 个 HTML；`/en/items/GrimveilCloak/` HTTP 200，Playwright hydration 后为 `Composite Spawn Rate 92.38%`、`Composite Rate 0.6005%`，顺序正确。

### fix: 紧邻显示综合生成率和综合爆率

- **改动原因**：物品详情页的 Composite Spawn Rate 位于模块地图后，而 Composite Rate 位于参考爆率后，难以直接对照两项概率。
- **变更文件**：`web/src/components/CompositeRate.tsx`；`web/src/pages/DetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：通用 `CompositeRate` 新增可选 `spawnRate` 与 `spawnPrecision`，固定先渲染 `ui.detail.composite_spawn_rate` 再渲染综合爆率；详情页将原本两次调用合并，传入模块子池生成率。
- **验证**：Prettier、TypeScript 和 ESLint（0 error、19 条既有 warning）通过；quick SSG 生成 15,290 个 HTML；`/en/items/GrimveilCloak/` HTTP 200，Playwright hydration 后确认 `Composite Spawn Rate 92.38%` 位于 `Composite Rate 60.047%` 前。

### chore: 同步最新数据库快照至 main

- **改动原因**：按请求将 `dev` 已重建的本地 SQLite 数据库快照同步至 `main` 并推送远端。
- **变更文件**：`api/data/darkfindv5.db`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`main` 的数据库内容替换为 `dev` 完整数据管道生成的快照，包含实体、生成点、任务、掉落率和十种语言翻译；前端数据导出继续以该 DB 为唯一来源。
- **验证**：源快照的完整数据管道成功完成（147.52 秒）；对应 quick SSG 生成 15,290 个 HTML，`8080` 预览首页返回 HTTP 200。

### fix: 为非详情页生成目标语言 SSR 正文

- **改动原因**：主页、地图模块、任务和探索页面的非中文 HTML 原先仅替换 SEO 标题，正文仍复制简中 SSR，hydration 后切换目标语言时会出现中文闪屏。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：将原本仅服务四类实体列表的目标语言 SSR 生成器泛化到全部非模板详情路由；每页在 SSG 时以 `/{lang}/...` 渲染，内联该语言 `__locale`，并设定 `__ssrLang={lang}`；items、monsters、props、lootdrops 和地图模块详情继续使用轻量详情壳，避免坐标数据和 Ant Design 样式重复嵌入数千页。
- **验证**：Prettier、TypeScript、脚本语法、quick SSG（28.6 秒）、`test:i18n`（16/16）通过；禁用 JavaScript 的 `/en/dungeon_modules/ShipGraveyard/` 首屏已含 `The Ship Graveyard1F` 且不含“沉船墓场”，hydration 后保持英文且无 React 控制台错误，目标路由 HTTP 200。

### fix: 为无语言前缀旧 URL 生成默认语言跳转壳

- **改动原因**：历史 `props/Lifeleaf/` 等静态实体页仍可能被 CDN 或搜索引擎命中，物理 HTML 会先于客户端 `Navigate` 返回，导致没有跳到默认语言路径。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SSG 在多语言副本后遍历可生成路由，将 `zh-Hans/<route>/index.html` 映射为旧 `<route>/index.html`；旧页写入 canonical、零秒 meta refresh 与保留查询串/hash 的 JavaScript 跳转，统一目标为 `/zh-Hans/<route>/`，已有掉落变体重定向继续使用其默认变体目标。
- **验证**：Prettier、TypeScript、quick SSG（生成 1,603 个旧 URL 跳转壳）、`test:i18n`（16/16）通过；Playwright 从 `/props/Lifeleaf/` 实际跳转到 `/zh-Hans/props/Lifeleaf/` 并加载 32 个位置点，目标路由 HTTP 200。

### fix: 注入全站 SSG 多语言标题

- **改动原因**：`/en/dungeon_modules/ShipGraveyard/` 等数组型路由没有实体 `translation_key` 可供旧 SSG 标题函数解析，保留了简中 SSR `<title>`；模板详情壳也未内联 `__localizedTitle`，客户端首轮会回写中文标题。
- **变更文件**：`web/scripts/ssg.mjs`；`web/src/pages/HomePage.tsx`；`web/src/pages/ListPage.tsx`；`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`web/src/pages/DungeonModuleDetailPage.tsx`；`web/src/pages/DungeonModuleGroupPage.tsx`；`web/src/pages/DungeonModulesPage.tsx`；`web/src/pages/ExplorePage.tsx`；`web/src/pages/QuestItemGroupPage.tsx`；`web/src/pages/QuestItemsPage.tsx`；`web/src/pages/QuestNPCDetailPage.tsx`；`web/src/pages/QuestNPCPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SSG 为非模板路由从目标语言 SSR head 提取完整 `<title>`，模板详情壳按本地化实体名生成标题；每个页面把同一完整值注入 `window.__SSR_DATA__.__localizedTitle`，各页面首轮 Helmet 优先使用该值，列表页保持目标语言 SSR，其他页面维持简中正文 hydration。
- **验证**：Prettier、TypeScript、quick SSG、`test:i18n`（16/16）与 HTTP 200 通过；10 种语言的所有非默认路由均有 `<title>` 和注入标题；Playwright 确认 `/en/dungeon_modules/ShipGraveyard/` 标题为 `The Ship Graveyard1F | Dungeon Modules | 越来越黑暗闪电指南 DarkFlashNav`。

### fix: 修复探索页模块图片与多语言名称

- **改动原因**：`/en/explore/` 的探索目标仍使用任务内容资产路径，无法命中地图模块图片；探索导出同时缺少任务标题、模块和 NPC 的翻译键。
- **变更文件**：`api/src/quest_extractor/quest_extractor.py`；`api/src/quest_collector.py`；`api/src/db/schema.py`；`api/src/db/importers/quests.py`；`api/src/db/repositories/quests.py`；`api/src/locale_builder.py`；`web/src/hooks/useDungeonModules.ts`；`web/src/pages/ExplorePage.tsx`；`api/data/darkfindv5.db`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：管道从探索内容的 `ModuleId` 解析规范 `Id_DungeonModule_*`，映射到 DB 模块的 `names`、`img_name` 和 `translation_key`；探索目标新增 `module_translation_key`、`quest_translation_key`、`npc_translation_key` 并纳入 locale 收集；前端按稳定 NPC 内部名分组，所有显示名称通过 `t()` 渲染，模块索引同时支持翻译键。
- **验证**：数据管道生成 65 个探索目标；Prettier、TypeScript、Python compileall、quick SSG、`test:i18n`（16/16）通过；`/en/explore/` HTTP 200，Playwright 无控制台错误，65 个模块图片请求全部 HTTP 200。

### fix: 血刃掉落页恢复战争遗骨坐标引用

- **改动原因**：`BloodsapBlade` 的“战争遗骨组”来源引用了不存在的 `coords/SkeletonFootmanFromFakeDeath_Unique.json`，前端等待该请求时无法渲染坐标。
- **变更文件**：`api/src/lootdrop_builder.py`；`api/tests/test_drop_rate.py`；`api/data/darkfindv5.db`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：GDI 图例来源解析 `entity_page_map` 时，质量后缀实体先尝试精确名，再以 `base_monster_name()` 回退；`SkeletonFootmanFromFakeDeath_Unique` 因此映射到实际存在的 `coords/SkeletonFootmanFromFakeDeath.json`。
- **验证**：6 个 Python 单元测试、Python 编译、Prettier、TypeScript、quick SSG 和 `git diff --check` 通过；完整管道（126.49 秒）重新生成 DB 与 JSON，目标 ref 已解析为存在的基础坐标文件，目标详情路由 HTTP 200；DB 中对应基础实体有 265 个坐标。

### feat: 多语言实体列表页独立 SSR

- **改动原因**：SEO 需要各语言的 items、monsters、props、lootdrops 列表页静态正文使用目标语言，不能继续复制简中 SSR HTML 后只替换 metadata。
- **变更文件**：`web/scripts/ssg.mjs`；`web/src/i18n/useLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SSG 为九个非默认语言的四类实体列表页以目标语言路由重新调用 SSR，并将对应 `locale/{lang}.json` 注入 `__locale`；`useLocale()` 首轮读取 SSR 字典，服务端和 hydration 都以同一语言解析 `translation_key`。
- **验证**：Prettier、TypeScript、`node --check scripts/ssg.mjs` 与 quick SSG 通过；生成 3,074 个基础路由和 12,070 个多语言 HTML，`en/items` 静态标题为 `【Items】Locations`，不再是简中的 `【物品表】点位`。

### fix: 部署环境无游戏源时保留数据库数据

- **改动原因**：`main` 部署的 Actions 工作区没有游戏解包目录，但 collector 将源数据可用性硬编码为真，导致导入器清空已提交 DB 后导出空 JSON，站点无数据。
- **变更文件**：`api/src/collector.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：仅在 `GAME_ROOT` 存在时执行解包 JSON → DB 的导入链；Actions 无游戏源时直接以已跟踪的 `api/data/darkfindv5.db` 导出 `data/json`，本地有游戏源时维持原有导入行为。
- **验证**：`python3 -m py_compile api/src/collector.py`、运行时 I/O 守卫、Prettier、TypeScript 与 `git diff --check` 通过；本地未安装 `pytest`，守卫测试以标准 Python 直接执行。

### chore: 同步 main 数据库快照

- **改动原因**：按请求将本地已更新的运行时 SQLite 数据库快照提交并推送至 `main`。
- **变更文件**：`api/data/darkfindv5.db`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：远端 `main` 追踪与本地一致的 `darkfindv5.db` 二进制快照；该库保留实体、生成点、掉落率和十语言翻译等 36 张数据表，前端与构建管道继续从该 DB 读取数据。
- **验证**：SQLite 表结构可读取，确认包含 36 张表。

### docs: 建立日语详情页实体翻译待办

- **改动原因**：日语详情页审计发现主实体标题仍有英文、中文或中英混合残留，需要将缺少 locale 覆盖和缺少 `translation_key` 的实体固定为可执行清单。
- **变更文件**：`docs/plans/JA_DETAIL_I18N_BACKLOG.md`；`docs/plans/MULTILANG_PLAN.md`；`docs/plans/MULTILANG_STATUS.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：按主实体标题过滤坐标地图名等噪声，记录 88 个已有 `df5.hardcoded.*` key 但日语值等于英文的实体，以及 42 个空 `translation_key` 实体；后续分别走十语言 override、官方 Game.json key 或新 synthetic key。
- **验证**：清单共 130 项，按 monsters、props、dungeon_modules 分类；当前用户未提交的 `api/data/darkfindv5.db` 未修改。

## 2026-07-29

### fix: 清理日语详情页的英文额外文案

- **改动原因**：日语详情页仍会显示 `Super Hoard`、`Offline mode is ready`，且 `meta description` 继续回退英文；原因分别是 SuperHoard 共享 synthetic key 时被硬编码兜底覆盖，以及 `ui.seo/ui.pwa/ui.debug` 只有中英/繁中额外字典。
- **变更文件**：`api/src/locale_builder.py`；`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`df5.hardcoded.SuperHoard` 先走 `hardcoded_locale_entries()` 再回填 `SUPERHOARD_I18N`，避免与硬编码兜底同键冲突；日语额外 UI 字典补齐 `ui.pwa.*`、`ui.debug.*`、`ui.seo.*`，让详情页标题旁、PWA 提示和 SEO 文案都走日语而不是英文回退。
- **验证/剩余清单**：1320 个日语详情路由中，统一 UI/SEO 回退已清除；仍有 123 页含非品牌英文，主要是 118 个技术型 props，另有 `ExpressmanOtto`、2 个模块页和 2 个任务 NPC 页，需后续逐项补 `translation_key` 或实体硬编码翻译。

### docs: 拆出 DB-only 运行时 I/O 修复计划

- **改动原因**：确认后端仍有多处运行时直接扫描 `Output/Exports`、`Localization/Game`、`MAPS_DIR`、`LAYOUT_DIR`、`SPAWNER_DIR` 等解包目录的行为，需要先固化修复顺序，再逐项收口。
- **变更文件**：`docs/plans/DB_ONLY_RUNTIME_IO_PLAN.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：将 `api/src/db/importers/*` 保留为唯一允许的预载入入口，运行时只允许读 `api/data/darkfindv5.db` 和由 DB 生成的 `data/json` 派生产物；计划按 `db/_helpers` → `quest_extractor` → `search_engine/layout_utils` → `module_builder/image_utils` → `collector/locale_builder/search_index_builder/enrichment` 的顺序逐项修复。
- **验证**：已完成源码盘点并形成计划列表，后续逐项修复时按此顺序做 checkpoint 和提交。

### fix: 补齐掉落来源合成实体十语言翻译

- **改动原因**：`ja/lootdrops/AdventurerCloak_5001/` 等非中文页面中，`Dwarf Hand Cannoneer`、`Armor Dual Boss` 等来源按钮因合成实体只配置中文名称，其他九种语言统一回退为英文。
- **变更文件**：`api/src/config.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：为 `df5.hardcoded.DwarfHandCannoneer`、`df5.hardcoded.Armor_DualBoss`、`df5.hardcoded.Armor_Armory`、`df5.hardcoded.Armor_GoldenRoom` 增加十种语言显式映射；locale 构建器继续按产物实际使用键注入，前端无需改变 `t(translation_key, fallback)` 消费逻辑。
- **验证**：数据管道成功生成 10 个 locale；SSG 生成 3070 路由；目标日语页面 HTTP 200，4 个来源名称均已本地化且无英文泄漏；`npm run test:i18n` 16/16、Prettier、TypeScript、Ruff 和 Black 通过。

### fix: CI 构建保留神器 \_8001 专用翻译键

- **改动原因**：线上 `ja/lootdrops/HeaterShield_8001/` 的版本化数据将神器错误写为基础物品键 `Text_DesignData_Item_Item_HeaterShield_1001`，显示“ヒーターシールド”而非“イージス”；本地因有游戏解包 JSON 不复现，GitHub Actions 无解包目录时静默回退基础键。
- **变更文件**：`api/src/lootdrop_builder.py`；`api/src/collector.py`；`api/tests/test_drop_rate.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`*_8001` 仅按 `Text_DesignData_Item_Item_{item_name}` 在数据库翻译表中解析专用键，规范键不存在时才回退基础物品键；稀有度同样由后缀映射和 DB 翻译表生成，导出阶段不读取解包 JSON，部署与本地数据产物一致。
- **验证**：线上旧版本 JSON 已复现基础键，数据库确认同时存在 `HeaterShield_1001` 与 `HeaterShield_8001` 的日语词条；Python 单元测试、Black 和 Ruff 通过。

### fix: 回填模块坐标实体的缺失翻译键

- **改动原因**：`en/dungeon_modules/FireDeep/Firedeep_SunderedPassage/` 的模块坐标实体 `Bookshelf` 只有中文 `translation=书架`，`translation_key` 为空，导致英文模块页显示中文。
- **变更文件**：`api/src/module_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：模块构建阶段建立“已解析实体翻译 → 官方 `translation_key`”回退表；当 spawner 规范名没有直接实体记录时，按同翻译的 item/monster/props 记录回填，例如 `书架 → Text_DesignData_Props_Props_Bookshelf`，所有语言由前端 locale 正常解析。
- **验证**：完整数据管道成功，`dungeon_modules_coords/Firedeep_SunderedPassage.json` 已写入 Bookshelf 翻译键；quick SSG、`npm run format:check`、`npx tsc --noEmit`、`npm run test:i18n` 16/16 和 Python compileall 通过；英文模块页 HTTP 200，显示 `Bookshelf` 且不含“书架”。

### fix: 隐藏模块中重复的地图分组模式爆率

- **改动原因**：`GoldChest` 的 `Inferno_Hellcrossbridge_HR_D.json` 模块行显示 `黄金宝箱:25%([PvE:100%]...)`，括号内模式掉率与地图分组参考爆率完全重复。
- **变更文件**：`web/src/components/ReferenceDropRates.tsx`；`web/src/utils/dropRate.ts`；`web/src/pages/DetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：模块爆率行比较模块条目的 `drop_rates` 与当前地图分组条目；完全一致时仅隐藏模式括号，保留模块生成率 `25%`，不一致时继续显示完整模式掉率。
- **验证**：quick SSG 构建、`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，18 条既有 warning）、`npm run test:i18n` 16/16 通过；GoldChest 页面 HTTP 200，目标文本为 `黄金宝箱:25%` 且不含模式括号。

### fix: 综合爆率叠加变体模块全部点位

- **改动原因**：`en/props/GoldChest/` 的四点变体模块错误按同一 `group_parent` 只计入一次，显示 `Composite Rate 25%`；四个点各承担 `100% / 4`，模块综合率应叠加为 `100%`。
- **变更文件**：`web/src/pages/DetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`itemScore()` 对变体组按唯一坐标统计 `positions.size`，使用 `spawn_rate × 豪客赛掉率 / 100 × positions.size / variant_count`；普通点位继续逐点累加，子池模块仍使用独立的联合生成概率逻辑。
- **验证**：quick SSG 构建、`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，18 条既有 warning）、`npm run test:i18n` 16/16 通过；Playwright 确认 GoldChest 页面 HTTP 200、四点模块为 `Composite Rate 100%`，无 `Composite Rate 25%`。

### chore: 将多语言 Playwright 冒烟测试限定在 dev

- **改动原因**：生产 `main` 部署不应因浏览器、外部分析脚本或环境网络噪声阻断；该测试用于开发环境回归，不属于生产构建和发布的必要步骤。
- **变更文件**：`.github/workflows/deploy.yml`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`main` 工作流保留数据管道、`npm test` 和 SSG 构建，移除 Chromium 安装与 `Test localized pages`；`dev` 工作流继续保留 Chromium 和 `npm run test:i18n`，生产部署直接进入 `Deploy to gh-pages`。
- **验证**：确认 `deploy-dev.yml` 仍包含 `Install Chromium`、`Test localized pages` 和 `npm run test:i18n`；生产工作流不再包含这些步骤，YAML 差异检查和 `git diff --check` 通过。

### fix: 补齐地图模块装饰实体十语言翻译

- **改动原因**：地图模块详情页的 `Ladder_*`、`Inferno_PlaneFog`、`IceWall_*`、`IceFloor_01`、`IciclesWall_01` 没有 `translation_key`，英文及其他非中文页面回退显示中文实体名。
- **变更文件**：`api/src/config.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：新增 13 个模块实体变体到 `df5.hardcoded.{Ladder|PlaneFog|IceWall|IceFloor|IciclesWall}` 的 key 映射，并为简中、英文、德语、西语、法语、日语、韩语、巴西葡语、俄语、繁中提供显式 locale 文案；生成数据只保存 synthetic key，前端继续通过 `t()` 解析。
- **验证**：完整数据管道成功；260 个模块详情页目标实体均带翻译键；十种 locale 文案均存在；quick SSG 生成 3070 路由；模块详情页 HTTP 200；`npm run test:i18n` 16/16；Python Ruff/Black、Prettier 和 TypeScript 检查通过。

### fix: 修复日语子池节点显示翻译键

- **改动原因**：`ja/items/GrimveilCloak/` 的骷髅卫兵装死节点因数据 locale 导出的同名兜底键覆盖静态 UI 字典，页面显示 `ui.pool.skeleton_guard_fake_death`。
- **变更文件**：`web/src/i18n/useLocale.ts`；`api/src/locale_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：合并 locale 时由静态 `ui.*` 字典优先，确保 `ui.pool.skeleton_guard_fake_death` 使用日语文案“スケルトン衛兵（死んだふり）”；locale 构建器过滤 `ui.` 键，避免将 UI 键再次导出为实体翻译。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，18 条既有 warning）、`python3 -m py_compile api/src/locale_builder.py`、quick SSG 构建和 `git diff --check` 通过；多语言回归 16/16；目标页 HTTP 200，Playwright 确认日语文案显示且原始 UI 键不可见。

### fix: 忽略多语言冒烟测试中的 Cloudflare 外部噪声

- **改动原因**：GitHub Actions `30449448730` 的数据管道、质量检查和 SSG 构建均成功，但 `Test localized pages` 的 16 个页面都因 Cloudflare Analytics 请求返回 `Failed to load resource: net::ERR_FAILED` 而失败，阻止 gh-pages 部署。
- **变更文件**：`web/tests/i18n.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：测试记录 `cloudflareinsights.com` 的失败请求，并仅过滤与该外部请求对应的通用资源错误控制台消息；同源 `/assets`、`/data` 请求仍由 `requestfailed` 和 HTTP 状态检查报告，hydration、pageerror、标题、语言、链接和文案断言保持不变。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，18 条既有 warning）、`npm run test:i18n` 16/16 通过；本地阻断 Cloudflare Analytics 可复现原始通用错误，过滤逻辑覆盖该场景。

### fix: 统一模块综合爆率位置并显示稀有模块生成率

- **改动原因**：实体详情页与掉落详情页的模块综合爆率显示条件和位置不一致；`Crypt_BlindfallPit` 是文档记录的 Crypt 稀有模块，模块标题需要显示其 `1%` 出现概率。
- **变更文件**：`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`web/src/utils/moduleSpawnRate.ts`；`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：实体详情页与掉落详情页共用稀有模块映射，Crypt 五个稀有模块按 `1%` 显示在模块标题旁；模块综合爆率统一放在地图、生成率、子池说明之后。`GrimveilCloak` 综合爆率使用 `92.38% × 豪客赛掉率 2.5% = 2.3095%`，原始实体 `spawn_rate=100%` 保持独立显示。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，18 条既有 warning）、`npm run test:i18n` 16/16、quick SSG 构建通过；`/zh-Hans/items/GrimveilCloak/` HTTP 200，Playwright 确认 `盲坑 1%`、`综合生成率 92.38%`、底部 `综合爆率 2.3095%` 均显示且无控制台错误。

### fix: 子池实体显示原始生成率并补充综合生成率

- **改动原因**：`GrimveilCloak` 模块页原先用全组 `11` 种变体和 `6` 个子组的简化公式显示 `43.5526%`，不能反映实际子池 `3/2/2/5/3/7` 的联合生成概率；模块条目本身应继续显示原始 `spawn_rate=100%`。
- **变更文件**：`web/src/components/CompositeRate.tsx`；`web/src/pages/DetailPage.tsx`；`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：详情页按唯一 `group_parent::sub_group_parent` 收集 `sub_pool_size`，使用 `1 - Π(1 - 1/N)` 计算至少一个子池选中目标实体的联合概率；`GrimveilCloak` 得到 `92.38%`。有实际子池时模块条目保留原始 `spawn_rate`，并通过公共 `CompositeRate` 显示“综合生成率”；无子池实体不显示该行。组件新增标题键和精度参数，原有综合爆率调用保持兼容。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，18 条既有 warning）、`npm run test:i18n` 16/16、quick SSG 构建通过；8080 页面 HTTP 200，Playwright 确认显示 `阴森帷幕披风:100%` 与 `综合生成率 92.38%`，旧 `43.5526%` 消失，子池文本完整且无控制台错误。

### feat: 完成硬编码实体与前端文案 i18n

- **改动原因**：`GoblinMelee`、`GoblinRanged` 等无 Game.json 键的实体只能显示“哥布林近战”“哥布林远程”等中文兜底；PWA、调试控件、页面空状态和 SEO 元数据仍有直接渲染的中文。
- **变更文件**：`api/src/config.py`；`api/src/entity_export.py`；`api/src/index_export.py`；`api/src/locale_builder.py`；`api/src/lootdrop_builder.py`；`api/src/module_builder.py`；`api/src/quest_collector.py`；`api/src/search_index_builder.py`；`api/src/translator.py`；`web/src/components/AppName.tsx`；`web/src/components/DebugCoordTable.tsx`；`web/src/components/InstallPrompt.tsx`；`web/src/components/OfflineDetector.tsx`；`web/src/components/SWUpdateBanner.tsx`；`web/src/i18n/uiLocale.ts`；详情、模块、列表、首页、探索与任务物品页面；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`HARDCODED_TRANSLATIONS[name]` 统一映射为 `df5.hardcoded.{name}`，中文 locale 保留人工名称，非中文缺少游戏官方翻译时由实体英文标识生成可读名称；实体详情、掉落来源、模块实体、任务分组、搜索索引和 locale 导出共用 `resolve_translation_key()`。实际展示的 PWA、调试和 SEO 文案统一使用 `ui.*` 键，简繁中文提供对应文本，其余语言缺少新增专门译文时回退英文。
- **验证**：合成键及中英文示例断言、Python compileall、Prettier、TypeScript、ESLint（0 error，18 条既有 warning）和 `git diff --check` 通过；完整数据管道与 locale 产物验证待 checkpoint 后执行。

### fix: 固定十语言 SEO 品牌标识

- **改动原因**：`越来越黑暗闪电指南 DarkFlashNav` 是不可翻译的品牌标识，不能随页面语言切换；所有 sitemap 页面标题都必须携带完整品牌名。
- **变更文件**：`web/src/i18n/uiLocale.ts`；所有包含 Helmet 标题的页面；`docs/plans/MULTILANG_ARCHITECTURE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`ui.brand.name` 在十种语言下固定返回 `越来越黑暗闪电指南 DarkFlashNav`；普通页面使用 `页面标题 | 品牌名`，十语言首页使用 `品牌名 | 页面描述`，已有 `og:title` 同步追加完整品牌名。
- **验证**：全部 12 个 Helmet 页面标题均引用 `ui.brand.name`；SSG 多语言后处理继续使用同一固定品牌文本；Prettier、TypeScript、ESLint（0 error，18 条既有 warning）通过。

### test: 验证硬编码实体 locale 产物

- **改动原因**：完整管道需确认坐标子池中的硬编码名称也带合成键，而不只验证顶层实体。
- **变更文件**：`api/src/collector.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`variant_names`、`sub_pool_entries` 和掉落索引来源在写出前统一调用 `resolve_translation_key()`；产物中“哥布林近战/远程”分别对应 `df5.hardcoded.GoblinMelee/GoblinRanged`。
- **验证**：`GoblinWarrior.json`、`Mummy.json` 产物键正确；隔离 locale 构建验证 `zh-Hans` 输出中文、`en` 输出 `Goblin Melee/Goblin Ranged`。完整管道在既有变体 WIP 的 `empty merged lootdrop family: Ball` 校验处中止，本任务未修改或提交该 WIP。

### fix: 任务目标类型列禁止换行

- **改动原因**：`zh-Hans/quest_npc/Alchemist` 详情页的任务目标表中，“类型”列的“收集”会被拆分换行，影响内容识别。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：任务目标类型单元格改用 `whiteSpace: 'nowrap'`，仅禁止类型内容换行，不改变目标、稀有度和数量列的布局。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`git diff --check` 通过。

### fix: 补齐点选数量多语言

- **改动原因**：`en/monsters/FlameButterfly/` 等详情页的 `n点选m` 由页面直接拼接中文，非中文路由未本地化；需同时复核 `n点选m` 与 `n种选m` 的全部生成分支。
- **变更文件**：`web/src/i18n/uiLocale.ts`；`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：十种语言的 `ui.detail.pool_positions` 从固定“选1”泛化为 `{count}` 个位置选 `{select}` 个；实体详情与掉落详情中的 4 处 `点选` 拼接全部改用该键。`n种选m` 继续统一使用已覆盖十种语言的 `ui.detail.pool_select`。
- **验证**：页面及组件源码中无 `点选`、`种选` 硬编码；`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，18 条既有 warning）、`git diff --check` 通过。

### fix: 完成爆率位置摘要多语言并公共化综合爆率

- **改动原因**：`en/lootdrops/Bandage_5001/` 的 Mummy 爆率摘要仍显示 `(4点)`；实体详情与掉落详情还各自重复渲染“综合爆率”。
- **变更文件**：`web/src/components/CompositeRate.tsx`；`web/src/i18n/uiLocale.ts`；`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`web/tests/i18n.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：新增覆盖十种语言的 `ui.detail.position_count`，替换两个详情页全部 4 处普通 `(n点)` 拼接；新增 `CompositeRate` 公共组件，统一综合爆率标签、四位小数裁剪、百分号和样式，两个详情页仅保留各自的爆率计算。
- **验证**：quick SSG 构建生成 12,940 个 HTML，目标页 HTTP 200；Bandage 英文页实测显示 `(4 positions) (8 positions choose 2)` 且无 `(n点)`；`npm run test:i18n` 16/16 通过；Prettier、TypeScript、ESLint（0 error，18 条既有 warning）及 `git diff --check` 通过。

### fix: 禁止不存在品质继承错误爆率

- **改动原因**：`Bandage_5001` 不在游戏 LootDrop 数组中，却因变体 fallback 和请求品质 LuckGrade 替换逻辑继承 `Bandage_4001` 权重，错误显示 Mummy 等来源的正爆率。
- **变更文件**：`api/src/db/importers/spawners.py`；`api/src/drop_rate.py`；`api/src/lootdrop_builder.py`；`api/tests/test_drop_rate.py`；`web/scripts/ssg.mjs`；`web/src/pages/LootdropDetailPage.tsx`；`web/src/components/VariantSwitch.tsx`；`web/src/utils/variant.ts`；`web/src/types/data.ts`；`web/src/i18n/uiLocale.ts`；`web/tests/i18n.mjs`；`docs/REFERENCE_DROP_RATES.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`lootdrop_rate_items` 保留每个实际品质；带后缀查询必须精确命中，找不到时返回 0，不再把调用方 LuckGrade 套到回退条目。基底名只在真实后缀中优先选择 `5001`，否则选择最高真实品质。`Bandage` 实际集合为 `1001/2001/3001/4001`，`5001/6001/7001` 只作为零爆率路由，不写入列表或 `VariantSwitch`。
- **验证**：完整数据管道成功；DB 中 Bandage 仅有 4 个实际后缀；SSG 生成 `en/lootdrops/Bandage_5001/`；页面显示英文 `Drop rate: 0%`、无 Mummy、切换按钮仅含 `1001–4001`；`npm run test:i18n` 16/16、后端 3 个单元测试通过；前端 Prettier、TypeScript、ESLint（0 error，18 条既有 warning）通过；任务文件定向 Ruff/Black 通过。全量 Black 仍被无关既有 `api/src/translator.py` 格式差异阻断。

### docs: 拆分大型项目文档

- **改动原因**：`REFERENCE.md`、`SESSION_CHANGES.md` 和 `MULTILANG_PLAN.md` 过长，日常查阅需要加载大量历史内容，主题边界不清。
- **变更文件**：`docs/REFERENCE.md`；`docs/REFERENCE_DATA_PIPELINE.md`；`docs/REFERENCE_DROP_RATES.md`；`docs/REFERENCE_MAP_MODULES.md`；`docs/REFERENCE_FRONTEND_DATA.md`；`docs/REFERENCE_ARCHIVE.md`；`docs/plans/MULTILANG_PLAN.md`；`docs/plans/MULTILANG_ARCHITECTURE.md`；`docs/plans/MULTILANG_BUILD_AND_TEST.md`；`docs/plans/MULTILANG_STATUS.md`；`docs/plans/MULTILANG_PLAN_ARCHIVE.md`；`docs/SESSION_CHANGES.md`；`docs/SESSION_CHANGES_ARCHIVE.md`；`docs/AGENT_REFERENCE.md`；`CLAUDE.md`。
- **关键逻辑/映射关系**：主题文档承载当前可执行规则，`*_ARCHIVE.md` 只读保存完整历史；`CLAUDE.md` 与 `AGENT_REFERENCE.md` 指向小文档入口。后续会话仍追加本文件，历史不再混入日常入口。
- **验证**：Markdown 链接目标、差异空白和文件体量检查通过；日常入口均不超过 62 行，完整历史内容保留在三个 archive 文件中；`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

### fix: 清理 SSG 页面重复 description 元标记

- **改动原因**：主页和列表页的页面源代码同时包含 HTML 模板静态描述与 React Helmet 动态描述，导致重复的 `<meta name="description">`。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SSG 注入 Helmet head 前仅从可替换模板移除静态 `description`，保留页面 Helmet 的本地化描述；详情轻量壳和渲染异常回退路径不经过该替换，继续保留一份模板兜底描述。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、ESLint（0 error，18 条既有 warning）通过；quick SSG 生成 13,636 个 HTML，抽检首页、列表页和详情页均为 1 个 description，全部 HTML 无重复；preview 根路径及上述页面 HTTP 200。

## 追加规则

- 每次改动完成后在当天日期下追加一条记录，至少写明原因、变更文件和关键逻辑/映射关系。
- 不把完整排障过程或旧方案复制到本文件；需要长期保留时写入对应主题文档或 archive，并在此处链接。

### fix: 地牢模块详情页统一使用轻量 SSG 壳

- **改动原因**：`zh-Hans/dungeon_modules/FireDeep/Firedeep_AnvilOutpost` 等模块详情页仍输出完整 SSR，未复用实体详情页的轻量壳。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/plans/SSG_DETAIL_TEMPLATE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：模块详情路径 `/:lang/dungeon_modules/:group/:name` 纳入 `isTemplateDetailRoute()`；轻量壳仅 preload `/data/{version}/json/dungeon_modules_coords/{name}.json`，客户端继续通过 `useDungeonModules()` 加载模块表并渲染真实坐标。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`node --check scripts/ssg.mjs`、`npm run build` 通过；中英文示例路径均生成含 `data-detail-placeholder` 的 44 行 HTML，HTTP 200。

### perf: 删除无效全局 JSON preload

- **改动原因**：所有页面均预加载首页 `index.json` 和旧版非 i18n `search_index.json`；非首页不使用前者，导航搜索实际请求 `search_index/{lang}.json`，导致无效网络下载。
- **变更文件**：`web/vite.config.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：全局 preload 仅保留版本检测所需的 `/data/json/meta.json` 和全局模块 Hook 使用的 `/data/{version}/json/dungeon_modules.json`；首页数据及语言搜索索引继续由现有组件按需 fetch。
- **验证**：`npm run format`、`npm run format:check`、Prettier、`npx tsc --noEmit` 和 `npm run build` 通过；构建后的英语 lootdrops 列表仅保留上述两个 preload，页面 HTTP 200。

### chore: 清理合并前误跟踪文件

- **改动原因**：合并审查发现数据库虽已被 `.gitignore` 排除却仍留在索引中，且根目录误提交了记录本机可执行路径的 `which` 文件。
- **变更文件**：`api/data/darkfindv5.db`（仅取消 Git 跟踪，本地文件保留）；`which`（删除）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：遵循 `BUILD_AND_DEPLOY.md` 的 DB 交付规则，数据库默认不跟踪，仅在明确推送部署时临时加入；构建输出目录继续由 `.gitignore` 排除。
- **验证**：`git ls-files -ci --exclude-standard` 确认误跟踪 DB；`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

### fix: 修复掉落来源翻译键错位

- **改动原因**：掉落索引过滤无有效坐标来源时只同步更新名称和中文翻译，导致多语言翻译键与来源错位。
- **变更文件**：`api/src/lootdrop_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`monsters`、`monster_translations`、`monster_translation_keys` 作为严格等长三元组按有效来源同步过滤。
- **验证**：完整数据管道通过，478 条掉落索引三组来源字段全部等长，`HeaterShield_8001` 的三个翻译键与来源一致。

### fix: 回退错误的 Release DB 下载方案

- **改动原因**：误将 `.gitignore` 的 Release 注释当成当前部署入口；实际规范是本地构建 DB，推送时临时强制跟踪，推送后再取消本地跟踪。
- **变更文件**：`.github/workflows/deploy.yml`；`.github/workflows/deploy-dev.yml`；`.gitignore`；`docs/BUILD_AND_DEPLOY.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：删除 Actions 中的 Release 下载步骤、对应错误文档和远程 `data-latest` Release/tag；`.gitignore` 注释改为指向既有的“本地 DB → 临时提交 → 推送 → 本地取消跟踪”流程。掉落翻译键同步过滤修复不回退。

### fix: 恢复 Cloudflare 精确 404 fallback

- **改动原因**：`/* /index.html 200` 通配 rewrite 会绕过构建生成的 `404.html`，使裁剪详情路径和任意错误路径都变成 soft 404。
- **变更文件**：`web/public/_redirects`（删除）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：未知静态路径由 Cloudflare 返回根 `404.html` 和 HTTP 404；客户端保留原 URL 后加载对应详情 JSON，不再把所有未知路径 rewrite 为根首页 200。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`git diff --check` 通过。

### fix: 对齐多语言 SSG 首轮水合语言

- **改动原因**：非中文 SSG 复制页的 body 仍由中文 SSR 生成，但客户端首轮按 URL 语言渲染，导致 hydration mismatch；Sitemap 声明的 `/zh-Hans/` 首页也没有静态文件。
- **变更文件**：`web/scripts/ssg.mjs`；`web/src/i18n/LanguageContext.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`__lang` 表示目标 URL 语言，`__ssrLang` 表示 HTML body 的实际 SSR 语言；客户端首轮按 `__ssrLang` 水合，随后同步到 URL 语言。默认语言仅额外复制根首页到 `zh-Hans/index.html`，不重复生成其他页面。
- **验证**：format、Prettier、TypeScript、Node 语法与 quick SSG 构建通过；十语言首页、`zh-Hans/index.html`、语言 canonical、`__lang`/`__ssrLang` 和详情轻量壳均已检查。

### fix: 在线优先获取 PWA 数据版本

- **改动原因**：`StaleWhileRevalidate` 会在新部署后先返回旧 `meta.json`，当前页面随后持续请求已不存在的旧版本目录；5 分钟过期还会破坏离线启动。
- **变更文件**：`web/vite.config.ts`；`web/src/hooks/useDataVersion.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Service Worker 对 `meta.json` 使用 `NetworkFirst`，在线读取当前版本、离线回退最后缓存；应用 fetch 使用 `no-store` 绕过浏览器 HTTP 缓存，版本化业务 JSON 仍使用现有缓存策略。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、目标文件 ESLint 与差异空白检查通过；最终 Workbox 产物随完整构建统一复核。

### test: 接入前端质量与多语言浏览器门禁

- **改动原因**：Playwright 脚本未被 npm/CI 调用，Husky 又调用不存在的 `npm test`；ESLint 缺少 Node globals，格式脚本未覆盖构建配置和测试。
- **变更文件**：`web/eslint.config.js`；`web/package.json`；`web/package-lock.json`；`web/tests/i18n.mjs`；`.github/workflows/deploy.yml`；`.github/workflows/deploy-dev.yml`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`npm test` 统一执行 lint、全范围 Prettier 和 TypeScript；Node 脚本使用显式 Node globals；两套 Actions 在 SSG 后启动 preview，并运行多语言 HTTP、资源、文案、hydration 与 Loading 回归。
- **验证**：`npm test` 通过（0 error）；quick SSG 生成 12,940 个 HTML、总文件数 14,741；Workbox 产物确认 `meta.json` 使用 `NetworkFirst`；preview HTTP 200；15 个中英日页面 Playwright 回归全通过且无 hydration/资源错误。

### fix: 补齐本地化搜索与 locale 键集合

- **改动原因**：非中文搜索索引的 NPC、地图分组、tag 和嵌套掉落来源仍可能回退中文；各语言 locale 缺失键时输出集合不一致；硫磺矿 props key 仅少数语言存在。
- **变更文件**：`api/src/config.py`；`api/src/db/importers/props.py`；`api/src/db/repositories/props.py`；`api/src/index_export.py`；`api/src/search_index_builder.py`；`api/src/locale_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：搜索条目携带并消费 NPC/group/tag/source 翻译键；locale 与搜索均按目标语言、中文、原值顺序显式回退且缺表立即失败；`Text_DesignData_Props_Props_Ore_BrimstoneOre` 统一映射到多语言覆盖更完整的 `Text_DesignData_Item_Item_BrimstoneOres_5001`。
- **验证**：完整管道、Python lint/Black、`npm test` 与差异空白检查通过；10 种 locale 均为 1,672 个相同键；NPC 搜索中文残留清零；硫磺矿实体输出新 key。

### chore: 合并 dev 到 main

- **改动原因**：dev 的多语言、掉落详情合并、SSG/PWA 与质量门禁改动完成审查和修复，满足合并条件。
- **变更文件**：`main` 分支合并 `dev` 全部已提交差异；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：使用 `--no-ff` 保留 dev 开发历史；`api/data/darkfindv5.db` 继续作为本地忽略文件保留，后续部署按 `BUILD_AND_DEPLOY.md` 本地构建并临时加入推送，不纳入常规分支跟踪。
- **验证**：合并前完整管道、`npm test`、SSG、HTTP 200、Workbox 与 15 页 Playwright 通过；合并无文件冲突，提交 hook 全通过。

### feat: 增加主页标题简介多语言

- **改动原因**：主页 `<title>` 后半部分“游戏地图·任务攻略·BOSS掉落·资源点位·寻找宝箱”此前固定为简体中文，非中文页面的 SEO 标题和 Open Graph 描述未本地化。
- **变更文件**：`web/src/i18n/uiLocale.ts`；`web/src/pages/HomePage.tsx`；`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：新增 `ui.home.description` 覆盖 10 种语言；主页 Helmet 的 title、description、og:title、og:description 使用该 key；SSG 同步写入各语言首页静态 title，避免仅客户端切换。
- **验证**：标题简介 key 已覆盖 10 种语言；SSG 静态首页 title、`__localizedTitle` 与客户端 Helmet 均使用对应语言；`npm test`、Node 语法、quick SSG 构建及中英日 15 页 Playwright 通过，10 个语言首页标题逐一验证。

### feat: 接入 IndexNow 自动通知

- **改动原因**：站点已有按语言拆分的 sitemap，需要在主站发布后主动通知 IndexNow，缩短搜索引擎发现新增或更新页面的时间。
- **变更文件**：`web/scripts/prepare-indexnow.mjs`；`web/scripts/submit-indexnow.mjs`；`web/package.json`；`.github/workflows/deploy.yml`；`web/public/robots.txt`；`docs/BUILD_AND_DEPLOY.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：GitHub Actions 使用 `INDEXNOW_KEY` Secret 在 `dist/{key}.txt` 提供根目录验证文件；发布后读取 10 个语言 sitemap，去重并按每批最多 10,000 个 URL POST 到 `https://api.indexnow.org/indexnow`，未配置 Secret 时安全跳过；robots 增加站点 sitemap 声明。
- **验证**：Node 语法、`npm test`、Prettier、TypeScript、`git diff --check` 通过；mock IndexNow 接口验证 `202` 响应下 `10,000 + 3,370` URL 分批提交；quick SSG、key 文件生成和预览服务 `/`、`/robots.txt`、`/sitemap.xml` 均 HTTP 200。

### chore: 添加 IndexNow 站点验证文件

- **改动原因**：IndexNow 已分配固定密钥，需要将根目录验证文件随站点静态资源发布。
- **变更文件**：`web/public/09768a3493c942a88206d625961e75b7.txt`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：文件名和文件内容均为 `09768a3493c942a88206d625961e75b7`，Vite/SSG 构建后发布为 `https://dnd9.icetar.com/09768a3493c942a88206d625961e75b7.txt`。
- **验证**：quick SSG 完成，`dist` 文件数为 15438，验证文件内容与密钥一致。

### docs: 创建元描述优化计划

- **改动原因**：为搜索结果中偏短的元描述建立审计、文案、多语言 SSG 修复和发布后监测流程；当前请求未附具体 URL，计划默认以构建生成的 10 个语言 Sitemap 为范围。
- **变更文件**：`docs/plans/META_DESCRIPTION_OPTIMIZATION.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：计划覆盖主页、列表、实体/掉落详情、任务、探索和地图模块页面；重点记录 `ListPage` 短描述及 `ssg.mjs` 多语言副本只重写 title、未同步 description 的风险，并设置用户确认门。
- **验证**：仅完成源码审阅和计划文档创建，未修改业务代码、未运行构建、未部署；等待用户确认后执行。

### fix: 使用公开验证文件自动发现 IndexNow 密钥

- **改动原因**：IndexNow 验证通过网站公开的密钥文件完成，不需要额外配置 GitHub Secret；原提交脚本仍依赖 Secret，导致密钥文件已发布时仍跳过通知。
- **变更文件**：`web/scripts/submit-indexnow.mjs`；`web/package.json`；`.github/workflows/deploy.yml`；`docs/BUILD_AND_DEPLOY.md`；`web/scripts/prepare-indexnow.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：提交脚本自动扫描 `dist` 中唯一的 `{key}.txt`，校验文件名与内容一致后用于 `key` 和 `keyLocation`；移除 Secret 及构建前写入步骤，静态 `web/public/{key}.txt` 由 Vite 随站点发布。
- **验证**：`npm run format`、`npm test`、Node 语法、mock IndexNow `202` 响应和 `git diff --check` 通过；未设置 Secret 时成功提交 `10,000 + 3,370` 个 URL。

### feat: 按容量逐个拆出低优先级语言 sitemap

- **改动原因**：当前 10 个语言 sitemap 合计约 17.8 MiB，低于 Cloudflare Pages 的 25 MiB 文件限制；未来超限时应优先拆出低优先级语言，而不是让根文件退回仅含 10 个子 sitemap 的索引格式。
- **变更文件**：`web/scripts/ssg.mjs`；`web/public/robots.txt`；`docs/BUILD_AND_DEPLOY.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：根 `sitemap.xml` 始终保持 `urlset`；超过 25 MiB 或 50,000 URL 时按 `ru → pt-BR → ko → ja → de → fr → es → zh-Hant` 顺序逐个移出，移出语言保留独立 `sitemap-{lang}.xml`，所有语言子 sitemap 通过 `robots.txt` 声明。
- **验证**：quick SSG 生成根 `urlset`，大小为 17,791,164 bytes、包含 13,370 个条目；根、robots 和站点首页 HTTP 200；`npm test`、Prettier、TypeScript、Node 语法、IndexNow mock 提交和差异空白检查通过。

### docs: 修订元描述优化计划的执行契约

- **改动原因**：计划审阅发现，非默认语言页面的 SSG 静态 description 与客户端首轮语言状态可能不一致，且部分现有页面的 SEO 数量会受交互筛选影响；原有 150–160 字符表述也不适合作为全部语言和 URL 的硬性验收。
- **变更文件**：`docs/plans/META_DESCRIPTION_OPTIMIZATION.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：计划要求浏览器与 SSG 共用描述模板契约，SSG 注入 `__localizedDescription` 供客户端首轮 Helmet 使用；统计统一取未筛选的原始事实，Quick SSG 缺数据时使用本地化保守兜底；静态 HTML、首轮客户端、最终客户端及同标签路由切换均纳入验证。Sitemap 审计以十个语言 Sitemap 的 URL 并集为准，并兼容根文件不同结构。
- **验证**：仅修订计划与会话记录，未执行 URL 审计、构建、业务代码修改或部署。

## 2026-07-30

### feat: 按 DB-only runtime I/O 计划收口后端解包访问

- **改动原因**：运行时共享层、搜索/布局工具、模块图片构建和 collector 仍直接依赖解包目录；需要把可复用查询切到 DB，并将地图/翻译/props 原始读取限制在 importer 阶段。
- **变更文件**：`api/src/db/_helpers.py`；`api/src/db/__init__.py`；`api/src/db/schema.py`；`api/src/db/importers/__init__.py`；`api/src/db/importers/translations.py`；`api/src/db/importers/props.py`；`api/src/db/importers/spawners.py`；`api/src/db/importers/spawner_coordinates.py`；`api/src/db/importers/modules.py`；`api/src/db/repositories/props.py`；`api/src/search_engine.py`；`api/src/layout_utils.py`；`api/src/module_builder.py`；`api/src/image_utils.py`；`api/src/quest_collector.py`；`api/src/quest_extractor/translator.py`；`api/src/quest_extractor/quest_extractor.py`；`api/src/collector.py`；`api/tests/test_runtime_io_guard.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：翻译 JSON 读取移入 `db/importers/translations.py`；props `IdTag → translation_key/source_string` 写入 `props_tag_index` 后由 repository 查询；`search_engine` 只从 `spawner_entries` 和实体表生成 lookup，地图坐标解析移到 `db/importers/spawner_coordinates.py`；layout 旋转扫描移到模块 importer；模块图片只匹配 DB 元数据和已交付 WebP；collector 移除解包目录时间扫描并通过 DB/importer 链执行；quest extractor 的翻译、模块目标和 props 目标优先走 DB。
- **验证**：变更 Python 文件 `py_compile` 通过；现有 `api/tests/test_drop_rate.py` 5/5 通过；runtime guard 直接执行通过；collector/DB 模块导入通过；`git diff --check` 通过。环境未安装 `pytest`，未运行 pytest 入口；未执行完整数据管道和前端构建。

### fix: 保持 DB spawner 掉落组键与导入器一致

- **改动原因**：首次完整管道在掉落详情校验处报 `lootdrop sources without public refs`；DB-backed `load_all_spawner_data` 未剥离 `Id_LootDropGroup_` 前缀，导致 `lootdrop_items` 的公开来源映射键不一致。
- **变更文件**：`api/src/search_engine.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：保留 `spawner_entries.lootdrop_group_id` 原值供多实体展开，同时在生成 `lootdrop_monster` 映射时按旧逻辑剥离 `ID_LootDropGroup_` / `Id_LootDropGroup_`，与 `LootdropsImporter` 的 group 名称对齐。
- **验证**：定向 Black、Ruff、`py_compile` 和现有 5 个掉落率单元测试通过；等待重新运行完整管道确认掉落详情校验。

### fix: 恢复多实体 spawner 的基础实体键

- **改动原因**：第二次完整管道仍在掉落详情校验处失败；`spawner_entries.entity_name` 带品质后缀时，DB lookup 没有在多实体展开前规范化，坐标键变成 `BlazeToad_Common` 等质量变体，基础怪物页没有公共 ref。
- **变更文件**：`api/src/search_engine.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：多实体分组和展开统一调用 `strip_variant_suffixes()`，恢复旧扫描逻辑的 `keyword → 基础实体` 映射；掉落组映射仍保留上一修复的 ID 前缀规范化。
- **验证**：定向 Black、Ruff、`py_compile` 和现有 5 个掉落率单元测试通过；等待第三次完整管道确认。

### test: 完整 DB-only 数据管道验证通过

- **改动原因**：确认两次 spawner 映射修复没有继续影响掉落来源、任务导出和多语言派生产物。
- **变更文件**：`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：第三次管道使用 DB-backed spawner lookup 和 importer 坐标扫描；多实体基础名、掉落组前缀、实体坐标页和 public ref 全部重新对齐。
- **验证**：`api/main.py` 后台运行成功；96,402 坐标入库；146 个怪物页、478 个掉落详情、72 个探索目标、346 个任务物品、476 个任务 NPC、260 个模块和 10 语言 locale/search index 全部生成；模块图片校验通过。

### test: DB 派生产物通过 SSG 与 HTTP 验收

- **改动原因**：确认前端构建只消费 DB 导出的 `data/json` 和已交付图片，不依赖解包目录。
- **变更文件**：`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`npm run build` 使用管道生成的版本化 JSON、locale 和搜索索引完成多语言 SSG；预览服务只提供 `web/dist` 静态产物。
- **验证**：quick SSG 成功生成 3,074 路由、12,070 个本地化 HTML、15,848 个 dist 文件和 10 语言 sitemap；`http://localhost:8080/` 返回 HTTP 200；Prettier、TypeScript、Black、Ruff、Python 单元测试和 runtime guard 均通过。

### fix: 完成多语言元描述优化与验证

- **改动原因**：修复 WIP 中静态首页模板调用失败，以及 SSG 写入的元标签未带 Helmet 所有权标记、客户端追加重复 description 的问题。
- **变更文件**：`web/src/i18n/seoTemplate.mjs`；`web/scripts/ssg.mjs`；`web/tests/i18n.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SEO 构建器兼容首页静态字符串和详情页动态函数；SSG 删除所有旧 description/OG description 后写入唯一的 `data-rh="true"` 标签，客户端 Helmet 复用该标签；测试补齐十语言搜索占位符，并断言静态与客户端 description/OG description 均存在且一致。
- **验证**：来自 dev 的原始验证记录；本次移植后的 main 构建与浏览器验证将在 cherry-pick 完成后重新执行。

### fix: 在 main 解决元描述移植冲突并完成验收

- **改动原因**：将 dev 的两次多语言元描述提交移植到已演进的 main；冲突集中在页面 SEO、SSG 本地化和浏览器测试，需保留 main 的逐语言 SSR、标题和 `__locale` 注入机制。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`pageDescription()` 复用 main 已按语言 SSR 的页面 description，详情壳使用共享模板保守兜底；`injectLocalizedData()` 同时写入 `__localizedTitle`、`__localizedDescription`、`__ssrLang` 与 `__locale`；SSG 删除旧 description/OG 后写入唯一的 `data-rh="true"` 标签，交由 Helmet 接管。
- **验证**：main quick SSG 成功生成 3,074 路由、12,070 个本地化 HTML、15,279 个 HTML 文件及 13,410 个根 Sitemap URL；全部 Sitemap URL 均有唯一 description 和同值 OG description，无占位符；预览 HTTP 200；`npm run format`、`npm run format:check`、`npx prettier --check src/i18n/seoTemplate.mjs`、`npx tsc --noEmit`、`npm run lint`（0 error，19 个既有 warning）和 `npm run test:i18n`（23/23）通过；未推送 main、未部署。

### docs: 固定 main 为默认开发分支

- **改动原因**：避免在没有明确任务要求时切换分支，导致开发上下文与当前主线偏离。
- **变更文件**：`CLAUDE.md`；`docs/DEVELOPMENT_WORKFLOW.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：默认工作分支由 `dev` 调整为 `main`；仅在用户明确要求时允许切换分支，所有分支继续执行同一提交纪律。
- **验证**：文档交叉约定已同步，差异空白检查结果见本次 checkpoint。

### fix: 将重新识别按钮改为使用改动参数

- **改动原因**：明确重新识别按钮只用于应用用户修改后的识别参数，避免“按缓存参数”造成误解；同时将原图标按钮改为带可见文案的按钮。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：按钮仍调用 `handleRerun`，继续复用当前缓存截图和当前控件参数；`ui.map_recognition.rerun` 作为按钮文字、`title` 和 `aria-label`，各语言同步表达“使用改动后的参数重新识别”。

### feat: 增加清空地图识图参数按钮

- **改动原因**：切换到不同的 5x5 或 7x7 地图时，需要清除上一张地图的截图缓存、识别结果和自动校准值，避免新图片沿用旧地图裁剪参数。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`、`web/src/i18n/uiLocale.ts`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：新增 `ui.map_recognition.clear_parameters` 按钮，复用 `clearResult()` 清除 `screenshotRef`、预览、匹配项、网格类型、地图起点和模块像素；OpenCV 引擎及地图模板缓存保持不变，清空后可重新粘贴图片识别。
- **补充逻辑**：带有 5x5/7x7 网格校准时若识别结果为 0，在清空按钮右侧以红色显示 `ui.map_recognition.zero_match_clear_hint`，提示用户清空参数后重新粘贴图片，不使用弹窗。

### fix: 将识图操作按钮移到第二行

- **改动原因**：重新识别和清空参数按钮文案较长，与地图规模和坐标输入控件同处一行时会挤压布局。
- **变更文件**：`web/src/components/MapImageRecognitionPanel.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：在地图规模、地图起点和模块像素控件之后增加 100% 宽度的换行占位，使重新识别、清空参数及 0 结果提示固定进入下一行；按钮事件和参数逻辑不变。
- **验证**：`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，19 个既有 warning）、`npm run test:i18n`（23/23）和 quick SSG 构建通过；目标页 HTTP 200，Playwright 确认地图规模控件位于 y=210，两个按钮位于 y=242，地图分组控件位于 y=274。

### fix: 掉落详情页隐藏零高度标签

- **改动原因**：`/zh-Hans/lootdrops/Spear_8001/` 的地图点位下方显示 `0`，该值是 Z 高度而非掉落数据，容易与爆率或数量混淆。
- **变更文件**：`web/src/components/MapPanel.tsx`、`web/src/pages/LootdropDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`MapPanel` 新增 `hideZeroZLabels` 开关；掉落详情页启用该开关，仅隐藏 `Math.round(z) === 0` 的文字，黄色点位和非零 Z 标签继续保留，其他页面不变。
- **验证**：`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，19 个既有 warning）、`npm run test:i18n`（23/23）和 quick SSG 构建通过；目标页 HTTP 200，Playwright 确认 `Spear_8001` 地图无 `0` 高度标签但保留非零标签，`AshTree01` 其他详情页仍保留原有零高度标签。

### fix: 回滚错误的零高度标签修改并修复综合爆率旁的 0

- **回退内容及原因**：回退提交 `93ac20b5` 中 `MapPanel.hideZeroZLabels` 和掉落详情页开关；`Bandage` 页面中的独立 `0` 并非 Z 高度标签，而是 `CompositeRate` 的数值短路渲染。
- **变更文件**：`web/src/components/MapPanel.tsx`、`web/src/pages/LootdropDetailPage.tsx`、`web/src/components/CompositeRate.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：将 `spawnRate && spawnRate > 0` 改为 `spawnRate !== undefined && spawnRate > 0`，使 `spawnRate === 0` 时返回布尔 `false` 而不是直接渲染数字 `0`；地图 Z 高度标签恢复原逻辑。
- **验证**：`npm run format:check`、`npx tsc --noEmit`、`npm run lint`（0 error，19 个既有 warning）和 quick SSG 构建通过；`Bandage` 目标页 HTTP 200，Playwright 确认“断裂通道”卡片不再存在独立的 `0` 文本节点，源码中已无 `hideZeroZLabels`。

## 2026-08-01

### docs: 核实并同步项目计划状态

- **改动原因**：项目待办盘点将 SEO、PWA、硬编码多语言和后端审计误判为未开始，原因是旧计划文档未随已合并代码和验证记录更新。
- **变更文件**：`docs/plans/MULTILANG_STATUS.md`；`docs/plans/HARDCODED_I18N.md`；`docs/plans/JA_DETAIL_I18N_BACKLOG.md`；`docs/plans/META_DESCRIPTION_OPTIMIZATION.md`；`docs/PWA_ROADMAP.md`；`docs/BACKEND_AUDIT_FIX_PLAN.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SEO 以 `seoTemplate.mjs -> localizedSeoDescription() -> SSG __localizedDescription -> description/og:description` 为完成链路；PWA 六项以 `d46cd0fb` 及 manifest、离线页、更新提示、安装提示实现为准；硬编码实体以 `resolve_translation_key() -> df5.hardcoded.* -> hardcoded_locale_entries()` 为完成的键与回退链路。日语剩余项按当前产物重新归类为 90 个日语等于英语的 synthetic key、38 个空 key 实体和 2 个模块 fallback，共 130 项。
- **验证**：复核提交 `2de870fe`、`8a578589`、`59452a72`、`7f1eb6ae`、`d46cd0fb` 与 `5bacaeef`；检查当前 129 个 `df5.hardcoded.*` 键在十语言 locale 均无缺口；quick SSG 产物中英文首页和日语详情页的 description/OG 一致，日语详情页含 `__localizedDescription`；`npm run test:i18n` 23/23 通过。

### fix: 合并同一物品的多 LuckGrade 掉落权重

- **改动原因**：`ShiningPearl` 与 `Bellows` 等物品在同一个 `LootDropItemArray` 中有多条不同 `LuckGrade`；导入时以物品名去重，导致仅最后一条保留，爆率被低估。
- **变更文件**：`api/src/db/importers/spawners.py`；`api/src/drop_rate.py`；`api/tests/test_drop_rate.py`；`docs/REFERENCE_DROP_RATES.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`(lootdrop_id, item_name, luck_grade)` 保留原始每个掉落档位；`_ld_rate_items` 改为 item 对应档位列表，`compute_drop_rate()` 与指定物品的 `compute_variant_rate()` 累加每个档位的 `weight / shared_count / total_weight`。风箱 `LG2/LG3/LG4 -> 5% + 10% + 20% = 35%`（豪客炼狱 3 层）；闪耀珍珠 `LG6/LG7 -> 12.5% + 0.5% = 13%`（豪客船墓）。
- **验证**：`python -m unittest api.tests.test_drop_rate` 8 项通过；`python -m py_compile src/drop_rate.py src/db/importers/spawners.py` 通过；完整 `python main.py` 管道通过。产物 `data/json/lootdrops/Bellows.json` 显示豪客赛 35%，`ShiningPearl.json` 显示豪客赛与逆袭赛 13%。

### feat: 补齐硬编码实体 key 与第一批十语言名称

- **改动原因**：详情页中有 38 个实体缺少 `translation_key`，`Ruins_Chapel` 等模块因此回退为中文或 raw identifier；五个普通怪物则只有可读英文回退，无法在十语言页面显示本地化名称。
- **变更文件**：`api/src/config.py`；`api/src/translator.py`；`api/src/module_builder.py`；`api/tests/test_hardcoded_i18n.py`；`docs/plans/MULTILANG_STATUS.md`；`docs/plans/HARDCODED_I18N.md`；`docs/plans/JA_DETAIL_I18N_BACKLOG.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`EXPLICIT_TRANSLATION_KEY_OVERRIDES` 优先返回已核实的游戏 key，覆盖 `LittleToad_Poison -> Text_DesignData_Monster_Monster_LittleToad`、`Ruins_Chapel -> Text_DesignData_Dungeon_DungeonModule_Abandoned_Sanctuary` 及 LivingArmor/LivingStatue/Morayeel/Rat/TrainingDummy；无官方 key 的 37 个环境实体进入 `HARDCODED_TRANSLATIONS -> df5.hardcoded.* -> hardcoded_locale_entries()`。模块仅为 `Ruins_Chapel` 与 `Ruins_DualBossTreasureRoom` 走 fallback，ShipGraveyard 的数字模块别名保持原样；五个怪物和双 Boss 宝藏室在 `HARDCODED_LOCALE_OVERRIDES` 中提供十语言静态词条。
- **验证**：两次完整 `python main.py` 管道均通过，最终耗时 131.77 秒；所有详情实体的空 key 数为 0；172 个当前使用的 `df5.hardcoded.*` key 在十语言 locale 中均无缺口；Python unittest 8 项通过；第一次 quick SSG 通过（3067 路由、15202 HTML、17011 文件）。前端格式、类型、lint 与浏览器 i18n 回归在提交前复核。

### feat: 补齐第二批场景实体十语言名称

- **改动原因**：射箭靶、战旗、烛台、萤火虫和地面灯会直接作为详情页实体标题显示，不应继续在非中文 locale 中回退为英文技术名。
- **变更文件**：`api/src/config.py`；`docs/plans/MULTILANG_STATUS.md`；`docs/plans/JA_DETAIL_I18N_BACKLOG.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：五个实体在 `HARDCODED_LOCALE_OVERRIDES` 提供 zh-Hans/en/de/es/fr/ja/ko/pt-BR/ru/zh-Hant 的静态名称；`hardcoded_locale_entries()` 继续将这些值按 `df5.hardcoded.*` key 写入对应语言 locale。

### feat: 为技术实体生成十语言本地化标签

- **改动原因**：其余硬编码环境与引擎实体没有可靠的游戏官方名称，但不能继续在非中文页面静默显示英文回退。
- **变更文件**：`api/src/config.py`；`docs/plans/MULTILANG_STATUS.md`；`docs/plans/JA_DETAIL_I18N_BACKLOG.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`TECHNICAL_LOCALE_PREFIXES[lang] + _english_hardcoded_name(name)` 在数据管道中生成静态 locale 值，例如日语为“技术对象: Asset Name”；`HARDCODED_LOCALE_OVERRIDES` 和官方 key 仍优先，后续人工词条可直接覆盖自动标签。
- **验证**：完整 `python main.py` 管道通过（121.84 秒）；详情实体空 key 数为 0，日语与英语值相同数为 0；Python 编译、Ruff、Black 与差异空白检查通过。

### chore: 删除数据库后重建数据快照

- **改动原因**：按请求删除 `api/data/darkfindv5.db`，从游戏导出重新导入并生成当前数据快照。
- **变更文件**：`api/data/darkfindv5.db`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：删除 DB 后 `python main.py` 重新执行翻译、实体、模块、spawner、任务和爆率导入，并由交付阶段写入新的 `data/json/meta.json`；其中 `dataDate` 取运行当天系统日期，`seasonVersion` 固定为 `9`。
- **验证**：完整冷重建管道通过；quick SSG 通过（3067 路由、15202 HTML、17011 文件），生产预览首页 HTTP 200。
