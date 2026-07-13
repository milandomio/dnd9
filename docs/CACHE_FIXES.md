# 缓存机制修复记录 (2026-07-14)

## 背景

前端缓存审查发现 5 个问题，涉及数据版本通知、HTTP 缓存头、localStorage 泄漏、组件渲染性能、全局缓存版本一致性。

## 修复列表

### Fix 1: `location.reload()` 硬刷新 → 通知横幅

**问题：** `useDataVersion.ts` 检测到数据版本变化时执行 `location.reload()`，丢失用户输入、折叠面板、调试模式等 UI 状态。

**方案：** 新增 `useRefreshNotice()` hook，模块级 `refreshListeners` 集合。版本变化时设置 `_needsRefresh = true`，`AppInner` 订阅该状态，渲染顶部蓝色通知横幅"数据已更新，点击刷新页面"，手动点击才 reload。

**文件：**
- `web/src/hooks/useDataVersion.ts` — 新增 `useRefreshNotice` 导出
- `web/src/AppInner.tsx` — 横幅渲染，z-index 9999 置顶

### Fix 2: `_headers` 缺乏 JSON/图片/HTML 缓存规则

**问题：** `public/_headers` 仅覆盖 `/assets/*`（`max-age=31536000, immutable`），`/data/json/*`、`/data/img/*`、SSG HTML 页面无缓存控制。

**方案：** 新增缓存规则：

| 路径 | 策略 |
|------|------|
| `/assets/*` | `max-age=604800, immutable`（7 天，content-hash 保证变更即新 URL）|
| `/data/json/*` | `max-age=604800`（7 天）|
| `/data/img/*` | `max-age=604800`（7 天）|
| `/*.html` | `max-age=604800`（7 天）|

**文件：** `web/public/_headers`

### Fix 3: `quest_npc_*` localStorage 永不过期

**问题：** 用户勾选 NPC/任务/目标完成后，key 永久存储在 localStorage，游戏更新后产生悬挂数据。

**方案：** 在 `QuestNPCPage` 和 `QuestNPCDetailPage` 的 mount 阶段检查 `quest_npc_version`。版本不匹配时清除所有 `quest_npc_*` 前缀的键并写入新版本。

**文件：**
- `web/src/pages/QuestNPCPage.tsx`
- `web/src/pages/QuestNPCDetailPage.tsx`

### Fix 4: `MapPanel` 缺乏 `React.memo`

**问题：** `MapPanel` 是 Canvas 重渲染组件，每次父组件渲染（如坐标变化、模式切换）都触发 `dots.map(...)` 重建。

**方案：** 用 `React.memo` 包裹导出。

**文件：** `web/src/components/MapPanel.tsx`

### Fix 5: `_globalRefCache` 版本变化不清除

**问题：** 模块级 `_globalRefCache` 在 `LootdropDetailPage` 实例间共享，`dataVersion` 变化后仍返回旧数据。

**方案：** 新增 `_globalCacheVersion` 变量，`useEffect` 依赖 `dataVersion` 变化时 `clear()` 缓存。

**文件：** `web/src/pages/LootdropDetailPage.tsx`

## 验证

```bash
cd web && npm run build
kill $(lsof -t -i:8080) 2>/dev/null; sleep 0.5
nohup npx vite preview --port 8080 --host 0.0.0.0 &>/tmp/vite.log &
sleep 2 && curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/
```

构建通过、HTTP 200。

## 最终缓存架构

### 分层策略

| 层级 | 内容 | 策略 | 失效机制 |
|------|------|------|---------|
| **SW 预缓存** | JS/CSS chunk | Precache | content-hash 变化 → 新 URL |
| **SW 运行时** | HTML 导航 | NetworkFirst | 稳定键，离线回退缓存 |
| **SW 运行时** | `/data/json/*` | StaleWhileRevalidate | 稳定键，ETag 条件请求判断更新 |
| **SW 运行时** | `/data/img/*` | StaleWhileRevalidate | 同上（原 CacheFirst 已改为 SWR） |
| **CDN/HTTP** | `/assets/*` | `max-age=31536000, immutable` | content-hash |
| **CDN/HTTP** | `/data/json/*` | `no-cache` | 每次条件请求（ETag 304/200）|
| **CDN/HTTP** | `/data/img/*`, `/*.html` | 7 天 | 非 SW 场景兜底 |

