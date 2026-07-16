# 2026-07-16 会话修改记录

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
