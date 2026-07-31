# SEO/GEO 元描述优化计划

## 状态

**已实施核心链路，保留为持续审计计划。** 2026-07-30 的 `2de870fe`、`8a578589`、`59452a72` 已完成十语言描述模板、React/SSG 共用构建入口、静态 HTML 注入和浏览器回归验证。

- `web/src/i18n/seoTemplate.mjs` 为主页、列表、实体、掉落、探索、任务和地图模块提供十语言 description 模板。
- 全部页面使用 `localizedSeoDescription()`，`meta[name="description"]` 与 `og:description` 取同一个值。
- SSG 对非默认语言注入 `__localizedDescription` 并重写静态 description/OG 标签；客户端首轮使用该值，locale 加载后再由同一模板重算。
- 2026-08-01 quick SSG 抽查确认英文主页与日语详情页的静态 description/OG 一致，且日语详情页含 `__localizedDescription`；`npm run test:i18n` 23/23 通过。

仍未执行的是全 Sitemap 的长度、重复、语言质量审计，以及 Bing Webmaster Tools 发布后监测；这些不应再被表述为“SEO 未开始”。

## 背景与当前发现

目标是为可索引页面提供准确、完整、与页面语言一致的 `meta[name="description"]`，将短描述优化为约 150–160 个字符，同时保持搜索结果摘要可读、动态数据真实、Open Graph 描述同步。

代码审阅发现：

- `web/index.html` 只有一个模板级描述；正常页面由 `react-helmet-async` 覆盖，不能只修改该模板。
- `HomePage.tsx` 使用主页宣传短句；`ListPage.tsx` 当前描述基本是“页面名称 + 数量”，信息不足。
- `DetailPage.tsx`、`LootdropDetailPage.tsx`、地图模块页和任务页分别使用短模板，部分只说明数量，没有说明查询内容和页面价值。
- `web/src/i18n/uiLocale.ts` 已有部分 `ui.seo.*` 键，但任务页、探索页、列表页等页面仍直接复用普通 UI 文案或拼接短字符串。
- `web/scripts/ssg.mjs` 的多语言复制流程会重写 `<title>`、`lang`、canonical 和 hreflang；当前 `localizePage()` 没有同等的 description 本地化逻辑。必须以生成后的 HTML 为准检查非默认语言页面，避免把简体中文描述带入其他语言页面。
- 当前请求未附具体 URL 清单。执行时以 10 个 `sitemap-{lang}.xml` 的 URL 并集为权威清单；根 `sitemap.xml` 可能是直接 `urlset`、`sitemapindex` 或受容量限制的语言子集，审计器必须兼容三种结构。如果用户补充 URL，则优先覆盖这些 URL，并继续检查其所属页面模板的全量影响。

## 审计范围

以 Sitemap 中的可索引 URL 为准，覆盖默认语言和以下 10 种语言：`zh-Hans`、`en`、`de`、`es`、`fr`、`ja`、`ko`、`pt-BR`、`ru`、`zh-Hant`。

- `/` 作为未带语言前缀的首页兜底页单独检查，确认其 description、canonical 和页面语言不意外扩大索引范围；Sitemap URL 和 canonical 策略不在本任务中修改。

页面类型：

- 主页：`/` 和各语言主页。
- 实体列表：`items`、`monsters`、`props`、`lootdrops`。
- 实体详情：物品、怪物、道具、掉落物详情及掉落物品质/变体 URL。
- 探索页：`explore`。
- 任务物品列表及地图分组详情：`quest_items`、`quest_items/:group`。
- NPC 任务列表及 NPC 详情：`quest_npc`、`quest_npc/:npc_name`。
- 地图模块列表、分组和模块详情：`dungeon_modules`、`dungeon_modules/:group`、`dungeon_modules/:group/:name`。

不作为可索引内容优化：Sitemap 排除的重定向页、`404.html` 和仅用于客户端兜底的非页面资源；这些页面只检查是否意外暴露为正常索引页面。

## 执行步骤

### 1. 建立 URL 与现状报告

- 按 `docs/BUILD_AND_DEPLOY.md` 生成与当前数据对应的前端产物，解析全部语言 Sitemap 的 URL 并集，去重后按语言、页面类型分组。
- 逐页读取最终 HTML，而不是只检查 React 源码，记录 URL、页面类型、语言、`title`、`meta description`、`og:description` 和 canonical。
- 统计 description 的 Unicode 字符数，并额外检查过短、过长、空值、重复、未替换占位符、语言不匹配和 `og:description` 不一致。
- 输出问题清单，标记“只需改文案”和“需要修复 SSG 元数据注入”的页面，保存到临时日志，不把审计产物写入 `data/` 或 `web/public/`。

