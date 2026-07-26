# 详情页 SSG 样板计划

## 目标

为 `items`、`monsters`、`props` 三类共用 `DetailPage.tsx` 的详情路由提供稳定的 SSG 首屏样板。

- 每种语言只 SSR 一次 `/[lang]/props/GoldChest/`。
- 将该语言的 GoldChest HTML 复制为同语言全部上述详情路由的正文样板。
- 每个目标路由单独写入其实体的本地化 `<title>`、canonical 和 hreflang。
- 首屏显示 GoldChest 的分组和地图卡片布局，但地图一律使用 `RareModule_1x1.webp`，不下载真实地图图片。
- 客户端水合完成后请求当前 URL 对应的详情 JSON，以真实实体数据和真实地图图片替换样板。

GoldChest 覆盖较多地牢分组及地图模块，适合作为布局样板；样板只解决首屏结构与加载稳定性，不代表目标实体的数据。

## 适用范围

| 路由                     | 页面组件                 | 样板策略                       |
| ------------------------ | ------------------------ | ------------------------------ |
| `/:lang/items/:name`     | `DetailPage.tsx`         | GoldChest 样板                 |
| `/:lang/monsters/:name`  | `DetailPage.tsx`         | GoldChest 样板                 |
| `/:lang/props/:name`     | `DetailPage.tsx`         | GoldChest 样板                 |
| `/:lang/lootdrops/:name` | `LootdropDetailPage.tsx` | 不纳入本计划，后续选择独立样板 |

列表页、首页、任务页、地图模块页维持现有 SSG 逻辑。

## SSG 生成流程

1. `ssg.mjs` 读取 `props/GoldChest.json` 和 GoldChest 坐标涉及的模块元数据。
2. 对 10 种语言分别以对应的 `/:lang/props/GoldChest/` URL 调用一次 `renderToString`。
3. 样板 SSR 数据包含 `isDetailTemplate: true`、GoldChest 实体数据和仅供布局使用的关联模块数据。
4. 生成其它详情页时复用该语言的 HTML 正文；将内联 `window.__SSR_DATA__` 的路由键替换为目标 `page/name`，但值保持样板数据和 `isDetailTemplate` 标记。
5. 逐路由使用目标实体的 `translation_key` 从 locale 字典生成 `<title>`，不使用 GoldChest 标题。
6. 样板阶段的所有 `MapPanel.imageSrc` 固定为 `/data/img/RareModule_1x1.webp`；模块尺寸、偏移和点位仍来自 GoldChest，以保留地图网格结构。

## 客户端接管

`DetailPage.tsx` 需要区分真实 SSR 数据和样板 SSR 数据：

1. 初始 `entity` 可接受 GoldChest 样板数据，保证 `hydrateRoot()` 的首个组件树与静态 HTML 一致。
2. 当 `isDetailTemplate` 为真时，不能走“SSR 数据完整，无需 fetch”的分支；必须请求当前路由的 `/data/json/{page}/{name}.json`。
3. 请求成功后以真实数据替换 `entity`，移除样板标记，模块图恢复实际 `img_name` / `sl_base_name`。
4. 样板期间不允许预加载或请求真实地图图片，避免 GoldChest 样板产生无关网络流量。
5. 语言模板必须以对应语言 URL SSR，使 `LanguageProvider`、`uiDict(lang)` 的首屏静态 UI 与客户端水合一致；实体和模块名可在 locale 字典到达前回退 GoldChest JSON 的中文值。

## 数据与类型

- 为详情 SSR 数据增加可选 `isDetailTemplate?: boolean` 标记，不写入 API 交付 JSON。
- 样板模块数据仅包含 GoldChest 所引用模块的布局字段；客户端仍通过 `useDungeonModules()` 获取完整模块表。
- `RareModule_1x1.webp` 是显式样板资源，不依赖 `mod` 缺失时的隐式 fallback。
- 子池 `sub_pool_entries`、参考爆率等 GoldChest 内容仅作为样板视觉结构；真实请求返回后再显示目标实体的对应数据。

## 验证

1. `npm run build` 后，抽查 `/zh-Hans/props/GoldChest/`、`/en/items/Ale/`、`/ja/monsters/.../` 的 HTML：标题为目标实体对应语言，正文包含样板卡片，地图 URL 仅为 `RareModule_1x1.webp`。
2. Playwright 打开上述目标详情页，确认无 React hydration 文本错误。
3. Network 确认首屏请求目标详情 JSON，随后才请求目标实体使用的真实地图图片；样板阶段不请求 GoldChest 的真实地图图片。
4. 确认目标 JSON 返回后，标题、实体名、分组、点位和地图均替换为当前路由的真实内容。
5. 对 `LootdropDetailPage` 单独回归，确认未被 GoldChest 样板逻辑影响。

## 非目标

- 不为每个详情路由、每种语言重复执行完整 SSR。
- 不把 GoldChest 数据持久化到 `data/` 或 API JSON。
- 不改变 lootdrop 详情页的 SSG 策略；该页面需另行确定合适的掉落样板。
