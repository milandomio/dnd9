# 全部非列表路由 SSG 样板壳计划

## 目标

轻量 SSG 样板壳覆盖网站地图中除主页和列表页以外的全部静态路由。壳不执行页面正文 SSR；浏览器启动后以 `createRoot()` 接管，并由当前页面按 URL 请求真实数据。

- 不以 `GoldChest` 或其他游戏实体作为 SSR 正文样板。
- 每个壳只保留页面标题、canonical、客户端资源、必要的目标数据 preload 与通用占位内容。
- 通用占位内容为标题、`#####` 和三个 `RareModule_1x1.webp` 图片；不得包含坐标、模块数据、掉落池、调试控件、真实地图图或 Ant Design SSR 样式。
- 根节点使用 `data-detail-placeholder`，`main.tsx` 必须对其调用 `createRoot()` 而非 `hydrateRoot()`。
- 页面大小目标为 2KB 以下，且不随实体点位、掉落池或语言线性增长。

## 路由分类

路由以 `AppInner.tsx` 与 `web/scripts/ssg.mjs` 的 `routes` 生成清单为准。语言副本沿用相同分类。

### 排除：主页与列表页

| 路由                                                                  | 页面组件                     | 原因             |
| --------------------------------------------------------------------- | ---------------------------- | ---------------- |
| `/`、`/:lang`                                                         | `HomePage.tsx`               | 主页             |
| `/:lang/items`、`/:lang/monsters`、`/:lang/props`、`/:lang/lootdrops` | `ListPage.tsx`               | 实体列表         |
| `/:lang/quest_items`                                                  | `QuestItemsPage.tsx`         | 任务物品分组列表 |
| `/:lang/quest_npc`                                                    | `QuestNPCPage.tsx`           | NPC 列表         |
| `/:lang/dungeon_modules`                                              | `DungeonModulesPage.tsx`     | 地牢模块分组列表 |
| `/:lang/dungeon_modules/:group`                                       | `DungeonModuleGroupPage.tsx` | 地牢模块列表     |

这些页面保留现有 SSG/SSR 逻辑，不使用样板壳。

### 纳入：全部非列表静态路由

| 路由                                  | 页面组件                      | 客户端真实数据                                |
| ------------------------------------- | ----------------------------- | --------------------------------------------- |
| `/:lang/items/:name`                  | `DetailPage.tsx`              | `items/{name}.json`                           |
| `/:lang/monsters/:name`               | `DetailPage.tsx`              | `monsters/{name}.json`                        |
| `/:lang/props/:name`                  | `DetailPage.tsx`              | `props/{name}.json`                           |
| `/:lang/lootdrops/:name`              | `LootdropDetailPage.tsx`      | `lootdrops/{name}.json`                       |
| `/:lang/quest_items/:group`           | `QuestItemGroupPage.tsx`      | `quest_items_groups/{group}.json`             |
| `/:lang/quest_npc/:npc_name`          | `QuestNPCDetailPage.tsx`      | `quest_npc.json`                              |
| `/:lang/dungeon_modules/:group/:name` | `DungeonModuleDetailPage.tsx` | `dungeon_modules_coords/{name}.json` 与模块表 |
| `/:lang/explore`                      | `ExplorePage.tsx`             | Explore 所需模块与索引数据                    |

lootdrop 基底名称到默认变体的重定向（例如 `/:lang/lootdrops/HeaterShield`）继续生成最小重定向 HTML。实际变体路径（如 `HeaterShield_5001`、`HeaterShield_8001`）属于样板壳范围。

## 当前状态

`items`、`monsters`、`props`、`lootdrops` 和地牢模块详情已由 `createTemplateDetailPage()` 生成轻量壳：

- `detailPlaceholder()` 在构建期直接写入每个输出 HTML，不保存独立样板文件。
- 默认语言与九种非默认语言均写入目标路由标题；壳不含 `__SSR_DATA__`、hreflang 集、公共数据 preload 或内联样式，仅保留当前详情所需的 JSON preload。
- `props/GoldChest` 当前约 1.8KB。

