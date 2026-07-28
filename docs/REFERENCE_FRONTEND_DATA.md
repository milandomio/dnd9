# 前端数据加载参考

本文只保留 SSR/SSG、数据 fetch 和 Hydration 的当前约定。组件职责见 [`AGENT_REFERENCE.md`](AGENT_REFERENCE.md)，历史修复见 [`REFERENCE_ARCHIVE.md`](REFERENCE_ARCHIVE.md) 的“JSON 加载机制”章节。

## URL 规则

所有数据 `fetch()` 和 CSS `url()` 使用绝对路径 `/data/...`。嵌套路由下使用相对路径会把请求解析到 `/items/name/data/...`，命中 HTML fallback 后造成页面空白。

版本化数据路径由 `dataUrl()` 统一生成；`dataVersion` 未就绪时不要发起依赖版本的请求。

## SSR 数据源

- 列表页 SSR 和客户端主数据源统一为 `search_index.json`，按 `page` 过滤；独立 `{page}.json` 只作为最终回退。
- 详情页 SSR 使用实体详情 JSON；`--quick` 模式只注入 `{name, translation}`，客户端仍须 fetch 完整数据。
- `dungeon_modules.json` 由 `useDungeonModules()` 全局缓存，详情页通过坐标的 `c.map` 查共享 Map。
- `AppInner.tsx` 顶层主动预取模块数据，SSG 还可注入版本化 preload，避免详情页首次渲染串行等待。

## 共享 Hook

- `useDataVersion()`：模块级 listeners 同步所有调用者，避免只有触发 fetch 的组件拿到新版本。
- `useDungeonModules()`：共享 `cachedModules`、promise 和版本号，避免重复请求。
- `useSearchIndex()`：共享搜索索引，也服务列表页客户端渲染。

## Hydration 约束

1. 所有 hooks 必须在条件返回之前调用。
2. SSR 与客户端 Provider 嵌套必须一致，包括 `SSRDataContext.Provider`。
3. Quick 模式的 SSR 对象字段不完整，必须校验必要字段存在，不能只检查对象是否 truthy。
4. 非中文 SSG HTML 的 body 与客户端首轮渲染必须保持一致；标题可通过 `ssrLocalizedTitle()` 使用 SSG 注入的 localized title。

Hydration 错误排查顺序见 [`DEBUG_HYDRATION_WITH_PLAYWRIGHT.md`](DEBUG_HYDRATION_WITH_PLAYWRIGHT.md)：Playwright 控制台、Vite 日志、curl 区分 SSR 和 CSR。

## 页面同步

`DetailPage.tsx` 同时覆盖 items、monsters、props；掉落详情和地图模块详情是独立页面。共享功能修改后检查对应页面是否都使用同一数据字段和翻译键，尤其是 `translation_key`、`group_drop_info`、`group_parent`、`variant_count`。
