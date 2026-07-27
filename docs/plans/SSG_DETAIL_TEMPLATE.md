# 统一详情页 SSG 样板壳计划

## 目标

将轻量 SSG 样板壳统一用于项目定义的全部详情页：`items`、`monsters`、`props`、`lootdrops`。

- 不再以 `GoldChest` 或其他实体执行详情正文 SSR。
- 每个静态 HTML 仅保留目标路由的本地化标题、canonical、客户端资源、目标 JSON preload 及通用占位内容。
- 首屏占位内容固定为标题、`#####` 模块名和三个 `RareModule_1x1.webp` 图片；不输出坐标、模块元数据、调试控件、地图图片或 Ant Design SSR 样式。
- 浏览器以 `createRoot()` 接管占位壳，再按当前 URL 请求真实详情 JSON 并渲染完整页面。
- 单页目标维持在 2KB 以内，不因实体坐标数量、掉落池规模或语言而显著增长。

项目术语中的“详情页”默认仅指以下四类实体；任务 NPC、任务物品分组和地牢模块详情维持独立 SSG 策略。

## 适用范围

| 路由                     | 页面组件                 | SSG 策略       |
| ------------------------ | ------------------------ | -------------- |
| `/:lang/items/:name`     | `DetailPage.tsx`         | 统一轻量样板壳 |
| `/:lang/monsters/:name`  | `DetailPage.tsx`         | 统一轻量样板壳 |
| `/:lang/props/:name`     | `DetailPage.tsx`         | 统一轻量样板壳 |
| `/:lang/lootdrops/:name` | `LootdropDetailPage.tsx` | 统一轻量样板壳 |

lootdrop 的基底名称到默认变体重定向页继续保持最小重定向 HTML；实际变体路由（如 `HeaterShield_5001`、`HeaterShield_8001`）使用统一壳。

## 当前状态

`items`、`monsters`、`props` 已通过 `createTemplateDetailPage()` 生成轻量壳：

- 由 `detailPlaceholder()` 在构建时直接生成，不保存独立 GoldChest 样板文件。
- 根节点标记 `data-detail-placeholder`，`main.tsx` 据此使用 `createRoot()`，避免对静态占位内容执行 hydration。
- 默认语言与九种非默认语言均写入目标路由的本地化标题；壳不含 `__SSR_DATA__`、hreflang 集、公共数据 preload 或内联样式。
- `props/GoldChest` 壳当前约 1.8KB。

`lootdrops` 目前仍走 `render()` 全量 SSR，因此单页约 114KB，并且非默认语言的中文 SSR 正文与客户端目标语言可能发生 hydration 不一致。

## 实施步骤

1. 在 `web/scripts/ssg.mjs` 的 `DETAIL_TEMPLATE_PAGES` 中加入 `lootdrops`，让所有四类实体详情路由进入 `createTemplateDetailPage()`。
2. 扩展 `detailPreloads()` 的实体匹配，将 `lootdrops` 映射到 `/data/{version}/json/lootdrops/{name}.json`。
3. 保持 `r.redirect` 在样板路由分支之前处理，确保多变体 lootdrop 基底 URL 仍重定向到默认变体。
4. 不向样板壳注入 `window.__SSR_DATA__`。`LootdropDetailPage.tsx` 在无 SSR 数据时应按当前 URL 请求对应的变体 JSON；现有 `currentSuffix`、变体切换及默认变体跳转逻辑必须保持不变。
5. 继续以 `data-detail-placeholder` 标记驱动 `main.tsx` 的 `createRoot()`；不得为 lootdrop 壳恢复 `hydrateRoot()`，以消除非默认语言的 SSR 文本不一致。

## 数据与渲染约束

- 样板标题由路由对应 `translation_key` 和当前 locale 字典生成；缺失时回退已有 translation 或实体 name。
- 样板只 preload 当前详情 JSON，不 preload 全局索引、模块数据、坐标引用或真实地图图片。
- 所有地图、掉落池、参考爆率、变体数据和调试控件只在客户端取得真实 JSON 后渲染。
- 语言继续由 URL 路径推导；壳不依赖 `__SSR_DATA__.__lang`。
- 不修改 `data/` 中自动生成的 JSON，样板行为仅在前端 SSG 层实现。

## 验证

1. 执行 `npm run build`，确认完成全部路由与 10 种语言的静态输出。
2. 量测 `/zh-Hans/items/Ale/`、`/en/monsters/.../`、`/ja/props/GoldChest/`、`/en/lootdrops/HeaterShield_8001/`：每个实际详情页 HTML 小于 2KB，且不存在内联 Ant Design CSS、`__SSR_DATA__` 或 `data-detail-placeholder` 以外的实体数据。
3. 确认 lootdrop 基底 URL 仍返回重定向页，变体 URL 的 preload 指向对应的 `lootdrops/{name}.json`。
4. 在生产预览中直接打开四类详情页的各语言 URL：HTTP 200，壳先显示，随后加载真实实体、地图、掉落池和变体切换内容。
5. 使用 Playwright 检查直接打开 `/en/lootdrops/HeaterShield_8001/` 时无 hydration error、无永久 loading、无错误重定向。
6. 执行 `npm run format`、`npm run format:check`、`npx tsc --noEmit` 后提交。

## 非目标

- 不为每个实体或每种语言执行完整详情正文 SSR。
- 不持久化任何 GoldChest、lootdrop 或模块样板数据。
- 不改变列表页、首页、任务页、任务 NPC、任务物品分组或地牢模块详情的 SSG 策略。
