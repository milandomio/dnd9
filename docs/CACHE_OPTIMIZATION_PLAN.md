# 缓存优化计划

> **目标**：全量 JSON 版本化 + SW 缓存优先 + preload 消除 LCP 瓶颈

## 现状问题

| 问题 | 说明 |
|------|------|
| 仅 `dungeon_modules.json` 使用版本化路径 | 其余 12+ 个 fetch 仍用非版本化 `/data/json/...` |
| SW 规则不兼容版本化路径 | `startsWith('/data/json/')` 不匹配 `/data/{ver}/json/...` |
| 详情页无 preload | LCP P99=17.86s，主要瓶颈在 coord JSON 和图片未预下载 |

## 架构流程

```
首次访问（版本 A）：
  HTML（含版本 A preload）
    ├─ SW 拦截 → /data/{verA}/json/* → StaleWhileRevalidate → 缓存 A
    ├─ meta.json（固定路径）→ SW 返回 → 版本号 A
    └─ render: dataUrl("A", "/json/foo") → SW 缓存 A → 渲染

部署新版后（版本 B）：
  HTML（含版本 B preload）
    ├─ SW 拦截 → /data/{verB}/json/* → 缓存 B
    ├─ meta.json → 版本号 B → useDataVersion 更新
    └─ 所有 fetch → dataUrl("B", "/json/foo") → SW 缓存 B → 新数据
```

版本化路径保证 CDN 永不清到旧数据；SW 缓存优先保证回访加载速度。

## 改动清单

### ✅ 1. 新建 `web/src/utils/dataUrl.ts` (已实施)

```ts
// /data/json/foo → /data/{verShort}/json/foo
export function dataUrl(version: string, path: string) {
  if (!version) return path;
  const short = Number(version).toString(36);
  return path.replace('/data/json', `/data/${short}/json`);
}
```

### ✅ 2. 修改 `web/vite.config.ts` (已实施)

**SW 路由规则** — df5-data-json 的 urlPattern：

```ts
// 兼容版本化和非版本化路径
urlPattern: ({ url }) => /^\/data\/(?:[a-z0-9]+\/)?json\//.test(url.pathname),
```

**全局 preload** — 在 `inject-versioned-preload` 插件中增加常用全局 JSON：

- `index.json`（首页）
- `search_index.json`（导航搜索 + 列表页）
- `dungeon_modules.json`（已有 ✅）

```ts
// 当前
const preloads = [
  `<link rel="preload" href="/data/json/meta.json" as="fetch" crossorigin="anonymous">`,
  `<link rel="preload" href="/data/${short}/json/dungeon_modules.json" as="fetch" crossorigin="anonymous">`,
];

// 增加
  `<link rel="preload" href="/data/${short}/json/index.json" as="fetch" crossorigin="anonymous">`,
  `<link rel="preload" href="/data/${short}/json/search_index.json" as="fetch" crossorigin="anonymous">`,
```

每个 SSG HTML 页面都使用同一个 `template`（`index.html`），全局 preload 注入一次，所有页面都受益。

### 3. 修改 `web/scripts/ssg.mjs`

在页面生成循环（~331-377 行）中按路由类型注入详情页特定的版本化 preload：

| 路由 | Preload URL |
|------|------------|
| `/dungeon_modules/:group/:name` | `/data/{short}/json/dungeon_modules_coords/{name}.json` + `/data/img/{name}.webp` |
| `/:page/:name` (items/monsters/props) | `/data/{short}/json/{page}/{name}.json` |
| `/lootdrops/:name` | `/data/{short}/json/lootdrops/{name}.json` |

每个详情页只 preload 自己需要的 1-2 个文件，不浪费带宽。

### 4. 修改所有客户端 fetch 调用

**Hooks（3 处）：**

| 文件 | URL 模式 | 改动 |
|------|---------|------|
| `hooks/useDungeonModules.ts` | `/data/{ver}/json/dungeon_modules.json` | 已版本化 ✅ |
| `hooks/useSearchIndex.ts` | `/data/json/search_index.json` | 加 `dataVersion` dep + `dataUrl()` |
| `hooks/useDataVersion.ts` | `/data/json/meta.json` | 不变（固定路径） |

**页面（~12 处）：** 所有 `fetch('/data/json/...')` 改为 `fetch(dataUrl(dataVersion, '/data/json/...'))`：

| 文件 | Fetch URL(s) |
|------|-------------|
| `DetailPage.tsx` | `/:page/:name.json`（模块级 preload + useEffect） |
| `DungeonModuleDetailPage.tsx` | `dungeon_modules_coords/{name}.json` |
| `ListPage.tsx` | `/:page.json` |
| `LootdropDetailPage.tsx` | `lootdrops/{name}.json` + ref 坐标 |
| `HomePage.tsx` | `index.json` |
| `ExplorePage.tsx` | `explore.json` |
| `QuestItemsPage.tsx` | `quest_items_groups.json` |
| `QuestItemGroupPage.tsx` | `quest_items_groups/{group}.json` |
| `QuestNPCPage.tsx` | `quest_npc.json` |
| `QuestNPCDetailPage.tsx` | `quest_npc.json` |

每个页面需要：
1. 从 `useDataVersion()` 获取 `dataVersion`
2. fetch URL 用 `dataUrl(dataVersion, path)` 包装
3. `useEffect` dep 包含 `dataVersion`，版本变化时自动用新版本化路径 refetch

### 5. 删除模块级 JS preload（替换为 SSG preload）

三个详情页有模块作用域的 `fetch()` 作预加载，改为 SSG `<link rel="preload">` 替代后可以删除：

| 文件 | 删除内容 |
|------|---------|
| `DungeonModuleDetailPage.tsx` | `_preloadedCoordsUrl` / `_preloadedCoords` 和相关逻辑 |
| `DetailPage.tsx` | `_preloadedEntityUrl` / `_preloadedEntity` 和相关逻辑 |
| `LootdropDetailPage.tsx` | `_preloadedLootdropUrl` / `_preloadedLootdrop` 和相关逻辑 |

### 6. 不动的资源

| 资源 | 路径 | 策略 |
|------|------|------|
| `meta.json` | `/data/json/meta.json` | 固定路径，SW 5 分钟 TTL，作版本检测 |
| 图片 | `/data/img/*` | 非版本化（很少变化），ETag 足够 |
| JS/CSS chunk | `/assets/*` | content-hash，SW 预缓存 |
| HTML | `/*.html` | SSG 产物，NetworkFirst |

## 注意事项

1. **版本号必须在调用 `dataUrl()` 前就绪。** `useDataVersion` 初始返回空字符串，`useEffect` 中 `if (!dataVersion) return;` 跳过——这是现有模式，所有 hooks 和页面已遵守。
2. **SSG preload 不能使用变量版本号。** preload 在构建时写入 HTML，版本号由 `VITE_DATA_VERSION` 决定，必须在 ssg.mjs 阶段确定。构建后的 HTML 中的 preload URL 是静态的。
3. **版本更新时，旧版本化 JSON 缓存自然淘汰。** SW 的 `StaleWhileRevalidate` + `maxEntries: 3300` 确保旧版本路径条目在新版本注入后逐渐被 LRU 驱逐。
4. **SSG 构建时全量复制 JSON（已有逻辑）。** `ssg.mjs:69` 的 `copyDeep(join(DIST, 'data', 'json'), vJsonDir)` 已将所有 JSON 复制到版本化目录，基础设施完备。
