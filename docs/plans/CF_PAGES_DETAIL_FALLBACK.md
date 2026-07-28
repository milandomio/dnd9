# CF Pages 多语言详情页 404 接管计划

## 2026-07-28 实施修订

- 品质变体裁剪范围扩展至全部 10 种语言，`zh-Hans` 不再保留非默认品质的静态 HTML。
- 每个多变体基底仅保留既有默认选择规则选出的品质；独立 `_8001` 条目仍按普通详情路由完整保留。
- 被裁剪品质从所有语言 Sitemap 及其 hreflang 集合中移除；在线直达继续由根 `404.html` 与版本化 JSON 接管。
- 该修订优先于下文涉及「默认语言保留全部品质变体」的旧规则和验收示例。

## 可行性结论

方案可行，执行时只裁剪 9 个非默认语言的重复 lootdrop 品质变体 HTML；`zh-Hans` 保持完整。当前数据与构建产物实测：

- `web/dist`：32,203 个文件，其中 28,569 个 HTML。
- lootdrop 基底条目：267 个，共生成 1,831 个品质变体路由。
- 每个非默认语言可省 1,564 个重复变体 HTML，9 种语言共省 14,076 个文件。
- 预计产物：约 18,127 个文件，低于 Cloudflare Pages Free 的 20,000 文件上限，剩余约 1,873 个文件余量。
- 当前 267 个基底条目都包含 `5001`；实现仍保留“优先 `5001`，否则取 `variant_suffixes[0]`”的既有默认选择规则。

原计划中的以下表述已纠正：

- 被裁剪的是非默认语言副本，不是 `zh-Hans` 路由。
- `*_8001` 当前是独立 lootdrop 条目，不在基底条目的 `variant_suffixes` 中；它按普通详情路由保留全部语言 HTML。
- `404.html` 的 `#root` 为空，客户端入口实际调用 `createRoot()`，不是 `hydrateRoot()`。
- Cloudflare Pages 使用自定义 `404.html` 时，被裁剪文档的响应状态预期为 404；这是有意放弃这些重复 URL 的 SEO，只保留在线客户端可访问性。
- 被裁剪 URL 必须从对应非默认语言 Sitemap 及其 hreflang 集合中移除，不能向搜索引擎提交返回 404 的 URL。
- `No build command specified` 对预构建的 `gh-pages-dev` 分支是正常配置；验收关键是来源分支、commit SHA 和输出根目录正确。

## 目标与边界

- 保留 `zh-Hans` 的全部现有 SSG 路由。
- 保留 10 种语言的主页、列表页、items、monsters、props、任务、模块及普通 lootdrop 详情壳。
- 非默认语言中，每个 lootdrop 基底只保留默认品质变体；`*_8001` 独立神器条目继续保留。
- 非默认语言的其余 `1001` 至 `7001` 品质变体不生成 HTML，由根 `404.html` 启动 SPA 后请求同名版本化 JSON。
- 不删除任何数据 JSON、图片或默认语言 HTML。
- 不引入 `/dnd9/` basename、`_redirects`、Pages Functions 或新的客户端路由逻辑。
- 不修改 GitHub Actions 的 `dev -> gh-pages-dev` 产物推送流程。
- `web/scripts/ssg.mjs` 是 dev/main 共用构建脚本；改动先在 dev 验证，后续合入 main 时会同样作用于生产构建，不做环境变量分叉。
- 本任务只创建本地 commit checkpoint，不执行远程推送。

## 最终生成规则

### 路由标记

在 `web/scripts/ssg.mjs` 发现 lootdrop 路由时直接记录该路由是否允许生成非默认语言副本，避免后续通过文件名再次猜测：

