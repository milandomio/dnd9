# Sitemap 全量 URL 水合验证计划

## 状态

草案，未执行。等待确认后再运行全量 Playwright 验证，不在本计划阶段修改业务代码。

## 背景

2026-07-27 曾修复非默认语言详情页的 React hydration #425/#418/#423：Quick SSG 不再输出与客户端语言不一致的 SSR 正文，详情页统一使用轻量壳和 `createRoot()` 接管，并等待 `dataVersion` 后请求版本化 JSON。

本地现有构建产物包含 10 个语言 Sitemap，每个 1,266 个 URL，共 12,660 个 URL。需要确认当前所有 Sitemap URL 均不存在 #425 水合错误，同时覆盖普通详情、lootdrop 品质 URL、任务、地图模块和多语言路由。

## 目标

- 读取 `sitemap.xml` 索引和全部语言 Sitemap，得到待测 URL 集合。
- 使用 Playwright 在浏览器中访问全部 URL，捕获 React 水合错误和页面加载异常。
- 区分真实应用错误与已知 Cloudflare Insights localhost CORS 噪声。
- 对失败 URL 自动重试，输出可复现的失败清单和按语言/页面类型/错误类型汇总。
- 验证完成后只在发现确定性代码问题时另开修复任务，不把验证脚本或临时产物混入业务代码。

## 验证范围

### Sitemap 输入

- `web/dist/sitemap.xml`
- `web/dist/sitemap-{zh-Hans,en,de,es,fr,ja,ko,pt-BR,ru,zh-Hant}.xml`
- 校验 Sitemap 索引中的语言文件均存在，URL 无重复，URL 数量与各文件 `<loc>` 数量一致。
- 保留 URL 的原始语言前缀、编码和尾斜杠，不自行拼接或规范化路由。

### 浏览器检查

每个 URL 记录：

- 页面响应状态和最终 URL。
- `pageerror` 内容。
- 控制台 `error` 内容。
- 是否出现 `#425`、`#418`、`#423`、`Hydration failed`、`hydration`、`Minified React error`。
- 根节点是否持续 Loading、空白或出现错误边界。
- 页面类型对应的基本渲染标记是否出现。
- 页面加载期间 JS、CSS、meta、版本化 JSON 请求是否返回非 2xx。

### 错误分类

- **水合错误**：React #425/#418/#423、`Hydration failed`、SSR/client mismatch。
- **运行时错误**：`pageerror`、未捕获异常、错误边界、持续 Loading。
- **资源错误**：应用资源或版本化数据 JSON 非 2xx。
- **路由错误**：最终 URL 改变、错误页面、空页面。
- **已知噪声**：`cloudflareinsights.com/cdn-cgi/rum` 在 localhost 的 CORS/网络失败单独统计，不计为应用失败。

## 执行方式

1. 创建本地 checkpoint，确认工作区中与本任务无关的用户改动不被 stage。
2. 按 `docs/BUILD_AND_DEPLOY.md` 生成并启动可验证的前端服务；优先使用与 Sitemap 产物对应的生产预览，而不是混用旧 dev 数据。
3. 解析 Sitemap，去重后按语言和页面类型分片。
4. 使用 Playwright Chromium 并发 worker 访问 URL；并发数设置为可调参数，默认 4，避免 WSL/本地服务过载。
5. 每个 URL 等待页面完成初始渲染或达到超时；水合检查至少覆盖首屏、数据加载完成和路由稳定后三个时点。
6. 失败 URL 自动重试 1 次；两次均失败才进入最终失败清单。
7. 保存 JSON 汇总、失败 URL、错误原文和统计信息到临时日志目录，不修改 `data/`、`web/public/` 或构建产物。
8. 对失败样本按页面类型抽样复现，确认是否为共同代码路径，再决定是否创建修复任务。

## 资源与超时

- 浏览器：Chromium headless。
- 单 URL 导航超时：30 秒。
- 页面稳定等待：最多 20 秒。
- 全量执行必须使用 `nohup ... > 日志 2>&1 &`，通过短命令轮询进程和读取日志。
- 记录开始/结束时间、worker 数、完成数、失败数和重试数。
- 若本地服务崩溃或超过资源上限，降低并发后从失败清单继续，不重复整轮扫描。

## 验收标准

- 10 个语言 Sitemap 全部被读取，去重后的 URL 数量与预期一致。
- 所有 URL 至少完成一次浏览器访问，失败 URL 已完成一次重试。
- `#425`、`#418`、`#423` 和 hydration mismatch 最终数量为 0。
- 应用 `pageerror`、错误边界、持续 Loading 和应用数据非 2xx 请求最终数量为 0。
- 已知 Cloudflare Insights CORS 错误与应用错误分开统计，不掩盖真实错误。
- 输出按语言、页面类型、路由和错误类型的汇总，能够定位任意失败 URL。
- 验证结束后工作区只包含本任务明确产生的日志/文档改动；临时测试文件删除。

## 回退与边界

- 本计划只做验证，不因单个 URL 失败直接修改水合逻辑。
- 若发现错误，保留最小复现 URL、控制台原文、网络请求和对应静态 HTML，再单独制定修复计划。
- 不把 Cloudflare 真实 404 响应与本地 Vite preview 的 SPA fallback 混为一谈；被裁剪品质 URL 的生产行为需另外按 CF Pages 规则验证。
- 不执行远程 push。
