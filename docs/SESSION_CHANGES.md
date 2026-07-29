# 会话修改记录

当前会话记录写在本文件；历史记录已移至 [`SESSION_CHANGES_ARCHIVE.md`](SESSION_CHANGES_ARCHIVE.md)，按日期保留原始内容。

## 2026-07-30

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

### fix: CI 构建保留神器 _8001 专用翻译键

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