### 离线兜底覆盖

| 资源 | 策略 | 离线可用 | 说明 |
|------|------|---------|------|
| JS/CSS | Precached | ✅ | 安装即永远可用 |
| HTML 页面 | NetworkFirst | ✅ | 访问过即缓存 |
| JSON 数据 | StaleWhileRevalidate | ✅ | 稳定缓存键 |
| 图片 | StaleWhileRevalidate | ✅ | 同上 |
| meta.json | 裸 fetch + `.catch(∅)` | ❌ | 刻意的 — 仅版本检测用，静默失败不影响其他 |

## 冗余分析：SW 接管后的 `dataVersion`

引入 SW 后，`useDataVersion()` 返回的 `dataDate` 在 `useEffect` dep 和模块缓存键中的角色变为冗余。SW 的 `StaleWhileRevalidate` 通过 HTTP ETag 条件请求自动感知数据更新，不需要手动控制的重 fetch。

### meta.json 字段依赖追踪

```
meta.json
├─ dataDate: string (unix timestamp)
│  └─ useDataVersion() hook
│     ├─ Disclaimer.tsx          → 格式化显示"地图生成日期"    ← 仍有用
│     ├─ useDungeonModules.ts    → useEffect dep + 缓存版本键  ← 冗余
│     ├─ useSearchIndex.ts       → useEffect dep + 缓存版本键  ← 冗余
│     ├─ DetailPage.tsx          → useEffect dep               ← 冗余
│     ├─ DungeonModuleDetailPage → useEffect dep               ← 冗余
│     ├─ ListPage.tsx            → useEffect dep               ← 冗余
│     ├─ QuestItemsPage.tsx      → useEffect dep               ← 冗余
│     ├─ QuestItemGroupPage.tsx  → useEffect dep               ← 冗余
│     ├─ LootdropDetailPage.tsx  → useEffect dep + 缓存版本键  ← 冗余
│     ├─ ExplorePage.tsx         → useEffect dep               ← 冗余
│     └─ HomePage.tsx            → 仅调用，不用于任何 dep       ← 可删
│
└─ seasonVersion: number
   └─ useSeasonVersion() hook
      ├─ QuestNPCPage.tsx        → localStorage 赛季清理       ← 仍有用
      └─ QuestNPCDetailPage.tsx  → localStorage 赛季清理       ← 仍有用
```

### 冗余详情

**1. `useEffect` dep 中的 `dataVersion`**
- 所有页面组件在 `useEffect` deps 中包含 `dataVersion`，意图是版本变化时重新 fetch
- 实际上：SW 后台自动更新缓存，页面刷新后组件重挂载即取最新数据
- `dataVersion` dep 的触发时机（meta.json 异步返回后）比 SW 缓存更新慢
- 去掉 dep 不影响功能，仅影响 React 层面的一条额外更新路径

**2. 模块级缓存版本键**
- `useDungeonModules.ts` 和 `useSearchIndex.ts` 用 `dataVersion` 做模块缓存 key
- 意图是版本变化时清缓存重新 fetch
- 实际上：SW 的稳定键 + StaleWhileRevalidate 自动处理，模块级缓存多余
- 影响：多一层缓存命中判断，逻辑正确但增加了代码复杂度

**3. `HomePage.tsx` 的无用调用**
- 仅 `const dataVersion = useDataVersion();` 不用于任何 dep 或条件判断
- `useDataVersion()` 内部触发模块级 fetch 已在 import 时由模块级 `if (typeof window !== 'undefined')` 块处理
- 可以删除而不影响任何功能

### 清理建议（暂未实施）

如果未来清理，步骤：
1. 删除所有 `[dataVersion]` useEffect dep（约 9 个文件），改为 `[]` 或保持现有 dep 不变
2. 删除 `useDungeonModules.ts` / `useSearchIndex.ts` 中的 `dataVersion` 缓存版本判断
3. 删除 `HomePage.tsx` 的 `const dataVersion = useDataVersion();`
4. 可选：删除 `_globalCacheVersion` 机制（LootdropDetailPage.tsx），因为 SW 自动处理
5. 保留 `Disclaimer.tsx` 的 `useDataVersion()` 调用用于日期显示
