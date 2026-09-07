# 缓存机制修复记录 (2026-07-14)

## 背景

前端缓存审查发现多个问题，涉及数据版本通知、HTTP 缓存头、localStorage 泄漏、组件渲染性能、全局缓存版本一致性、SW 路由冲突、PWA 基础设施预缓存。

## 修复列表

### Fix 1: `location.reload()` 硬刷新 → 移除横幅，SW 自动接管

**问题：** `useDataVersion.ts` 检测到数据版本变化时执行 `location.reload()`，丢失用户输入、折叠面板、调试模式等 UI 状态。

**方案（已回退）：** 曾新增 `useRefreshNotice()` hook 和横幅组件，后因 SW 集成而移除。SW 的 StaleWhileRevalidate 自动管理数据缓存，不再需要用户手动刷新。

**当前状态：** `useRefreshNotice` hook 及相关死代码已删除，`meta.json` 通过 SW 运行时缓存（`df5-meta`，5 分钟 TTL）提供服务。

### Fix 2: `_headers` 缺乏 JSON/图片/HTML 缓存规则

**问题：** `public/_headers` 仅覆盖 `/assets/*`（`max-age=31536000, immutable`），`/data/json/*`、`/data/img/*`、SSG HTML 页面无缓存控制。

**方案：** 新增缓存规则（与 SW 策略配合，非 SW 环境兜底）：

| 路径 | 策略 | 说明 |
|------|------|------|
| `/assets/*` | `max-age=31536000, immutable` | 365 天，content-hash 保证变更即新 URL |
| `/data/json/*` | `no-cache` | 每次 ETag 条件请求，SW 层 StaleWhileRevalidate 缓存 |
| `/data/img/*` | `max-age=604800` | 7 天 |
| `/*.html` | `max-age=604800` | 7 天 |

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

### Fix 6: `navigateFallback` 覆盖 NetworkFirst 路由

**问题：** `navigateFallback: 'index.html'` 生成的 `NavigationRoute` 在 `NetworkFirst` 之前注册，拦截所有导航请求返回 precached `index.html`（无 SSR 数据），SSG 页面 HTML 永不缓存。

**方案：** 移除 `navigateFallback`，让 `NetworkFirst` 正常接管 SSG 路由。访问过的页面离线可正常显示（含 SSR 数据）。

**文件：** `web/vite.config.ts`

### Fix 7: `registerSW.js` 未预缓存

**问题：** SW 注册脚本 `registerSW.js` 仅由 HTML 的 `<script>` 标签加载，SW 不拦截自身加载请求（SW 在其安装期才生效），离线首次访问时注册脚本加载失败 → SW 根本不注册。

**方案：** 将 `registerSW.js` 加入 `globPatterns` 预缓存清单。`manifest.webmanifest` 和 `icons/*` 由 `vite-plugin-pwa` 自动处理，不重复声明。

**文件：** `web/vite.config.ts`

### Fix 8: 清理 SW 相关死代码

**问题：** SW 集成后，以下代码变为遗留死代码：
- `useDataVersion.ts` 中的 `useRefreshNotice` hook（横幅已移除）
- 5 个页面的 `if (!dataVersion) return;` 守卫（meta.json 已进 SW 缓存，守卫多余）
- `SWUpdateBanner.tsx` 中的 `waiting` 事件监听（`autoUpdate` + `self.skipWaiting()` 下永不触发）

**方案：**
- 删除 `useRefreshNotice` hook 及相关模块变量（`_needsRefresh`、`refreshListeners`、`notifyRefresh`）
- 删除 5 个页面的 `!dataVersion` 守卫
- 简化 `SWUpdateBanner`：移除 `needRefresh`/`handleRefresh`，仅保留首次安装"离线模式已就绪"提示（5 秒自动消失）

**文件：**
- `web/src/hooks/useDataVersion.ts`
- `web/src/pages/ExplorePage.tsx`
- `web/src/pages/DungeonModuleDetailPage.tsx`
- `web/src/pages/QuestItemsPage.tsx`
- `web/src/pages/QuestItemGroupPage.tsx`
- `web/src/pages/QuestNPCPage.tsx`
- `web/src/components/SWUpdateBanner.tsx`

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
| **SW 预缓存** | JS/CSS chunk + `registerSW.js` | Precache | content-hash 变化 → 新 URL |
| **SW 运行时** | HTML 导航 | NetworkFirst | 访问后稳定缓存（无 navigateFallback 覆盖） |
| **SW 运行时** | `/meta.json` | StaleWhileRevalidate | 5 分钟 TTL |
| **SW 运行时** | `/data/json/*` | StaleWhileRevalidate | 稳定键，ETag 条件请求判断更新 |
| **SW 运行时** | `/data/img/*` | StaleWhileRevalidate | 同上 |
| **CDN/HTTP** | `/assets/*` | `max-age=31536000, immutable` | content-hash |
| **CDN/HTTP** | `/data/json/*` | `no-cache` | 每次条件请求（ETag 304/200）|
| **CDN/HTTP** | `/data/img/*`, `/*.html` | 7 天 | 非 SW 场景兜底 |

### 离线兜底覆盖

| 资源 | 策略 | 离线可用 | 说明 |
|------|------|---------|------|
| JS/CSS | Precached | ✅ | 安装即永远可用 |
| `registerSW.js` | Precached | ✅ | 确保 SW 注册脚本离线可用 |
| HTML 页面 | NetworkFirst | ✅ | 访问过即缓存（含 SSR 数据）|
| JSON 数据 | StaleWhileRevalidate | ✅ | 稳定缓存键 |
| 图片 | StaleWhileRevalidate | ✅ | 同上 |
| meta.json | StaleWhileRevalidate (5min) | ✅ | 版本检测 + 离线日期显示 |
| 未访问 SSG 页面 | — | ❌ | 首次离线深度链接无缓存时报错 |

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

### 已实施的清理

1. ✅ 删除 `useRefreshNotice` 死代码及横幅相关逻辑（SW 接管了版本管理）
2. ✅ 删除 5 个页面的 `!dataVersion` 守卫（ExplorePage, DungeonModuleDetailPage, QuestItemsPage, QuestItemGroupPage, QuestNPCPage）
3. ✅ 删除 `HomePage.tsx` 的 `dataVersion` 调用
4. ✅ 删除 `QuestItemGroupPage.tsx` 的 `dataVersion` 依赖

### 剩余可清理（低优先）

如果未来清理：
1. 删除 `[dataVersion]` useEffect dep（约 7 个文件，不影响功能但增加代码复杂度）
2. 删除 `useDungeonModules.ts` / `useSearchIndex.ts` 中的 `dataVersion` 缓存版本判断
3. 可选：删除 `_globalCacheVersion` 机制（LootdropDetailPage.tsx），SW 自动处理
