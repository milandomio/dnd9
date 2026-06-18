# Hydration / Error #310 调试记录

## 问题现象

- `/lootdrops/KrisDagger/` — 报 `Minified React error #310`，页面空白
- `/items/Bandage/` — 正常显示
- F5 刷新详情页可正常显示（SSR HTML 正确，hydrate 后内容出现）
- 清除 `root.innerHTML` 后 `createRoot` 渲染正常（说明 React 能正确渲染，问题出在 hydrate 过程）

## 环境

- React 18.3.1 (`react: ^18.3.0`)
- Ant Design 5.29.3
- Vite 6 + vite preview

## 已尝试的修复

| 方案 | 结果 |
|------|------|
| `React.lazy` → 同步 `import` | ❌ 仍然报错 |
| 移除 `Suspense`/`PageLoader` | ❌ 仍然报错 |
| `createRoot` → `hydrateRoot` | ❌ 仍然报错 |
| 移除 `React.StrictMode` | ❌ 未验证（prod build StrictMode 是 noop） |
| `root.innerHTML = ''` + `createRoot` | ✅ 不报错，页面正常（但丢失 SSR） |

## 错误 #310 定位

`Error(p(310))` 在 **react-dom 生产包** `react-dom.production.min.js` 的 `Uh` 函数中：

```js
function Uh() {
  if (null === N) {
    var a = M.alternate;
    a = null !== a ? a.memoizedState : null;
  } else a = N.next;
  var b = null === O ? M.memoizedState : O.next;
  if (null !== b) O = b, N = a;
  else {
    if (null === a) throw Error(p(310));  // ← #310
    N = a;
    a = { memoizedState: N.memoizedState, ... };
    null === O ? M.memoizedState = O = a : O = O.next = a;
  }
  return O;
}
```

React 开发版的对应错误消息：

> **Rendered more hooks than during the previous render.**

所以 #310 不是 hydration DOM 不匹配，而是 **hook 数量不一致**——组件在 hydrate 过程中，当前 fiber tree 和 work-in-progress fiber tree 的 hook 链表数量不匹配。

## 关键线索

1. `/items/Bandage/`（`/:page/:name` → **`DetailPage`**）正常
2. `/lootdrops/KrisDagger/`（`/lootdrops/:name` → **`LootdropDetailPage`**）报错
3. 两个组件同步 import，row/lifecycle 顺序应一致
4. 清除 root 内容后直接 render（跳过 hydrate）正常 → **问题一定在 hydrate 过程**

## 可能原因

### 1. `AppInner.tsx`（SSR 用）与 `App.tsx`（客户端用）route 顺序不同

**SSR** (`AppInner.tsx`):
```
<Route path="/:page" .../>        ← 在第 0 位
<Route path="/lootdrops/:name" .../>
```

**客户端** (`App.tsx`):
```
<Route path="/lootdrops/:name" .../>  ← 在第 0 位
<Route path="/:page" .../>
```

虽然对于 URL `/lootdrops/KrisDagger` 两个都匹配 `/lootdrops/:name` 组件，但 React Router 内部 `useRoutes` 处理的 route config 数组顺序不同。如果 React Router 内部用了某个基于 route index 的 hook/state 判定，hook 序列可能变化。

### 2. Ant Design 的 ConfigProvider 在 SSR vs Client 的包裹方式不同

**SSR**（`ssr.tsx`）:
```
<ConfigProvider locale={zhCN} ...>
  <DebugProvider>
    <SSRDataContext.Provider>
      <StaticRouter>
        <AppInner />
```

**客户端**（`App.tsx`）:
```
<AntdConfigProvider>  → 内部 <ConfigProvider>
  <DebugProvider>
    <BrowserRouter>
      <AppRoutes />
```

`AntdConfigProvider` 是多余的函数组件层，虽然 render 出一样的 ConfigProvider，但 fiber 树多了一个组件节点。hydrate 时 React 会对比 SSR fiber（没有 AntdConfigProvider）和 client fiber（有 AntdConfigProvider），hook 链表错位。

### 3. `window.__SSR_DATA__` 在不同 route 的 key 格式不同

- `/items/Bandage` → `dataKey = "items/Bandage"`
- `/lootdrops/KrisDagger` → `dataKey = "lootdrops/KrisDagger"`

`useSSRData` hook 在 SSR 期间读到数据（通过 SSRDataContext），在客户端 hydrate 时未提供 SSRDataContext → 回退到 `window.__SSR_DATA__`。

如果 SSR 有 SSRDataContext 而客户端没有，context 使用方式不同可能影响 hook 数。

## 下一步

1. 验证 `AppInner` 与 `AppRoutes` 是否在路由顺序上导致`<Routes>` 内部 hook 数变化
2. 尝试去掉 `AntdConfigProvider` 封装，改成直接在 `App()` 中嵌入 `<ConfigProvider>` 消除 fiber 树差异
3. 尝试在 `App()` 中嵌入 `<SSRDataContext.Provider>`（值为空），使 SSR 和 client 的 context 层级一致
