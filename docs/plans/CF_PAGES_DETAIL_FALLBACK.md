# CF Pages 多语言详情页 404 接管计划

## 目标

在 `dev` 分支的预览部署中保留所有语言的 SEO SSG 壳，同时仅将重复的 lootdrop 品质变体详情页交给 `404.html` + `BrowserRouter` 客户端接管，降低 Cloudflare Pages 单次部署文件数量。

- 保留 `zh-Hans` 默认语言的完整 SSG 路由。
- 保留所有语言现有的主页、列表页和详情 SEO 壳。
- lootdrops 每个语言仅为默认变体和 `8001` 神器变体生成独立 SEO HTML；其他重复品质变体不生成独立 HTML 文件。
- items、monsters、props 以及任务、模块等非 lootdrop 详情页不在本次裁剪范围内。
- 不改变当前 CF 三级域名根目录部署，不引入 `/dnd9/` 二级路径。
- 不改变 GitHub Actions 推送 `gh-pages-dev` 预览分支的流程；实现后验证 CF Pages 确实消费该预览分支产物。
- 实现完成后只创建本地 commit checkpoint；不包含远程推送，除非用户单独明确要求。

## 当前问题

`npm run build` 的 Quick SSG 当前生成约 28,569 个 HTML 文件，整个 `web/dist` 约 32,203 个文件，超过 Cloudflare Pages 的 20,000 文件部署上限。

其中多语言 HTML 副本主要来自每种语言重复生成实体和 lootdrop 变体详情页。lootdrops 下 `*_1001` 至 `*_7001`（不含实际默认变体）的 SEO 标题和正文高度重复，继续为它们生成多语言静态页面既不能扩大有效收录，还可能形成关键词重复堆砌；默认变体和 `*_8001` 神器变体仍保留所有语言的 SEO SSG 壳。

## 实施范围

### SSG 路由输出

在 `web/scripts/ssg.mjs` 增加明确的 lootdrop 变体 SEO 路由过滤：

1. 默认语言 `zh-Hans` 的现有路由全部保留。
2. 所有语言的主页、实体列表页、任务列表页、模块列表页和普通详情页保持现有 SSG 壳输出。
3. lootdrop 基底名称的重定向逻辑保持不变。
4. 每种语言的 lootdrop 默认变体和 `8001` 神器变体继续生成 SEO HTML 壳。
5. lootdrop 的 `1001`、`2001`、`3001`、`4001`、`6001`、`7001` 变体不生成独立 SEO HTML；访问由 `404.html` 交给客户端路由处理。若数据中默认变体不是 `5001`，以 `variant_suffixes` 的现有默认选择逻辑为准。
6. `404.html` 继续复制根 `index.html`，保证被裁剪的重复变体路径可启动 SPA。

### 客户端接管

1. 保持 `BrowserRouter` 使用当前浏览器 URL，不增加二级目录 basename。
2. 保持 `main.tsx` 对 `404.html` 中普通根节点使用 `hydrateRoot()`；对于已有 `data-detail-placeholder` 的默认语言详情壳继续使用 `createRoot()`。
3. 验证被裁剪的 lootdrop 变体从 404 启动后，`LanguageContext` 能从 URL 推导语言，页面组件能等待 `dataVersion` 并请求同名版本化 JSON。
4. 验证默认变体和 `8001` 仍保留本地化 `<title>`、canonical、hreflang 和详情壳，能够被 Google/Bing 抓取。
5. 验证被裁剪的 lootdrop 变体不会因为缺少静态 HTML 而落入永久 Loading 或错误重定向。

## Cloudflare Pages 配置验收

不在本次代码改动中重设 CF 配置，先确认现有预览分支设置：

- Pages 预览部署来源为 GitHub Actions 推送的 `gh-pages-dev`。
- 输出目录为 `gh-pages-dev` 分支根目录中的预构建文件。
- 不应从 `dev` 源码根目录直接部署，也不应出现 `No build command specified` 后校验源码仓库根目录的情况。
- 部署域名继续使用 CF 三级域名根目录。

## 验证

1. 运行 `npm run format`、`npm run format:check`、`npx tsc --noEmit`。
2. 后台运行 `npm run build`，确认构建成功。
3. 统计 `web/dist` 文件数，目标低于 20,000，保留安全余量。
4. 确认 `sitemap.xml` 索引和 10 个语言 Sitemap 仍生成，单文件小于 25 MiB。
5. 本地预览验证所有语言的 SEO 壳、lootdrop 默认变体、`8001` 神器变体以及被裁剪的重复变体。
6. 预览部署后直接访问：
   - `/en/lootdrops/Spear_8001/`
   - `/ja/lootdrops/Spear_8001/`
   - `/en/lootdrops/Spear_1001/`
   - `/zh-Hant/lootdrops/Spear_7001/`
7. 检查浏览器控制台无资源 404、React 错误或永久 Loading，并确认详情 JSON 请求返回 200。

## 非目标

- 不修改 CF Pages Dashboard 配置，除非验收确认其仍未使用 `gh-pages-dev`。
- 不删除数据 JSON、地图图片或默认语言静态 HTML。
- 不改变生产站点 `https://dnd9.icetar.com` 的根路径规则。
- 不执行远程推送。
