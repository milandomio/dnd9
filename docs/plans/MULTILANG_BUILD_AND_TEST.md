# 多语言构建与验收

## 数据与构建

完整流程必须先运行管道，再构建前端：

```bash
cd api && python main.py
cd web && npm run build
```

管道生成 `data/json/locale/{lang}.json`；SSG 生成默认语言和其他语言 HTML、canonical、hreflang 及 sitemap。长流程按 [`BUILD_AND_DEPLOY.md`](../BUILD_AND_DEPLOY.md) 的 WSL 后台规则运行。

## SSG 约束

- 中文页面执行完整 React SSR；其他语言优先复用中文 HTML 做文本后处理。
- 每个非中文页面注入语言字段和当前实体的 localized title，不要把整份 locale 字典内联到 HTML。
- lootdrop SEO 标题只包含当前掉落物名称，不把大量嵌套来源塞进 `<title>`。
- 页面生成策略变化后同步 sitemap 和 hreflang，避免生成了 HTML 却没有入口。

## PWA

版本化 locale URL 复用现有 `df5-data-json` Workbox 缓存规则。修改缓存资源类型或条目上限前，先确认实际资源数量和部署平台文件限制。

## 验收清单

- locale 输出共 10 个文件，键集合一致，非空翻译率符合当前基线。
- 关键实体 JSON 含 `translation_key`。
- `python main.py` 和 `npm run build` 无错误。
- 至少验证 en、ja 和 zh-Hans 的首页、列表页、实体详情、掉落详情和地图模块详情。
- 用 Playwright 检查标题、locale 文案、Hydration #418/#423/#425、持续 Loading 和关键资源 HTTP 状态。
- 构建后按部署文档验证预览服务 HTTP 200。
