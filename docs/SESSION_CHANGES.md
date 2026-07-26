# 2026-07-27 会话修改记录

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
