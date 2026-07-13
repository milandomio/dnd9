# Service Worker 集成计划

## 目标

为静态网站添加离线缓存和运行时网络策略，提升加载速度和离线可用性。

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
    globPatterns: ['**/*.{js,css,webp,png}'],
    runtimeCaching: [
      // JSON 数据：版本变化时取新
      {
        urlPattern: /^\/data\/json\//,
        handler: 'StaleWhileRevalidate',
        options: {
          cacheName: 'df5-data-json',
          expiration: { maxEntries: 500, maxAgeSeconds: 86400 * 7 },
        },
      },
      // 地图图片：大文件，优先缓存
      {
        urlPattern: /^\/data\/img\//,
        handler: 'CacheFirst',
        options: {
          cacheName: 'df5-data-img',
          expiration: { maxEntries: 200, maxAgeSeconds: 86400 * 30 },
        },
      },
      // SSG HTML 页面：保证新内容
      {
        urlPattern: /\.html$/,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'df5-html',
          expiration: { maxEntries: 100, maxAgeSeconds: 86400 },
        },
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

当前 `useDataVersion.ts` 通过 `location.reload()` 处理数据版本变化。引入 SW 后需要调整：

SW 注册 `autoUpdate` 模式（`registerType: 'autoUpdate'`）：
- SW 检测到新版本 → 自动安装并激活
- 旧 SW 控制的页面会被新 SW 接管
- `StaleWhileRevalidate` 策略会自动拉取最新 JSON

可以移除 `location.reload()`，改为 SW 的 `update` 事件触发提示。

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
