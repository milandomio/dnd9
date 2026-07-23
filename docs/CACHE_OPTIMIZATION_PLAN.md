# 缓存优化计划

> **目标**：全量 JSON 版本化 + SW 缓存优先 + preload 消除 LCP 瓶颈

## 现状问题

| 问题                                     | 说明                                                      |
| ---------------------------------------- | --------------------------------------------------------- |
| 仅 `dungeon_modules.json` 使用版本化路径 | 其余 12+ 个 fetch 仍用非版本化 `/data/json/...`           |
| SW 规则不兼容版本化路径                  | `startsWith('/data/json/')` 不匹配 `/data/{ver}/json/...` |
| 详情页无 preload                         | LCP P99=17.86s，主要瓶颈在 coord JSON 和图片未预下载      |

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
  return path.replace("/data/json", `/data/${short}/json`);
}
```

### ✅ 2. 修改 `web/vite.config.ts` (已实施)

**SW 路由规则** — df5-data-json 的 urlPattern：

```ts
// 兼容版本化和非版本化路径
urlPattern: ({ url }) => /^\/data\/(?:[a-z0-9]+\/)?json\//.test(url.pathname),
```

### ✅ 2b. 全局 preload 增加 index.json + search_index.json（已实施）

```ts
  `<link rel="preload" href="/data/${short}/json/index.json" as="fetch" crossorigin="anonymous">`,
  `<link rel="preload" href="/data/${short}/json/search_index.json" as="fetch" crossorigin="anonymous">`,
```

### ✅ 3. 修改 `web/scripts/ssg.mjs` 详情页 preload 注入（已实施）

在页面生成循环中按路由类型注入详情页特定的版本化 preload：

| 路由                                  | Preload URL                                                                       |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| `/dungeon_modules/:group/:name`       | `/data/{short}/json/dungeon_modules_coords/{name}.json` + `/data/img/{name}.webp` |
| `/:page/:name` (items/monsters/props) | `/data/{short}/json/{page}/{name}.json`                                           |
| `/lootdrops/:name`                    | `/data/{short}/json/lootdrops/{name}.json`                                        |

### ✅ 4. 修改所有客户端 fetch 调用（已实施）

| 文件                         | URL 模式                                | 状态              |
| ---------------------------- | --------------------------------------- | ----------------- |
| `hooks/useDungeonModules.ts` | `/data/{ver}/json/dungeon_modules.json` | 无需改 ✅         |
| `hooks/useSearchIndex.ts`    | `/data/json/search_index.json`          | `dataUrl()` 完成 |
| `hooks/useDataVersion.ts`    | `/data/json/meta.json`                  | 不变（固定路径）  |
| `DetailPage.tsx`              | `/:page/:name.json`                     | `dataUrl()` 完成 |
| `DungeonModuleDetailPage.tsx` | `dungeon_modules_coords/{name}.json`    | `dataUrl()` 完成 |
| `ListPage.tsx`                | `/:page.json`                           | `dataUrl()` 完成 |
| `LootdropDetailPage.tsx`      | `lootdrops/{name}.json` + ref 坐标      | `dataUrl()` 完成 |
| `HomePage.tsx`                | `index.json`                            | `dataUrl()` 完成 |
| `ExplorePage.tsx`             | `explore.json`                          | `dataUrl()` 完成 |
| `QuestItemsPage.tsx`          | `quest_items_groups.json`               | `dataUrl()` 完成 |
| `QuestItemGroupPage.tsx`      | `quest_items_groups/{group}.json`       | `dataUrl()` 完成 |
| `QuestNPCPage.tsx`            | `quest_npc.json`                        | `dataUrl()` 完成 |
| `QuestNPCDetailPage.tsx`      | `quest_npc.json`                        | `dataUrl()` 完成 |

所有页面已完成 `dataUrl(dataVersion, path)` 包装 + `dataVersion` useEffect dep。

### ✅ 5. 删除模块级 JS preload（已实施 — 替换为 SSG preload）

三个详情页的模块级 preload 已全部移除，由 SSG `<link rel="preload">` 替代。

### 6. 不动的资源

| 资源         | 路径                   | 策略                                |
| ------------ | ---------------------- | ----------------------------------- |
| `meta.json`  | `/data/json/meta.json` | 固定路径，SW 5 分钟 TTL，作版本检测 |
| 图片         | `/data/img/*`          | 非版本化（很少变化），ETag 足够     |
| JS/CSS chunk | `/assets/*`            | content-hash，SW 预缓存             |
| HTML         | `/*.html`              | SSG 产物，NetworkFirst              |

## 注意事项

1. **版本号必须在调用 `dataUrl()` 前就绪。** `useDataVersion` 初始返回空字符串，`useEffect` 中 `if (!dataVersion) return;` 跳过——这是现有模式，所有 hooks 和页面已遵守。
2. **SSG preload 不能使用变量版本号。** preload 在构建时写入 HTML，版本号由 `VITE_DATA_VERSION` 决定，必须在 ssg.mjs 阶段确定。构建后的 HTML 中的 preload URL 是静态的。
3. **版本更新时，旧版本化 JSON 缓存自然淘汰。** SW 的 `StaleWhileRevalidate` + `maxEntries: 3300` 确保旧版本路径条目在新版本注入后逐渐被 LRU 驱逐。
4. **SSG 构建时全量复制 JSON（已有逻辑）。** `ssg.mjs:69` 的 `copyDeep(join(DIST, 'data', 'json'), vJsonDir)` 已将所有 JSON 复制到版本化目录，基础设施完备。
