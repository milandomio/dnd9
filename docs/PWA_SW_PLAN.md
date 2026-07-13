# Service Worker 集成计划

## 目标

为静态网站添加离线缓存和运行时网络策略，提升加载速度和离线可用性。

> **缓存策略**: SW 运行时缓存无时间过期（`refreshNow()` 版本变化时主动清除 `df5-*` 缓存）；CDN/HTTP 层 asset 永久、JSON 短缓存。

## 改动清单

### 1. 安装依赖

```bash
cd web && npm install vite-plugin-pwa
```

`vite-plugin-pwa` 会：
- 构建时自动生成 Service Worker 脚本（基于 Workbox）
- 通过 Vite HTML transform 注入注册代码到 index.html
- 生成 `manifest.json`

### 2. vite.config.ts 配置

在 client build plugin 列表中添加 `VitePWA` 插件：

```ts
VitePWA({
  registerType: 'autoUpdate',     // SW 更新后自动接管
  workbox: {
    // 不包含 index.html — 避免 Workbox 自动添加 NavigationRoute 覆盖 SSG 路由
    globPatterns: ['assets/**/*.{js,css}'],
    runtimeCaching: [
      // 版本变化由 refreshNow() 清除 df5-* 缓存，无需 maxAgeSeconds
      {
        urlPattern: /^\/data\/json\//,
        handler: 'StaleWhileRevalidate',
        options: { cacheName: 'df5-data-json', expiration: { maxEntries: 500 } },
      },
      // 地图图片：大文件，优先缓存
      {
        urlPattern: /^\/data\/img\//,
        handler: 'CacheFirst',
        options: { cacheName: 'df5-data-img', expiration: { maxEntries: 200 } },
      },
      // SSG HTML 页面：NetworkFirst（导航请求，不包含 .html 后缀）
      {
        urlPattern: ({ request }) => request.mode === 'navigate',
        handler: 'NetworkFirst',
        options: { cacheName: 'df5-html', expiration: { maxEntries: 200 } },
      },
    ],
  },
  manifest: {
    name: 'DarkFindV5',
    short_name: 'DarkFind',
    start_url: '/',
    display: 'standalone',
    background_color: '#141414',
    theme_color: '#1677ff',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
  },
})
```

### 3. 生成 PWA 图标

项目无现成 app 图标，需要生成最小 192×192 和 512×512 PNG。

方案 A：用 Canvas/ImageMagick 生成纯色带文字图标
方案 B：用项目内某张地图缩略图裁剪
方案 C：使用在线工具生成后放入 `web/public/icons/`

推荐方案 A（不依赖外部工具）：

```bash
cd web && mkdir -p public/icons
# 用 ImageMagick 生成纯色图标（服务器通常已安装）
convert -size 192x192 xc:'#1677ff' -font Sans -pointsize 72 \
  -fill white -gravity center -annotate +0+0 "DF" public/icons/icon-192.png
convert -size 512x512 xc:'#1677ff' -font Sans -pointsize 180 \
  -fill white -gravity center -annotate +0+0 "DF" public/icons/icon-512.png
```

### 4. 修改 main.tsx

需要在 `main.tsx` 中调用 `registerSW()` 注册 Service Worker。

`vite-plugin-pwa` 提供了两种方式：
- **auto**（推荐）：设置 `injectRegister: 'auto'`，插件自动在 index.html 插入注册脚本，`main.tsx` 无需修改
- **manual**：手动调用 `registerSW()` 获取更新控制

推荐 auto 模式，默认行为。

### 5. 更新 _headers

`public/_headers` 已为 `/assets/*` 设置缓存。SW 接管后浏览器缓存的优先级低于 SW，但保留 _headers 作为兜底。

### 6. 数据版本联动

`location.reload()` 已在 Fix 1 中替换为 `useRefreshNotice` 通知横幅（查看 `docs/CACHE_FIXES.md`）。引入 SW 后：

- SW 的 `autoUpdate` 模式（`registerType: 'autoUpdate'`）检测到新 SW → 自动安装并激活
- `refreshNow()` 清除所有 `df5-*` 前缀的 SW 缓存后执行 `location.reload()`，实现版本变化时全量刷新
- JSON 的 `?v=${dataVersion}` query param 确保跨版本的请求 URL 不同，SW 自然走网络

## 不需要改动的部分

| 文件 | 原因 |
|------|------|
| `ssg.mjs` | SW 不干预 SSG 构建流程 |
| `scripts/` | 无影响 |
| `api/` | 纯后端，无关 |
| 组件代码 | PWA 对 React 组件透明 |

## 验证方法

```bash
# 构建
cd web && npm run build

# 启动预览
npx vite preview --port 8080 --host 0.0.0.0

# 浏览器验证
# 1. DevTools → Application → Service Workers → 应有 SW 注册
# 2. DevTools → Application → Cache Storage → 应有 df5-data-json / df5-data-img / df5-html
# 3. 断网刷新 → 页面应正常加载
# 4. 重复访问 → Network 面板 /data/json/* 显示 (ServiceWorker)
```

## 回退方案

如果出现问题，回滚只需两步：

```bash
git revert <commit-hash>
cd web && npm uninstall vite-plugin-pwa
```
