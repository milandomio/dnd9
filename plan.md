# DarkFindV5 SSG 改造计划

## 当前状态（2026-06-09）

### 已完成

1. **HashRouter → BrowserRouter** — 干净 URL，SEO 友好
2. **react-helmet-async** — 每个页面动态 title/description
3. **SSRDataContext** (`src/context/SSRDataContext.tsx`) — 构建时注入数据，客户端 hydration 回退到 useEffect fetch
4. **所有 7 个页面组件已改造** — 使用 `useSSRData()` 优先取构建时数据，等保底 fetch
5. **App.tsx 拆分** — `AppInner` 不含路由包裹器，SSR/Client 两套路由
6. **SSR 入口** (`src/ssr.tsx`) — renderToString + StaticRouter，含 antd/helmet/data 包裹层
7. **SSG 构建脚本** (`scripts/ssg.mjs`) — 读取 JSON → renderToString → 注入模板 → 输出 861 个 HTML
8. **Vite 配置** (`vite.config.ts`) — `mode=ssr` 时构建 SSR bundle，默认构建客户端 SPA

### 当前问题

SSG 构建能在 **16 秒**跑完 861 个页面，内容也渲染到了 HTML 里（`麦酒` 出现在 `items/Ale/index.html`），但 **所有页面的 `<title>` 都是默认值 `DarkFindV5游戏导航`**，而不是预期的动态标题（如 `麦酒 位置汇总 | DarkFindV5游戏导航`）。

根因：`react-helmet-async` 在 SSR 中没有正确捕获 Helmet 标签。

## 架构图

```
data/json/*.json
       │
       ▼
scripts/ssg.mjs
       │
       ├── 读取所有 JSON 构建 ssrDataMap
       ├── 执行 vite build（客户端 SPA）
       ├── 执行 vite build --mode ssr（SSR bundle）
       └── 遍历 861 路由：
               │
               ▼
           src/ssr.tsx (renderToString)
               │
               ├── antd ConfigProvider / ThemeProvider / DebugProvider
               ├── SSRDataContext.Provider (注入数据)
               ├── StaticRouter (React Router v6)
               └── AppInner (页面组件)
               │
               ▼
           注入到 dist/index.html 模板
               │
               ▼
           dist/{path}/index.html
```

## 下一步修复计划

### Step 1: 修复 Helmet 标签捕获

当前 `src/ssr.tsx` 中 `helmetContext` 未被正确填充。排查点：

**a) 检查 HelmetProvider 的 context 形状**
```ts
const helmetContext = {};
const html = renderToString(<HelmetProvider context={helmetContext}>...</HelmetProvider>);
console.log(helmetContext); // 应该包含 { helmet: { title, meta } }
```
如果 `helmetContext.helmet` 是 undefined，说明 HelmetProvider 没有写入 context。

**可能原因**：`react-helmet-async` v3+ 要求 `HelmetProvider` 的 `context` prop 必须是一个对象且有特定结构。尝试：
```ts
const helmetContext = { helmet: {} };
```
或者检查 react-helmet-async 版本是否需要 `HelmetProvider.renderStatic()` 方式。

**备选方案**：如果 Helmet 修复困难，可以在 SSG 脚本中直接根据路由注入静态标题（因为路由和标题的对应关系已知）。

**b) 验证 head 输出**
```js
// 在 ssg.mjs 中打印 result.head 看是否为空
console.log(`head for ${urlPath}:`, JSON.stringify(result.head));
```

### Step 2: 验证数据注入到 `window.__SSR_DATA__`

检查生成的 HTML 中 `__SSR_DATA__` 脚本是否存在且格式正确：
```bash
grep -o '__SSR_DATA__' dist/items/Ale/index.html
```

如果数据脚本注入正常，客户端 hydration 时 `useSSRData` 会读取它，跳过 fetch。

### Step 3: 检查 Ant Design SSR 错误

构建输出中出现 `LocaleProvider` / `MotionWrapper` 等 antd 内部组件的报错。虽然构建没崩溃（try/catch 兜底了），但这些错误会导致组件树部分渲染失败，页面内容不完整。

**根因**：antd v5 的 CSS-in-JS 使用 `@ant-design/cssinjs`，它内部调用了 `document.createElement` 等方法。虽然我们已经 stub 了 `document`，可能不够完整。

**修复方案**：在 `src/ssr.tsx` 的 global stub 中补充 antd 需要的更多方法：
```ts
globalThis.document = {
  ...documentStub,
  createElement: (tag) => {
    if (tag === 'style') return { sheet: { cssRules: [], insertRule: () => {} }, appendChild: () => {} };
    if (tag === 'div') return { className: '', setAttribute: () => {}, appendChild: () => {} };
    return { className: '', setAttribute: () => {}, appendChild: () => {} };
  },
  // 更多…
};
```

更彻底的方案：使用 `@ant-design/cssinjs` 的 SSR 模式——用 `StyleProvider` + `extractStyle` 提取 CSS，但因为项目不大，stub 可能就够了。

### Step 4: 更新构建流程

修复完成后更新：

- **`package.json`**：用 `node scripts/ssg.mjs` 替代旧的 prerender 命令
- **`.github/workflows/deploy.yml`**：去掉 Playwright 安装步骤（不再需要）

### Step 5: 清理

- 删除 `web/scripts/prerender.mjs`（旧 Playwright 脚本）
- 卸载 `playwright` 依赖
- 删除 `web/src/context/` 下旧的数据上下文（如果有）
- 删除 `.github/workflows/deploy.yml` 中的 Playwright 步骤

## 回退方案

如果 SSR + renderToString 路线持续遇到 antd 兼容性问题，回退到 Playwright 方案（只预渲染 8 个顶级页面，详情页走 SPA 兜底）。Playwright 方案已在 commit `d837fa2` 验证可用。

## 关键文件清单

| 文件 | 用途 |
|------|------|
| `web/src/ssr.tsx` | SSR 入口，renderToString |
| `web/src/context/SSRDataContext.tsx` | 数据上下文 + useSSRData hook |
| `web/src/App.tsx` | AppInner（无路由器）+ App（含 BrowserRouter） |
| `web/scripts/ssg.mjs` | SSG 构建脚本 |
| `web/vite.config.ts` | Vite 双模式配置（client / ssr） |
| `.github/workflows/deploy.yml` | CI 部署 |
| `web/package.json` | 构建脚本 |