1. 对 `variant_suffixes.length > 1` 的基底条目计算 `defaultSuffix`：包含 `5001` 时取 `5001`，否则取第一项。
2. 基底名称重定向页维持现状：只生成 `zh-Hans` 静态重定向；非默认语言基底 URL 继续由 SPA 读取基底 JSON 后跳到同语言默认变体。
3. 每个品质变体路由增加布尔标记，例如 `localized: suffix === defaultSuffix || suffix === '8001'`。
4. `localized === false` 仅表示跳过非默认语言 HTML；默认语言首次渲染循环仍照常写盘。
5. 没有该标记的所有普通路由默认生成全部语言副本，因此独立 `Spear_8001` 一类条目无需特殊分支。
6. Quick 模式的 `ssrDataMap` 可继续包含全部变体的最小元数据，不做额外清理；它不增加部署文件数，保持改动最小。

### 本地化 HTML

在现有 step 5b 的非默认语言复制循环中：

- `r.redirect` 继续跳过。
- 新增跳过 `r.localized === false`。
- 不改 `createTemplateDetailPage()`、`detailPreloads()`、canonical、标题本地化或 JSON 路径。
- `404.html` 继续在 step 6 复制根 `index.html`，根资源路径保持绝对路径。

### Sitemap 与 hreflang

Sitemap 必须和真实静态响应一致：

1. `sitemap-zh-Hans.xml` 保留全部非重定向路由。
2. 其余 9 个 Sitemap 跳过 `r.localized === false` 的路由。
3. 生成每条 Sitemap 的 `xhtml:link` 时，根据路由可用语言计算集合：普通路由为 10 种语言，被裁剪路由仅为 `zh-Hans`。
4. `sitemap.xml` 继续作为 10 个语言 Sitemap 的索引。
5. 当前轻量详情壳本身不输出 hreflang；本次不扩大范围修改。保留页的语言互链由 Sitemap 提供，HTML 中继续保留本地化 `<title>` 和 canonical。
6. 不为被裁剪 URL 添加重定向或 canonical 到默认品质，因为不同品质仍对应可访问的实际 JSON，错误合并会改变用户访问语义。

## 客户端与 404 行为

现有客户端链路无需改代码：

1. Cloudflare 找不到裁剪后的路径时返回根 `404.html`，文档状态为 404，HTML 中空 `#root` 和客户端模块仍会执行。
2. `main.tsx` 因根节点没有子节点而调用 `createRoot()`。
3. `BrowserRouter` 保留原始 URL；`LanguageContext` 从第一段路径推导语言。
4. `LootdropDetailPage` 从 `:name` 得到完整变体名，等待 `dataVersion` 后请求 `/data/{version}/json/lootdrops/{name}.json`。
5. 文档请求的 404 是预期结果；JS、CSS、`/data/json/meta.json` 和版本化详情 JSON 必须返回 200。
6. Workbox 的导航 `NetworkFirst` 默认不会把 404 文档当成功响应缓存，因此裁剪路由只承诺在线直达可用，不承诺首次或重复离线深链可用。

不删除顶层 `404.html`。删除后 Cloudflare 会把所有未知路径按 SPA 规则返回 200，虽然裁剪路由可用，但任意错误 URL 也会成为 soft 404，不符合本次精确裁剪目标。

## 文件预算保护

在 `ssg.mjs` 完成 Sitemap 输出后递归统计 `dist` 普通文件总数：

- 构建日志输出 HTML 总数和文件总数。
- 设内部硬阈值为 19,000；超过即抛错使本地构建和 GitHub Actions 失败。
- 19,000 不是 Cloudflare 上限，而是为 20,000 上限预留至少 1,000 个文件的项目安全线。
- 若未来数据增长触发阈值，应重新评估裁剪范围，不静默提高阈值。

## Cloudflare Pages 配置验收

代码无法确认 Dashboard 配置，首次远程验证时人工核对：

- Cloudflare Pages 监听的分支是 `gh-pages-dev`，不是源码分支 `dev`。
- 部署记录的 commit SHA 等于 GitHub Actions 最新推送的 `gh-pages-dev` 头提交。
- Build command 为空是预期行为；输出目录指向该分支的预构建根目录（Dashboard 语法可能显示 `/` 或 `.`）。
- 部署日志中的上传文件数低于 19,000，且不再出现 20,000 文件限制错误。
- 域名继续挂载在 CF 三级域名根目录，不设置 `/dnd9/`。
- Cloudflare preview URL 会附带 `X-Robots-Tag: noindex`，因此预览环境只验收 HTML 元信息和路由行为，不用于判断 Google/Bing 是否实际收录。

