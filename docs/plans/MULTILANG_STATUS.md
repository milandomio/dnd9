# 多语言状态

## 已完成

- P0-P8d：版本化数据目录、实体 `translation_key`、10 语言 locale、语言前缀路由、`LanguageProvider`、多语言 SSG、搜索与主要页面 UI i18n。
- P9：Ant Design locale 切换和 locale 字典体积优化。
- P10：Playwright 多语言回归框架。
- P11：移除 `translation_EN` / `resolver_en`。

当前主链路为：

```text
URL 前缀 -> LanguageProvider -> locale fetch -> t()/ut()
实体 translation_key -> locale JSON -> 当前语言名称
中文 SSR -> SSG 标题后处理 -> 多语言 HTML/sitemap
```

## 已知问题

非中文页面的 NavBar 标签曾出现 Hydration mismatch，原因是 SSG body 为中文而客户端首轮直接渲染目标语言。若重新处理，必须先选择门控、body 后处理或纯 CSR 方案，再执行代码修改；不要仅通过忽略控制台错误验收。

详情页标题和 ModuleDetail 标题重复问题已有修复，相关历史验证见 [`MULTILANG_PLAN_ARCHIVE.md`](MULTILANG_PLAN_ARCHIVE.md) 第 10 节。

## 后续原则

- 新页面接入必须同时补 UI key、实体 key、SSG 标题和 Playwright 断言。
- 不重新引入 `translation_EN` 作为长期 i18n 数据源。
- UI locale 键集合保持各语言一致；缺失值应显式回退并记录，不用中文字符串作为跨语言 key。
