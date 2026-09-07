# 会话修改记录归档

以下 2026-07-29 至 2026-08-17 的记录从 `docs/SESSION_CHANGES.md` 移出，按原日期分区保留。

## 2026-08-17

### feat: 为无语言前缀 URL 生成 Cloudflare Pages 301 重定向（_redirects）

- **改动原因**：无语言 URL（如 `/props`、`/props/LavaMushroom`、`/`）此前仅返回 HTTP 200 的 meta-refresh 客户端跳转页（step 5c），不是真 301；根路径 `/` 直接服务首页。需要在 Cloudflare Pages 上用 `_redirects` 提供真正的 301。网站地图（本地与线上）经验证已无无语言 URL，无需改动 sitemap 生成逻辑。
- **变更文件**：`web/scripts/ssg.mjs`（新增 step 5d，生成 `web/dist/_redirects`，共 543 条规则）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`_redirects` 规则 = 根规则 `/ /zh-Hans/ 301` → 多变体 lootdrop 基底精确规则（对每个带 `r.redirect` 的路由生成带/不带尾斜杠两条，直达默认变体如 `/zh-Hans/lootdrops/GoldBangle1I_5001/`）→ 8 个 section（`items`/`monsters`/`props`/`lootdrops`/`explore`/`quest_items`/`quest_npc`/`dungeon_modules`）各一条静态规则 `/${section} /zh-Hans/${section}/ 301` 加一条通配 `/${section}/* /zh-Hans/${section}/:splat 301`。具体规则在前、通配在后，首条命中生效；总条数 543，低于 CF Pages 的 2000 静态 + 100 动态上限。CF Pages 在静态文件之前解析 `_redirects`，因此非语言 URL 返回真 301，本地 `vite preview` 不处理 `_redirects`，仍由 step 5c 的静态页兜底。
- **验证**：`npx prettier --write scripts/ssg.mjs`、`node --check scripts/ssg.mjs` 通过；`npm run build` 成功（`_redirects generated: 543 rules`，sitemap 13400 URLs）；`dist/sitemap.xml` 无语言 `<loc>` 数量为 0 且不含裸根 URL；`npm test`（lint 0 errors / 20 既有 warnings、format:check、tsc --noEmit）通过；preview HTTP 200。注意：构建需用 Node 20（`~/.nvm/versions/node/v20.20.0/bin`），Node 22 的 `globalThis.navigator` getter-only 会导致 SSR bundle 报错。

## 2026-08-17

### chore: 删除错误的 ShipGraveyard_FloatingIsland 地图图片

- **改动原因**：`ShipGraveyard_FloatingIsland` 未出现在两个 7x7 Layout（`ShipGraveyard_7x7_01_HR_P`/`7x7_02_N_P`）的 95 个 LevelStreaming 条目中，是未被 7x7 布局实例化的模块，其地图图片内容错误，前端不应再展示。
- **变更文件**：删除 `api/src/img/ShipGraveyard_FloatingIsland.webp`（git 跟踪源文件）；同步清理交付目录副本 `data/img/ShipGraveyard_FloatingIsland.webp`（data/ 为可再生交付目录，不入 git）。
- **关键逻辑/映射关系**：删除源文件后，下次管道 `_deliver` 不再复制该图；`module_builder.py:_resolve_img` 匹配不到 → `has_img=false` → 回退 `RareModule_1x1` 占位图；`main.py:_validate_images` 兜底将缺失 img_name 替换为占位图。
- **验证**：`git ls-files` 确认源文件已从版本库移除；`data/img/` 残留已清理；`RareModule_1x1.webp` 占位图存在。

## 2026-08-15

### chore: 将指令文件改造为多 agent 兼容的 AGENTS.md 规范源

- **改动原因**：原 `CLAUDE.md` 仅 Claude 自动读取；改为以 `AGENTS.md` 作为统一的规范源文件（业界通用约定），使各类 agent（Claude/Codex/Cursor/Gemini 等）都能读取同一份项目指令，避免多份重复维护。
- **变更文件**：新增 `AGENTS.md`（规范源，内容与原文一致且措辞保持 agent 无关）；`CLAUDE.md` 由普通文件改为指向 `AGENTS.md` 的软链接；新增 `claude.md` 软链接指向 `AGENTS.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：单一事实源 = `AGENTS.md`；`CLAUDE.md -> AGENTS.md` 保证 Claude 仍自动加载原有指令，`claude.md -> AGENTS.md` 提供小写别名；原文内容本身已是 agent 无关的项目规则，无需改写。
- **验证**：`ls -la AGENTS.md CLAUDE.md claude.md` 确认两者均为指向 `AGENTS.md` 的软链接；`git status` 显示 `CLAUDE.md` 为 typechange（symlink），`AGENTS.md`/`claude.md` 为 new file；`readlink` 均解析为 `AGENTS.md`。

## 2026-08-11

### fix: 延后普通页面的地图模块缓存预热

- **改动原因**：线上首次加载时全局 HTML preload 与 App 根部预取会让 `dungeon_modules.json` 参与所有页面的关键网络竞争；该文件仍需由详情页及时加载，并继续通过 Service Worker 和模块级缓存跨页面复用。
- **变更文件**：`web/src/hooks/useDungeonModules.ts`；`web/src/AppInner.tsx`；`web/src/components/NavBar.tsx`；`web/vite.config.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`useDungeonModules({ defer: true })` 使用 `requestAnimationFrame` 后再以 timer 启动全局缓存预热，及时模式保持详情、探索和地图模块页面原有加载行为；删除 `AppInner` 无消费者的顶层 hook；NavBar 改为首屏提交后后台预热；Vite 全局仅保留 `meta.json` preload，删除 `dungeon_modules.json` preload，不改 Workbox `df5-data-json` StaleWhileRevalidate 缓存。
- **验证**：`web` 下 `npm run format:check`、`npm run lint`（0 errors，20 条既有 warnings）、`npx tsc --noEmit`、quick SSG 构建、preview HTTP 200 通过；Playwright 确认首页 preload 仅包含 `meta.json`，模块请求由 `fetch` 在首屏绘制后发起，控制台无错误。

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

# 2026-08-21 会话修改记录

## 同步游戏数据并重新生成数据库

**改动原因**：运行同步脚本以获取最新游戏数据，删除旧数据库并重新生成以确保数据一致性，然后推送新生成的数据库到主分支

**变更文件**：api/data/darkfindv5.db

**关键逻辑/映射关系**：
- 运行 ~/sync_fmod.sh 同步 FMOD Output 数据
- 删除 api/data/darkfindv5.db
- 运行 api/main.py 重新生成数据库和相关数据文件
- 新生成的数据库包含更新的游戏数据（物品、怪物、道具、掉落等）

# 2026-07-29 会话修改记录

## fix: 拆分同名巨蚌陷阱与宝箱坐标

- **改动原因**：`GiantClam_Trap` 与 `GiantClam_Chest` 使用相同翻译文本“巨蚌”，Props 导出按翻译文本合并，导致陷阱坐标进入宝箱页面，并被红宝石等掉落详情间接展示。
- **变更文件**：`api/src/entity_export.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Props 分组键由翻译文本改为“翻译文本 + 是否存在掉落配置”；同类质量变体仍可合并，但有掉落配置的 `GiantClam_Chest` 与无掉落配置的 `GiantClam_Trap` 分离导出。
- **验证**：数据管道成功；Chest 与 Trap 分别生成独立 Props 文件且互不包含对方坐标；`lootdrops/Ruby.json` 中 `GiantClam_Trap` 出现次数为 0；Python 语法、ruff、black、`npm run format`、`npm run format:check`、`npx tsc --noEmit` 检查通过。

## fix: 独立神器与多语言物品名清洗

- **改动原因**：`WarMaul_8001` 等神器被错误暴露为普通品质变体；非中文语言的掉落详情物品名仍保留 `Triple Gem Bangle (Cracked)`、`トリプルジェム・バングル (ひび割れ)` 等末尾品质括号。
- **变更文件**：`api/src/lootdrop_builder.py`；`web/src/pages/LootdropDetailPage.tsx`；`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：独立 `_8001` 条目保留自身详情数据与物品 `translation_key`，同时输出 `1001~8001` 稀有度元数据供切换组件导航到基底物品的普通品质页面；掉落详情客户端及 SSG 多语言标题统一移除末尾半角/全角括号及其内容，例如 `WarMaul_8001` 在繁中显示 `利維坦`。
- **验证**：数据管道成功（locale/search_index 各 10 种语言）；`WarMaul_8001` 保持独立 `Text_DesignData_Item_Item_WarMaul_8001` 翻译键并恢复八档稀有度切换元数据；Quick SSG 成功生成 14,732 个文件；英语 `GoldBangle1I_5001` 静态标题为 `Triple Gem Bangle`，繁中神器静态标题为 `利維坦`；`npm run format`、`npm run format:check`、`npx tsc --noEmit`、Python/SSG 语法检查通过。

## fix: 任务详情表头禁止换行

- **改动原因**：日语任务详情页在窄任务卡片中会将目标表的“タイプ”“戦利品”等标题拆行，奖励表的 Item 列名也缺少不换行约束。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：目标表 Type、Target / Rarity、Loot、Count 表头统一使用 `whiteSpace: 'nowrap'`；奖励表 Item 表头及底部 Gold、EXP 标签同步禁止换行，Type、Count 延续已有单行规则。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过；按用户要求不继续执行浏览器验证。

## fix: 掉落详情分类按钮 i18n

- **改动原因**：英语掉落详情页的来源分类按钮组仍有“隐藏全部/全部显示”硬编码中文。
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：分类按钮的全选状态文案改为 `ui.common.hide_all` / `ui.common.show_all`，英语分别显示 `Hide All` / `Show All`，其余语言复用现有 UI locale 映射。

## docs: Sitemap 全量 URL 水合验证计划

- **改动原因**：需要验证全部语言 Sitemap URL 是否仍存在 React #425 水合错误；当前 10 个语言 Sitemap 每个 1,266 个 URL，共 12,660 个 URL。
- **变更文件**：`docs/plans/SITEMAP_HYDRATION_425_AUDIT.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：计划使用 Playwright 逐 URL 捕获 `pageerror`、控制台错误、#425/#418/#423、持续 Loading、资源状态和路由结果；Cloudflare Insights localhost CORS 单独归类，不掩盖应用错误。计划阶段不执行全量扫描、不修改业务代码。
- **验证**：仅创建计划文档，尚未执行全量 URL 验证。

## fix: 掉落来源分类名称 i18n

- **改动原因**：`Spear` 掉落详情中的生成型来源没有游戏官方 `translation_key`，英语页面的“矮人秘密武器”等分类按钮仍回退为中文，单纯重建无法翻译。
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`；`web/src/i18n/uiLocale.ts`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`DwarfSecretWeapon` → `ui.loot_source.dwarf_secret_weapon` → en `Dwarven Secret Weapon`；同时覆盖 `Weapon`、`Weapon_DualBoss`、`Weapon_MysticalTreasureRoom`、`Weapon_GoldenRoom`、`Weapon_FrozenRoom`、`Weapon_SkullRoom`，10 种语言共用合成翻译键。来源标题、筛选按钮和参考爆率均使用该键；全选按钮继续使用 `ui.common.hide_all` / `ui.common.show_all`。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 和 pre-commit 通过；Quick SSG 构建完成（12,929 HTML），`8080` 首页及目标页 HTTP 200。Playwright 确认 7 个来源分类均显示英文，`Dwarven Secret Weapon` 存在、“矮人秘密武器”不存在，全选按钮显示 `Show All`；仅有已知 Cloudflare Insights localhost CORS 噪声。

# 2026-07-28 会话修改记录

## feat: CF Pages 非默认语言掉落品质详情 404 接管

- **改动原因**：10 种语言完整生成 lootdrop 品质变体会使 Cloudflare Pages 部署文件数超过 Free 计划 20,000 上限；非默认语言的非默认品质改由 CF `404.html` 启动客户端加载。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：多变体基底条目以 `5001`（否则首个 suffix）标记默认品质；仅默认品质和 `8001` 写入非默认语言 HTML，`zh-Hans` 保留全部。相同标记过滤非默认语言 Sitemap，并令裁剪路由的 hreflang 仅指向 `zh-Hans`。根 `404.html` 写入 Vite 空根模板，`main.tsx` 因而使用既有 `createRoot()`，再按原 URL 请求版本化详情 JSON。构建递归统计 `dist` 文件和 HTML 数，超过 19,000 即失败。
- **验证**：`npm run format`、`npm run format:check`、`npx prettier --check scripts/ssg.mjs`、`npx tsc --noEmit`、`npm run build` 通过；产物为 18,127 文件（14,493 HTML）。保留/裁剪文件与 10 个 Sitemap 符合规则；生产预览首页 HTTP 200，Playwright 确认 `404.html` 根节点为空、保留详情无 React 错误且版本化 JSON 返回 200。Vite preview 对不存在路径返回 `index.html` 200，不能模拟 Cloudflare 的 404 文档状态。

## feat: 默认语言同步裁剪品质静态页

- **改动原因**：默认语言的非默认品质详情与其他语言一样可由 `404.html` 在线接管，继续生成只增加 SSG 与部署文件数。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/plans/CF_PAGES_DETAIL_FALLBACK.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：多变体路由统一使用 `generateStatic` 标记；默认语言首次写盘、非默认语言复制及全部语言 Sitemap 均跳过 `false`。默认品质与独立 `_8001` 条目保持静态页，其他品质由原 URL 的 `404.html` → SPA → 版本化 JSON 链路处理。
- **验证**：`npm run format`、`npm run format:check`、`npx prettier --check scripts/ssg.mjs`、`npx tsc --noEmit`、`npm run build` 通过；产物为 16,563 文件（12,929 HTML）。

## docs: 稀有度变体改造草案

- **改动原因**：记录以默认品质静态页加 `?r=1001` 承载其他品质的可选方向，避免未确定 URL 设计时直接改动站内链接。
- **变更文件**：`docs/plans/RARITY_VARIANT_REFACTOR_DRAFT.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`Spear_5001` 静态壳 + `r=1001` → 客户端读取实际品质 → `Spear_1001.json`；草案状态为未决定执行，当前 404 接管保持不变。

## docs: lootdrop 品质变体 JSON 合并计划

- **改动原因**：普通品质变体重复导出完整怪物、容器和坐标数据；明确改为基底 JSON 内按“来源实体 × 地图分组”保存品质爆率，坐标从实体 JSON 引用并在客户端按分组筛选。
- **变更文件**：`docs/plans/LOOTDROP_VARIANT_JSON_MERGE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`lootdrops/{base}.json.sources[source_id].ref` → 实体坐标；`variants[suffix].group_drop_info` → 来源在有效地图分组的爆率 → 坐标过滤及 score/max_score 重算。普通 `_1001` 至 `_7001` 计划停止独立写盘，独立 `_8001` 保留。
- **验证**：仅计划文档；以 `HeaterShield` 现有 53 来源、约 3,000 内联坐标、175 条分组爆率作为改造前基线，实施时必须做旧新语义与请求预算对比。

## feat: lootdrop 品质变体 JSON 合并