## 执行顺序

1. 仅修改 `web/scripts/ssg.mjs` 的路由元数据、本地化输出、Sitemap 过滤和文件预算检查。
2. 运行 `npm run format`、`npm run format:check`、`npx prettier --check scripts/ssg.mjs`、`npx tsc --noEmit`。
3. 按 WSL 规则后台运行 `npm run build`，完成后读取 `web/build.log`。
4. 检查文件预算、目标文件存在性、Sitemap 内容和单文件大小。
5. 启动本地生产预览并验证 HTTP 200 与客户端路由；注意 Vite preview 的 SPA fallback 不能模拟 Cloudflare 文档 404 状态。
6. 运行 Playwright 检查 retained/fallback 页面无 React 错误、无永久 Loading，详情 JSON 为 200。
7. 追加 `docs/SESSION_CHANGES.md`，只 stage 本任务文件并本地 commit。
8. 等用户明确要求 push 后，再执行 GitHub Actions 与 Cloudflare 线上验收。

## 验收矩阵

### 构建产物

| 路径 | 预期 |
|------|------|
| `dist/zh-Hans/lootdrops/Spear_1001/index.html` | 存在 |
| `dist/zh-Hans/lootdrops/Spear_7001/index.html` | 存在 |
| `dist/en/lootdrops/Spear_5001/index.html` | 存在 |
| `dist/en/lootdrops/Spear_8001/index.html` | 存在 |
| `dist/en/lootdrops/Spear_1001/index.html` | 不存在 |
| `dist/zh-Hant/lootdrops/Spear_7001/index.html` | 不存在 |
| `dist/en/items/*/index.html` | 仍存在 |
| `dist/404.html` | 存在，内容等于根 `index.html` |

### Sitemap

- `sitemap-zh-Hans.xml` 包含 `zh-Hans/lootdrops/Spear_1001/`。
- `sitemap-en.xml` 不包含 `en/lootdrops/Spear_1001/`，包含 `en/lootdrops/Spear_5001/` 和 `en/lootdrops/Spear_8001/`。
- `Spear_1001` 的 zh-Hans Sitemap 条目不声明不存在的非默认语言 alternate。
- 10 个语言 Sitemap 均存在且单文件小于 25 MiB。

### 本地浏览器

- `/en/lootdrops/Spear_5001/` 与 `/en/lootdrops/Spear_8001/` 直接打开并加载详情。
- `/en/lootdrops/Spear_1001/` 与 `/zh-Hant/lootdrops/Spear_7001/` 即使无静态文件，也由 SPA 加载对应语言和品质数据。
- 控制台无 hydration/createRoot 错误、JSON 解析错误或永久 Loading。
- 网络中 `meta.json`、版本化 lootdrop JSON、JS 和 CSS 均为 200。

### Cloudflare 线上

- retained URL 文档返回 200，HTML 含对应语言的 title、canonical 和 `data-detail-placeholder`。
- fallback URL 文档返回 404，但页面在启用 JavaScript 时正常渲染；版本化详情 JSON 返回 200。
- 默认语言被裁剪品质 URL 仍返回 200。
- 部署文件数低于 19,000，部署来源 SHA 与 `gh-pages-dev` 一致。

## 非目标与回退条件

- 不修改 Cloudflare Dashboard，除非验收发现来源分支或输出目录错误。
- 不改变生产站点 `https://dnd9.icetar.com` 的根路径规则。
- 不保证 fallback URL 的 SEO 收录、分享爬虫正文或离线深链；它们是有意返回 404 的客户端可访问页。
- 不执行远程推送。
- 若实测产物仍超过 19,000、任一保留页缺失，或 fallback JSON 不是 200，则停止部署并回退本次 SSG 过滤，不继续扩大裁剪范围。