### 2. 设计按页面类型的描述模板

保留动态事实字段，避免为凑长度添加无法从页面验证的关键词。模板应包含“是什么、可查询什么、页面中的关键数量/范围、对用户的帮助”四类信息。

| 页面类型 | 描述应包含的事实 |
|---|---|
| 主页 | 游戏名、地图/任务/掉落/资源查询能力、宝箱或模块查找入口 |
| 实体列表 | 实体类别、可查询地图点位或掉落信息、当前条目数量 |
| 实体详情 | 实体名、地图位置数量、地图/坐标查询能力；按实体类型补充掉落或用途 |
| 掉落详情 | 掉落物名、来源数量、位置数量、地图和来源详情；品质/模式使用当前变体数据 |
| 探索页 | 探索目标数量、涉及 NPC 数量、任务目标位置查询能力 |
| 任务物品页 | 任务物品、地图模块分组、实体和位置统计 |
| 任务物品分组 | 地图/分组名、任务实体数、位置数和地图定位能力 |
| NPC 任务页 | NPC 任务列表、活跃 NPC 数量、任务筛选能力 |
| NPC 详情 | NPC 名、任务数量或任务列表、收集目标/任务进度查询能力 |
| 地图模块列表/分组 | 地图分组、模块数量、模块检索能力 |
| 地图模块详情 | 模块名、尺寸、实体数量、点位数量和地图坐标信息 |

文案规则：

- 每种语言单独撰写自然文案，不通过拼接英文关键词或重复句子强行填充长度。
- 以 150–160 个 Unicode 字符作为拉丁语言的参考目标，而非所有 URL 的硬性验收线；CJK、长实体名和无法安全补足动态事实的页面按语言、页面类型设定合理区间，并在审计报告中列出例外原因，不用无意义内容填充。
- 描述中的名称、数量、尺寸和变体必须来自页面实际数据；数据为空时使用稳定的本地化兜底句，不输出 `undefined`、内部 key 或原始占位符。
- `og:description` 与 `meta[name="description"]` 使用同一最终字符串，避免社交分享和搜索摘要内容分叉。

### 3. 修复元数据生成链路

优先采用一个可复用的 SEO 描述构建入口，供 React Helmet 和 SSG 使用，避免客户端与静态 HTML 生成两套不同文案逻辑。计划修改范围预计为：

- `web/src/i18n/uiLocale.ts`：补齐 10 种语言的 SEO 页面类型文案键。
- `web/src/pages/*.tsx`：将各页面的 description 和 `og:description` 改为统一模板，并传入当前页面已有的动态统计字段。
- `web/scripts/ssg.mjs` 及必要的 SSR/SEO 辅助模块：确保每种语言的静态副本都写入本地化 description，而不仅重写 title；同时保留 canonical、hreflang 和现有详情页壳策略。
- 仅在审计发现确有必要时修改 `web/index.html` 的模板兜底描述，不把模板描述当成所有页面的最终 SEO 内容。

元数据一致性契约：

- 描述模板、占位符替换和兜底规则必须来自浏览器与 `ssg.mjs` 都能加载的纯数据/纯函数入口；不得只在 TypeScript 页面组件中实现后再由 MJS 复制一份字符串拼接逻辑。
- 非默认语言的 SSG 页面除 `__localizedTitle` 外还必须注入 `__localizedDescription`。客户端首轮 Helmet 优先读取此值，待 locale 数据加载完成后以相同的模板和事实字段重算，避免当前 `__ssrLang=zh-Hans` 水合策略将静态本地化 description 短暂覆盖为简体中文。
- `meta[name="description"]` 和 `og:description` 均从同一个最终字符串输出；页面切换时由同一 SEO 入口覆盖前一路由标签。
- 描述统计只能使用原始、稳定的页面事实，例如实体原始坐标数、当前掉落变体的全部来源/唯一位置数、任务总数或模块原始实体数。不得使用调试开关、默认隐藏、品质、掉率或用户筛选后的可见数量。
- Quick SSG 无法取得完整事实时使用已本地化的保守描述，不伪造 `0`、坐标数、来源数或变体统计；客户端取得完整数据后仅以真实原始事实更新。

