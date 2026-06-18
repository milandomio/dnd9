# Hydration Error #310 修复记录

## 问题现象

- `/lootdrops/KrisDagger/`、`/lootdrops/Mitre/` 等详情页报 `Minified React error #310`
- 页面空白，F5 刷新也无法显示

## 根因

React #310 = **"Rendered more hooks than during the previous render"**

`LootdropDetailPage` 中有一个 `useMemo` 放在了 `if (!data)` 提前返回**之后**：

```tsx
// ❌ 错误结构
useEffect(() => { ... }, []);      // hook #N
useCallback(() => { ... }, []);    // hook #N+1

if (!data) return <Loading />;     // 提前返回

const orderedMonsters = useMemo(   // hook #N+2 — 只在 data 有值时调用
  () => [...monsters].sort(...), [monsters]
);
```

- 首次渲染（SSR / hydration）：`data` 为 null → 提前返回 → hooks 数量 = N
- fetch 完成后：`data` 有值 → 继续渲染 → hooks 数量 = N+1
- React 检测到 hook 数量变化 → 抛出 #310

## 修复

将 `useMemo` 移到 `if (!data)` 之前，确保 hook 数量恒定：

```tsx
// ✅ 正确结构
useEffect(() => { ... }, []);      // hook #N
useCallback(() => { ... }, []);    // hook #N+1

const monsters = data?.monsters ?? [];
const orderedMonsters = useMemo(   // hook #N+2 — 始终调用
  () => [...monsters].sort(...), [monsters]
);

if (!data) return <Loading />;     // 提前返回
```

## 额外修复：组件树一致性

SSR 和客户端的组件树必须完全一致，否则 hydration 时 fiber 树 hook 链表也会错位。

### SSR (`ssr.tsx`)
```
HelmetProvider → ThemeProvider → ConfigProvider → DebugProvider
  → SSRDataContext.Provider → StaticRouter → AppInner
```

### 客户端 (`App.tsx`) — 必须匹配
```
HelmetProvider → ThemeProvider → ConfigProvider → DebugProvider
  → SSRDataContext.Provider → BrowserRouter → AppInner
```

已修复的问题：
1. 移除 `AntdConfigProvider` 包装函数（额外 fiber 节点）
2. 添加 `SSRDataContext.Provider value={null}`（SSR 有 context，客户端也要有）
3. 移除 `App` 组件中的 `useTheme()` hook（在 `ThemeProvider` 外部调用，破坏 hook 一致性）

## SSR 数据不完整（Quick 模式）

Quick 模式只注入 `{ name, translation }`，缺少 `monsters` 等字段。

修复：`useState` 初始化时检查数据完整性：

```tsx
const [data, setData] = useState<LootdropItem | null>(
  ssrData?.item?.monsters ? ssrData.item : null
);
```

## 关键规则

1. **Hook 必须在条件返回之前** — 所有 `useState`/`useEffect`/`useMemo`/`useCallback` 必须在任何 `if (...) return` 之前
2. **SSR 和客户端组件树必须一致** — Provider 层数、顺序、类型必须完全匹配
3. **Quick 模式下 SSR 数据不完整** — 初始化时必须验证必要字段存在
