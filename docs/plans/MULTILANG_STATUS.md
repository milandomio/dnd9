# 多语言状态

## 已完成

- P0-P8d：版本化数据目录、实体 `translation_key`、10 语言 locale、语言前缀路由、`LanguageProvider`、多语言 SSG、搜索与主要页面 UI i18n。
- P9：Ant Design locale 切换和 locale 字典体积优化。
- P10：Playwright 多语言回归框架。
- P11：移除 `translation_EN` / `resolver_en`。
- P12：硬编码实体使用 `df5.hardcoded.*` 合成键；当前输出使用的 172 个键在 10 个 locale 文件中均有值。已补齐五个怪物的十语言名称，并为可确认的实体优先复用官方 key。
- 多语言标题、`description` 与 `og:description` 已由 SSG 注入本地化首屏值，客户端复用 `__localizedTitle` / `__localizedDescription`。

当前主链路为：

```text
URL 前缀 -> LanguageProvider -> locale fetch -> t()/ut()
实体 translation_key -> locale JSON -> 当前语言名称
中文 SSR -> SSG 标题后处理 -> 多语言 HTML/sitemap
```

## 当前剩余

- 非中文 NavBar 曾有 Hydration mismatch；`LanguageProvider` 现以 SSG 注入的 `__ssrLang` 对齐客户端首轮语言。2026-08-01 的 23 页多语言 Playwright 回归未发现 hydration 错误，因此不再作为已知问题。
- 日语详情页不再有空 key、raw identifier 或中文模块兜底；仍有 110 个技术实体的日语值等于英文。完整审计口径见 [`JA_DETAIL_I18N_BACKLOG.md`](JA_DETAIL_I18N_BACKLOG.md)。
- `df5.hardcoded.*` 已保证所有语言有稳定显示值，但 110 个技术实体仍使用可读英文回退；后续须按十语言范围决定保留技术英文或补人工译文。

## 后续原则

- 新页面接入必须同时补 UI key、实体 key、SSG 标题和 Playwright 断言。
- 不重新引入 `translation_EN` 作为长期 i18n 数据源。
- UI locale 键集合保持各语言一致；缺失值应显式回退并记录，不用中文字符串作为跨语言 key。