实现时需要特别验证：

- Quick SSG 详情页的最小 SSR 数据不足时，description 不读取不存在的坐标、来源或数量字段，并保留与客户端首轮一致的本地化兜底。
- 掉落物变体 URL 使用当前变体的名称和统计，不把基础条目或其他品质的文案误用于当前 URL。
- 多语言页面的首屏静态 HTML 和客户端 Helmet 最终值一致，不引入 hydration 错误。
- 页面切换时 Helmet 不残留前一个路由的 description。

### 4. 生成后验证

- 重新审计全部 Sitemap URL，确认每个可索引页面只有一个最终 description。
- 抽样检查 10 种语言的主页、列表、实体详情、掉落详情、任务页和地图模块详情；对所有短描述页面保留完整清单。
- 验证 description 与 `og:description` 一致、语言正确、占位符已替换、动态计数与页面正文一致。
- 静态审计直接读取生成 HTML，验证原始响应中的 description、`og:description`、canonical、`lang` 和重复标签；不以执行 JavaScript 后的 DOM 代替静态验证。
- 用 Playwright 检查页面加载、Hydration #418/#423/#425、持续 Loading、关键 JSON 请求，以及 locale 加载完成后的 meta 标签。新增或扩展自动化测试，覆盖全部语言的代表页面和同一标签页路由切换，断言首轮与最终 description/OG 描述一致。
- 按项目流程执行 `npm run format`、`npm run format:check`、`npx tsc --noEmit`、`npm run lint`、`npm run test:i18n`，再执行前端构建。
- 启动生产预览并验证首页、每类页面和关键语言 URL 返回 HTTP 200；长流程遵守 WSL 后台日志规则。

### 5. 发布后监测

- 发布后在 Bing Webmaster Tools 检查 Sitemap 抓取、元描述问题、点击率和平均排名变化。
- 记录修改前后的 URL、语言、描述版本和观察窗口；不把短期排名波动直接归因于单次文案改动。
- 对高曝光页面保留两版候选文案，只有在数据足够且平台支持时进行 A/B 测试；避免同一 URL 频繁变更导致观察结果不可比较。
- 定期复查新增 Sitemap URL 和数据字段变化，防止新页面回退到模板级短描述。

## 验收标准

- Sitemap 中所有可索引 URL 均有非空、与页面语言一致的 `meta[name="description"]`。
- 描述符合对应语言和页面类型的目标长度区间；未达到拉丁语言参考区间或采用 CJK/长名称例外时，审计报告必须说明原因并确认内容仍准确、自然。
- description 不含内部 key、未替换占位符、`undefined`、重复填充语句或与页面不符的统计。
- `og:description` 与 description 完全一致；静态 HTML、客户端首轮和 locale/详情数据稳定后的最终值一致。
- 10 种语言的文案键集合完整，页面切换和 SSG 生成无新增 hydration 或运行时错误。
- 质量检查、前端构建、预览 HTTP 200 和关键页面浏览器验证全部通过。
- Bing Webmaster Tools 的监测作为发布后动作，不阻塞本地代码验收；无凭据时不伪造结果。

## 风险与回退

- 搜索引擎可能按像素宽度截断，不保证字符数等于最终展示宽度；通过报告同时记录字符数和内容类型，必要时按语言调整。
- 详情页统计依赖 JSON 数据，若 Quick SSG 无法取得完整数据，必须使用保守兜底而不是错误数量。
- 如果多语言静态后处理改动引发水合差异，回退到上一个稳定的 SSG 注入方式，保留审计报告并另开修复任务。
- 根首页与 `zh-Hans` 首页当前有不同的 URL/Canonical 语义；本任务只报告其元数据和索引暴露状态，不在未获额外确认时改变路由或 canonical。
- 本计划不改变路由、Sitemap URL、数据结构或掉落/地图业务逻辑。

## 确认门

请确认以下范围后再执行：

1. 使用当前构建生成的 10 个语言 Sitemap 作为 URL 清单；如需只处理指定 URL，请先提供清单。
2. 同意“150–160 字符为默认目标，CJK 依据像素宽度单独审计”的长度策略。
3. 同意为修复多语言静态 HTML 元描述而修改 SSG/SEO 生成链路，并执行构建与浏览器验证。

确认后才进入第 1 步，不在本计划阶段直接修改网站代码或提交部署。