其余非列表路由仍走 `render()` 完整 SSR，包括任务物品分组、任务 NPC、Explore 和地牢模块分组页。

## 实施方案

### 1. 用路由规则识别壳页

在 `web/scripts/ssg.mjs` 以显式路径规则替代仅检查 `DETAIL_TEMPLATE_PAGES` 的实体白名单：

1. 先处理 `r.redirect`，保持 lootdrop 变体重定向不变。
2. 排除主页与上述所有列表页。
3. 对其余 `routes` 统一调用 `createTemplateDetailPage()`。
4. 不通过“路径段数大于一”这种宽泛判断，避免将 `/dungeon_modules/:group` 分组列表误判为详情页。

建议将判断整理为单一 `isTemplateShellRoute(path)` 函数，并由该函数服务默认语言生成和九种语言副本生成，避免两条生成链路覆盖范围不一致。

### 2. 按路由生成壳元数据和 preload

`createTemplateDetailPage()` 接收路由类型和名称，统一生成：

- 目标路由的本地化 `<title>`、`<html lang>`、canonical。
- 当前数据资源的 versioned JSON preload；无需在壳中 preload 的页面可返回空字符串。
- 带 `data-detail-placeholder` 的通用占位正文。

preload 规则必须使用显式映射：

| 路由类型                             | preload                                                   |
| ------------------------------------ | --------------------------------------------------------- |
| items / monsters / props / lootdrops | `/data/{version}/json/{type}/{name}.json`                 |
| quest item group                     | `/data/{version}/json/quest_items_groups/{group}.json`    |
| quest NPC detail                     | `/data/{version}/json/quest_npc.json`                     |
| dungeon module detail                | `/data/{version}/json/dungeon_modules_coords/{name}.json` |
| explore                              | 页面首次实际请求的模块/索引资源，或无 preload             |

不得保留首页 `meta.json`、索引、模块表等公共 preload，也不得 preload 真实地图图片、引用坐标或 GoldChest 数据。

### 3. 客户端接管与数据回退

1. 所有壳均不注入 `window.__SSR_DATA__`；避免把任一路由的旧 SSR 数据传给客户端。
2. `main.tsx` 检测 `data-detail-placeholder` 后使用 `createRoot()`，所有非壳 SSR 页面继续 `hydrateRoot()`。
3. 每个纳入页面组件必须在 SSR 数据缺失时显示自身 loading 状态，并按当前 URL fetch 真实数据；不得把缺失 SSR 数据当作终态。
4. 需要模块表或索引的页面继续通过现有 hooks 取得数据。若某组件当前仅在 SSR 数据存在时可初始化，应先补齐空壳客户端加载路径，再纳入壳规则。
5. URL 语言继续由 `LanguageContext` 推导。壳没有跨语言正文，因此无需以 `__SSR_DATA__.__lang` 协调 hydration。

## 验证

1. 执行 `npm run build`，确认默认语言及九种语言副本均成功生成。
2. 抽查四类实体详情、任务物品分组、任务 NPC 详情、地牢模块详情和 Explore 的中英文 URL：静态 HTML 小于 2KB，含 `data-detail-placeholder`，不含 Ant Design CSS、`__SSR_DATA__`、坐标或实体详情 JSON 内容。
3. 抽查所有排除路由：首页、四类实体列表、任务物品列表、NPC 列表、模块列表与模块分组列表，确认继续保留既有 SSR 输出，未出现 `data-detail-placeholder`。
4. 检查 lootdrop 基底路径仍重定向，变体路径的 preload 精确指向同名变体 JSON。
5. 在生产预览直接打开每种纳入类型的英文 URL，确认 HTTP 200、无 hydration error、无永久 loading，随后出现真实标题、坐标、地图、任务或掉落内容。
6. 执行 `npm run format`、`npm run format:check`、`npx tsc --noEmit` 后提交实现。

## 非目标

- 不为每个路由或每种语言执行完整正文 SSR。
- 不修改 `data/` 下的自动生成 JSON，也不持久化 GoldChest、lootdrop、地图或坐标样板数据。
- 不改变主页与列表页的 SSG/SSR 策略。