- **改动原因**：执行品质变体合并计划，移除普通 `_1001` 至 `_7001` 详情 JSON 的重复来源元数据与内联坐标。
- **变更文件**：`api/src/lootdrop_builder.py`；`web/src/pages/LootdropDetailPage.tsx`；`web/src/types/data.ts`；`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：生成端改为 `sources[source_id].ref` + `variants[suffix].group_drop_info[].source_id`；客户端始终按基底名加载并从当前 suffix 选择来源，按实体坐标所属地图分组过滤后重算 `score/max_score`；SSG 品质路由复用基底详情并预载基底 JSON。
- **别名处理**：无效 ref 会继续按坐标键、原实体名、规范基名和大小写无关实体名查找实际 JSON；唯一 spawner → 实体反向映射覆盖 `PirateCrossbow → PirateCrossbowman`，`TideWalkerShaman → TidewalkerShaman` 使用已有 84 个坐标。GDI 按 `entity_name + source_kind` 补齐同翻译不同来源，避免 `Weapon_Rare` 被中文翻译去重。
- **管道与数据验证**：热 DB 管道成功，lootdrop 阶段 34.90s、总计 39.25s；267 家族 / 1,831 旧品质文件的 GDI、score、max_score 全量对比 0 差异；12,590 个 source ref 全部存在，普通品质独立文件为 0。
- **体积与请求验证**：`HeaterShield` 家族 3,059,536 B → 97,898 B；冷开 `_5001` 传输增加 48,535 B，同家族切换 `_7001` 由 400,104 B 降至 4,029 B，跨家族访问由 608,582 B 降至 97,462 B。
- **前端验证**：Python `compileall` / Black / ruff、前端 `format:check` / Prettier / `tsc --noEmit`、SSG 脚本语法均通过；Playwright 确认 `_5001` 只请求基底、切换 `_7001` 不新增 lootdrop 请求、独立 `_8001` 请求自身 JSON。

# 2026-07-27 会话修改记录

## fix: SSG 后导航栏 Ant Design 样式失效

- **改动原因**：SSR 渲染时 Node 默认开发环境生成 `css-dev-only-*` 类名，生产客户端水合后使用 `css-*` 类名，内联的 Ant Design CSS 无法匹配，导致导航栏搜索框和语言下拉框失去组件样式。
- **变更文件**：`web/scripts/ssg.mjs`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SSG 的 SSR bundle 构建及运行时均固定 `NODE_ENV=production`，使服务端 `extractStyle()` 产出的 CSS 哈希与客户端 `ConfigProvider` 生成的 `css-plsjn` 类一致。
- **验证**：`npm run build` 完成；Playwright 打开 `8080` 后语言下拉层为 `position: absolute`、深色背景、选项 `display: flex`，无控制台错误；HTTP 200。

## fix: 地图模块实体翻译键导出

- **改动原因**：`Firedeep_Sinkhole` 的小型宝箱怪已使用官方 `Text_DesignData_Monster_Monster_Mimic_Small_Ornate`，但 locale 导出未扫描 `dungeon_modules_coords`，英文词典缺键后回退显示中文。
- **变更文件**：`api/src/locale_builder.py`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`dungeon_modules_coords/*.json` 内任意 `translation_key` → `_collect_keys()` → 每种语言的 locale JSON；`Mimic_Small_Ornate` → 官方 key → en `Mimic`。

## fix: 任务目标表格自适应列宽

- **改动原因**：Tavern Master 英文任务卡片将目标、地图等列固定为少量字符宽度，长文本会互相覆盖。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`。
- **关键逻辑/映射关系**：目标表格使用浏览器自动布局并移除各列表头固定宽度；地图单元格允许换行，长翻译按可用宽度分配且不会覆盖相邻列。
- **补充**：目标列为主要信息，保持不换行；空间不足时仅地图列换行。
- **补充**：每个目标拆为两行，类型与 Target 在首行，地图、掉落、稀有度和数量在次行，避免辅助列压缩 Target。
- **补充**：Count 表头与数值统一水平居中。
- **补充**：Reward 表格同样使用自动列宽，移除 Type/Count 固定宽度，且 Count 表头和数值居中。
- **补充**：Target 单元格覆盖表格的长文本断行规则，英文目标始终保持单行。
- **补充**：任务放大镜将当前 locale 的 Target 文本写入受控搜索框；页面内任务高亮也以任务和目标的翻译文本匹配，不再填入原始中文值。
- **补充**：Reward 的 Type 表头保持左对齐，Count 列仍居中。
- **补充**：Objective 的 Count 作为唯一固定宽度列，稳定停靠在任务卡片右侧；Target 仍由首行跨列显示。
- **补充**：任务放大镜通过路由状态将当前 locale 的 Target 文本填入导航栏全局搜索框，而非页面内任务搜索框。
- **补充**：导航栏使用 Ant Design Input 的原生输入节点滚动到可视区后再以 `preventScroll` 聚焦，兼容移动端键盘触发后的滚动位置。
- **补充**：Type、Target、Map 均左对齐，Target/Map 轨道仅由列头决定；长内容绝对定位且不换行，Map 内容保留在次行并从 Map 表头左边界显示。
- **补充**：Objective 的辅助信息改为跨列弹性行，Count 用自动左边距固定最右；Type 列使用自然最小宽度并贴近 Target。Reward 的 Type 表头左对齐。
- **补充**：Objective 恢复 Target、地图、掉落、稀有度、Count 的真实列坐标；Target Map 贴近 Target，地图值与其表头左对齐。
- **补充**：Target 列头禁止换行。
- **补充**：Objective 的 Count 表头和内容右对齐，贴近卡片右边界。
- **补充**：Objective 的 Count 列最小宽度扩展为 `5em`，列头禁止换行且数值居中。
- **补充**：Count 列头恢复右对齐，数值保持居中。
- **补充**：移除 Count 的人工最小宽度，改由不换行列头自然决定列宽，数值在该列内居中。
- **补充**：Count 的 `5em` 作为最大宽度，而非最小宽度。
- **补充**：Objective 的 Count 改为与 Reward 一致的内容收缩末列（`width: 1%`），固定在右侧，数值居中。
- **回退**：移除 Count 的 `width: 1%`，该宽度会重新分配整张表的列宽并影响 Type、Target、Map；Count 保留末列位置与居中数值。
- **补充**：Objective 的 Count 表头直接复用 Reward 的居中对齐规则，表头与数值均居中。
- **补充**：Objective 通过末尾 `<col>` 将 Count 列真实固定为 `5em`，右侧末列内的表头与数值均居中，不影响其他列的自动宽度。

## perf: 消除 locale 掉落文件二次扫描

- **改动原因**：热 DB 管线总计 98.18s，其中 locale 为收集 `translation_key` 二次读取约 670MB 掉落 JSON，耗时 14.16s；多变体导出还会重复扫描 7867 行 rate item 查找基础物品 spawner。
- **变更文件**：`api/src/collector.py`；`api/src/drop_rate.py`；`api/src/locale_builder.py`；`api/src/lootdrop_builder.py`；`docs/plans/PERF_PIPELINE_AND_RUNTIME_DRAFT2.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：lootdrop 最终确认写盘时收集 item/entity/GDI/rarity `translation_key`，`collector` 将集合传给 locale 导出以跳过 `lootdrops/` 重读；未传集合的独立调用继续走旧扫描路径。`DropRateEngine.preload()` 预建 `base_item -> lootdrop_id -> group_id -> spawner_keyword`，`get_base_item_spawners()` 改为字典查询。
- **实测结果**：`api/logs/pipeline_20260727_024506.log` 热 DB 总计 82.31s，较基线减少 15.87s；locale 14.16s → 0.48s，lootdrops 79.08s → 77.87s。A3 跨地图组批量爆率首次实测无收益，已撤回且记入草案2。
- **验证**：API `compileall`、ruff、Black 通过；Web `npm run format`、`format:check`、`npx tsc --noEmit` 通过；10 种 locale 键和值完全一致；`HeaterShield_8001`、`Lifeleaf_5001` JSON 语义一致。

## fix: 区分同组多点与单点多实体的选择文案

- **改动原因**：`FrostDemon` 的 HoundVale 同实体互斥组被显示为 `(2点)`，IceMaze 两实体互斥组被显示为 `(1点选2)`，均未表达实际选择关系。
- **变更文件**：`web/src/pages/DetailPage.tsx`；`web/src/pages/LootdropDetailPage.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`group_parent` 是 `BP_GameSpawnerGroup_C` 互斥组依据。同实体且仅一个组时按该组坐标数显示 `N点选1`；有 `variant_names` 且当前实体仅一个点时显示全部实体名加 `N种选1`；多点混合组维持 `N点选M`（M=`variant_count`）。
- **验证**：`npm run format` / `npm run format:check` / `npx tsc --noEmit` 通过。

## fix: 地图生成日期按时间戳正确显示

- **改动原因**：SSG 写入的 `meta.json.dataDate` 为 Unix 秒级时间戳（如 `1785084775`），免责声明组件误按 `YYYYMMDD` 切片，显示为 `1785-08-47`。
- **变更文件**：`web/src/components/Disclaimer.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：8 位 `YYYYMMDD` 继续直接格式化；其他值按 Unix 秒级时间戳转换为 ISO 日期，`1785084775` → `2026-07-26`。

## fix: 地图模块下无运算时不重复展示爆率

- **改动原因**：模块下 `ReferenceDropRates` 数据来自分组级 `group_drop_info`；无变体时与分组「参考爆率」完全相同却重复显示（如 AncientStingray）。
- **变更文件**：`web/src/pages/DetailPage.tsx`；`docs/AGENT_REFERENCE.md`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：模块图下仅 `hasVariant`（坐标 `variant_count > 1`，会走 `adjRate` 分摊）时渲染爆率 + N点选m 文案；无运算直接 `return null`，只保留分组头参考爆率。
- **验证**：待 format / tsc。

## docs: 性能优化草案（管线 + 运行时）

- **改动原因**：当前无时间执行优化；先固化热 DB 基线（~98s）与分阶段方案，供后续按阶段落地。
- **变更文件**：`docs/plans/PERF_PIPELINE_AND_RUNTIME.md`（新建）；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  - 基线 log：`api/logs/pipeline_20260727_005114.log` — lootdrops 79s / locale 14s
  - **阶段 A**：locale 顺带收集 keys、`get_base_item_spawners` 反向索引、全实体 compact JSON
  - **阶段 B**：变体 GDI/结构复用与外层结果缓存（主降 loot 耗时）
  - **阶段 C**：LootdropDetail `useMemo`、MapPanel 密集点 canvas/SVG
  - **阶段 D**：enrichment 合并写、冷 import 指纹、Workbox 大 JSON 策略
  - 关联：`PERF_LOOTDROPS_OPTIMIZATION.md`（已完成）、`PERF_VARIANT_DROP_RATE_CACHE.md`（废弃勿实施）、P005 / CACHE_OPTIMIZATION
- **验证**：仅文档，未改代码；状态为草案/待执行。

## fix: 无语言前缀详情页误匹配导致空白

- **改动原因**：`/monsters/AncientStingray/` 等无 `/:lang` 前缀路径被 `/:lang/:page` 当成 `lang=monsters`，DetailPage 的 `page`/`name` 错位，页面空白；`LegacyRedirect` 在 `*` 路由上无法拦截已匹配路径。
- **变更文件**：`web/src/AppInner.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：进入 Routes 前检查首段；非 `SUPPORTED_LANGS` 则 `<Navigate replace>` 到 `/${DEFAULT_LANG}${pathname}`（如 `/zh-Hans/monsters/AncientStingray/`）。`/` 与合法 `/:lang/...` 不变。
- **验证**：`npm run format` / `format:check` / `npx tsc --noEmit` 通过。

## fix: 钉手岛/象岛改为数字编号

- **改动原因**：`ShipGraveyard_BladehandRefuge`/`ShipGraveyard_ElephantIsland` 硬编码中文名，与 EmptyModule 数字编号风格不一致且有 i18n 问题。
- **变更文件**：`api/src/config.py` — `HARDCODED_TRANSLATIONS` 中两处显示名；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：
  - `ShipGraveyard_BladehandRefuge` → `1-1`（原「钉手岛」）
  - `ShipGraveyard_ElephantIsland` → `3-6`（原「象岛」）
  - 象岛额外绑定（**未改**）：`MODULE_DISPLAY_OVERRIDE` size 1x2；`MODULE_OFFSET_MAP` 偏移 `(-1600, 1600)`；钉手岛另有 size 2x2 / range 3200 / 偏移 `(-1600, -1600)`
- **验证**：仅显示名映射，布局尺寸与偏移保持原值。

## fix: 地图模块名称移除硬编码后缀

- **改动原因**：4 个特殊地图模块名称包含硬编码中文“模块”，非中文 locale 无法翻译该后缀。
- **变更文件**：`api/src/config.py` — 调整 `MODULE_NAME_OVERRIDE`；`docs/SESSION_CHANGES.md` — 登记本次修改。
- **关键逻辑/映射关系**：`EmptyModule_1F_14` → `3-1`、`EmptyModule_1F_09` → `5-1`、`EmptyModule_1F_15` → `7-4`、`EmptyModule_1F_13` → `6-5`；纯数字标识不再依赖 i18n。

# 2026-07-26 会话修改记录

## docs: 网站美化计划方案

- **原因**：当前不适合直接改动前端，先记录不更换 Ant Design 的最小化美化路线，供后续逐阶段实施与回退。
- **变更文件**：`docs/plans/WEBSITE_VISUAL_REFINEMENT.md` — 新增全局 token、导航、首页卡片、列表与详情页四阶段方案。
- **关键逻辑/映射关系**：`useTheme.tsx` token → 页面内联样式；`App.tsx`/`ssr.tsx` 同步 `ConfigProvider` theme → 保持 SSR/client hydration 一致；每阶段单独提交，不纳入其他进程的前端 WIP。
- **验证**：仅文档改动，待执行前端实现时按方案运行 format、format:check 与 TypeScript 检查。

## fix: 子池成员名称与模块生成率 i18n

- **原因**：`/en/items/GrimveilCloak/` 的 ObjectLinker 子池直接输出中文 `sub_pool_names` 与“种选”文案；模块卡片的生成率名称和数值之间缺少冒号。
- **变更文件**：
  - `api/src/collector.py` / `api/src/translator.py` — 子池导出从纯名称数组改为含 `translation_key` 的 `sub_pool_entries`；金矿及装死骷髅卫兵补齐可本地化 key。
  - `web/src/pages/DetailPage.tsx` / `web/src/pages/LootdropDetailPage.tsx` / `web/src/types/data.ts` — 逐项翻译并保留完整子池成员列表，按语言格式化“种选/点选”提示。
  - `web/src/components/ReferenceDropRates.tsx` / `web/src/i18n/uiLocale.ts` — 模块级生成率显示为 `名称:生成率`，新增 10 语言子池提示及装死骷髅卫兵文案。
- **关键逻辑/映射关系**：`sub_pool_entries[].translation_key` → `t(key, name)`；`SkeletonGuardsmanFromFakeDeath` → `ui.pool.skeleton_guard_fake_death`，简体中文仍为“骷髅卫兵（装死）”，英语为 `Skeleton Guardman (Feign Death)`。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`python main.py` 均通过；`http://localhost:8090/en/items/GrimveilCloak/` 返回 HTTP 200。

## fix: 列表页标题和有效项目数 i18n

- **原因**：items、monsters、props、lootdrops 四个列表页共用的标题「点位」及统计「有效实体」为硬编码中文，英语页面仍显示个人风格中文文案。
- **变更文件**：
  - `web/src/pages/ListPage.tsx` — H1、浏览器标题、OG 标题和有效数量改用共享列表 i18n 词条；统计文字统一为「有效项目」。
  - `web/src/i18n/uiLocale.ts` — 10 语言新增 `ui.list.locations`、`ui.list.valid_items`；英语分别映射为 `Locations`、`Valid items: {count}`。
- **关键逻辑/映射关系**：四类 URL → `ListPage` → `ui.list.locations` / `ui.list.valid_items`；`data.length` 替换 `{count}`，简体中文呈现「有效项目478个」。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过；`http://localhost:8090/en/lootdrops/` 返回 HTTP 200。

## fix: 开发模式清除 PWA 旧数据缓存

- **原因**：`SWUpdateBanner` 在 Vite dev 模式仍注册 `/sw.js`；残留生产 Workbox 以 `StaleWhileRevalidate` 返回旧 `FlatChestLarge.json`/locale，同日数据重建后页面首次请求仍显示旧中文。
- **变更文件**：
  - `web/src/components/SWUpdateBanner.tsx` — dev 模式不注册 Service Worker，主动注销残留注册并删除 `df5-*` 缓存；生产模式维持原 PWA 更新流程。
- **关键逻辑/映射关系**：开发环境 `import.meta.env.DEV` → unregister SW + delete `df5-*` → 浏览器直接读取 Vite 当前 JSON；仅当前已被旧 SW 控制的页面需刷新一次释放控制权。
- **验证**：`localhost:8090/data/json/props/FlatChestLarge.json` 已返回 `translation_key` 和 `label_type=special`；英语 locale 返回 `Flat Chest` / `Normal`。

## fix: 派生宝箱参考爆率名称 i18n

- **原因**：`FlatChestLarge` 等 props 的参考爆率名称由生成端拼接「海底 / 特殊 / 随机 / 组 / 可能上锁」，完整中文组合名没有 Game.json key，英语页面显示「方型宝箱(特殊)」。
- **变更文件**：
  - `api/src/enrichment.py` — props 的 `group_drop_info` 写入基础 `translation_key`、`label_prefix`、`label_type`、`may_be_locked` 结构化分类信息。
  - `web/src/types/data.ts` / `web/src/utils/dropRate.ts` — 定义并格式化结构化分类标签；缺少基础译名时安全回退完整原始中文。
  - `web/src/components/ReferenceDropRates.tsx` — 统一通过 `formatDropRateEntryLabel()` 显示名称。
  - `web/src/i18n/uiLocale.ts` — 10 语言新增海底、特殊、随机、组、可能上锁的标签片段。
- **关键逻辑/映射关系**：`方型宝箱(特殊)` → `Text_DesignData_Props_Props_FlatChestLarge` + `label_type=special` → `Flat Chest (Special)`；模式仍由 `formatDropRateSuffix()` 映射至 Game.json `FilterMode*` 文案。
- **验证**：重跑 `api/main.py` 后，`FlatChestLarge.group_drop_info` 含 `translation_key` / `label_type`；英语 locale 含 `Flat Chest`；目标页 HTTP 200。

## fix: 实体参考爆率名称 i18n

- **原因**：`props/GoldChest` 的 `group_drop_info` 普通「黄金宝箱」条目没有 `translation_key`，`ReferenceDropRates` 只能回退显示中文，英语页面显示「黄金宝箱100%」。
- **变更文件**：
  - `api/src/enrichment.py` — 直接物品、怪物的 `group_drop_info` 写入实体 `translation_key`；props 仅当爆率名称等于实体基础译名时写入 key，避免「海底 / 特殊 / 可能上锁」组合标签丢失限定信息。
- **关键逻辑/映射关系**：`GoldChest.group_drop_info[].translation_key` → `Text_DesignData_Props_Props_GoldenChest` → 英语 locale `Golden Chest`；locale_builder 递归收集该 key 后将其导出。
- **验证**：重跑 `api/main.py`，生成条目与 `data/json/locale/en.json` 均包含该 key；`http://localhost:8090/en/props/GoldChest/` 返回 HTTP 200。

## fix: Z 颜色说明 i18n

- **原因**：`DetailPage` 底部颜色说明 `颜色说明 / 高于地面 / 正常高度 / 低于地面` 硬编码中文
- **变更文件**：
  - `web/src/i18n/uiLocale.ts` — 新增 `ui.detail.color_legend` / `z_above_ground` / `z_normal_height` / `z_below_ground` 10 语言键
  - `web/src/pages/DetailPage.tsx` — 颜色说明改为 `ut('ui.detail.*')`
  - `docs/plans/LOCATION_STATS_I18N.md` — 补记同区域颜色说明 i18n 范围

## fix: 参考爆率公共组件 + 掉落模式 i18n

- **原因**：详情页/掉落页的「参考爆率」为硬编码，且 PVE/普通/豪客赛/逆袭赛模式名未按 Game.json 10 语翻译；en 页将 `Squire Royale` 错显示成 `Counter Raid`
- **变更文件**：
  - `web/src/components/ReferenceDropRates.tsx` — 抽出参考爆率公共组件，统一前缀/条目渲染
  - `web/src/utils/dropRate.ts` — 掉落模式翻译键映射、模式名格式化、爆率后缀格式化
  - `web/src/pages/DetailPage.tsx` / `web/src/pages/LootdropDetailPage.tsx` — 分组头与地图模块内联爆率改复用公共组件；模块行模式名也走 i18n
  - `web/src/types/data.ts` — `GroupDropInfo` 补 `translation_key`
  - `web/src/i18n/uiLocale.ts` — 新增 `ui.detail.ref_rate`，并将 filter 模式 fallback 同步为 Game.json 官方文案
  - `api/src/locale_builder.py` — 强制导出 4 个 `FilterMode*` 翻译键到 locale 文件
- **关键逻辑/映射关系**：
  - `PVE` → `Text_Code_DCPartyFinderCreateWidget_FilterModePvE`
  - `普通` → `Text_Code_DCPartyFinderCreateWidget_FilterModeNormal`
  - `豪客赛` → `Text_Code_DCPartyFinderCreateWidget_FilterModeHighRoller`
  - `逆袭赛` → `Text_Code_DCPartyFinderCreateWidget_FilterModeSquireRoyale`
  - `dropRateModeLabel()` 优先读 locale 中的 `Text_Code_*`，缺失时才退回 `ui.filter.*`，最终再退原始数据 key

## fix: 地图模块「综合爆率」i18n

- **原因**：DetailPage / LootdropDetailPage 地图卡片下硬编码「综合爆率」
- **变更**：两处改为 `ut('ui.detail.composite_rate')`（字典 10 语言已有）

## fix: LocationStats / 底部地图模块名 i18n

- **原因**：`/en/lootdrops/...` 底部「位置统计」「包含地图」硬编码中文；模块名用 `.translation` 未 `t(translation_key)`
- **变更文件**：
  - `web/src/components/LocationStats.tsx` — `useLocale` + `mapKeys`/`modules`，`ui.location.*`
  - `web/src/i18n/uiLocale.ts` — 10 语言 `pos_stat` / `map_includes` / `map_sep`
  - `DetailPage` / `LootdropDetailPage` / `QuestItemGroupPage` — 调用改造；h3/mapLabel 用 `t`
- **文档**：`docs/plans/LOCATION_STATS_I18N.md` 状态已修复

## 分析：LocationStats / 底部地图模块名 i18n 缺口

- **原因**：`/en/lootdrops/WarMaul_5001/` 底部「位置统计」与「包含地图」模块名未走 i18n
- **根因**：
  1. `LocationStats.tsx` 硬编码中文，未用 `ut`
  2. 调用方 `modules.get(k)?.translation` 未 `t(translation_key)`（地图 h3 已正确）
  3. `ui.module_detail.pos_stat` / `ui.quest_group.*` 已存在但未统一到公共组件
- **变更文件**：`docs/plans/LOCATION_STATS_I18N.md`（分析 + 修复方案，状态待修复）
- **涉及**：DetailPage / LootdropDetailPage / QuestItemGroupPage + debug mapLabel

## fix: DetailPage labelMatch 非对称匹配（GoldChest_special 空白）

- **原因**：`props/GoldChest_special` 页空白；coord label=`ChestSpecial_UnderSea` 含 UnderSea，GDI translation=`黄金宝箱(特殊)` 无海底；对称 `!eF && lF` 全否
- **变更文件**：`web/src/pages/DetailPage.tsx` — `labelMatch` 仅要求 entry 标记出现在 label（entry 权威），允许多余 label 标记
- **文档**：`docs/plans/PLAN_GOLDCHEST_SPECIAL_SPLIT.md` §10 回写 follow-up 根因/修复/提交
- **验证**：format + tsc 通过；刷新 `/zh-Hans/props/GoldChest_special/` 应出 ShipGraveyard 分区

## 实现：黄金宝箱(特殊) 拆独立 props 页

- **原因**：`props/GoldChest` 混装 direct(100%) 与 `ChestSpecial_UnderSea`(17.5%)；lootdrop ref 整页导致 100% 误赋
- **方案**：合成实体 `GoldChest_special`；`all_coords` 拆 special 点；enrichment/lootdrop 独立 gdi 与 ref
- **变更文件**：
  - `api/src/label_type.py` — 公共 `classify_label` + `split_goldchest_special_coords`
  - `api/src/collector.py` — 导出前拆坐标；注入 synthetic props / entity_class
  - `api/src/entity_export.py` — 导出 `props/GoldChest_special.json` + 索引
  - `api/src/enrichment.py` — special 页 gdi 仅 17.5%；GoldChest 去掉 special 行
  - `api/src/lootdrop_builder.py` — 注入 special 坐标；ref→`props/GoldChest_special`；变体率查 `GoldChest_UnderSea`
  - `docs/plans/PLAN_GOLDCHEST_SPECIAL_SPLIT.md` — 状态已完成
- **验证**：GoldChest 55 点无 Special；special 32 点 sr=17.5；Spellbook/CourtlyDress `_7001` 有「黄金宝箱(特殊)」ref 正确

## 计划：黄金宝箱(特殊) 拆独立 props 页

- **原因**：`props/GoldChest` 混装 direct(100%) 与 `ChestSpecial_UnderSea`(17.5%)；gdi 虽列出「(海底)黄金宝箱(特殊)」但坐标/ref 仍绑整页，lootdrop 引用后爆率与分类按钮错乱
- **方案**：仿宝藏堆/超级宝藏堆，导出合成实体 `props/GoldChest_special`（仅 special 坐标）；主页去掉 special 点与 gdi 行；lootdrop ref 指向新页
- **变更文件**：`docs/plans/PLAN_GOLDCHEST_SPECIAL_SPLIT.md`（状态：待执行→已完成见上）

## P002 降级：lootdrop gdi ↔ monsters 对齐（容器生成器子类）

- **原因**：`group_drop_info` 有子类翻译（如「黄金宝箱(特殊)」）但 `monsters` 缺失 → 前端参考爆率/图例被滤掉；原计划「实体详情页」过时且不做
- **变更文件**：
  - `api/src/lootdrop_builder.py` — `_ensure_gdi_monster_entries` / `_resolve_legend_ref`；预算对 0 坐标不 `break`；预算后+变体路径再 ensure；变体滤空仍留条目；`variant_gdi` 暂留 `_entity_name`
  - `docs/PLAN_CONTAINER_GENERATOR_ENTITIES.md` — 降级范围与验收，状态已完成
- **不做**：方案 B、props/monsters 列表补 UnderSea、独立详情页
- **验证**：管道 EXIT:0；`*_7001` 共 267 文件 gdi orphan=0；Spellbook 黄金宝箱(特殊) 仍 32 坐标；CourtlyDress/GoldBangle2H 原孤儿已进 monsters

## 废弃 PERF 变体爆率缓存计划

- **原因**：`docs/PERF_VARIANT_DROP_RATE_CACHE.md` 原「待执行」微缓存方案；现已有 `_variant_rate_cache`，计划仅减冷路径 dict/后缀查找，外层循环不变，收益不高
- **变更文件**：`docs/PERF_VARIANT_DROP_RATE_CACHE.md` — 状态改为 **废弃**，写明废弃原因；正文保留备查
- **未改**：`api/src/drop_rate.py` 等代码

## HARDCODED 全量 10 语 i18n 计划（仅文档，未执行代码）

- **原因**：`HARDCODED_TRANSLATIONS` 仅中文；空 `translation_key` 导致 en 等页 fallback 中文；用户担心扩 10 语时键冲突
- **结论**：禁止裸名/中文作 locale key；用 `df5.hardcoded.{EntityName}`；有 `Text_*` 的不造 df5；locale 必须 used_keys + 赋 key 同步
- **决策**：全量 230 条；AI 起草 10 语；SuperHoard 共用 key 保留
- **变更文件**：`docs/plans/HARDCODED_I18N.md`（状态：仅计划，未执行）
- **未改**：config / builders / locale 代码

## SuperHoard 超级宝藏堆 10 语硬编码 i18n

- **原因**：`SuperHoard*` 无 Game.json key，en 页显示中文「超级宝藏堆」；历史「超级宝藏」与「超级宝藏堆」统一
- **策略**：合成 key `df5.hardcoded.SuperHoard` + 10 语整词（不运行时拼接）；语义基准 `Text_DesignData_Props_Props_Hoard`
- **变更文件**：
  - `api/src/config.py` — `SUPERHOARD_I18N` / `SUPERHOARD_I18N_KEY` / `superhoard_translation_key()`；HARDCODED 中文统一为「超级宝藏堆」
  - `api/src/locale_builder.py` — 各语言 locale 强制注入合成 key
  - `api/src/lootdrop_builder.py` — 索引/详情对 SuperHoard* 赋 translation_key
  - `api/src/module_builder.py` — entity_class SuperHoard 注入合成 key
  - `docs/plans/SUPERHOARD_I18N.md` — 计划文档
- **验证**：管道 EXIT:0；`locale/en.json` → Super Treasure Hoard；Ruby_5001 SuperHoard01_9 有 key；详情 empty keys=0

## 炼金术师归入装备NPC分组

- **原因**：`Alchemist`（炼金术师）原先落在「可用NPC」，应与制甲匠等一并归入「装备NPC」
- **变更文件**：`api/src/quest_collector.py` — `_get_npc_category` 的 `equipment` 集合加入 `"Alchemist"`
- **即时数据**：本地 DB `quest_npcs` + `data/json/quest_npc.json` 已把 Alchemist 的 `category` 改为 `装备NPC`（下次全量 quest 提取也会按代码写入）
- **验证**：DB 查询 `Alchemist` → `装备NPC`

## 修复 lootdrop 详情掉落源 translation_key 缺失（en 页仍中文）

- **原因**：`build_and_save_lootdrop_details` 的 `m_tk_map` 只扫 `monster_entities`，宝箱/堆等 props 掉落源 `translation_key` 为空；前端 `t('', 中文)` 只能显示中文（如 Ruby_5001 的宝藏堆、黄金宝箱等）
- **变更文件**：`api/src/lootdrop_builder.py`
  - `m_tk_map` 合并 `entity_class`（含 props/items）
  - 写 monster 时优先 `entry.monster_translation_keys[i]`，再 map / entity_class
- **验证**：管道 EXIT:0；Ruby_5001 25 源中 24 有 key（en 如 Treasure Hoard / Golden Chest）；仅 `SuperHoard01_9` 无 Game key（`HARDCODED_TRANSLATIONS` 中文，DB props 空 key）
- **残留**：中文后缀 `(特殊)/(可能上锁)/组` 仍拼在 `translation` 上；有 key 时 en 只显示基名（无后缀）。SuperHoard 需另案（无官方 key）

## 统一 DetailPage SEO 标题构造，对齐 LootdropDetailPage 格式

- **原因**：DetailPage Helmet `<title>` fallback 为 `{entityLabel}{entity.name} 位置汇总Location`（翻译名+原始名重复，中英混写），与 LootdropDetailPage 的 `{itemLabel}{rarityLabel} -{pageLabel}` 格式不一致
- **变更文件**：
  - `web/src/pages/DetailPage.tsx` — 新增 `pageLabel = ut('ui.nav.' + page)`；标题 fallback 改为 `{entityLabel} -{pageLabel}`；description 去掉 `（{entity.name}）` 冗余；og:title 同步修改
- **关键逻辑**：模板统一为 `{ssrLocalizedTitle() ?? 标签名 -页面标签} | 越来越黑暗闪电指南 DarkFlashNav`；pageLabel 复用现有 `ui.nav.*` locale key
- **验证**：TSC 无报错，Prettier 通过

## 地图分组名 i18n 修复 — 全量完成

- **原因**：分组标题（如"废墟2层（地穴）"）在 en 页仍显示中文；slot_key 未进 locale，前端无法 i18n
- **变更文件**：
  - `api/src/translator.py` — `resolve_group_label()` → `{slot_key, floor, sub_key}`
  - `api/src/collector.py` — 注入 `group_key`/`group_floor`/`group_sub_key` + 双写 `group_display`（zh fallback）
  - `api/src/index_export.py` — quest_items_groups 写出三 key 字段
  - `api/src/locale_builder.py` — 扫描 `dungeon_modules.json` 的 group_key/group_sub_key
  - `web/src/types/data.ts` — DungeonModule 新增三字段，保留 group_display
  - `web/src/utils/formatGroupLabel.ts` — 新建统一组装 + fallback
  - `web/src/i18n/uiLocale.ts` — 各语言 `ui.common.floor`
  - 8 页面：LootdropDetail / Detail / DungeonModuleDetail / DungeonModuleGroup / DungeonModules / QuestItems / QuestItemGroup / Explore
  - `web/scripts/ssg.mjs` — SSR 分组摘要携带 key 字段
- **关键逻辑**：`formatGroupLabel` = `t(group_key)+floor+ui.common.floor[（t(sub_key)）]`；zh-Hans 无 locale 时回退 `group_display`
- **module_builder**：`.copy()` 已透传，无需改
- **验证**：
  - TSC + Prettier + pre-commit 通过；commit `8ccfc569`
  - `python main.py` EXIT:0（约 95s）
  - `dungeon_modules.json` Crypt：`group_key=…TheCrypts_1stFloor` floor=2 sub=`…2ndFloor` + `group_display=废墟2层（地穴）`
  - `locale/en.json` 含 8 个 `DungeonSlot` key（GoblinCave/FireDeep/Ice/Crypts/ShipGraveyard）
  - formatGroupLabel 冒烟：en=`The Ruins2F（The Crypt）` / zh fallback=`废墟2层（地穴）`
  - quest_items_groups 同步写出三 key 字段
- **附**：强化 `docs/DEVELOPMENT_WORKFLOW.md` / `CLAUDE.md` — **dev 分支同样必须任务完成即本地 commit**，禁止堆积未提交 diff
- **计划**：`docs/plans/DUNGEON_GROUP_I18N.md`

## 工作区脏文件复核 — 实为「做完未提」（已补交）

- **原因（误判）**：分组 i18n 提交时按「禁止混提」把其它脏文件标成半成品搁置；复核 diff 后确认均为**逻辑已完成**，不是改一半。
- **补交内容**：
  1. 列表掉落怪物名 i18n：`lootdrop_builder` 产出 `monster_translation_keys` + `ListPage` 消费
  2. 首页/页脚等 UI i18n：`AppName`、`HomePage` 卡片、`Footer`/`Disclaimer`/`NavBar`、`locale.ts` pt-BR 显示名
  3. 变体标签方案文档：`VARIANT_LABEL_FIX_PLAN.md`、`DETAILPAGE_VAR_REG_SPLIT.md`
- **流程补丁**：`docs/DEVELOPMENT_WORKFLOW.md` 增加「脏文件验收」表；`CLAUDE.md` 要求脏文件先判改完/改一半，**禁止把已完成当 WIP 长期搁置**
- **历史条目**：上文「有意未并入」清单作废，以本条与后续 commit 为准

# 2026-07-25 会话修改记录

## 变体标签格式修复：去掉误导的"选M组"，混合实体改显"点选N种" + DetailPage 固定点/变体点分离

- **原因**：`(N点选M组)` 格式读起来像"从N个里选M个"，实际N个位置各自独立产出1个物品。无 variant_names 时（同实体多组）信息冗余且误导；有 variant_names 时（混合实体）旧格式啰嗦。DetailPage 历史未分离固定点/变体点，Mummy 的 `(12点选2)` 实为 4 固定 + 8 变体
- **变更文件**：
  - `web/src/pages/LootdropDetailPage.tsx` — names case: `(名称N种选M)` → `(N点选{variant_count})`；no-names case: `(N点选M组)` → `(N点)`；移除未使用的 `groupCount`
  - `web/src/pages/DetailPage.tsx` — names case: `(名称N种选M · N点选M)` → 分离 reg/var；no-names case: `(N点选M组)` → 分离 reg/var；新增 `varCoords`/`regCoords` 分裂逻辑，分别计算 `regPosCount`/`varPosCount`
  - `docs/plans/VARIANT_LABEL_FIX_PLAN.md` — 新建方案文档
  - `docs/plans/DETAILPAGE_VAR_REG_SPLIT.md` — 新建方案文档
- **关键逻辑**：
  - 无 names 时（cnt=1，同一实体类型）去掉组数
  - 有 names 时（cnt>1，混合实体）改"位置数点选种类数"格式
  - DetailPage 固定点/变体点分离：`mapCoords` → `varCoords`(有 `group_parent`) + `regCoords`(无 `group_parent`)；`forcedVcN` 无 names 时 fallback 从 `posCount` 改为 `varPosCount`
  - 两页保持一致的展示逻辑
- **验证**：TSC 无报错，Prettier 通过

## main 分支回滚 + dev 设为默认工作分支

- **原因**：main 回滚至 `f9177a5`（多语言 P8-P12 回退），仅保留 `translation_EN`；后续多语言和修复在 dev 分支开发
- **变更文件**：
  - `CLAUDE.md` — 新增"默认工作分支：dev，main 已回滚至 f9177a5"说明
  - 回滚范围：41 个提交（`fa973c16` refactor: remove translation_EN ～ `1cf1924f` fix: language switch hard navigation）

## 修复 SSR ConfigProvider 双重 locale 导致 Ant Design Select 样式崩坏

- **原因**：`ssr.tsx` 外层 `ConfigProvider` 硬编码 `locale={zhCN}`，同时 `AppInner` 通过 `AntdLocaleProvider` 再次提供 locale，两层嵌套 CSS-in-JS 哈希与客户端（仅内层有 locale）不一致，导致 Select 等组件 hydration 后样式丢失
- **变更文件**：
  - `web/src/ssr.tsx` — 移除冗余 `locale={zhCN}` 及 `import zhCN`，locale 统一由 `AppInner` → `AntdLocaleProvider` 注入
  - `docs/SESSION_CHANGES.md`
- **关键逻辑/映射关系**：SSR 与客户端 ConfigProvider 树完全一致：外层无 locale → AntdLocaleProvider 注入 → Select 等组件哈希匹配 → hydration 后样式正常
- **验证**：`/lootdrops/` 语言下拉框显示正常（与 `/zh-Hant/lootdrops/` 一致）

## 修复 Ant Design locale 懒加载 + 语言下拉栏显示优化

- **原因**：语言下拉栏只显示语言代码（zh-Hans/en…），没有 readable 名称；AntD locale 模块用 `import()` 动态加载导致切换语言时重新渲染配置提供器，样式可能崩坏
- **变更文件**：
  - `web/src/i18n/antdLocale.ts` — 改为 10 语言全部同步 `import`，移除 `useEffect` 中的异步 fetch；`useAntdLocale()` 直接根据当前 `lang` 返回对应 locale 对象
  - `web/src/i18n/locale.ts` — 新增 `LANG_DISPLAY_NAME` 映射表（简体中文/English/Deutsch…）
  - `web/src/components/NavBar.tsx` — Select 组件 `virtual={false}` 禁用虚拟列表，`listHeight={320}` 展示全部 10 项，`getPopupContainer` 定位到父元素避免样式错位，`width=130` 容纳完整语言名
- **关键逻辑/映射关系**：原 `ANTD_LOCALE_MAP` 值为 `() => Promise<{default: Locale}>`（懒加载函数），改为直接 `Locale` 对象；同步加载消除配置变更导致的整个 AntD 树重渲染

## 修复 ListPage SSR 路由匹配错误（zh-Hans 列表页渲染为 HomePage）

- **原因**：`AppInner.tsx` 中 `/:lang` 路由在 `/:page` 之前，导致 `/lootdrops`、`/items` 等单段路径在 SSR 时被 `/:lang` 匹配，渲染 HomePage 而非 ListPage。P4 引入 `/:lang` 时遗留
- **变更文件**：`web/src/AppInner.tsx` — 在 `/:lang` 之前插入 4 条显式列表路由：`/items`、`/monsters`、`/props`、`/lootdrops` → `<ListPage />`
- **关键逻辑/映射关系**：React Router v6 按序匹配，`/:lang` 为单段通配符会意外捕获所有非显式路由的单段路径；在 catch-all 前补显式路由即可解除歧义
- **验证**：`curl /lootdrops/` title 从 HomePage 标题 → `【】点位`

## §10.1/10.2 修复执行：非中文 SSG 标题 hydration + ModuleDetail 标题重复

- **原因**：执行 MULTILANG_PLAN.md v0.8 推荐的修复方案
- **变更文件**：
  - `web/scripts/ssg.mjs` — `injectLang()` 替换为 `injectLocalizedData(page, lang, title)`，在注入 `__lang` 时同步注入 `__localizedTitle`
  - `web/src/i18n/ssrTitle.ts` — 新建，导出 `ssrLocalizedTitle()` 读取 `window.__SSR_DATA__.__localizedTitle`
  - `web/src/pages/DetailPage.tsx` — Helmet `<title>` / `og:title` 优先使用 `ssrLocalizedTitle() ?? 原中文拼接`
  - `web/src/pages/LootdropDetailPage.tsx` — 同上
  - `web/src/pages/DungeonModuleDetailPage.tsx` — 同上；同时修复 §10.2（`moduleDisplayName = m.translation || m.name` 统一标题/描述/H1，消除 `钉手岛钉手岛` 重复）
  - `web/src/pages/QuestNPCDetailPage.tsx` — 同上（防御性接入，NPC 页 SSG 暂未生成 localized title）
  - `docs/plans/MULTILANG_PLAN.md` — 升级版本到 v0.9，标记 10.1/10.2 已完成，新增 10.3（NavBar 残留分析）
  - `docs/SESSION_CHANGES.md` — 本次记录
- **关键逻辑/映射关系**：
  - `ssg.mjs`: `localizedTitle(routeData, localeDict)` → 同时写入 `<title>` 和 `__SSR_DATA__.__localizedTitle`；中文页（无 prefix）不注入该字段
  - 前端: `ssrLocalizedTitle()` 在 hydration 首轮返回与 SSG head 一致的值 → Helmet 不产生 mismatch
  - `__localizedTitle` 仅服务首轮 hydration 对齐；正文翻译仍走 `translation_key -> locale dict -> t()`
- **验证结果**：
  - `curl /en/lootdrops/HeaterShield_8001/ | grep title` → `Heater Shield` ✓
  - `curl /ja/items/Ale/ | grep title` → `エール` ✓
  - Playwright: 标题 hydrated 正确（lootdrop en/ja 标题分别是英文/日文）；hydro 错误从 8→7（-1 标题错误消除，剩余 7 全部来自 NavBar 标签 mismatch — 见 §10.3）
  - zh-Hans 页：无 regression
- **已知残留**：NavBar 标签（~8 个 tab）在非中文页仍产生 hydration mismatch（root cause: `ut()` 在 lang=en 时直接返回静态英文标签，而 body 是中文 SSG DOM）。暂时接受，留待后续修复。

## 多语言 v0.8 未解决问题分析与方案回写

- **原因**：`docs/plans/MULTILANG_PLAN.md` 已记录非中文 SSG 页 hydration 崩溃和 ModuleDetail 标题重复，但原文只有备选方案，未明确推荐路径、执行边界和验收标准；同时部分旧验收/风险描述仍写成无前缀按浏览器语言重定向，与当前“无前缀固定 zh-Hans”策略冲突
- **变更文件**：
  - `docs/plans/MULTILANG_PLAN.md` — 状态更新为“已知问题分析完成，待确认执行修复”；修正 `/items/Ale/` 无前缀验收标准；修正风险表中的 hydration 与无前缀策略；补充 10.1/10.2 推荐修复方案、关键约束、验收标准和“用户确认前不得执行”的边界
  - `docs/SESSION_CHANGES.md` — 记录本次文档分析回写
- **关键逻辑/映射关系**：
  - 10.1 推荐方案：SSG 后处理继续写本地化 `<title>`，同时只注入当前页面轻量 `__localizedTitle`；Helmet 首轮优先使用该值，保证 SSG head 与 hydration 首轮一致；正文翻译仍走 `translation_key -> locale dict -> t()`，不 inline 整份 locale JSON
  - 10.2 推荐方案：`DungeonModuleDetailPage` 统一 `moduleDisplayName = m.translation || m.name`，title/description/H1 复用同一展示名；若执行 10.1，则优先级扩展为 `__localizedTitle -> t(translation_key) -> moduleDisplayName`
- **执行边界**：本次仅分析并回写文档；未修改 `web/scripts/ssg.mjs`、页面 Helmet 或 i18n hook，未执行计划中的修复方案

## P11: 移除 translation_EN / resolver_en（16 文件，~50 处引用）

- **原因**：`translation_EN` 和 `resolver_en` 是多语言过渡期的历史产物，现在所有实体都有 `translation_key` + locale dict 处理翻译，不再需要英文本地化冗余字段；移除后每个详情 JSON 减 ~1.5 MB
- **变更文件**：
  - `api/src/collector.py` — 移除 `resolver_en` / `en_resolve` 创建和传递（到 8 个导出函数的参数）
  - `api/src/entity_export.py` — 3 个 export 函数移除 `resolve_en_name` 参数；items/monsters/props 输出移除 `translation_EN`
  - `api/src/module_builder.py` — `build_modules_map`/`build_and_save_module_coords` 移除 `resolve_en_name`；模块 map 和 coords 输出移除 `translation_EN` + `trans_lookup_en`
  - `api/src/lootdrop_builder.py` — `build_loot_index`/`build_and_save_lootdrop_details` 移除 `resolve_en_name`；索引和详情输出移除 `translation_EN`
  - `api/src/index_export.py` — `generate_quest_items_groups` 移除未使用的 `resolve_en_name` 参数
  - `web/src/types/data.ts` — `ItemEntity`/`MonsterEntity`/`PropsEntity`/`DungeonModule` 接口移除 `translation_EN?: string`
  - `web/src/types/quest.ts` — `NPCEntry` 接口移除 `translation_EN?: string`
  - `web/src/pages/DetailPage.tsx` — `<Helmet>` title/og:title 改为 `entity.name` 代替 `entity.translation_EN ?? entity.name`
  - `web/src/pages/DungeonModuleDetailPage.tsx` — 同上，改用 `m.name`
  - `web/src/pages/LootdropDetailPage.tsx` — `LootdropItem` 接口移除 `translation_EN`；title/og:title 改用 `data.name`
  - `web/src/pages/QuestNPCDetailPage.tsx` — title 改用 `npc.npc_name` 代替 `npc.translation_EN ?? npc.npc_name`
  - `web/scripts/ssg.mjs` — quick mode SSR 数据注入移除 `translation_EN`
- **验证**：管道通过（EXIT 0），前端构建通过，HTTP 200，JSON 中 `translation_EN` 全部消失

## P10: Playwright 回归测试框架

- **原因**：多语言功能需要回归测试确保标题正确 + 无 hydration 错误
- **变更文件**：
  - `web/tests/i18n.mjs` — 新建 Playwright 测试（15 页面 = 5 页 × 3 语言 zh-Hans/en/ja）；检测非中文页 title 非空 + 跨语言标题不同 + 控制台 hydration 错误
- **测试结果**：
  - zh-Hans 页正常（HomePage 通过，ItemDetail 通过，ModuleDetail 通过）
  - 非中文页检测到 8/10 有 hydration 错误（#418/#423），根因是 SSG 后处理替换 `<title>` 但 React Helmet hydration 时尚未加载 locale dict 导致 mismatch
  - 跨语言标题验证通过（en≠ja）
- **遗留问题**：非中文 SSG 页的 hydration 不匹配需单独修复（本轮未修）

## P9: locale 字典体积优化 — 只导出实际使用的 translation_key

- **原因**：`locale_builder.py` 从 DB 导出全部 1608 个翻译 key 到每种语言的 locale JSON，前端只用到 search_index + 实体数据文件中的 ~1055 个 key，多出 ~552 个无用 key（34% 冗余）
- **变更文件**：
  - `api/src/locale_builder.py` — 新增 `_load_used_keys()`，扫描 `search_index.json` + items/monsters/props/lootdrops 目录下所有 JSON 文件（含嵌套 monsters、group_drop_info）收集实际使用的 `translation_key`；`build_locale_files()` 按此集合过滤翻译字典
- **关键逻辑/映射**：过滤集来源 = search_index 中所有含 `translation_key` 的条目 + 每个实体 JSON 的顶层 `translation_key` + 嵌套 `monsters[].translation_key` + `group_drop_info/chains[].translation_key`；未命中 key 的前端 `t()` 回退到中文 `translation`/`name`
- **验证**：管线通过（88s），HTTP 200，10 语言 locale 各 1054-1056 key（原 ~1608），实体翻译键无缺失（0 missing）
- **效果**：每个 locale JSON 从 ~100KB 降到 ~65-83KB（↓34%），10 文件总计从 ~1.07MB 降到 ~698KB

## P8d: 剩余页面 UI i18n 全量接入 + LootdropDetail 嵌套实体名翻译

- **原因**: P8 仍有 9 个页面未接入 `useLocale`/`ut()`，页面标题/统计/按钮/标签等仍硬编码中文；LootdropDetail 嵌套怪物名需按 locale 翻译
- **变更文件**:
  - `web/src/i18n/uiLocale.ts` — 追加 ~75 个新 key (10 语言全覆盖): home/module/explore/quest_items/quest_group/quest_npc/quest_detail/content/npc 各组
  - `web/src/pages/HomePage.tsx` — 导航卡片描述/home tagline/计数文本全部替换为 `ut()`
  - `web/src/pages/DungeonModulesPage.tsx` — 页面标题/统计/模块计数接入 `ut()`
  - `web/src/pages/DungeonModuleGroupPage.tsx` — 页面标题/隐藏计数/调试按钮接入 `ut()`
  - `web/src/pages/ExplorePage.tsx` — 页面标题/统计/任务标签接入 `ut()`
  - `web/src/pages/QuestItemsPage.tsx` — 页面标题/统计/实体计数/位置计数/页脚接入 `ut()`
  - `web/src/pages/QuestItemGroupPage.tsx` — 页面标题/图例/位置统计/包含地图/调试按钮接入 `ut()`
  - `web/src/pages/QuestNPCPage.tsx` — 活跃NPC统计/任务计数/NPC分类标签(CATEGORY_KEYS → locale)接入 `ut()`
  - `web/src/pages/DungeonModuleDetailPage.tsx` — 标题/实体类型标签/选1点/位置统计/包含实体接入 `ut()`
  - `web/src/pages/QuestNPCDetailPage.tsx` — 任务列表/奖励类型(CONTENT_TYPE_KEY/REWARD_TYPE_KEY → locale)/任务目标/奖励/前置任务/金币经验值标签全部接入 `ut()`
  - `web/src/pages/LootdropDetailPage.tsx` — GDI 条目怪物名改用 `t(translation_key)`；模块名改用 `t(translation_key)`；GroupDropInfo 接口补充 `translation_key` 字段
- **关键逻辑/映射**:
  - 新增 `CATEGORY_KEYS` 映射（NPC 分类中文→locale key），`CONTENT_TYPE_KEY`（内容类型→locale key），`REWARD_TYPE_KEY`（奖励类型→locale key）
  - 所有页面的 `const { t, ut }` 拆分为：用到 `t` 的页面保留两者，只用 `ut` 的页面只解构 `ut`
  - 模板字符串（含 `{count}` 占位符）使用 `.replace()` 替换后传入，避免引入模板引擎依赖

# 2026-07-24 会话修改记录

## 多语言 P8-P12 持续推进：UI i18n + AntD locale + 嵌套 translation_key

- **原因**：P0-P7 核心链路已落地但 UI 仍全量硬编码中文，P8-P12 待执行项需逐步收尾
- **变更文件**：
  - `api/src/lootdrop_builder.py` — 嵌套 monsters 和 group_drop_info 补 `translation_key`，前端可按 `translation_key` 翻译 lootdrop 内嵌实体名
  - `web/src/i18n/uiLocale.ts` — 新建 10 语言 UI 文案字典（~60 key/语言），覆盖 NavBar、搜索、提示、筛选、爆率标签、列表分组、通用按钮；键命名遵循 `ui.<模块>.<key>`
  - `web/src/i18n/useLocale.ts` — 扩展 `useLocale` 新增 `ut(key)` 方法，运行时合并 UI locale 与实体 locale dict；`t(key, fallback)` 优先查合并字典
  - `web/src/i18n/antdLocale.ts` — 新建 `useAntdLocale` hook，按当前语言懒加载 Ant Design locale 模块（10 语言映射）
  - `web/src/App.tsx` — 移除顶层硬编码 `zhCN`，locale 改为 AppInner 内 `AntdLocaleProvider` 动态切换；ssr.tsx 保持固定 zhCN
  - `web/src/AppInner.tsx` — 新增 `AntdLocaleProvider` 组件，在 LanguageProvider 内按 URL 语言注入 AntD locale
  - `web/src/components/NavBar.tsx` — 将 `LABEL_MAP` 改为 `NAV_LABEL_KEYS` + `ut()` 动态翻译；搜索 placeholders、结果标签、最近搜索、面包屑、主题按钮全部接入 `ut()`
  - `web/src/components/Disclaimer.tsx` — 免责声明和反馈链接接入 `ut()`
  - `web/src/pages/ListPage.tsx` — 页面标题、组件分组名（神器/小型神器等）、调试按钮全部接入 `ut()`；列表实体名已用 `t(translation_key)` 翻译
  - `web/src/pages/DetailPage.tsx` — 加载文字、调试按钮、爆率显示/模式筛选/隐藏零爆率标签接入 `ut()`
  - `web/src/pages/LootdropDetailPage.tsx` — 同上，外加爆率品质标签（极低/低/中/高）接入 `ut()`
  - `docs/BUILD_AND_DEPLOY.md` — 完整构建说明补充 locale 字典导出和多语言 HTML 后处理流程
  - `CLAUDE.md` — 子文档查阅表新增 `docs/plans/MULTILANG_PLAN.md` 多语言文档映射
  - `docs/plans/MULTILANG_PLAN.md` — 更新 P8/P9 完成状态
  - `docs/SESSION_CHANGES.md` — 记录本次持续落地
- **关键逻辑/映射关系**：
  - UI locale：`ui.nav.*/ui.search.*/ui.common.*/ui.filter.*/ui.rate.*/ui.list.*/ui.detail.*/ui.disclaimer.*` 10 组 60+ key → 10 语言 `UI_LOCALE` 字典 → `ut(key)` 查找（fallback 到中文）
  - 实体 locale：`translation_key → localeDict（运行时 loadLocale） → t(key, fallback)` 合并 UI+实体字典
  - AntD locale：`lang → ANTD_LOCALE_MAP` 懒加载 → `ConfigProvider locale` 嵌套在 LanguageProvider 内
  - lootdrop 嵌套：`monster_name → monster_entities.translation_key → localeDict` 前端翻译路径已打通
- **待完成**：
  - locale 字典体积优化（当前导出完整 Game.json，需过滤到实际使用 key）
  - 其余页面（DungeonModule/QuestNPC/Explore/HomePage/QuestItems/DungeonModules）UI i18n 接入
  - Playwright 多语言 hydration/console 回归测试
  - 清理 `translation_EN` / `resolver_en`

## 多语言计划补充翻译边界

- **原因**：多语言剩余任务需要明确翻译边界，避免把调试字段、坐标 label、rarity 或 lootdrop 嵌套来源误纳入高成本/低收益翻译范围
- **变更文件**：
  - `docs/plans/MULTILANG_PLAN.md` — 补充 UI 文案必须人工翻译且参考对应语言 Game.json；坐标 label/keyword/file 等调试字段默认不翻译；variant rarity 已来自 Game.json 翻译链路；lootdrop SSG SEO 标题不包含嵌套怪物名
  - `docs/SESSION_CHANGES.md` — 记录本次计划约束补充
- **关键逻辑/映射关系**：用户可见实体名走 `translation_key -> locale`；UI 文案走人工维护 `ui.*`；调试/溯源字段保留原始值；rarity 继续复用 Game.json key；lootdrop SEO 标题仅使用物品名降低计算量和标题噪声

## 多语言计划未完成项回写

- **原因**：多语言核心链路已落地，但原计划仍显示“计划中/等待执行”，且未明确剩余 UI i18n、嵌套 translation_key、回归测试和清理任务
- **变更文件**：
  - `docs/plans/MULTILANG_PLAN.md` — 状态改为“核心链路已落地 — UI/回归/清理仍待收尾”；新增当前完成情况，列出 P0-P7 已完成与 P8-P12 待完成项
  - `docs/SESSION_CHANGES.md` — 记录本次计划回写
- **关键逻辑/映射关系**：已完成链路为 `translation_key -> locale dict -> SSG localized head -> runtime core display`；未完成链路集中在全量 UI 文案、嵌套实体名 key、locale 体积优化、AntD locale、Playwright hydration 回归和 `translation_EN` 清理

## 多语言计划阶段 6：运行时 locale 加载与核心显示切换

- **原因**：SSG 已能生成非中文 HTML，但客户端页面仍显示中文实体名；需要运行时加载 locale 字典，并让导航、列表页、详情页使用 `translation_key` 显示当前语言
- **变更文件**：
  - `web/src/i18n/LanguageContext.tsx` — 将语言上下文提升为 `LanguageProvider`，覆盖 NavBar 和所有页面；保留路径转换工具
  - `web/src/i18n/useLocale.ts` — 新增运行时 locale hook，按当前语言和 data version 加载版本化字典
  - `web/src/AppInner.tsx` — 用 `LanguageProvider` 包裹应用内容，语言前缀路由复用原页面组件
  - `web/src/components/NavBar.tsx` — 新增语言选择下拉；搜索结果和导航跳转保留/切换语言前缀；搜索结果实体名按 locale 翻译
  - `web/src/pages/ListPage.tsx` — 列表卡片实体名按 locale 翻译，详情链接保留当前语言前缀
  - `web/src/pages/DetailPage.tsx` — 详情页主标题、SEO 标题/描述按 locale 翻译实体名
  - `web/src/pages/LootdropDetailPage.tsx` — lootdrop 主标题、SEO 标题/描述按 locale 翻译物品名
  - `web/src/hooks/useSearchIndex.ts` — `SearchEntry` 类型增加可选 `translation_key`
  - `docs/SESSION_CHANGES.md` — 记录阶段 6 变更
- **关键逻辑/映射关系**：URL 第一段支持语言 → `LanguageProvider.lang`；非 `zh-Hans` 时 `useLocale()` 加载 `/data/{short}/json/locale/{lang}.json`；实体显示用 `translation_key -> localeDict -> 中文 translation/name fallback`

## 多语言计划阶段 5：SSG 多语言 HTML 后处理

- **原因**：需要为 `/en/...` 等非中文路径生成静态 HTML，并写入对应语言标题、canonical、hreflang 和 `__SSR_DATA__.__lang`；同时避免二次 React 渲染导致构建时间和 hydration 风险增加
- **变更文件**：
  - `web/scripts/ssg.mjs` — 新增语言常量、locale 字典读取、HTML 后处理函数；中文 SSG 完成后复制非中文 HTML 到 `dist/{lang}/...`，替换 `<html lang>`、`<title>`、canonical、alternate links，并向 `window.__SSR_DATA__` 注入 `__lang`
  - `web/scripts/ssg.mjs` — sitemap 改为 10 语言 URL，并为每条 URL 注入 `xhtml:link rel="alternate"`
  - `docs/SESSION_CHANGES.md` — 记录阶段 5 变更
- **关键逻辑/映射关系**：React 仍只渲染无前缀中文页面；非中文页面 = 中文 HTML body + 语言化 head + `__lang` 标记；标题来源 `routeData.translation_key -> locale/{lang}.json -> fallback translation/name`

## 多语言计划阶段 4：语言前缀识别与无前缀中文策略

- **原因**：多语言路由需要支持 `/en/...` 等语言前缀，但无前缀 URL 必须继续作为简体中文，避免旧链接被浏览器语言自动重定向破坏
- **变更文件**：
  - `web/src/i18n/LanguageContext.tsx` — 新增 `LanguageRoute`、`useLanguage()`、`stripLangPrefix()`、`withLangPrefix()`，统一识别支持语言并提供路径转换工具
  - `web/src/AppInner.tsx` — 在现有无前缀路由之外追加 `/:lang/...` 路由，语言路径复用同一页面组件，并放在泛型 `/:page` 路由之前避免误匹配
  - `docs/plans/MULTILANG_PLAN.md` — 将“无前缀自动按浏览器语言重定向”修正为“无前缀固定 zh-Hans”
  - `docs/SESSION_CHANGES.md` — 记录阶段 4 变更
- **关键逻辑/映射关系**：`/items/Ale/` → `zh-Hans` 原路径；`/en/items/Ale/` → `lang=en` + 复用 `DetailPage`；语言切换后续通过 `withLangPrefix(path, lang)` 生成目标 URL

## 多语言计划阶段 3：导出版本化 locale 字典

- **原因**：多语言前端需要按 `translation_key` 查询语言字典；字典路径必须复用现有版本化数据策略，避免绕开 SW/CDN 缓存失效机制
- **变更文件**：
  - `api/src/locale_builder.py` — 新建 `build_locale_files()`，从 DB 10 张翻译表导出 `api/output/json/locale/{lang}.json`
  - `api/src/collector.py` — 在 `search_index` 后增加 `locale export` 管道步骤，生成 locale 字典并随 data delivery 交付
  - `web/src/i18n/locale.ts` — 新增支持语言列表、`localeUrl()`、`loadLocale()`、`translate()`，字典读取路径走 `dataUrl(version, '/data/json/locale/{lang}.json')`
  - `CLAUDE.md` — 将日志重定向规则扩展为所有长流程命令，覆盖 `python main.py`、构建、部署和全站测试
  - `docs/BUILD_AND_DEPLOY.md` — 将数据管道命令改为 `python main.py > pipeline.log 2>&1`，部署命令改为 `./deploy.sh > deploy.log 2>&1`
  - `docs/plans/MULTILANG_PLAN.md` — 修正 locale 路径和 PWA 缓存策略为版本化 `/data/{short}/json/locale/*.json`
  - `docs/SESSION_CHANGES.md` — 记录阶段 3 变更
- **关键逻辑/映射关系**：DB `translations` / `translations_{lang}` → `data/json/locale/{lang}.json` → 构建时复制到 `/data/{short}/json/locale/{lang}.json` → 前端用 `translation_key` 查 `LocaleDict`

## 多语言计划阶段 2：实体与搜索索引补 translation_key

- **原因**：多语言字典需要用 `translation_key` 查找各语言文本；当前 items/monsters/props/lootdrops 的索引、详情和 `search_index.json` 只输出 `translation` / `translation_EN`，无法稳定做实体名 i18n
- **变更文件**：
  - `api/src/entity_export.py` — items/monsters/props 的索引和详情 JSON 写入 canonical `translation_key`
  - `api/src/lootdrop_builder.py` — lootdrop 索引、基础详情、变体详情写入 `translation_key`；`_8001` 变体沿用基础物品 translation key
  - `api/src/index_export.py` — `search_index.json` 对 items/monsters/props/lootdrops/dungeon_modules 透传 `translation_key`
  - `web/src/types/data.ts` — 实体和 dungeon module 类型新增可选 `translation_key`
  - `docs/SESSION_CHANGES.md` — 记录阶段 2 变更
- **关键逻辑/映射关系**：前端后续可用 `entry.translation_key -> localeDict[translation_key]` 翻译列表、搜索结果和详情标题；聚合 monsters/props 使用 canonical 实体 key；lootdrop `_8001` 页面复用基础物品 key 作为多语言回退入口

## 多语言计划阶段 1：修复 SSG 版本化数据目录顺序

- **原因**：`web/scripts/ssg.mjs` 先删除 `dist/data/json` 后再写入 `meta.json`，会导致构建阶段复制 `meta.json` 到不存在目录；多语言计划 P0 要求先修复版本化数据目录处理
- **变更文件**：
  - `web/scripts/ssg.mjs` — 在版本化复制前生成 `data/json/meta.json`，复制到 `/data/{short}/json/` 后移除版本目录内的 `meta.json`；删除原始 `dist/data/json` 后重建目录并只保留 `/data/json/meta.json`
  - `.gitignore` — 忽略 `*.log`，避免 `build.log` 等构建验证日志被提交
  - `CLAUDE.md` — 新增禁止直接实时输出 `npm run build` 的强制规则，要求写入 `build.log` 后单独读取
  - `docs/BUILD_AND_DEPLOY.md` — 将构建命令改为 `npm run build > build.log 2>&1`，补充避免阻塞 TUI 的日志读取规则
  - `docs/SESSION_CHANGES.md` — 记录阶段 1 变更
- **关键逻辑/映射关系**：大 JSON 只保留在版本化路径 `/data/{short}/json/...`；版本检测文件固定保留在 `/data/json/meta.json`，供 `useDataVersion()` 和 SW `df5-meta` 缓存规则使用

## 主文档精简与低频内容归档

- **原因**：`CLAUDE.md` 混入大量低频参考内容（项目树、页面布局、组件表、Hydration 排障、数据管道细节、PWA 缓存、DB 推送流程、长文档索引），导致主文档过长且高频规则不够突出
- **变更文件**：
  - `CLAUDE.md` — 保留执行规则、术语、工具约束、开发/构建强制入口；新增子文档查阅表，按任务场景映射到对应 docs 文档
  - `docs/AGENT_REFERENCE.md` — 新建长期参考归档，承接项目结构、V4 参考、页面布局、组件架构、详情页同步规则、fetch 路径规则、useDataVersion 状态同步、React Hydration 规则、前端排错流程、数据管道关键规则、子池规则、PWA 缓存规则和文档索引
  - `docs/DEVELOPMENT_WORKFLOW.md` — 新建开发流程文档，承接 checkpoint、提交前 format / format:check / tsc 预检、常见 TS/Prettier 问题和自动生成数据警告
  - `docs/BUILD_AND_DEPLOY.md` — 新建构建部署文档，承接完整构建、仅前端构建、启动 web、HTTP 200 验证、一键部署、数据流、远端和含 DB 推送流程
  - `docs/SESSION_CHANGES.md` — 记录本次文档拆分
- **关键逻辑/映射关系**：`CLAUDE.md` 通过“子文档查阅规则”让代理知道不同任务先查哪份文档；开发/提交查 `DEVELOPMENT_WORKFLOW.md`；构建/部署/DB 推送查 `BUILD_AND_DEPLOY.md`；架构/页面/排障/历史索引查 `AGENT_REFERENCE.md`；技术详细规范继续指向 `REFERENCE.md` / `PWA_ROADMAP.md`

## 所有语言翻译导入数据库

- **原因**：英文翻译 `en/Game.json` 之前直接从文件读取到内存，需要与中文一样导入 DB 统一管理；其他语言也一并入库以便后续扩展
- **变更文件**：
  - `api/src/config.py` — 添加 `LOCALIZATION_ROOT` 指向语言目录根
  - `api/src/db/_helpers.py` — 添加 `discover_languages()` 自动发现所有语言目录、`locale_display_name()` 友好名
  - `api/src/db/schema.py` — 添加 `ensure_translation_table(lang)` 为每种语言创建独立表
  - `api/src/db/__init__.py` — `import_translations()` 导入所有 10 种语言到对应表（`translations_en`、`translations_de` 等）zh-Hans 保持 `translations` 表不变；`get_translations_map(lang)` 支持按语言查询
  - `api/src/collector.py` — EN 改为 `db.get_translations_map("en")`，移除文件直读；`LOCALIZATION_ROOT` 加入 `_SOURCE_PATHS` 触发 DB 更新
  - `api/src/config.py` — 移除未使用的 `LOCALIZATION_EN_DIR`/`EN_GAME_JSON`
  - `api/src/db/_helpers.py` — 移除未使用的 `load_en_game_json()`
- **DB 结果**：10 张翻译表，各 1.2-1.3 万条记录
- **效果**：英文名显示不变（`Heater Shield`、`Soul-Devoted Folio`），流水线 107s 运行正常
- **验证**：3096 pages 构建通过

# 2026-07-23 会话修改记录

## Cloudflare Pages 构建检查修复：关闭预览分支拉取

- **原因**：推送 `7a9c6756` 后 GitHub check run 显示 `Cloudflare Pages: failure`。调查发现 CF Pages 将 `main` 分支当作预览分支，从源码重新构建（而非直接 serve gh-pages 的预构建文件），因构建命令/环境不一致立即失败（`09:50:28` 开始和完成同秒）。实际服务正常（`dnd9.icetar.com` 已部署新代码：SW regex urlPattern、版本化 preload 均正确）。
- **修复方式**：在 Cloudflare Dashboard → Pages → dnd9 → Settings → Preview branches 关闭预览分支拉取（或限制为 `preview/*`），使 main 的 push 不再触发 CF 构建。
- **变更文件**：无（Dashboard 配置改动，非代码变更）
- **验证**：后续推送不会再有 CF Pages 构建失败 check run。旧 commit 的死 check 不会重新运行。

## SSG preload 注入 + 移除模块级 JS preload

- **原因**：完成缓存优化计划其余项。全局 preload 增加 `index.json` + `search_index.json`；SSG 构建时注入详情页特定 preload（实体 JSON / lootdrops / 坐标 + 图片）；移除 3 个详情页的模块级 JS preload。
- **变更文件**：
  - `web/vite.config.ts` — 全局 preload 增加 `index.json` + `search_index.json`
  - `web/scripts/ssg.mjs` — 页面生成循环中按路由类型注入版本化 preload（items/monsters/props/lootdrops/dungeon_modules）
  - `web/src/pages/DetailPage.tsx` — 移除 `_preloadedEntity` / `_preloadedEntityUrl` 模块级 preload
  - `web/src/pages/DungeonModuleDetailPage.tsx` — 移除 `_preloadedCoords` / `_preloadedCoordsUrl` 模块级 preload
  - `web/src/pages/LootdropDetailPage.tsx` — 移除 `_preloadedLootdrop` / `_preloadedLootdropUrl` 模块级 preload
- **关键逻辑**：
  - SSG preload 注入：在循环中根据 `urlPath` 正则匹配路由类型，追加 `<link rel="preload">` 到 `</head>` 前
  - 模块级 preload 移除后，详情页初始状态由 SSR 数据或 `null` 兜底，useEffect 的版本化 fetch 负责获取数据
  - 浏览器通过 SSG `<link rel="preload">` 预加载资源，useEffect fetch 命中 HTTP 预加载缓存，无额外延迟

## 移动散落文档 PLAN_MERGE_VARIANT_SPAWN.md → docs/

- **原因**：`PLAN_MERGE_VARIANT_SPAWN.md` 位于项目根目录，未归入 `docs/` 文件夹
- **变更文件**：`PLAN_MERGE_VARIANT_SPAWN.md` → `docs/PLAN_MERGE_VARIANT_SPAWN.md`

## 全量 JSON 版本化 — 客户端 fetch 改用 dataUrl()

- **原因**：所有 fetch 仍使用非版本化路径 `/data/json/...`，SW 缓存旧数据后永不更新。部署新版后旧缓存不失效，用户看不到新数据。
- **变更文件**：
  - `web/src/utils/dataUrl.ts` — 新建工具函数 `dataUrl(version, path)` 将 `/data/json/...` 转为 `/data/{ver}/json/...`
  - `web/vite.config.ts` — SW urlPattern 从 `startsWith('/data/json/')` 改为 `/^\/data\/(?:[a-z0-9]+\/)?json\//` 兼容版本化路径
  - `web/src/hooks/useSearchIndex.ts` — fetchIndex 使用 `dataUrl(version, ...)`
  - `web/src/pages/DetailPage.tsx` — useEffect fetch 使用 `dataUrl(dataVersion, ...)` + `dataVersion` dep
  - `web/src/pages/DungeonModuleDetailPage.tsx` — useEffect fetch 使用 `dataUrl(dataVersion, ...)`
  - `web/src/pages/LootdropDetailPage.tsx` — 主 fetch + ref coords fetch 使用 `dataUrl(dataVersion, ...)`
  - `web/src/pages/ListPage.tsx` — fallback fetch 使用 `dataUrl(dataVersion, ...)`
  - `web/src/pages/HomePage.tsx` — 新增 `useDataVersion` + `dataUrl()` + `dataVersion` dep
  - `web/src/pages/ExplorePage.tsx` — fetch 使用 `dataUrl(dataVersion, ...)`
  - `web/src/pages/QuestItemsPage.tsx` — fetch 使用 `dataUrl(dataVersion, ...)`
  - `web/src/pages/QuestItemGroupPage.tsx` — 新增 `useDataVersion` + `dataUrl()` + `dataVersion` dep
  - `web/src/pages/QuestNPCPage.tsx` — fetch 使用 `dataUrl(dataVersion, ...)`
  - `web/src/pages/QuestNPCDetailPage.tsx` — 新增 `useDataVersion` + `dataUrl()` + `dataVersion` dep
- **关键逻辑**：
  - 数据版本由 SSG 构建时的 `meta.json` mtime 决定，转换为 base36 短码嵌入版本化路径
  - `dataUrl('', '/data/json/...')` 返回原路径（版本未就绪时）
  - 部署新版后，新 HTML 的 preload + 客户端 fetch 都使用新版本化路径，SW 无法命中旧缓存
  - 旧版本化路径缓存被 SW LRU 策略逐渐驱逐

## 修复 SW 更新 Banner 不显示的竞态问题

- **原因**：`vite-plugin-pwa` 默认自动注入 `registerSW.js`，在 `<head>` 阶段抢先注册 SW。浏览器检测到新 SW 后触发 `updatefound`+`statechange`，但此时 React 尚未 mount，`SWUpdateBanner` 的监听器错过了事件，导致 Banner 永不出现。
- **变更文件**：
  - `web/vite.config.ts` — 添加 `injectRegister: false` 禁止自动注入，`SWUpdateBanner` 成为唯一注册点；移除不再生成的 `registerSW.js` 从 precache 列表
  - `web/src/components/SWUpdateBanner.tsx` — 注册后增加 `reg.waiting` 防御性检查，若已有 SW 处于 waiting 状态则直接显示 Banner
- **关键逻辑**：
  - 禁止自动注入后，`SWUpdateBanner` 的 `useEffect` 中 `navigator.serviceWorker.register('/sw.js')` 成为唯一注册调用
  - `reg.waiting` 检查兜底 catch 到已在 waiting 状态的新 SW（旧版本已抢注的场景）

## 共生池 vs 冲突池逻辑文档补充

- **原因**：分析 Firedeep_MagmaFalls 赤焰巨像的子池问题时，发现 BP_GameObjectLinker_C 有两种语义——有 `group_parent` 时为冲突池（互斥 N 种选 M），无 `group_parent` 时为共生池（所有实体共存）。当前代码三层过滤（SQL WHERE、build_coord_out、前端 `!gp continue`）已正确排除共生池，无需代码修改。
- **变更文件**：
  - `docs/BLINDFALL_PIT_PROBABILITY_ANALYSIS.md` — 新增"共生池 vs 冲突池"章节，包含区分标准、三层过滤机制、分布统计
- **关键逻辑**：
  - 冲突池（11 个文件）：`group_parent != ''` → `sub_pool_size`/`sub_pool_names` 注入 → 前端显示 `(N种选M)`
  - 共生池（41 个文件）：`group_parent == ''` → 不注入子池字段 → 普通坐标点，无特殊标注

## sub_group_parent 追踪 + 坐标去重修复（GrimveilCloak 从 1 点恢复为 6 点）

- **原因**：BP_GameSpawnerGroup_C_8 内含 6 个 BP_GameObjectLinker_C 子组，每个独立从 11 种变体池中选 1，但坐标去重 key 只有 (x, y, z, json_filename)，导致同一个位置 6 个 ObjectLinker 的 spawn 被合并为 1 点，GrimveilCloak 显示 1 点而非 6 点
- **变更文件**：
  - `api/src/search_engine.py` — `_resolve_world_loc` 收集 `sub_group_name`；`sub_group_root_to_name` 映射 BP_GameObjectLinker_C / BP_ObjectLinkWithTriggerBox_C → parent；scene dict + results 包含 `sub_group_parent`
  - `api/src/db/schema.py` — 迁移添加 spawners 表 `sub_group_parent` 列
  - `api/src/collector.py` — INSERT 语句第 14 个参数加入 `sub_group_parent`
  - `api/src/db/repositories/coordinates.py` — SpawnerCoord 新增 `sub_group_parent` 字段；SQl 查询 select sub_group_parent；dedup key 改为 `(x, y, z, json_filename, group_parent, sub_group_parent)`
  - `api/src/translator.py` — `build_coord_out` 输出 `sub_group_parent`
  - `api/src/module_builder.py` — SQL 查询 + coord 构建包含 `sub_group_parent`
  - `web/src/types/data.ts` — Coord 接口新增 `sub_group_parent?: string`
  - `web/src/pages/DetailPage.tsx` — groupCount 计算从仅 `group_parent` 去重改为 `(group_parent, sub_group_parent)` 联合去重，确保"11种选6"正确显示
- **关键映射**：
  - 同 group_parent + 不同 sub_group_parent → 多个独立 ObjectLinker 子组 → 算多次选
  - 同 group_parent + 同 sub_group_parent + 不同位置 → 同一 ObjectLinker 内的多个刷怪点
- **验证**：GrimveilCloak JSON 从 1 coord 变为 6 coords；DB 有 6 行 GrimveilCloak 分别对应 BP_GameObjectLinker_C_1~C_11；HTTP 200

## adjRate 改为 exact 公式（反映 6 次独立抽选）

- **原因**：adjRate 仍用 `v / N`（假设 11 种互斥选 1），但实际是 6 次独立抽选，概率应为 `v × (1 − (1 − 1/N)^groupCount)`
- **变更文件**：
  - `web/src/pages/DetailPage.tsx` — 删除重复 groupCount 计算，提前计算 groupCount 供 adjRate 使用；公式改为 `v * (1 - (1 - 1/variant_count) ** groupCount)`
- **效果**：GrimveilCloak 豪客赛爆率从 `0.2273%` → `1.0888%`（↑4.8×）
- **文档**：`docs/BLINDFALL_PIT_PROBABILITY_ANALYSIS.md` 新增概率修正章节，区分怪物直接生成（43.5%）和物品掉落（≈1/9,200）

## adjRate 回退到 v×(1−(1−1/N)^G)

- **原因**：将公式改为 `100×(1−(1−v/(100N))^G)` 是错误的——引擎对同位置同实体去重（如幽鬼只出 1 只），最多 1 个 pickup
- **变更文件**：
  - `web/src/pages/DetailPage.tsx` — adjRate 回退到 `v * (1 - (1 - 1 / N) ** G)`
- **最终结论**：GrimveilCloak 豪客赛掉率 `0.2273%` → `1.0888%`（仅 4.8× 提升，无额外叠加效应），综合概率 ≈1/9,191

# 2026-07-22 会话修改记录

## 修复 ElephantIsland 硬编码未生效问题（前端构建过时）

- **原因**：`data/json/dungeon_modules.json` 已在 `api/src/config.py` 中正确写入 "象岛"/1x2/偏移，但 `web/dist/` 构建时间（06:05）早于数据更新时间（12:21），前端仍加载旧 JSON 数据
- **变更文件**：
  - `web/src/pages/ListPage.tsx` — prettier 自动格式化（无逻辑变更）
- **验证**：`npm run build` 后 `curl http://localhost:8080/` 返回 HTTP 200；SSG 产物的 SSR 数据中 ElephantIsland 的 translation="象岛"/size=(1,2)/offset=(-1600,1600) 均正确

## 修复 ShipGraveyard_ElephantIsland 大小错误 + 补充硬编码翻译

- **原因**：`ShipGraveyard_ElephantIsland` 无 DungeonModule JSON，`extra_rows` 路径将 size 硬编码为 1x1，但实际为 1x2 模块，导致前端显示异常
- **变更文件**：
  - `api/src/config.py` — HARDCODED_TRANSLATIONS 新增 `"ShipGraveyard_ElephantIsland": "象岛"`；MODULE_DISPLAY_OVERRIDE 新增 `{"size_x": 1, "size_y": 2}`
- **文档补充**：`docs/REFERENCE.md` — 新增"无 DungeonModule JSON 的模块（extra_rows）"章节，完整说明 extra_rows 发现流程、默认值限制、MODULE_DISPLAY_OVERRIDE 修复机制、10 个 extra_rows 模块列表、当前覆写条目
- **验证结果**：管道重跑后 `dungeon_modules.json` 中 size 从 1x1→**1x2**，translation 从英文→**象岛**，rotate=90.0 布局计算正确，has_img=true 图片正常
- **关联**：与 BladehandRefuge 同一类问题（无 DungeonModule JSON 的模块）

## 新增 ShipGraveyard_ElephantIsland 硬编码翻译"象岛"

- **原因**：`ShipGraveyard_ElephantIsland` 无 DungeonModule JSON 文件，`translation_key` 为空，前端显示英文名
- **变更文件**：`api/src/config.py` — HARDCODED_TRANSLATIONS 新增 `"ShipGraveyard_ElephantIsland": "象岛"`
- **生效条件**：需重新运行 `python main.py` 后前端才显示中文

## Crypt_BlindfallPit 出现概率分析文档（创建 + 补充阴森帷幕披风完整掉落链路）

- **原因**：用户需推算 Crypt 5x5 地图中盲坑（Crypt_BlindfallPit）模块的出现概率，以及该模块内阴森帷幕披风（GrimveilCloak）的完整掉落概率
- **变更文件**：`docs/BLINDFALL_PIT_PROBABILITY_ANALYSIS.md`
- **关键结论**：
  - 模块级：**1%**（40 布局 × 5 稀有模块，确认无双 Rare 槽布局）
  - 冲突级：**1/11**（11 种生成物互斥，披风仅 1 个唯一坐标 810,-10,-1600）
  - 掉落级：**2.5%**（豪客赛，仅披风 1 件物品，97.5% 概率空手）
  - 综合：**1/44,000**（豪客赛），约每 4.4 万局出一个
  - S2R 无 Rare 槽，概率为 0%
- **数据来源**：`spawners`/`mutually_exclusive_groups`/`lootdrop_groups`/`lootdrop_rate_weights` DB 表 + 布局文件

# 2026-07-22 会话修改记录

## ShipGraveyard_BladehandRefuge 旋转值修复

- **原因**：`ShipGraveyard_BladehandRefuge` 无 DungeonModule JSON 文件，通过 `extra_rows` 分支插入 DB 时旋转值硬编码为 270，而布局文件计算值为 0
- **变更文件**：`api/src/db/importers/modules.py`
- **关键逻辑**：`extra_rows.append` 第 9 个参数从 `270` 改为 `module_rotations.get(base_name, 270)`，使无 DungeonModule 文件的模块也能从布局文件中获取正确的旋转值
- **验证结果**：DB 中 `rotation` 从 `270.0` → `0.0`，`dungeon_modules.json` 中 `rotate` 同步为 `0.0`
- **文档补充**：`docs/REFERENCE.md` 旋转值章节重写，补充公式、映射表、插入路径、前端链路

## SW 更新检测修复

- **原因**：原有 `workbox-window` 库未安装导致动态 import 失败被 `.catch()` 吞掉 + `autoUpdate` 使 SW 跳过 waiting 状态，页面无法感知 SW 更新
- **变更文件**：`web/vite.config.ts`、`web/src/components/SWUpdateBanner.tsx`
- **关键逻辑**：
  - `registerType: 'autoUpdate'` → `'prompt'`：新 SW 安装后进入 waiting 状态等待用户确认，不再自动 skipWaiting
  - `SWUpdateBanner.tsx` 重写为原生 `navigator.serviceWorker` API（移除未安装的 `workbox-window` 依赖）
  - 监听 `updatefound` → `statechange` = `'installed'` 时弹出 banner（带有 controller 为更新，无 controller 为首次安装）
  - 点击"刷新以应用"→ `postMessage({ type: 'SKIP_WAITING' })` 激活等待中的新 SW
  - `controllerchange` 监听 + `refreshing` 引用防死循环

# 2026-07-18 会话修改记录

## Dungeon Module 页面 SSR 改造

**原因：** `/dungeon_modules/`（列表页）和 `/dungeon_modules/:group/:name`（详情页）是纯 CSR Shell，HTML 中 `<div id="root">` 为空，用户需等 JS 全量下载→执行→fetch 才能看到内容。参照 lootdrop 页面模式加入 SSR。

**变更文件：**

- `web/scripts/ssg.mjs` — 3 处修改
  - `routeDataKey()`: 详情页从 `return ""` 改为 `return \`dungeon_modules_detail/${group}/${name}\``
  - `SINGLE` 循环: 替换 `continue`，注入预计算的分组 summary 到 `ssrDataMap["dungeon_modules"]`
  - 新增 detail SSR 数据填充块: 完整模式注入 `{ module: DungeonModule, coords: ModuleCoordsData }`，quick 模式注入 `{ module: { name, translation }, coords: null }`
- `web/src/pages/DungeonModuleDetailPage.tsx` — SSR 数据消费
  - 添加模块级预加载 `_preloadedCoords`（同 lootdrop 的 `_preloadedLootdrop`）
  - 添加 `useSSRData`，guard 验证 `ssrData?.coords?.entities`
  - `useState` 初始值链: `_preloadedCoords ?? effectiveCoords ?? null`
  - `mod` 增加 SSR fallback: `modFromHook || effectiveModSsr`
  - `useEffect` 中若 SSR 数据齐全则跳过 fetch
- `web/src/pages/DungeonModulesPage.tsx` — SSR 数据消费
  - 添加 `useSSRData("dungeon_modules")`，初始 `groups` 状态使用 SSR 数据
  - `useEffect` 中若 SSR 数据已存在则跳过分组构建

**逻辑/映射关系：**

- 路由数据键：详情页 → `dungeon_modules_detail/:group/:name`（区别于 group 页的 `dungeon_modules/:group`）
- SSR 数据守卫：`ssrData?.coords?.entities`（同 lootdrop 的 `ssrData?.item?.monsters`）
- Quick 模式：`coords: null` → guard 失败 → 自动降级 CSR
- 列表页数据结构：`[{ group, group_display, module_count }, ...]`（8 个分组）
- 详情页 coords 数据：完整模式下 ~100KB 内联，含 37 个实体坐标

## /items 页面只显示地面掉落物

**原因：** 用户要求物品列表页只展示地面掉落物（从地面直接拾取的物品），从箱子或怪物爆出的物品应归类到掉落表（/lootdrops）。

**变更文件：**

- `api/src/entity_export.py:42-46` — 在 `export_items()` 中添加过滤逻辑

**逻辑/映射关系：**

- 保留条件：`monsters` 列表包含 `"Ground"`（地面掉落物）或 `monsters` 为空（装饰/任务物品）
- 排除条件：`monsters` 列表存在但不含 `"Ground"`（仅从怪物/箱子产出）
- 效果：items 从 517 降为 96 个物品
- 被排除的物品仍可在 /lootdrops 页面按怪物/箱子查询

## 超级金堆命名神器爆率计算验证

**验证结论：** 计算正确，`0.0018%` 即 `5/28/10000`。

**爆率公式：** `pool_weight / shared_count / rate_total`

- `pool_weight` = 该 luck_grade 的权重
- `shared_count` = 同 luck_grade 的物品数
- `rate_total` = 所有 luck_grade 正权重之和

**超级金堆 Inferno Lv1 (`ID_Droprate_Hoard_WeaponArmor_3001`)：**

| LuckGrade | 权重 | 物品数 | 说明                       |
| :-------: | ---: | -----: | -------------------------- |
| 5 (魔法)  | 7190 |    191 | 白色/蓝色武器              |
| 6 (稀有)  | 2500 |      0 | 无 LG6 物品，权重闲置      |
| 7 (史诗)  |  305 |      0 | 无 LG7 物品，权重闲置      |
| 8 (神器)  |    5 | **28** | 28 件命名神器平分 LG8 权重 |

**关键点：**

- `5/10000 = 0.05%` — 超级金堆产出**任意**神器的概率
- `5/28/10000 = 0.0018%` — 超级金堆产出**某件特定**神器的概率
- 游戏机制：先按权重 roll 运气等级，再在同级内均匀随机挑选
- LG6(2500) 和 LG7(305) 无对应物品，相关权重闲置不参与分配

# 2026-07-17 会话修改记录

## 诊断：ShipGraveyard_BladehandRefuge 模块翻译丢失原因

**原因：** `ShipGraveyard_BladehandRefuge` 没有对应的 DungeonModule JSON 文件（`Data/Generated/V2/Dungeon/DungeonModule/` 下不存在），仅作为地图文件存在（`Maps/.../ShipGraveyard_BladehandRefuge_A.json`）。`ModulesImporter` 通过 `_build_path_group_map()` 将其添加为"extra row"，但：

- `translation_key` = `""`（没有源 DungeonModule JSON 继承 Name.Key）
- `sl_base_name` = `""`（没有 SubLevelAsset 引用）
- `NameResolver` 所有翻译策略均失败（无 Game.json key `Text_DesignData_Dungeon_DungeonModule_BladehandRefuge`、无 HARDCODED 条目、模糊匹配无效）

**影响：** 前端显示英文名 `ShipGraveyard_BladehandRefuge`，无中文翻译。

**修复方式：** 在 `config.py` 的 `HARDCODED_TRANSLATIONS` 中添加 `"ShipGraveyard_BladehandRefuge": "刃手避难所"`（沿用 HARDCODED 中 `Bladehand_` 前缀的"刃手"译法），确保第 140 行 `name in HARDCODED_TRANSLATIONS` 命中。

**变更文件：** `api/src/config.py`

## 修复：TearofHrimthurs 不显示爆率

**原因：** spawner keyword `TearofHrithurs` 比物品名 `TearofHrimthurs` 少一个 m，导致 `_spawner_ldg` 无 item_name 映射，enrichment 无法注入 `group_drop_info`。前端 `variant_count > 1` 条件又过滤了非变体物品。

**变更：**

- `api/src/drop_rate.py` — 预加载时从 `lootdrop_rate_items` 反向取 item base name → lootdrop_group_id 映射，处理 keyword 与 item_name 不一致的情况
- `web/src/pages/DetailPage.tsx` — 移除 `variant_count > 1` 条件，有 `group_drop_info` 就显示；variant 仅作爆率分摊和 "(N种选1)" 文字

**关键逻辑：**

- `TearofHrimthurs_5001`(lootdrop_rate_items) → 去后缀 `_5001` → `TearofHrimthurs` → 通过 `_ld_id_to_groups` 关联 `ID_LootdropGroup_TearofHrimthurs`
- 综合爆率：PVE 0.1%, 普通 0.35%, 豪客赛 0.5%, 逆袭赛 0.5%

## 回滚 _8001 变体继承基底怪物列表

- **原因**：`9ef1a483` 修复让 _8001 变体继承基底全量怪物列表，但 RondelDagger 跨越 8 个地图（Inferno/FireDeep/GoblinCave/Ruins/IceAbyss/ShipGraveyard/Crypt/IceCavern），`group_drop_info` 中继承这 8 个地图是正确的行为，无需变更
- **操作**：回滚 `e87446e2` + `9ef1a483`，`api/src/lootdrop_builder.py` 第 160/168 行回到 `loot_map.get(v8001, [])`
- **遗留问题**：ShipGraveyard 参考爆率缺失是前端渲染问题，非数据问题

## SW 图片缓存 maxEntries 250→300

- **原因**：游戏模块图片增加，`api/src/img/` 现已有 255 个 webp，原 250 上限不够用
- **变更文件**：`web/vite.config.ts` — `df5-data-img` 缓存上限 250 → 300

## 新增 PNG→WebP 自动转换流水线

- **原因**：V5 项目原本没有任何 PNG→WebP 转换代码，`api/src/img/` 中的 webp 文件被视为预存静态资产。新增游戏 PNG 时无法自动生成 webp。
- **变更文件**：
  - `api/src/image_utils.py` — 新增，导出 `sync_webp_images()` 和 `compress_and_save_image()`
  - `api/src/collector.py` — 在 JSON 导出阶段前调用 `sync_webp_images()`
- **⚠️ 重要规则**：`api/src/img/` 下的 .webp 文件是**不可再生资源**，禁止删除。这些文件从游戏解包 PNG 转换而来，一旦丢失无法从游戏重新提取。

## 修复 _8001 变体 group_drop_info 缺少参考爆率

- **原因**：`build_merged_loot_map()` 中 `_8001` 变体只使用自己的怪物列表（RondelDagger_8001 仅 3 个怪物），而非继承基底 RondelDagger 的合并全量列表（40 个怪物），导致 ShipGraveyard 参考爆率丢失。
- **变更文件**：
  - `api/src/lootdrop_builder.py` — `build_merged_loot_map()` 中 `_8001` 使用 `merged_loot[base]` 代替 `loot_map.get(v8001, [])`
- **验证**：RondelDagger_8001 group_drop_info.ShipGraveyard 从 1 条（宝藏堆 0%）恢复到 29 条完整参考爆率
- **剩余操作**：见 `docs/FIX_8001_VARIANT_GROUP_DROP_INFO.md`

## 新增 DwarvenLockWay.webp 地图图片

- **原因**：FireDeep 组模块 `DwarvenLockWay`（矮人闸道）的源 PNG 文件存在，但项目中无 PNG→WebP 自动转换流水线，webp 文件缺失，前端始终显示占位图 `RareModule_1x1`
- **操作**：
  - 使用 Pillow 将 `DwarvenLockway.png`（小写 w）转换为 `DwarvenLockway.webp`（quality=85, 50KB）
  - 存入 `api/src/img/DwarvenLockway.webp`
  - 重新运行管道 → `dungeon_modules.json` 中 `img_name` 从 `RareModule_1x1` 变为 `DwarvenLockway`，`has_img=true`
  - 前端构建 + 预览验证通过（HTTP 200, 图片可访问）
- **变更文件**：
  - `api/src/img/DwarvenLockway.webp` — 新增（50218 bytes）
  - `docs/SESSION_CHANGES.md` — 本记录
- **备注**：项目中不存在自动 PNG→WebP 转换机制，新增模块图片需手动转换后放入 `api/src/img/`

## 跨变体 Fallback 爆率 Bug（未修复，已记录暂存）

- **原因**：`compute_drop_rate` 和 `compute_variant_rate` 的 `_base` 跨变体 fallback 允许未注册变体借用同物品其他变体的爆率，产生虚假数据
- **关键发现**：`lootdrop_rate_items` 中仅注册了部分变体（如 `SurgicalKit_4001`、`HeaterShield_5001`/`8001`），其余变体均无直接绑定。fallback 通过 `_base` + `_VARIANT_SUFFIXES` 循环命中错误变体，算出不应存在的爆率
- **变更文件**：
  - `docs/CROSS_VARIANT_FALLBACK_ISSUE.md` — 问题文档（待解决）
- **操作**：回滚到 checkpoint `e7623d8`，恢复原始状态，问题延期处理

## 修复重复请求 + preload URL 对齐 + 空版本跳过

- **原因**：Playwright 网络追踪发现 `/lootdrops/EmberGem/` 页面打开时 `dungeon_modules.json` 被请求 3 次、`search_index.json` 被请求 2 次，页面卡顿约 1 秒。根因：
  1. `useDataVersion()` 初始返回空字符串 `''`，`useEffect` 在 meta.json 加载前就用空版本发起 fetch
  2. meta.json 到达后 `dataVersion` 更新，`cachedVersion !== dataVersion` 清空 in-flight 的 `cachedPromise`，触发第二次 fetch（真正的重复）
  3. preload URL 使用 base36 编码（`/data/{short}/json/`），但 fetch URL 使用原始十进制时间戳 `/data/{dataVersion}/json/` — 总是不匹配，preload 缓存浪费
- **变更文件**：
  - `web/src/hooks/useDungeonModules.ts`
    - `useEffect` 开头加 `if (!dataVersion) return;`，空版本时跳过，等待 meta.json 到达
    - fetch URL 改为 `/data/${Number(version).toString(36)}/json/dungeon_modules.json`，与 preload 的 base36 格式对齐
  - `web/src/hooks/useSearchIndex.ts` — `useEffect` 开头加 `if (!dataVersion) return;`
  - `web/src/pages/ListPage.tsx` — `useEffect` 开头加 `if (!dataVersion) return;`
  - `docs/REFERENCE.md` — 更新详情页 `_modules` 描述为当前共享 Map 架构，新增 preload 策略说明（版本化 URL、AppInner 主动预取、防重复机制）
- **效果验证**（Playwright 实测 localhost:8080）：
  - BEFORE：`dungeon_modules.json` 3 次（preload + 2 fetch，总计 1.1s），`search_index.json` 2 次（629ms）
  - AFTER：`dungeon_modules.json` **1 次**（preload cache hit，20ms），`search_index.json` **1 次**（19ms）
  - 重复请求完全消除，preload 缓存被正确复用

## 移除 fetch+blob 图片加载 + preload meta.json + 延迟 search_index

- **原因**：上一轮修复后 Playwright 追踪仍有三大问题：
  1. 每张模块图片被加载两次（`<img>` 降级 + `fetch`+blob），SW 无法消除首次访问的双重请求
  2. `search_index.json` 在首屏关键路径中 fetch，阻塞内容渲染
  3. `meta.json` 被 ESM 模块评估阻塞，等 JS 下载完才开始请求
- **变更文件**：
  - `web/src/pages/LootdropDetailPage.tsx` — 删除 `scheduleFetch`、`imageUrlsRef`、`controllersRef`、`timersRef` 等整个 fetch+blob+createObjectURL 机制；IntersectionObserver 只控制 `visibleMaps`，MapPanel 直传 `/data/img/*.webp` URL
  - `web/src/components/MapPanel.tsx` — 删除 `imgName` prop 和 `imageSrc || /data/img/...` 回退逻辑；`imageSrc` 改为必填
  - `web/src/pages/DetailPage.tsx` — MapPanel 传 `imageSrc` 直连 URL，去除 `imgName`
  - `web/src/pages/DungeonModuleDetailPage.tsx` — 同上
  - `web/src/pages/QuestItemGroupPage.tsx` — 同上
  - `web/src/hooks/useSearchIndex.ts` — useEffect 中 fetch 包裹 `setTimeout(0)`，让出首屏渲染
  - `web/vite.config.ts` — `inject-versioned-preload` 插件额外注入 `<link rel="preload" href="/data/json/meta.json">`
- **效果验证**（Playwright 实测 localhost:8080）：
  - meta.json 开始时间从 **+2689ms → +69ms**（提前 ~2.6s）
  - EmberGem.json 开始从 **+2857ms → +1266ms**（提前 ~1.6s）
  - 图片每张 **2 次 → 1 次**，无重复
  - 全页面总耗时从 **~4.6s → ~1.6s**（-3s）
  - 用户感知的"数据加载中→内容出现"从 ~2.8s 降到 ~1.2s

## 模块级数据预加载 — 消除详情页首条数据 fetch 的串行等待

### 原因

Chrome DevTools 网络面板追踪 `/lootdrops/GoldenKey/` 发现首条数据 fetch 到 +1041ms 才启动：

```
+0ms     HTML 到达 (18ms TTFB)
+38ms    meta.json / dungeon_modules.json preload 完成
+44ms    JS bundle 开始下载 (antd 415KB + react 180KB + index 119KB)
+130ms   JS 下载完毕
+130~400ms  浏览器解析 JS (~270ms，含 ESM 模块求值)
+400~1041ms React hydrateRoot 执行 (~640ms，含组件树对齐 SSR + Ant Design 复杂 DOM)
+1041ms  useEffect 中 fetch 启动
+1059ms  fetch 完成 (18ms，SW 缓存命中)
```

核心问题：**数据 fetch 被 React 水合串行阻塞**。虽然 `meta.json` 在模块级 fetch（ESM 求值时发起，数据在 hydration 前已就绪），但详情页的实体数据 fetch 放在 `useEffect` 里，必须等 React 水合完 → 组件 mount → effect 调度 → 才发出请求。这导致：

1. **无用串行等待**：数据请求不需要 `dataVersion`（URL 不含版本号），却放在 `useEffect` 里等组件 mount
2. **缓存利用不足**：SW 已经缓存了数据，但请求发得晚，缓存命中的 18ms 也被串行在后
3. **首次渲染缺数据**：`useState(null)` 先渲染空状态 → fetch 完成 → `setData` 再渲染；两次渲染浪费 CPU

### 方案

在 **ESM 模块求值阶段**（JS 解析时，比 hydrateRoot 早 ~300ms）就直接解析 URL 发起数据 fetch，结果存模块级变量。组件从模块级变量读取数据作为 `useState` 初始值，`useEffect` 只作为导航切换的兜底。

```
BEFORE (串行):
  ESM求值 → JS执行 → hydrateRoot → 组件mount → useEffect → fetch → setData → 渲染
                                                       └── wait 1041ms ──┘

AFTER (并行):
  ESM求值 → fetch ─┬─ 完成 ────┐
                    │           ↓
  JS执行 → hydrateRoot → 组件mount → useState(预加载数据) → 渲染
                                    └── useEffect: 命中跳过
```

### 变更文件

#### `web/src/pages/LootdropDetailPage.tsx`

**① 模块级变量 + 预加载 fetch**（行 70–83，组件函数之前）

```ts
let _preloadedLootdropUrl = "";
let _preloadedLootdrop: LootdropItem | null = null;
if (typeof window !== "undefined") {
  const _m = window.location.pathname.match(/^\/lootdrops\/([^/]+)/);
  if (_m) {
    _preloadedLootdropUrl = `/data/json/lootdrops/${_m[1]}.json`;
    fetch(_preloadedLootdropUrl)
      .then((r) => r.json())
      .then((d) => {
        _preloadedLootdrop = d as LootdropItem;
      })
      .catch(() => {});
  }
}
```

- `typeof window !== 'undefined'`：SSR 构建时跳过（Node.js 无 window）
- URL 从 `location.pathname` 提取，与 React Router 的 `useParams` 同步
- fetch 结果异步写入 `_preloadedLootdrop`，组件 mount 时可能已就绪

**② useState 初始值优先使用预加载数据**（行 140–143）

```ts
const [data, setData] = useState<LootdropItem | null>(
  _preloadedLootdrop ??
    (effectiveSsrData?.item?.monsters ? effectiveSsrData.item : null),
);
```

数据优先级：**模块预加载 > SSR 内联数据 > null**

**③ useEffect URL 对齐检查 + 移除 dataVersion 依赖**（行 194–219）

```ts
useEffect(() => {
  if (!baseName) return;
  if (effectiveSsrData?.item?.monsters) { ... return; }
  const fetchName = currentSuffix && !isArtifact
    ? `${baseName}_${currentSuffix}` : baseName;
  const lootUrl = `/data/json/lootdrops/${fetchName}.json`;
  if (_preloadedLootdrop?.monsters && _preloadedLootdropUrl === lootUrl) return;
  if (lootFetchedRef.current) return;
  lootFetchedRef.current = true;
  // ...fallback fetch...
}, [baseName, currentSuffix, effectiveSsrData]); // ← 移除 dataVersion
```

关键变更：

- **`_preloadedLootdropUrl === lootUrl`**：精确比对预加载 URL 和当前组件需要的 URL，防止导航切换后误用旧预加载数据跳过新 fetch
- **移除 `dataVersion` 依赖**：因为 URL 不含版本号，不需要等 meta.json 信号
- **不变**：`lootFetchedRef.current` 兜底机制保留，导航切换时 `name` 的 effect 重置该 flag，确保新页面走 fallback fetch

#### `web/src/pages/DetailPage.tsx`

**① 模块级预加载**（行 30–45）

```ts
let _preloadedEntityUrl = "";
let _preloadedEntity: Entity | null = null;
if (typeof window !== "undefined") {
  const _m = window.location.pathname.match(
    /^\/(items|monsters|props)\/([^/]+)/,
  );
  if (_m) {
    _preloadedEntityUrl = `/data/json/${_m[1]}/${_m[2]}.json`;
    fetch(_preloadedEntityUrl)
      .then((r) => r.json())
      .then((d) => {
        _preloadedEntity = d as Entity;
      })
      .catch(() => {});
  }
}
```

正则 `/(items|monsters|props)/:name` 覆盖所有实体详情页。

**② useState + useEffect** 与 LootdropDetailPage 相同模式：

- `useState` 初始值：`_preloadedEntity ?? (ssrData?.entity?.coords ? ssrData.entity : null)`
- `useEffect` 开头：`if (_preloadedEntity?.coords && _preloadedEntityUrl === url) return;`
- `useEffect` deps：移除 `dataVersion`，改为 `[page, name, ssrData]`
- **删除 `useDataVersion()` 调用**（已无引用，`dataVersion` 在 DetailPage 无其他用途）

### 正确性保证

| 场景                                                    | 预加载行为                                                            | 预期结果                            |
| ------------------------------------------------------- | --------------------------------------------------------------------- | ----------------------------------- |
| 首次加载（SSG 页面）                                    | 模块级 fetch 在 hydration 前发起，可能已返回                          | useState 带数据，useEffect 命中跳过 |
| 导航切换（同页不同 name）                               | 模块级变量未更新（ESM cache），URL 比对不匹配                         | useEffect fallback fetch 接手       |
| SSR data 已注入（Quick mode 有数据）                    | 预加载数据覆盖 SSR（优先级更高）                                      | ✅ 数据正确                         |
| 预加载失败（网络错误）                                  | `_preloadedLootdrop` 保持 null                                        | useEffect fallback fetch 兜底       |
| 变体跳转（`/lootdrops/GoldenKey/` → `GoldenKey_5001/`） | 初始预加载 `GoldenKey.json` 与跳转后 `GoldenKey_5001.json` URL 不匹配 | fallback fetch 获取变体数据         |

### 效果

- 数据 fetch 从 +1041ms → **约 +200ms（ESM 求值阶段）**，提前 ~840ms 发起
- 首次渲染带数据（`useState` 预填充），减少一次因 `setData` 触发的重渲染
- 与 React 水合并行，消除无用的串行等待
- 剩余 ~800ms 瓶颈为 JS 解析 + React 水合 CPU 时间，属架构限制（Quick mode SSG）

## Decimal-化 spawners.py 生成概率浮点除法

- **原因**：lootdrops/SkullKey 页 CofferSmall(迷你宝盒组) spawn_rate=3.0001 应 3.0，根因是 ChestMedium spawner 中 ∑SpawnRate=999960（非 100万），`100*30000/999960` 产生 3.00012% 尾数
- **变更文件**：`api/src/db/importers/spawners.py`
  - 添加 `from decimal import Decimal` 导入
  - 三处除法 `100*raw_rate/X` 全部改用 `Decimal(str(100*raw_rate))/Decimal(str(X))` 后转 float，消除中间浮点精度损失
  - 排序：lint-fix 自动调整 import 顺序 + black 格式化
- **现状**：3.0001 仍存在（因游戏数据 SimpleChestSmall SpawnRate=519960 而非 520000 导致 pool=999960），但当游戏数据分母为整万时 Decimal 化会确保结果精确

# 2026-07-16 会话修改记录

## computeModuleScore 变体组综合爆率改用 selected_count / variant_count

- **原因**：骷髅双手剑士在沼泽等的综合爆率计算中，变体组（如 3种选1）贡献错误地加了完整 baseScore，应为 baseScore × 组内点数 / 变体总数
- **公式**：变体组贡献 = baseScore × count_in_group / variant_count（count_in_group 为同 group_parent 的坐标点数）
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx` 的 `computeModuleScore()` 函数
  - `varGroups` 记录从 `{ translation }` 改为 `{ translation, count, vc }`
  - 遍历 dots 时递增 `existing.count` 而非去重后置 1
  - 最终累加时：`Math.round(baseScore)` → `Math.round(baseScore * g.count / g.vc)`

## 分类按钮数字 + 底部统计同步 hideZeroRate 过滤；抽离 LocationStats 组件

- **原因**：按钮数字（1080→163）在按钮熄灭时未更新（回退 `m.coords.length`）；底部"包含地图"列表未过滤已隐藏坐标
- **变更文件**：
  - `web/src/components/LocationStats.tsx` — 新建（共享底部统计行组件）
  - `web/src/pages/LootdropDetailPage.tsx` — `visibleCountByMonster` 从 `resolvedMonsters` 直接计算（不排除 hidden），按钮始终显示过滤数；底部用 `bottomCount`/`visibleMapsSet`（hidden + hideZeroRate 双重过滤）替换旧 `totalCoords`/`mapGroups.keys()`
  - `web/src/pages/DetailPage.tsx` — 底部统计同步覆盖 hideZeroRate 过滤；使用 LocationStats

## 坐标计数同步 hideZeroRate 过滤：迷你宝盒组 1080 不再显示错误数字

- **原因**：`hideZeroRate` 过滤后，怪物切换按钮和底部统计仍显示原始未过滤的坐标总数（如迷你宝盒组 1080），未反映过滤后的实际可见坐标数
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`
- **变更逻辑**：新增 `visibleCountByMonster` 遍历 `sortedGroups` 同步应用 `hideZeroRate`/`modeFilter` 过滤逻辑，统计每个怪物翻译的实际可见坐标数；`filteredTotalCoords` 汇总为底部统计总数；切换按钮和 `Helmet` meta 描述均使用过滤后的数字
- **注意**：此功能是核心筛选机制，除非用户要求否则不能移除

## 零爆率坐标过滤修复：modeFilter=全部时检测所有模式

- **原因**：`hideZeroRate` 在 `modeFilter=""`（全部）时跳过过滤，导致 OldRustyKey 等全模式爆率为 0 的坐标/地图分组错误显示
- **变更文件**：`web/src/pages/LootdropDetailPage.tsx`、`web/src/pages/DetailPage.tsx`
- **核心逻辑**：新增 `hasAnyRate()` 辅助函数；当 `hideZeroRate=true` 且 `modeFilter=""` 时，检查 `drop_rates` 中 PVE/普通/豪客赛/逆袭赛 是否任一 > 0，全 0 才隐藏。选中具体模式时保持原行为（只检查该模式）
- **效果**：Billet（PVE=65%、豪客赛=0%）选"全部"时 AshTree 坐标保留；OldRustyKey 沉船墓场1层（全模式=0%）在"全部"时也被隐藏

## PWA 图标内容改为 "DND" + 去掉白色边框 + iPhone 风格圆角

- **原因**：原图标仅显示字母"D"，用户要求改为"DND"；边缘有白色半透明环状边框需移除
- **变更**：`web/public/icons/icon-192-v2.png`、`web/public/icons/icon-512-v2.png` — 内容从蓝色字母"D"改为粗体"DND"（DejaVuSans-Bold，字号 ≈ 尺寸 × 30%，RGB(200,220,255)）；移除白色边框像素；应用 iPhone 风格 squircle 圆角（半径 ≈ 尺寸 × 22%）
- **变更文件**：
  - `web/public/icons/icon-192-v2.png`
  - `web/public/icons/icon-512-v2.png`
  - `web/public/favicon.ico` — 同步更新为 "DND" 图标（含 16/32/48/64 多尺寸）

# 2026-07-15 会话修改记录

## 稀有掉落阈值调整 2.5→1.5 + 零豪客赛掉落显示修复

- **原因**：用户反馈列表页「稀有掉落」分组过严（2.5 阈值），且 Billet（小木块）等只有 PVE 爆率的掉落详情页无数据
- **阈值修改**：`web/src/pages/ListPage.tsx:57` 列表页稀有掉落分组阈值 2.5 → 1.5
- **零豪客赛修复**：`api/src/lootdrop_builder.py:525-548` 移除对 `豪客赛=0` 条目的过滤。原逻辑只保留豪客赛爆率 > 0 的怪物，但 Billet（木材掉落）的 AshTree 在 PVE 模式有爆率（65%）而豪客赛权重为 0，导致所有怪物被过滤、JSON 文件未生成。修改后所有有坐标的怪物均保留
- **变更文件**：
  - `web/src/pages/ListPage.tsx` — `2.5 → 1.5`
  - `web/src/pages/LootdropDetailPage.tsx` — 阈值回滚（用户要求只改列表页）

### 小型神器分类恢复

- **原因**：提交 `0f29744` 修复水合错误时重构 `groupLootdrops()`，无意中移除了 `hr100`（小型神器）分类逻辑。后端一直正常生成 `hr100` 标记，仅前端不消费
- **变更**：`web/src/pages/ListPage.tsx` — `IndexEntry` 补回 `hr100?: boolean` 类型定义，`groupLootdrops()` 恢复 `hr100` 数组、分类判断、和"🪙 小型神器"分组

### 提交 0f29744 误删功能批量恢复

- **原因**：审计发现提交 `0f29744` 在删 `dataUrl` 导入时，同一文件中的不相关代码被整体回退到旧版本
- **恢复内容**：
  - 阈值 2.5 → 1.0（用户要求 1.0）
  - `NavBar.tsx` search bar 恢复 `scrollIntoView` 自动滚动到搜索框
  - `NavBar.tsx` 搜索框宽度恢复 `flex: 0 0 360px`（被改为 `flex: 1 1 280px`）
  - 删除死代码 `web/src/utils/dataUrl.ts`（无人引用的残留文件）

### 列表页数据源统一 + search_index 补 hr100

- **原因**：列表页有两个数据源——SSR 用 `{page}.json`、运行时用 `search_index.json`，加 `hr100` 时只改了前者，导致客户端导航无小型神器分组。详情页只有一个数据源没有此问题
- **变更**：
  - `api/src/index_export.py:264` — `search_index` 的 lootdrop 条目补上 `hr100` 字段
  - `web/scripts/ssg.mjs:149` — 列表页 SSR 数据改为从 `search_index.json` 提取（过滤 `page`），不再读 `{page}.json`，消除两套数据源不一致的隐患

## 掉落详情页 spawn_rate 修正：使用原始生成器关键词 + 允许 0 值入缓存

- **原因**：用户反馈 `WanderlightLantern` 掉落页面中「中型诡污(特殊)」显示 100% 生成概率，实际应为 0%（该实体在 ChestLarge 中的权值为 0）。错误地使用了容器实体（ChestLarge=100%）的生成概率
- **根因**：
  1. `lootdrop_builder.py:414-416` 在 `keyword != original_keyword` 时使用 `_c["keyword"]`（如 "Mimic_Medium_MidLevel"）查 `spawn_rate_detail`，但 `spawner_entries` 表的 key 是 `original_keyword`（如 "ChestLarge"），导致查不到时返回默认值 100
  2. `drop_rate.py:155,161,164` 中缓存条件 `sr > 0` 排除了 spawn_rate=0.0 的合法值，该条目根本未入缓存
- **变更**：
  - `api/src/lootdrop_builder.py:415` — 查 `spawn_rate_detail` 时用 `original_keyword` 替代 `keyword`
  - `api/src/lootdrop_builder.py:416,418` — `.get()` 默认值 100 → 0
  - `api/src/drop_rate.py:155,161` — `spawn_rate_cache` 条件 `sr > 0` → `sr > -1`（允许 0 值存储）
  - `api/src/drop_rate.py:164` — `spawn_rate_detail` 条件 `sr > 0` → `sr > -1`（允许 0 值存储）
- **验证**：WanderlightLantern 掉落详情中「中型诡污(特殊)」spawn_rate 100% → 0.0%，「巨型诡污(特殊)」保持 0.01%

## spawn_rate 精度 2→4 位 + 公式 100 前置

- **原因**：`round(40/1000040*100, 2)` = 0.0，0.004%被吞掉。文档要求 4 位精度但实际代码用 `round(x, 2)`
- **变更**：
  - `api/src/db/importers/spawners.py` — `round(x, 2)` → `_round_rate(x)`，公式 `x/总池*100` → `100*x/总池`
  - `api/src/search_engine.py` — 同上
  - `docs/REFERENCE.md:264` — 更新公式示例
- **验证**：ChestLarge 中 Unique 宝箱怪 `40/1000040*100` 从 0.0 → 0.004%
  - `api/src/lootdrop_builder.py` — 移除豪客赛=0 过滤

## 彻底修复 React #418/#423 hydration 错误（全站 1235 页面 0 错误）

- **原因**：React 18 `hydrateRoot` 对无 SSR 内容的空容器会导致双重渲染（hydration → CSR fallback），期间模块级 `meta.json` fetch 可能完成并突变 `cachedDate`，造成 hook 数量不匹配。受影响页面为所有无 SSR 渲染的页面（`dungeon_modules` 列表页 + 详情页，共 244 个）。
- **变更文件**：`web/src/main.tsx`
- **改动**：检查 `root.hasChildNodes()` — 有 SSR 内容时用 `hydrateRoot`，无 SSR 内容时用 `createRoot` 避免 hydration 失败
- **验证**：Playwright 全站 1235 页测试，0 个 #418/#423 错误；剩余的 `Timeout` 是测试 100 并发造成的性能问题，非应用错误

## OfflineDetector SSR 不匹配修复

- **原因**：OfflineDetector 在 SSR 时 `useState(typeof navigator !== 'undefined' && !navigator.onLine)` 返回 `false`，但客户端 hydrate 时 `navigator.onLine` 为 `true`，导致返回 `null`，引发 #418
- **变更文件**：`web/src/components/OfflineDetector.tsx`
- **改动**：`useState(false)` 固定初始值，`useEffect` 在客户端才设置正确状态

## 数据版本预加载修复 + Playwright 调试文档

- **原因**：SSG 构建时序问题 — 版本号在 Vite 构建后才计算，导致 `VITE_DATA_VERSION` 为空
- **变更文件**：`web/scripts/ssg.mjs`、`web/vite.config.ts`
- **改动**：版本号计算移至构建前（step 0），`process.env.VITE_DATA_VERSION` 提前设置
- **文档**：新增 `docs/DEBUG_HYDRATION_WITH_PLAYWRIGHT.md`（调试指南）

# 2026-07-14 会话修改记录

## fix: variant 详情页综合爆率使用 variant_gdi 重算

- **原因**：variant 详情页（如 LargeScroll_7001）的 `coords[].score` 继承自 base 物品的 `_hk_lookup`（`get_group_drop_rates`），而 `group_drop_info` 用 `get_variant_group_drop_rates(luck_grade=7)` 计算，两者不一致。表现为 group_drop_info 显示 0.1111% 但综合爆率显示 2.4815%。
- **变更文件**：`api/src/lootdrop_builder.py` — variant 分支新增 per-coord score 从 `variant_gdi` 重算
- **关键映射**：variant 分支的 `coords[].score` 现在用 variant_gdi 的 `豪客赛` 值重算，score = `spawn_rate * 豪客赛 / 100`，与 group_drop_info 对齐

## 新增"小型神器"分类 — 豪客赛 100% 爆率 + 低生成率装备

- **原因**：用户需要从掉落表页面快速筛选豪客赛模式下必定掉落但生成率低的稀有装备
- **筛选条件**：`drop_rates.豪客赛 >= 100`（怪物必定掉落）AND `spawn_rate < 5`（生成率低于 5%）
- **变更文件**：
  - `api/src/lootdrop_builder.py` — 构建索引时扫描 `group_drop_info` 中两个条件同时满足的条目，标记 `hr100: true` 写入 `lootdrops.json`
  - `web/src/pages/ListPage.tsx` — `groupLootdrops()` 增加 `hr100` 分类逻辑，新增"🪙 小型神器"分类（位于"🏺 神器"之后）
- **数据流**：后端管道计算 → lootdrops.json 索引含 `hr100` 字段 → 前端 CSR 加载后按分类渲染
- **共 7 个物品**被标记：吸血之刃、迷乱之刃、荆棘之盾、缠丝长裤、静谧长靴、流光灯笼、盗法者权杖

## 导航栏搜索框点击放大镜后滚动到可视区域

- **原因**：手机端任务详情页底部点击放大镜搜索后，`inputRef.current?.focus()` 不会自动滚动页面，用户看不到搜索框被填充
- **变更文件**：`web/src/components/NavBar.tsx:79-85`
- **改动**：`NavBar.useEffect`（消费 `searchQuery`）中在 `focus()` 后添加 `scrollIntoView({ behavior: 'smooth', block: 'center' })`

## 导航栏搜索框宽度改为 8 字符

- **原因**：搜索框默认 `flex: 1 1 280px` 过长，经尝试后改为 `flex: 0 0 360px`
- **变更文件**：`web/src/components/NavBar.tsx:208`

## 修复 apple-touch-icon 指向旧图标

- **原因**：`index.html` 中 `<link rel="apple-touch-icon">` 仍指向 `/icons/icon-192.png`（旧版无圆角），iOS 添加到主屏幕时显示方形图标
- **修复**：改为 `/icons/icon-192-v2.png`（圆角版）
- **变更文件**：`web/index.html:12`

## 修复 webp 图片在 iOS 14 不显示

- **原因**：上次修复只改了 `MapPanel.tsx` 的 `aspect-ratio` → `paddingBottom`，但 `DungeonModuleGroupPage.tsx` 和 `ExplorePage.tsx` 仍直接使用 CSS `aspect-ratio` 属性。iOS Safari < 15 不支持 `aspect-ratio`，div 高度为 0 → `backgroundImage` 不可见
- **修复**：两个页面改为 `paddingBottom` 占位 + `position: absolute` 内层 div 渲染背景图（与 MapPanel 相同模式）
- **变更文件**：
  - `web/src/pages/DungeonModuleGroupPage.tsx:172` — 模块卡片缩略图
  - `web/src/pages/ExplorePage.tsx:157` — 探索页模块缩略图

## 移动端排版换行修复

- **原因**：手机屏幕窄，多处 flex 容器未设置 `flexWrap: 'wrap'`，导致内容溢出或强制同行显示
- **变更文件**：
  - `web/src/components/NavBar.tsx` — 导航栏容器 + 右侧按钮区加 `flexWrap: 'wrap'`，搜索框 `flex: '1 1 280px'`
  - `web/src/pages/DetailPage.tsx` — "参考爆率" 容器 + 变体图例内层 flex 加 `flexWrap: 'wrap'`
  - `web/src/pages/LootdropDetailPage.tsx` — "参考爆率" 容器 + 怪物图例内层 flex 加 `flexWrap: 'wrap'`
  - `web/src/pages/QuestNPCPage.tsx` — 搜索框包装为 `width: 100%` 独立一行；NPC 卡片名+任务数改用 `display: flex; flexWrap: wrap`
  - `web/src/pages/QuestNPCDetailPage.tsx` — 搜索框 `width: 100%` 独立一行；h1 标题加 `flexWrap: 'wrap'`

## 修复 SW runtime caching urlPattern 正则不匹配问题

- **原因**：`vite.config.ts` 中 Workbox runtime caching 的 `urlPattern` 使用了 `^` 锚定正则（`/^\/data\/json\//`），Workbox 用 `regex.test(request.url)` 匹配完整 URL（含协议/域名），导致 `df5-data-json` 和 `df5-data-img` 缓存池**永远不会被写入**
- **后果**：离线时 HTML（NetworkFirst）可正常加载，但数据 JSON fetch 全部失败 → 详情页显示"数据加载中"
- **修复**：改为函数式 `({ url }) => url.pathname.startsWith(...)` 匹配 pathname
- **变更文件**：`web/vite.config.ts`（data-json、data-img、meta 三个缓存规则）

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

| 优化                       | commit    | 效果             |
| -------------------------- | --------- | ---------------- |
| compact JSON               | `4109ee1` | 省 15s           |
| fuzzy candidate_ids 匹配   | `764acc7` | 省 1s            |
| 移除 variant_suffixes 冗余 | `ec15e98` | 省 44s           |
| 修复 variant 后缀计算      | `3be3910` | 恢复正确后缀     |
| 修复 _8001 变体显示        | `e2f3e6a` | 恢复神器变体切换 |

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

| 代码库 group  | 基础键                                       | 公式                        | 结果示例                  |
| ------------- | -------------------------------------------- | --------------------------- | ------------------------- |
| GoblinCave    | `Slot_GoblinCave_1stFloor`                   | base + "1层"                | 哥布林洞穴1层             |
| FireDeep      | `Slot_GoblinCave_1stFloor`                   | base + "2层（`_2ndFloor`）" | 哥布林洞穴2层（赤焰深窟） |
| IceCavern     | `Slot_IceCavern_1stFloor`                    | base + "1层"                | 寒冰洞穴1层               |
| IceAbyss      | `Slot_IceCavern_1stFloor`                    | base + "2层（`_2ndFloor`）" | 寒冰洞穴2层（寒冰深渊）   |
| Ruins         | `Slot_TheCrypts_1stFloor`                    | base + "1层"                | 废墟1层                   |
| Crypt         | `Slot_TheCrypts_1stFloor`                    | base + "2层（`_2ndFloor`）" | 废墟2层（地穴）           |
| Inferno       | `Slot_TheCrypts_1stFloor`                    | base + "3层（`_3rdFloor`）" | 废墟3层（炼狱）           |
| ShipGraveyard | `Text_WB_DungeonSlot_ShipGraveyard_1stFloor` | base + "1层"                | 沉船墓场1层               |

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

## InstallPrompt 增加关闭按钮

- **原因**：安装 DND闪电指南 提示无法关闭，用户不需要时只能等待浏览器自动隐藏
- **变更文件**：`web/src/components/InstallPrompt.tsx`
- **改动**：新增 `dismissed` 状态 + ✕ 关闭按钮，点击后隐藏 prompt；关闭按钮绝对定位在卡片右上角

## MapPanel 兼容 iOS 14（不支持 aspect-ratio）

- **原因**：iOS 14.6 不支持 CSS `aspect-ratio` 属性（iOS 15+ 才支持），MapPanel div 高度为 0 导致背景地图图片不可见
- **变更文件**：`web/src/components/MapPanel.tsx`
- **改动**：将 `aspectRatio` 改为 `padding-bottom` 百分比 hack + 内层 `position: absolute` 容器，兼容所有浏览器；现代浏览器性能无差异

## CDN 缓存破坏 — 数据路径版本化

- **原因**：Cloudflare Pages CDN 和 SW 缓存无法在游戏更新时自动失效，用户看到旧版本数据。查询参数（`?_v=`）不可靠（CF 默认忽略 query string 作为缓存键）
- **方案**：构建时将数据版本（Unix 时间戳）通过 Vite `define` 注入为全局常量 `__DATA_VERSION__`，`dataUrl()` 将请求路径从 `/data/json/foo` 变换为 `/data/<base36>/json/foo`（base36 缩短时间戳，如 `1784008247` → `ti5hp2`）→ 版本变化时路径完全不同 → CDN 无歧义视为新资源
- **不版本化的资源**：图片（很少变化）、meta.json（固定路径用于版本检测）
- **构建流程**：
  1. `ssg.mjs` 在 `vite build` **之前**扫描所有 JSON 文件 mtime 计算 `dataDate`，设置 `VITE_DATA_VERSION` 环境变量
  2. `vite build` 时 Vite `define` 将 `__DATA_VERSION__` 替换为时间戳字符串，嵌入 JS bundle
  3. `vite build` 后 `ssg.mjs` 复制 `dist/data/json/` → `dist/data/<base36>/json/`（移除 versioned 副本中的 `meta.json`）
  4. `meta.json` 保持固定路径 `dist/data/json/meta.json`
- **SW 兼容**：`vite.config.ts` 中 SW 路由正则 `/^\/data\/\w+\/json\//` 匹配 base36 版本化路径
- **关键函数** `dataUrl()`：`/data/json/foo` → `path.slice(5)` 截断 `/data` 后插入 `/data/<base36>` → `/data/ti5hp2/json/foo`
- **版本更新机制**：`useDataVersion` 从 `/data/json/meta.json` 获取最新时间戳 → `setDataVersion()` 数值仅升不降，长会话能自动切到新版本 URL
- **`_headers` 最终状态**：仅 `meta.json` 设 10 分钟缓存（`/data/json/* → max-age=600`），其他全走 Cloudflare Pages 默认缓存策略
- **变更文件**：`dataUrl.ts`（新建）、`vite.config.ts`、`ssg.mjs`、`vite-env.d.ts`、`_headers`、`index.html`、`useDataVersion.ts`、`useDungeonModules.ts`、`useSearchIndex.ts`、`MapPanel.tsx`、所有 11 个页面

## 删除 SWUpdateBanner — SW 更新静默化，不再打扰用户

- **原因**：`SWUpdateBanner.tsx` 用 `workbox-window` 额外注册 SW，弹横幅让用户点"刷新以应用"。但 vite.config.ts 已设 `registerType: 'autoUpdate'`，Workbox 生成的 SW 自带 `skipWaiting()`，新 SW 安装后自动激活，完全不需要用户干预。且双注册（`registerSW.js` + `workbox-window`）竞争，用户要点两次才生效
- **教训**：此文件上次被删后又因"用户会看到旧内容"的理由被加回。错。`autoUpdate` + `skipWaiting()` 激活后，`StaleWhileRevalidate` / `NetworkFirst` 策略自动用新数据更新缓存，用户不刷新也会在后台同步。**客户不需要知道 SW 更新了，更不需要手动确认**
- **变更文件**：
  - 删除 `web/src/components/SWUpdateBanner.tsx`
  - `web/src/AppInner.tsx` — 移除 import 和 `<SWUpdateBanner />` 标签

## 坐标位置去重 + 矿石品质提取与前端的品质切换

- **原因**：钴矿类掉落数据中同一物理点位因品质等级（VeryLow/Low/Med/High）被导出为多条记录，导致计数膨胀（5点位 × 4品质 = 20条）。前端按 (x,y,z) 去重后显示正确点位；同时提取品质字段支持切换查看
- **公式**：
  - 品质概率：豪客赛→High 100%，普通赛→Low 90%+Med 10%，PVE→VeryLow 100%
  - 钴矿组在洞坑大厅展现：默认"高品质(豪客赛100%)"去重后 5 点位
- **变更文件**：
  - `api/src/translator.py` — `build_coord_out()` 从 keyword/original_keyword 提取品质后缀
  - `api/src/lootdrop_builder.py` — inline coord 生成同样提取 quality 字段
  - `web/src/pages/LootdropDetailPage.tsx`：
    - `LootdropCoord` 接口新增 `quality?: string`
    - mapGroups 循环中按 `qualityFilter` 过滤坐标
    - `computeModuleScore` 支持 `quality` 字段
    - `visibleCountByMonster` / `bottomCount` 按 (translation,x,y,z) 去重计数
    - 新增品质切换 UI（默认 High，点击切换品质/显示全部）
- **CobaltOres 数据**：重新运行管道后每组品质各 5 坐标（钴矿组）/ 13 坐标（钴矿随机）

## 新增物品坐标链式反查（lootdrop chain）

- **原因**：`TearofHrimthurs`（霜巨人之泪）虽然存在于 DB 中，但因 spawner 文件名缺 m（`TearofHrithurs` vs `TearofHrimthurs`）导致坐标匹配失败，物品表不显示。更深层问题是管道缺少 lootdrop 容器→坐标→物品的链式反查机制
- **变更文件**：
  - `api/src/collector.py` — 通过 `lootdrop_rate_items→lootdrop_groups→spawner_entries` 三表 JOIN 构建 `item_coord_chain_map`（529 个物品 → spawner keyword 映射）
  - `api/src/entity_export.py` — `export_items()` 新增 `item_coord_chain_map` 参数，直接坐标查找失败时作为回退（跳过 `filter_coords`，因为 spawner keyword 不是物品名）
  - `docs/REFERENCE.md` — 新增"物品坐标链式反查"章节
- **关键映射**：`TearofHrimthurs` → 链式反查到 spawner `TearofHrithurs` → 坐标 `IceAbyss_HoundVale` (x=-40, y=1430, z=-1187.73)
- **影响**：物品索引从 94 增至 517 个（新增 423 个 lootdrop 容器坐标物品）

## 2025-07-17 会话修改记录

### 变体切换组件提取 + 导航刷新修复

**原因：** `/lootdrops/WarMaul_6001/` 导航到 `/lootdrops/WarMaul_8001/` 时页面不刷新，需 F5 才能显示正确标题和分类按钮。

**变更文件：**

- `web/src/components/VariantSwitch.tsx` — 新建变体稀有度切换组件，从 LootdropDetailPage 提取
- `web/src/pages/LootdropDetailPage.tsx` — 内联变体按钮替换为 `<VariantSwitch>`；导航时清除 `_preloadedLootdrop` 缓存

**关键修复：**

- 模块级 `_preloadedLootdrop` 缓存在客户端导航后仍保留旧页面数据，干扰 useEffect 数据拉取逻辑
- 在 `name` 变化的 useEffect 中同时清除 `_preloadedLootdrop` 和 `_preloadedLootdropUrl`，确保下次 fetch 不被跳过

### 宝藏堆神器爆率缺失修复

**原因：** `build_and_save_lootdrop_details` 中 `monsters_out` 的每个怪物条目未填充 `drop_rates` 字段，导致前端地图卡片中不显示爆率。此问题在 _8001 神器变体页面（继承基础物品的完整怪物列表后）尤为明显。

**变更文件：**

- `api/src/lootdrop_builder.py` — 在 `max_score` 计算后，聚合 `group_drop_info` 中各模式的最高爆率，注入到每个怪物条目的 `drop_rates` 字段

**修复效果：**

- 所有 lootdrop 详情页的怪物现在都有 `drop_rates`（各模式下跨组取最大值）
- 前端地图卡片中怪物名称旁正确显示 `[豪客赛:X%]` 等爆率信息
- WarMaul_8001 页面：宝藏堆 显示 `[豪客赛:0.0107%][逆袭赛:0.0107%]`

### 宝藏堆神器爆率调查与 compute_drop_rate 修复

**调查结论：** 宝藏堆在 RondelDagger_8001 页面显示的神器爆率 `[豪客赛:0.0107%]` 是**正确的**。

**数据链路：**

- `Hoard01_3` 的候选 LDG 包含 `ID_LootDropGroup_SuperHoard`
- SuperHoard 在 mode=3(豪客赛) floor=23 绑定 `ID_Lootdrop_Drop_HoardWeaponArmor`
- 该 LootDrop 直接包含 `WarMaul_8001` 条目（LuckGrade=8）
- 对应的 `ID_Droprate_Hoard_WeaponArmor_3023` 有 LuckGrade 8 weight=30（非零）

用户检查的 `ID_Droprate_Hoard_Treasure_*` 的 LG8=0，但 **SuperHoard 走的是 WeaponArmor 通道**，该通道的 droprate 文件有 LG8 数据。

**bug：** `compute_drop_rate` 在 item fallback 时使用基础物品的 luck_grade（如 WarMaul→5）计算 pool weight，而非使用变体后缀的 luck_grade（如 8001→8）。导致某些场景下神器爆率使用了非神器的权重。

**修复：** 从 item_name 的 `_\d{4}` 后缀提取 luck_grade，用于 pool weight 查询；shared count 仍使用物品本身的 luck_grade（与 `compute_variant_rate` 的行为一致）。

**变更文件：**

- `api/src/drop_rate.py` — `compute_drop_rate` 新增 `_variant_luck_grade` 提取逻辑

### get_group_drop_rates 分离主/备 LDG 修复

**原因：** `_get_candidate_ids` 的 `_no_num` fallback（去尾数后缀）导致 `Hoard01_3`（宝藏堆）继承 `Hoard01_9`（超级宝藏堆）的 `ID_LootDropGroup_SuperHoard` LDG，进而拿到非法的 LuckGrade 8 神器爆率。

**修复：** `get_group_drop_rates` 将候选 LDG 分为 `_primary_set`（spawner_ldg 直连）和 `_fallback_set`（entity_ldg_all + 去尾数聚合）。对于 `luck_grade >= 8` 的变体物品，仅使用 `_primary_set` 计算爆率，不使用 fallback LDGs。

**影响：**

- 宝藏堆（Hoard01_3）→ 神器爆率 = 0 ✓
- 超级宝藏堆（SuperHoard01_9）→ 神器爆率正确（Primary 直连 SuperHoard LDG）✓
- 其他实体（AncientStingray 等）→ 不变 ✓
- 基础物品爆率（非变体）→ 不变（走原有 primary+fallback 逻辑）

**变更文件：**

- `api/src/drop_rate.py` — `get_group_drop_rates` 分离 primary/fallback LDGs，LG≥8 仅用 primary

### 回退怪物级 drop_rates 注入

**原因：** 前端地图分组头部"参考爆率"已展示完整爆率信息，无需在每个地图卡片怪物名旁重复显示 `[豪客赛:X%]`。`N种选M`/`N点选1` 等变体展示不受影响（数据在 coords 的 variant_count 字段）。

**操作：** 删除 `lootdrop_builder.py` 中 `max_score` 计算后聚合 `group_drop_info` 注入 `monsters[]` 每个条目的 `drop_rates` 字段的代码块。

**变更文件：**

- `api/src/lootdrop_builder.py` — 移除 `_agg_drop_rates` 聚合与注入逻辑

## 显示每个 ObjectLinker 子池的实体翻译名列表 + 种类数 + 刷怪点数

- **原因**：变体显示"11种选6"过于笼统，且之前显示 `(c3子池2种选3)` 应改为直接显示子池内的实体翻译名列表
- **变更文件**：
  - `api/src/db/repositories/coordinates.py` — `get_sub_group_pool_sizes` → `get_sub_group_pool_info`，同时返回 `(pool_size, entity_names[])`
  - `api/src/db/__init__.py` — 暴露 `get_sub_group_pool_info()` 方法
  - `api/src/collector.py` — 调用后用 NameResolver 翻译子池内实体名；参数名改为 `_sub_pool_info`
  - `api/src/translator.py:build_coord_out` — 参数 `sub_pool_sizes` → `sub_pool_info`；输出 `sub_pool_size` + `sub_pool_names`
  - `api/src/entity_export.py` — 参数名同步改为 `sub_pool_info`
  - `web/src/types/data.ts` — Coord 接口新增 `sub_pool_names?: string[]`
  - `web/src/pages/DetailPage.tsx` — 变体标签显示 `(骷髅冠军、GrimveilCloak2种选3)` 格式
- **效果**：SkeletonChampion 地穴模块：`(骷髅冠军、GrimveilCloak2种选3)(骷髅冠军、幽鬼、骷髅弩手...7种选1)`
- **验证**：HTTP 200 ✓

## 修复子池实体名翻译（GrimveilCloak→阴森帷幕披风）

- **原因**：GrimveilCloak 是 item 类型实体（翻译键 `Text_DesignData_Item_Item_GrimveilCloak_5001`），但子池名称解析代码只处理 monster 和 props，未处理 item 类型，导致回退为英文名
- **变更文件**：
  - `api/src/collector.py` — 子池名翻译新增 `elif "item" in _cls_types` 分支，传入正确的 translation_key 和 scope
- **效果**：C_3 子池显示 `(骷髅冠军、阴森帷幕披风2种选3)`，C_11 显示 `(骷髅冠军、幽鬼、骷髅弩手、骷髅弓箭手、骷髅长枪兵、骷髅双手剑士、阴森帷幕披风7种选1)`
- **验证**：HTTP 200 ✓

## SSG 页面标题修复（英文名 + 中文名）

- **原因**：Quick 模式 SSR 注入数据不全（只有 `name`/`translation`），组件提前 return 导致 `<Helmet>` 不渲染，title 为空；详情页标题缺少英文名
- **变更文件**：
  - `web/src/pages/DetailPage.tsx` — SSR state init 接受无 coords 的 entity
  - `web/src/pages/LootdropDetailPage.tsx` — SSR state init 接受无 monsters 的 item
  - `web/src/pages/DungeonModuleDetailPage.tsx` — SSR state init 接受仅有 name 的 module
  - `web/src/pages/QuestItemGroupPage.tsx` — SSR loading 状态修复（不再因 entities 为空阻塞 Helmet）
  - 所有详情页标题格式统一为 `{translation}{name} {typeChinese}{typeEnglish}`（如 `献魂册SoulDevotedFolio 掉落来源Source`）
- **效果**：3096 个 SSG 页面全部有正确 SEO 标题（含英文名 + 中文分类）
- **验证**：curl 检查 items/monsters/props/lootdrops/quest_items/quest_npc/dungeon_modules 各类型页面 title 均正确 ✓

## 添加 translation_EN（英文本地化名称）替代 asset name

- **原因**：标题中使用原始 asset name（如 `HeaterShield`、`Mimic_Large_Flat`），需要改用游戏英文本地化的正确英文名（如 `Heater Shield`、`Mimic`）
- **变更文件**：
  - `api/src/config.py` — 添加 `EN_GAME_JSON` 路径指向 `en/Game.json`
  - `api/src/db/_helpers.py` — `load_game_json()` 支持缓存 + 可指定路径；新增 `load_en_game_json()`
  - `api/src/collector.py` — 加载英翻创建 `resolver_en`，传入所有 export 函数
  - `api/src/translator.py` — （无改动，复用 NameResolver 逻辑）
  - `api/src/entity_export.py` — 所有三种实体导出均注入 `translation_EN` 字段
  - `api/src/lootdrop_builder.py` — `build_loot_index` + `build_and_save_lootdrop_details` 添加 `translation_EN`（含 variant 详情页）
  - `api/src/module_builder.py` — `build_modules_map` + `build_and_save_module_coords` 添加 `translation_EN`
  - `api/src/index_export.py` — `generate_quest_items_groups` 接受 `resolve_en_name` 参数
  - `web/src/types/data.ts` — `ItemEntity`/`MonsterEntity`/`PropsEntity`/`DungeonModule` 增加 `translation_EN?: string`
  - `web/src/types/quest.ts` — `NPCEntry` 增加 `translation_EN?: string`
  - `web/src/pages/DetailPage.tsx` — title/og:title 改用 `translation_EN` as fallback
  - `web/src/pages/LootdropDetailPage.tsx` — title/og:title 改用 `translation_EN`；`LootdropItem` 接口增加 `translation_EN`
  - `web/src/pages/DungeonModuleDetailPage.tsx` — title 改用 `translation_EN`；SSR loading 改为 `!effectiveCoords && !effectiveModSsr`
  - `web/src/pages/QuestNPCDetailPage.tsx` — title 改用 `translation_EN`
  - `web/scripts/ssg.mjs` — quick mode SSR 注入 `translation_EN`
- **效果**：标题显示正确英文名: `献魂册Soul-Devoted Folio`、`斗盾Heater Shield`、`信徒会所Admirer's Room`
- **验证**：3096 pages, 检查各类型 title 均使用翻译后英文名 ✓

- **dev 后台启动修复**：`CLAUDE.md` dev 分支启动web 命令改为 `(npm run dev ... &>/dev/null &)` 避免阻塞 TUI
- **dev 版本化数据路径修复**：`vite.config.ts` 添加 `dev-versioned-data` 中间件，将 `/data/{ver}/json/*` 请求重写为 `/data/json/*`，使 `dataUrl()` 生成的版本化路径在 dev server 上可正常访问
- **搜索索引加载容错**：`useSearchIndex.ts` 添加 `.catch(() => setLoading(false))`，防止 fetch 失败时加载动画永远不停
- **列表页路由参数缺失修复**：`ListPage.tsx` — 从 `useLocation().pathname` 末段推导 `page`，修复 `/items` `/monsters` `/props` `/lootdrops` 四个显式路由因缺 `:page` 参数导致页面无数据的问题。`useEffect` 已有 valid pages 白名单守卫，不会误触发。
- **分析结论**：`/lootdrops` 无需重定向到 `/zh-Hans/lootdrops`——`withLangPrefix(DEFAULT_LANG)` 设计即去前缀，`/lootdrops` 就是 zh-Hans 版本。SSG 的 `localizedPath` 同样对默认语言返回无前缀路径。

## 统一语言前缀路由重构 (v0.10)

- **原因**：双路由树（有/无 lang 前缀）导致 `:page` 参数丢失 bug（`/lootdrops` 匹配显式路由缺少 `:page` → ListPage 无数据），且 `:lang` 和 `:page` 动态段互斥难以区分。
- **方案**：zh-Hans 也使用 `/:lang/` 前缀，全语言统一路由结构。非前缀旧路径通过 `LegacyRedirect` 组件跳转到 `/zh-Hans/...`。
- **变更文件**：
  - `LanguageContext.tsx` — `withLangPrefix` 移除 `DEFAULT_LANG` 去前缀逻辑，始终返回 `/:lang/path`
  - `AppInner.tsx` — 移除所有非前缀路由，仅保留 `/:lang/...` 树 + `*` catch-all `LegacyRedirect`。`LegacyRedirect` 用 `useEffect` 检测路径首段是否支持语言，不支持则 `window.location.replace` 到 `/zh-Hans/...`
  - `ssg.mjs` — 所有路由 `path`/`file` 以 `/${DEFAULT_LANG}/` 前缀生成（如 `/zh-Hans/items`）；`routeDataKey` 先剥离 lang 前缀再匹配；`localizedPath` 先剥离已有前缀再添加目标 lang；本地化循环将默认语言文件路径前缀剥离后写入目标目录；`NON_DEFAULT_LANGS` 变量移除
  - `ListPage.tsx` — `useParams<{page}>` 从 `/:lang/:page` 正常获取，移除 pathname fallback
- **SSG 输出结构**: `dist/index.html` → `/`; `dist/zh-Hans/...` → 简体中文; `dist/en/...` → English; etc.
- **验证**: dev server `:8090` 所有路由 HTTP 200; TSC + ESLint + Prettier 通过
- **硬编码路径修复**: 全站 9 个文件中的 `Link`/`navigate` 路径补上 `/${lang}/` 前缀（HomePage、VariantSwitch、DungeonModulesPage、DungeonModuleGroupPage、QuestItemsPage、QuestNPCPage、QuestNPCDetailPage、LootdropDetailPage）；NavBar 面包屑改用 `stripLangPrefix` + `lang` 前缀，不再显示语言代码导航按钮
- **Variant name i18n**: `api/src/collector.py` `_vtr` 从 `list[str]`（已解析中文名）改为 `list[dict]`（`{translation_key, name}`），保留 translation_key 供前端多语言查询；`api/src/lootdrop_builder.py` `_get_variant_rarity` 返回 `{name, translation_key}` 而非纯文本；`api/src/locale_builder.py` `_load_used_keys` 改为递归 `_collect_keys()` 扫描所有嵌套 `translation_key` 字段，确保 variant_rarity/variant_names 中的 key 被纳入 locale 文件；前端 `VariantNameEntry` 类型 + `t(translation_key, name)` 展示；`RARITY_COLORS` 由中文 key 改为英文 rarity tag 防止多语言不匹配；`VariantSwitch.tsx` 引入 `useLocale` 实现多语言 label

## 怪物名称多语言 + ui.list.variant 模板化

- **原因**：Lootdrop 列表页和详情页的怪物名（如"远古刺鳐"）在英文及其他语言下仍显示中文；列表页 `-目标-`/`变体` 标签未使用 locale key
- **变更文件**：
  - `api/src/lootdrop_builder.py` — `build_loot_index()` 在收集 `monster_translations` 的同时并行收集 `monster_translation_keys`，存入 loot index
  - `api/src/index_export.py` — 将 `monster_translation_keys` 透传到 search index
  - `web/src/pages/ListPage.tsx` — `IndexEntry` 加 `monster_translation_keys` 字段；怪物名改为 `t(monster_translation_keys[i], monster_translations[i])` 逐条解析；`-目标-` → `ut('ui.list.target')`；`[N变体]` → `ut('ui.list.variant').replace('{count}', ...)`；分隔符按语言区分（中文/日文用`、`，其余用`, `）
  - `web/src/pages/LootdropDetailPage.tsx` — `LootdropMonster` 加 `translation_key`；h1 怪物名/按钮/坐标表均改为 `t(m.translation_key, m.translation)`；坐标汇总改为 `ut('ui.detail.coord_summary')`；分隔符语言化
  - `web/src/i18n/uiLocale.ts` — 所有 10 种语言的 `ui.list.variant` 从纯 label 改为 `{count}变体`/`{count} Variants`/等模板格式
- **关键逻辑/映射关系**：详情页 JSON 已有 `translation_key` per monster（`lootdrop_builder.py:404`），只需前端接口+渲染适配；列表页需后端补充 `monster_translation_keys` 到 search index
- **验证**：管道输出含 `monster_translation_keys` 字段；TSC + Prettier + Black 通过

## docs: GoldChest 详情页 SSG 样板计划

- **原因**：当前多语言详情页复制中文 SSR 正文会与客户端按 URL 使用的语言 UI 发生 hydration 文本不一致；逐详情、逐语言完整 SSR 的成本过高。
- **变更文件**：`docs/plans/SSG_DETAIL_TEMPLATE.md` — 新增详情 SSG 空壳样板设计。
- **关键逻辑/映射关系**：每种语言 `props/GoldChest` → 一次 SSR 样板 → 复制至同语言 items/monsters/props 详情路由；每页独立替换目标实体 title；`isDetailTemplate` → 首屏固定 `RareModule_1x1.webp` → CSR 请求当前 `page/name` JSON 后替换真实内容。
- **范围限制**：`LootdropDetailPage` 数据结构独立，不复用 GoldChest 样板，待后续确定专用样板。

# 2026-07-27 会话修改记录

## feat: 详情页 GoldChest SSG 样板

- **原因**：items、monsters、props 详情页逐路由 SSR 成本过高，且需要保留稳定的地图卡片首屏结构。
- **变更文件**：`web/scripts/ssg.mjs`、`web/src/pages/DetailPage.tsx`、`web/src/components/NavBar.tsx`、`web/src/types/data.ts`。
- **关键逻辑/映射关系**：每种语言仅 `render()` 一次 `/:lang/props/GoldChest`；其 HTML 复用于三类详情页，内联数据改写为 `目标 page/name -> GoldChest 样板 + isDetailTemplate`，而 `<title>`、canonical、hreflang 与 JSON preload 保持目标路由。样板模块仅保留 GoldChest 引用模块，`MapPanel` 固定 `RareModule_1x1.webp`；客户端等待 data version 后请求目标 JSON 并替换实体与真实地图。样板期间隐藏路由相关面包屑，确保复用 HTML 与目标 URL 的首个组件树一致。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run build` 通过；`http://localhost:8080/en/items/Ale/` HTTP 200，Playwright 无 hydration error 且页面更新为 Ale；lootdrop 回归无浏览器错误。

## fix: 详情页位置汇总改用 Locations i18n

- **原因**：详情页 h1 硬编码「位置汇总」，需与列表页一致改为 Locations 并支持多语言。
- **变更文件**：`web/src/pages/DetailPage.tsx`
- **关键逻辑/映射关系**：`{entityLabel} 位置汇总` → `{entityLabel} {ut('ui.list.locations')}`，复用既有 `ui.list.locations`（zh-Hans 点位 / en Locations / 等 10 语）。列表页标题 Locations 保持不变。

## fix: 地图模块名称 i18n

- **原因**：`/en/dungeon_modules/IceCavern` 分组页与模块详情页模块名仍用 `translation` 中文真值，未走 locale 字典。
- **变更文件**：`web/src/pages/DungeonModuleGroupPage.tsx`、`web/src/pages/DungeonModuleDetailPage.tsx`
- **关键逻辑/映射关系**：`mod.translation || mod.name` → `t(mod.translation_key, mod.translation || mod.name)`；详情页 `moduleDisplayName` 同理；debug 表 `mapLabel` 复用已 i18n 的 `moduleDisplayName`。数据侧 `dungeon_modules.json` 已有 `translation_key`，locale 含对应条目。

## fix: 地图模块详情页 i18n 同步

- **原因**：地图模块详情页沿用独立实现，面包屑硬编码中文分组名，模块坐标实体缺少 `translation_key`，导致模块详情的分组面包屑、分类按钮、地图 tooltip 和统计名称无法随语言切换。
- **变更文件**：`web/src/components/NavBar.tsx`、`web/src/pages/DungeonModuleDetailPage.tsx`、`api/src/module_builder.py`、`docs/AGENT_REFERENCE.md`。
- **关键逻辑/映射关系**：NavBar 删除 `GROUP_LABEL_MAP`，从 `dungeon_modules.json` 取对应模块并复用列表页的 `formatGroupLabel()`；`module_builder` 将 `entity_class.translation_key` 写进 `dungeon_modules_coords/*.json`（合并同名实体时保留 canonical key）；模块详情的分类按钮、地图 tooltip、调试表、实体统计统一通过 `t(translation_key, fallback)` 展示。`DungeonModuleDetailPage.tsx` 已标注为独立详情页，后续详情页 i18n 更新必须同步。
- **验证**：`python api/main.py` 重建数据，`IceCave_Bridge.json` 内 Bandage/BlackRose 等实体含 `translation_key`；Black、Prettier 与 TypeScript 预检通过。

## fix: 地图模块列表 SEO 标题 i18n

- **原因**：`/en/dungeon_modules/` 的 Helmet `<title>` 硬编码中文，浏览器标签与 SEO 标题不会随语言路由变化。
- **变更文件**：`web/src/pages/DungeonModulesPage.tsx`。
- **关键逻辑/映射关系**：硬编码标题改为 `ut('ui.module.title') | DarkFlashNav`，复用页面 h1 与现有 10 语言 UI 字典。

## fix: SSG 首屏 Ant Design 下拉样式

- **原因**：SSG SSR bundle 使用 `--mode ssr` 编译出开发态 Ant Design class hash，且没有把 CSS-in-JS 样式写入 HTML；生产页面的语言下拉栏首次显示为未样式化标签，交互后才恢复正常。
- **变更文件**：`web/scripts/ssg.mjs`、`web/vite.config.ts`、`web/src/ssr.tsx`。
- **关键逻辑/映射关系**：SSR 构建改为 `VITE_SSR_BUILD=true` + production mode；`StyleProvider(createCache())` 收集 Ant Design 样式，`extractStyle()` 注入每页 head。SSR 与客户端共享生产 class hash，首次渲染即可应用下拉样式。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run build` 通过；Playwright 验证 `http://localhost:8080/` 的 `.ant-select` 点击前后均为 24px，且无浏览器水合错误。

## fix: SSG 注入 Ant Design 样式

- **原因**：SSR 构建未使用生产模式且未提取 Ant Design CSS-in-JS 样式，SSG 页面无法正确注入组件样式。
- **变更文件**：`web/scripts/ssg.mjs`、`web/src/ssr.tsx`、`web/vite.config.ts`。
- **关键逻辑/映射关系**：SSG 子构建改为 `VITE_SSR_BUILD=true` 的 production mode；Vite 以环境变量识别 SSR bundle；SSR 通过 `StyleProvider`/`extractStyle` 采集并将 Ant Design 样式写入页面 head。

## fix: 统一 SEO 标题品牌结尾

- **原因**：部分列表页、SSG 本地化页面、重定向页与离线页的 `<title>` 仅以 `DarkFlashNav` 结尾，未遵循统一品牌文案。
- **变更文件**：`web/src/pages/ListPage.tsx`、`web/src/pages/DungeonModulesPage.tsx`、`web/scripts/ssg.mjs`、`web/index.html`、`web/public/offline.html`。
- **关键逻辑/映射关系**：除主页外，所有页面 `<title>` 统一以 `| 越来越黑暗闪电指南 DarkFlashNav` 结尾；SSG 的非默认语言标题及重定向页使用同一结尾；主页入口标题保持 `越来越黑暗闪电指南 DarkFlashNav` 为开头。

## fix: Quest NPC 英文列表页 i18n

- **原因**：`/en/quest_npc` 的标题、搜索框占位符和 NPC 展示名仍包含中文。
- **变更文件**：`web/src/pages/QuestNPCPage.tsx`、`web/src/components/QuestSearchBar.tsx`。
- **关键逻辑/映射关系**：列表页标题和 Helmet 元数据复用现有 UI 翻译键；非简体中文语言使用稳定的 `npc_name`，简体中文保持 `npc_name_display`；任务搜索框默认占位符改用 `ui.search.placeholder`，搜索结果 NPC 标签沿用相同语言映射。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过；Playwright 访问 `http://127.0.0.1:8090/en/quest_npc`，标题为 `Quest NPCs | DarkFlashNav`，页面正文未检测到中文。

## fix: Quest NPC 名称改用游戏 i18n 键

- **原因**：英文 Quest NPC 列表此前将内部 `npc_name` 直接作为显示文本，未经过 locale 字典。
- **变更文件**：`api/src/db/repositories/quests.py`、`api/src/locale_builder.py`、`web/src/types/quest.ts`、`web/src/pages/QuestNPCPage.tsx`、`web/src/components/QuestSearchBar.tsx`。
- **关键逻辑/映射关系**：导出的每个 NPC 注入 `translation_key = Text_DesignData_Merchant_Merchant_{npc_name}`；locale 构建器递归收集 `quest_npc.json` 的键；列表与搜索结果统一使用 `t(translation_key, npc_name_display)`，由游戏 locale 提供目标语言名称。
- **验证**：`python api/main.py` 数据管道完成；英文 locale 含 `Text_DesignData_Merchant_Merchant_Alchemist=Alchemist`；`api/lint.sh`、`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过；Playwright 验证 `/en/quest_npc` 正文无中文。

## fix: SSG Ant Design body 查询 mock

- **原因**：GitHub Actions 的 `dev` 构建在 SSG 阶段报 `document.body.querySelectorAll is not a function`，导致部署未发布到 `gh-pages-dev`。
- **变更文件**：`web/src/ssr.tsx`。
- **关键逻辑/映射关系**：为 Node SSR 的 `document.body` mock 补充 `querySelectorAll: () => []`，与既有 `document`、`document.head` 的空查询行为一致，使 `@ant-design/cssinjs` 初始化样式缓存时可安全扫描已有样式标签。

## fix: CI 从数据库导出 locale 字典

- **原因**：GitHub Actions 不具备原始本地化目录，`discover_languages()` 返回空列表，即使数据库已有多语言翻译表，locale 导出仍为 0 个文件，导致 SSG 找不到 `locale/en.json`。
- **变更文件**：`api/src/locale_builder.py`。
- **关键逻辑/映射关系**：locale 导出改遍历前端支持的 10 种语言，并从数据库对应的 `translations` / `translations_<lang>` 表读取；若旧数据库缺少某语言表则跳过，兼容本地与 CI 数据源。

## fix: Quest NPC 详情任务内容 i18n

- **原因**：`/en/quest_npc/TavernMaster` 的任务标题、目标、地图、稀有度、随机奖励、好感度和前置任务仍直接显示中文提取值。
- **变更文件**：`api/src/quest_collector.py`、`api/src/quest_extractor/quest_extractor.py`、`api/src/quest_extractor/content_renderer.py`、`api/src/locale_builder.py`、`web/src/pages/QuestNPCDetailPage.tsx`、`web/src/components/QuestSearchBar.tsx`、`web/src/types/quest.ts`。
- **关键逻辑/映射关系**：任务、任务内容、奖励分别保留游戏 `translation_key`；地图和稀有度使用独立键并纳入 locale 键收集；物品解析补充版本后缀键。详情与任务搜索结果统一通过 `t(key, fallback)` 显示，战利品状态改为非文本标记。

## fix: 泛型任务目标 i18n

- **原因**：Tavern Master 任务的 `亡灵`、`宝箱怪`、`骷髅` 使用 `Type.Character.*` 泛型标签，按怪物实体键无法找到英文；逃脱任务的目标本身没有翻译键。
- **变更文件**：`api/src/quest_collector.py`。
- **关键逻辑/映射关系**：击杀目标先尝试 `Text_DesignData_Monster_Monster_{名称}`，再把 `Type.Character.A.B` 映射为 `Text_Code_DCDataBlueprintLibrary_Type_Character_A_B`；Escape 目标复用 `DungeonIdTags` 对应的地图翻译键。

## fix: Quest NPC 搜索使用当前语言索引

- **改动原因**：任务列表和详情页可显示日文标题与目标，但搜索索引仍使用中文回退字段，导致日文输入无法命中。
- **变更文件**：`web/src/components/QuestSearchBar.tsx`；`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：构建扁平任务索引时，任务标题和每个目标优先按其 `translation_key` 从当前 locale 字典取值；locale 字典加载完成或语言切换时以 `dict` 依赖重建索引，缺失键继续回退中文字段。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: 保留 Objective Target 与 Map 双行

- **改动原因**：Count 独立为右列后，Target 与 Map 被排列到同一行，改变了原有的任务目标阅读顺序。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：左侧详情行改为 Type 跨两行，Target 位于第一行，Map、Loot 与 Rarity 位于第二行；右侧 Count 列保持独立且居中。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

# 2026-07-27 会话修改记录

## fix: Objective Count 独立右侧列

- **改动原因**：Quest NPC 详情页的 Objective 表格中，Count 与左侧目标详情混排，无法稳定靠右对齐。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Objective 外层改为 `minmax(0, 1fr) 5em` 两列网格；左列显示 Type、Target、Map 及可选 Loot/Rarity，右列的 Count 表头与每条数值均使用居中对齐。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: Objective 详情列对齐列头

- **改动原因**：Target 下方的 Map、Loot、Rarity 使用弹性布局，内容未与对应列头对齐。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：详情行复用表头的动态 CSS Grid 列定义；Target 的第二行空位固定为第二列，Map、Loot、Rarity 显式定位到第三列及其后续列。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: 合并 Objective Target 与 Map 列

- **改动原因**：Map 独立列会迫使 Loot 与 Rarity 换到第二行，影响可读性。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：列头通过 `ui.quest_detail.target` 与 `ui.quest_detail.target_map` 显示本地化的 `Target / Map`；Map 值作为 Target 单元格的第二行，Loot 与 Rarity 保持独立同一行。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: 统一 Objective Type 列宽

- **改动原因**：`Explore` 等较长的 Type 值会压缩同一任务行的 Target 内容，且各行列起始位置不一致。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Objective 的列头与每条内容行共享 `7em` 的 Type 列宽，Target、Loot、Rarity 在所有行从相同位置开始。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: Objective 自动共享列宽

- **改动原因**：固定 Type 列宽在内容较短时占用过多空间，无法根据实际最长值自适应。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Objective 容器直接定义 CSS Grid 的 `auto` Type 列；列头与所有内容单元格通过 `display: contents` 参与同一网格，最长 Type 值自动撑开该列并同步对齐全部行。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: 合并无地图目标的 Rarity 并强调 Loot

- **改动原因**：无 Map 的 Rarity 仍占用独立列，Loot 标记的视觉权重不足。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：单条目标无 `dungeon_type` 且有 Rarity 时，将其作为 Target / Map 的第二行并在 Rarity 列保留空网格单元；Loot 内容居中并使用 `fontWeight: 900`。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: Count 不遮挡 Objective 搜索按钮

- **改动原因**：Count 单元格覆盖 Target 末端的搜索图标时，点击图标不会触发搜索。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Target 单元格设置相对定位和 `zIndex: 1`，Count 单元格设置 `zIndex: 0`，使重叠区域的点击优先交给 Target 中的放大镜。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: 合并 Objective Rarity 到 Target

- **改动原因**：独立 Rarity 列未按期望合并，且较长 Target 文本会覆盖 Loot 内容；游戏原始目标名还带有重复的 Rarity 括号后缀。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Objective 改为 Type、`Target / Rarity`、Loot、Count 四列；Rarity 统一显示在 Target 单元格内。含 Rarity 的本地化目标名用 `/\s*\([^)]*\)/g` 移除括号内容；Target 列使用 `minmax(12em, 1fr)` 和断词换行保护 Loot。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: 清理繁中 Objective Rarity 括号后缀

- **改动原因**：目标名清理仅匹配半角括号，繁体中文 `鑽石（裂開）` 的全角后缀仍会显示。
- **变更文件**：`web/src/pages/QuestNPCDetailPage.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：Rarity 目标名的清理正则从仅匹配 `(...)` 扩展为匹配 `(...)` 与 `（...）`，保持所有语言只显示物品主名称。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit` 通过。

## fix: 缩小详情 SSG 占位页

- **改动原因**：详情页以 `GoldChest` SSR 作为样板，会将其坐标数据和 Ant Design 内联样式复制至全部物品、怪物及道具详情 HTML，单页约 208KB。
- **变更文件**：`web/scripts/ssg.mjs`、`web/src/main.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：详情 SSG 改为纯静态壳，仅输出本地化标题、`#####` 模块名及三个 `RareModule_1x1.webp` 占位图；不再渲染 `GoldChest`、地图坐标或调试控件。`__detailTemplate` 标志使客户端以 `createRoot` 替换壳，再按当前路由请求实际 JSON。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run build` 通过；`GoldChest` 输出 3601B、内联样式 0B；预览首页和详情页 HTTP 200。

## perf: 继续压缩详情 SSG 占位页

- **改动原因**：详情占位页无需重复保留首页响应式样式、公共数据预加载、hreflang 集及 SSR 状态脚本。
- **变更文件**：`web/scripts/ssg.mjs`、`web/src/main.tsx`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：构建时由 `detailPlaceholder()` 直接写入每个 `dist/{lang}/{items|monsters|props}/{name}/index.html`，不保存独立样板文件；根节点 `data-detail-placeholder` 驱动 `createRoot`，语言继续从 URL 推导。
- **验证**：`npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run build` 通过；`GoldChest` 输出 1814B，内联样式、hreflang 和 `__SSR_DATA__` 均为 0。

## docs: 统一全部默认详情页 SSG 样板壳计划

- **改动原因**：原计划以 GoldChest SSR 复用为核心且排除 lootdrops，已与当前轻量壳实现及“样板壳覆盖全部详情页”的目标不一致。
- **变更文件**：`docs/plans/SSG_DETAIL_TEMPLATE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：计划将 `items`、`monsters`、`props`、`lootdrops` 统一映射到 `createTemplateDetailPage()`；lootdrop 基底 URL 保留变体重定向，实际变体详情使用 `data-detail-placeholder` + `createRoot()` 并 preload 对应详情 JSON。

## docs: 扩大 SSG 壳至所有非列表路由

- **改动原因**：统一壳范围不能只按四类实体详情定义；根据路由与网站地图，除主页和列表页外的任务分组、NPC、模块详情及 Explore 也应纳入。
- **变更文件**：`docs/plans/SSG_DETAIL_TEMPLATE.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：计划以显式 `isTemplateShellRoute(path)` 分类排除主页、实体列表、任务/NPC/模块列表和模块分组列表；其余静态路由按类型映射目标 JSON preload，使用统一 `data-detail-placeholder` + `createRoot()` 接管。

# 2026-07-27 会话修改记录

## fix: 修复 Lootdrop 详情刷新失败

- **改动原因**：非默认语言的 lootdrop 详情在 Quick SSG 中输出中文 SSR 正文，客户端按 URL 语言 hydration 时触发 #425/#418/#423；刷新时 `dataVersion` 未就绪便请求未版本化 JSON，生产预览返回 HTML，导致页面永久显示 Loading。
- **变更文件**：`web/scripts/ssg.mjs`、`web/src/pages/LootdropDetailPage.tsx`、`web/src/hooks/useDataVersion.ts`、`web/src/components/NavBar.tsx`、`web/src/utils/dataUrl.ts`、`web/src/pages/{HomePage,ExplorePage,QuestItemsPage,QuestNPCPage,QuestItemGroupPage,DungeonModuleDetailPage}.tsx`、`web/index.html`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：`lootdrops` 纳入 `DETAIL_TEMPLATE_PAGES`，变体详情与 items/monsters/props 一样输出 `data-detail-placeholder` 壳并由 `createRoot()` 接管；预加载路径映射到 `/data/{version}/json/lootdrops/{name}.json`。`NavBar` 挂载单例 `DataVersionLoader`，版本请求失败后重试；所有页面仅在 `useDataVersion()` 返回版本后请求数据，`dataUrl()` 拒绝空版本，避免 `/data/json/...` 被 SPA fallback 解析为 JSON。Cloudflare 统计脚本改用 `async`，不能阻塞应用模块执行。
- **验证**：`npm run format`、`npm run format:check`、`npx prettier --check index.html scripts/ssg.mjs`、`npx tsc --noEmit`、`npm run build` 通过；8080 预览 HTTP 200，Playwright 直接打开 `/en/lootdrops/Spear_8001/` 与 `/ja/props/CobaltOre/` 均无 React hydration 错误，前者成功加载详情正文。

## docs: 规范 WSL 长流程执行

- **改动原因**：仅重定向日志仍可能等待前台构建或测试结束，阻塞后续命令执行。
- **变更文件**：`CLAUDE.md`、`docs/BUILD_AND_DEPLOY.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：管道、构建、部署和全站测试必须通过 `nohup ... > log 2>&1 &` 后台启动，再以短命令轮询进程和日志；8080 预览服务器同样保持后台运行。

# 2026-07-28 会话修改记录

## chore: 同步包含多语言表的数据库

- **改动原因**：GitHub Actions 使用的远程 DB 缺少多语言表，数据管道未生成 `data/json/locale/en.json`，导致 SSG 构建失败；本地 DB 原先被 `skip-worktree` 标记而未参与更新。
- **变更文件**：`api/data/darkfindv5.db`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：取消 DB 的 `skip-worktree` 标记并提交本地 41.9 MB DB，包含 `translations_en`、`translations_de`、`translations_es`、`translations_fr`、`translations_ja`、`translations_ko`、`translations_pt_BR`、`translations_ru`、`translations_zh_Hant`，使管道可生成全部语言 locale 文件。

## fix: 拆分 Sitemap 以适配 Cloudflare Pages

- **改动原因**：CF Pages 单文件限制为 25 MiB，原始 `sitemap.xml` 约 35.9 MiB；同时当前部署使用 CF 三级域名根目录，不需要 `/dnd9/` 二级路径。
- **变更文件**：`web/scripts/ssg.mjs`、`docs/BUILD_AND_DEPLOY.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：SSG 按 10 种语言生成 `sitemap-{lang}.xml`，每个文件保留该语言 URL 及 hreflang 互链；`sitemap.xml` 改为引用 10 个语言文件的 sitemap index。部署 URL 继续使用 `https://dnd9.icetar.com` 根路径。

## docs: 规划 CF Pages lootdrop 重复变体 404 接管

- **改动原因**：CF Pages 部署上限为 20,000 个文件，Quick SSG 当前约 32,203 个产物；需要在不改变预览分支、根域名部署和所有语言 SEO 壳的前提下，减少重复 lootdrop 品质变体静态文件并避免关键词堆砌。
- **变更文件**：`docs/plans/CF_PAGES_DETAIL_FALLBACK.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：计划保留所有语言现有 SSG SEO 壳；lootdrops 每种语言仅保留默认变体和 `8001` 神器变体的 SEO HTML，`1001` 至 `7001` 的其他重复变体交给 `404.html` + `BrowserRouter` 客户端请求同名版本化 JSON；普通实体、任务和模块详情不在本次裁剪范围内，同时验收 `gh-pages-dev` 预览分支确实是 CF Pages 的输入。
- **执行边界**：本计划及后续实现默认只创建本地 commit checkpoint，不包含远程推送；远程推送必须等待用户单独指令。

## docs: 敲定 CF Pages 详情 fallback 执行细节

- **改动原因**：原计划同时声称保留 `zh-Hans` 全路由和裁剪每种语言变体，且遗漏 Sitemap 中的 404 URL、Cloudflare 自定义 404 状态、实际 `createRoot()` 分支及文件安全余量，不能直接执行。
- **变更文件**：`docs/plans/CF_PAGES_DETAIL_FALLBACK.md`、`docs/SESSION_CHANGES.md`。
- **关键逻辑/映射关系**：仅给 9 个非默认语言跳过非默认品质变体 HTML；`zh-Hans` 全保留，默认品质按 `5001 -> variant_suffixes[0]` 选择，独立 `*_8001` 全语言保留；Sitemap 使用同一路由可用性标记同步过滤 URL 与 hreflang；`404.html` 文档预期 404 后由 `createRoot()`、`BrowserRouter` 和版本化 JSON 完成在线渲染。
- **容量与验收**：当前 32,203 个文件预计减少 14,076 个至约 18,127；构建期硬阈值定为 19,000。远程验收以 `gh-pages-dev` commit SHA、分支根产物和 Cloudflare retained 200/fallback 404 为准，不把空 Build command 误判为错误。
