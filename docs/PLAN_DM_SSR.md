# Dungeon Module SSR 改造方案

## 问题

`/dungeon_modules/`（列表页）和 `/dungeon_modules/:group/:name`（详情页）是纯 CSR Shell：HTML 中 `<div id="root">` 为空，无 `__SSR_DATA__`，用户需等 JS 全量下载→执行→fetch 才能看到内容。

其他页面类型（lootdrops/items/monsters/props/quest 等）均有 SSR 骨架渲染，用户几乎立即看到 UI。

## 修改清单

### 1. `web/scripts/ssg.mjs`

**a) `routeDataKey()` 新增详情页映射**

将 dungeon module 详情页从 `return ""`（无 SSR 数据）改为返回有意义的 data key，与 group 页区分为不同的命名空间。

**b) SSR 数据填充——详情页**

参照 lootdrop 详情页模式，为每个 dungeon module 注入 coords 数据：
- 完整模式：`{ module: DungeonModule, coords: ModuleCoordsData | null }`
- Quick 模式：`{ module: { name, translation }, coords: null }`

**c) SSR 数据填充——列表页**

参照 group 页的模式（`dungeon_modules/${group}`），注入预计算的 group summary 列表：
```js
ssrDataMap["dungeon_modules"] = groupsSummary;
```
数据结构：`[{ group, group_display, module_count }, ...]`

### 2. `web/src/pages/DungeonModuleDetailPage.tsx`

- 添加模块级预加载（`_preloadedCoords`），同 lootdrop 的 `_preloadedLootdrop` 急切 fetch 模式
- 添加 `useSSRData` 调用，guard 验证 `ssrData?.coords?.entities`
- `useState` 初始值改为 `_preloadedCoords ?? effectiveCoords ?? null`，`loading` 初始值相应调整
- `useEffect` 中若 SSR 数据已齐全则跳过 fetch
- `mod` 从 SSR 数据作 fallback（`modFromHook || modFromSsr`），避免 wait modules Map
- 保持所有 hooks 在条件 return 之前（水合规则）

### 3. `web/src/pages/DungeonModulesPage.tsx`

- 添加 `useSSRData("dungeon_modules")` 获取预计算的分组列表
- `useState` 初始值使用 SSR 数据
- `useEffect` 中若 SSR 数据已存在则跳过构建
- 移除对 `useDungeonModules` 的依赖（SSR 已含全部所需数据）

### 4. `docs/SESSION_CHANGES.md`

完成改造后追加变更摘要。

## 数据规模

| 指标 | 值 |
|------|-----|
| 详情页数量 | 260 |
| 列表页数量 | 1 |
| Coords 总大小 | 14MB（268 文件） |
| 最大单文件 | 262KB（ShipGraveyard_PiratePrison） |
| 构建时间增加 | ~5-10s（完整模式） |

## 验证

1. `cd web && npm run build` 通过
2. 检查 `/dungeon_modules/` HTML 含分组列表 SSR 内容
3. 检查 `/dungeon_modules/FireDeep/Firedeep_DwarvenGreatHall/` HTML 含 coords SSR 数据
4. `curl` 验证 HTTP 200
5. 浏览器验证首屏内容立即可见
