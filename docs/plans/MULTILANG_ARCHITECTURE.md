# 多语言架构

## 语言与路由

支持 `zh-Hans`、`en`、`de`、`es`、`fr`、`ja`、`ko`、`pt-BR`、`ru`、`zh-Hant`。除根路径 `/` 外，所有页面使用 `/:lang/...` 前缀，包含默认语言 `/zh-Hans/`。旧的无前缀路径由 `LegacyRedirect` 跳转到 `/zh-Hans/...`。

语言切换使用 `withLangPrefix()` 生成目标 URL，并整页导航；不要根据浏览器语言改变无前缀路径的语义。

## 翻译键

- 实体名使用后端导出的 `translation_key`，对应游戏 `Game.json` 的 key。
- UI 文案使用 `ui.<feature>.<key>`，由 `web/src/i18n/uiLocale.ts` 维护。
- `useLocale()` 暴露 `t(key, fallback)` 和 `ut(uiKey)`；实体字典运行时加载，UI 字典静态导入。
- 缺失翻译时按 locale、中文真值、实体名顺序回退。

## 数据与 Provider

`LanguageProvider` 从 URL 第一段确定语言，`loadLocale()` 请求版本化 `/data/{short}/json/locale/{lang}.json`。Ant Design 文案由 `useAntdLocale()` 按语言懒加载。

SSR 首轮保持中文 body；非默认语言的 SEO 标题由 SSG 注入 `__localizedTitle`，客户端通过 `ssrLocalizedTitle()` 使用同一值，避免首轮标题 Hydration 不一致。

## 页面边界

`DetailPage` 覆盖 items、monsters、props；`LootdropDetailPage`、地图模块页、任务页分别维护自身实体和 UI 文案。新增页面必须同时检查实体 `translation_key`、嵌套来源、参考爆率和 SEO 标题。

## 文件职责

| 文件 | 职责 |
|------|------|
| `web/src/i18n/locale.ts` | 语言列表、locale 加载 |
| `web/src/i18n/LanguageContext.tsx` | Provider、路径工具 |
| `web/src/i18n/useLocale.ts` | `t()` / `ut()` |
| `web/src/i18n/uiLocale.ts` | UI 文案 |
| `web/src/i18n/antdLocale.ts` | Ant Design locale |
| `api/src/locale_builder.py` | 生成实体 locale JSON |
